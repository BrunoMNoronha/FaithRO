"""Read installed MVP declarations; no SQL, game clients, writes or combats.

Run over SSH with python3 -B -. Rates are conditional checks, never casts/second.
This deliberately refuses SQL monster databases and global monster skill entries.
"""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

TARGETS = (1086, 1039, 1751, 1832)


def config_values(root, relative, wanted, stack=()):
    """Follow config imports in order; expose only explicitly requested keys."""
    assert relative not in stack, 'Cyclic config import'
    values = {}
    path = root / relative
    for number, line in enumerate(path.read_text().splitlines(), 1):
        line = line.split('//', 1)[0].strip()
        if ':' not in line:
            continue
        key, value = (part.strip() for part in line.split(':', 1))
        if key == 'import':
            values.update(config_values(root, value, wanted, (*stack, relative)))
        elif key in wanted:
            values[key] = {'value': value, 'source': relative, 'line': number}
    return values


def skill_rows(text, source, rate=100, delay=100, max_level=100):
    rows = []
    for number, line in enumerate(text.splitlines(), 1):
        line = line.split('//', 1)[0].strip()
        if not line:
            continue
        cells = [c.strip() for c in line.split(',')]
        assert len(cells) == 19, f'Unexpected skill row {source}:{number}'
        mob_id = int(cells[0])
        assert mob_id >= 0, 'Global monster skills require a separate runtime review'
        if mob_id not in TARGETS:
            continue
        if cells[1] == 'clear':
            rows.append({'monster_id': mob_id, 'clear': True})
            continue
        scaled = int(cells[5]) * rate // 100
        effective_rate = min(10000, scaled) if scaled else int(rate != 0)
        rows.append({
            'monster_id': mob_id, 'source': source, 'line': number,
            'label': cells[1], 'state': cells[2], 'skill_id': int(cells[3]),
            'database_level': int(cells[4]),
            'effective_level': min(max(1, int(cells[4])), max_level),
            'conditional_chance_per_10000': effective_rate,
            'cast_ms': int(cells[6]), 'recast_delay_ms': int(cells[7]) * delay // 100,
            'cancelable': cells[8] == 'yes' or cells[8] == '1',
            'target': cells[9], 'condition': cells[10],
            'condition_value': cells[11], 'values': cells[12:17],
        })
    return rows


def merge_rows(groups):
    result = {target: [] for target in TARGETS}
    for group in groups:
        for row in group:
            if row.get('clear'):
                result[row['monster_id']].clear()
            else:
                result[row['monster_id']].append(row)
    return result


def main():
    sys.dont_write_bytecode = True
    root = Path('/home/rathena/rathena')
    assert sys.platform == 'linux' and root.is_dir(), 'Installed Linux source required; no action taken'
    battle = config_values(root, 'conf/battle_athena.conf',
                           {'mob_skill_rate', 'mob_skill_delay', 'mob_max_skilllvl'})
    inter = config_values(root, 'conf/inter_athena.conf', {'use_sql_db'})
    assert inter.get('use_sql_db', {'value': '0'})['value'].lower() in ('0', 'no', 'off', 'false')
    rate = int(battle['mob_skill_rate']['value'])
    delay = int(battle['mob_skill_delay']['value'])
    assert rate > 0 and delay >= 0, 'Disabled skills or invalid delay require separate review'
    skill_hpp = (root / 'src/map/skill.hpp').read_text()
    maximum = int(re.search(r'#define MAX_MOBSKILL_LEVEL\s+(\d+)', skill_hpp)[1])
    max_level = int(battle.get('mob_max_skilllvl', {'value': str(maximum)})['value'])
    assert 1 <= max_level <= maximum
    spec = importlib.util.spec_from_file_location('gamedb', '/root/faithro/deploy/web/tools/build_gamedb.py')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    body = lambda rel: builder.collect_body(root, rel)
    mobs = builder.merge_by_id(body('db/pre-re/mob_db.yml') + body('db/import/mob_db.yml'))
    skills = builder.merge_by_id(body('db/pre-re/skill_db.yml') + body('db/import/skill_db.yml'))
    paths = ['db/pre-re/mob_skill_db.txt', 'db/import/mob_skill_db.txt']
    merged = merge_rows([skill_rows((root / p).read_text(), p, rate, delay, max_level) for p in paths])
    spawns = builder.build_spawns(root)
    targets = []
    for target in TARGETS:
        monster = mobs[target]
        rows = merged[target]
        for row in rows:
            row['skill_name'] = skills[row['skill_id']]['Name']
        targets.append({
            'monster_id': target, 'name': monster['Name'], 'aegis': monster['AegisName'],
            'hp': monster['Hp'], 'element': monster['Element'], 'element_level': monster['ElementLevel'],
            'damage_delivered_per_second_floor_at_600s_no_heal': round(monster['Hp'] / 600, 3),
            'active_static_spawns': [s for s in spawns if s['mob_id'] == target],
            'skill_declarations': rows,
        })
    paths += ['db/pre-re/mob_db.yml', 'db/import/mob_db.yml', 'src/map/mob.cpp', 'src/map/unit.cpp', 'src/map/skill.hpp',
              'db/pre-re/skill_db.yml', 'db/import/skill_db.yml', 'conf/import/battle_conf.txt']
    print(json.dumps({
        'timestamp_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status': 'installed_declarations_and_calculations_not_combat_results',
        'battle_settings': battle, 'default_max_monster_skill_level': maximum,
        'attackpcge_semantics': 'mob.cpp uses unit_counttargeted(md) >= condition_value; unit.cpp returns ud->target_count. Party size alone does not prove this trigger.',
        'targets': targets, 'source_sha256': {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in paths},
        'production_mutations': False, 'sql_queries': 0, 'combats_executed': 0,
        'limitations': [
            'Conditional chance is per eligible AI check; it is not casts per second.',
            'Rows with different attack/chase states are not independent simultaneous casts.',
            'HP/600 is a damage-delivered floor without healing, misses, mitigation, travel, summons or downtime.',
            'Static declarations do not prove a boss is alive or available; scripted spawns are excluded.',
            'Source reads do not authenticate the running binary or measure live skill behavior.',
        ],
    }, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
