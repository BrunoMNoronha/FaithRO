"""Read selected installed skill requirements and literal shop offers. No SQL/writes."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

WANTED = {'AC_DOUBLE', 'SN_SHARPSHOOTING', 'ASC_EDP', 'MG_SAFETYWALL',
          'SA_LANDPROTECTOR', 'SA_DISPELL', 'PF_SPIDERWEB', 'ALL_RESURRECTION',
          'PF_SOULCHANGE', 'PF_FOGWALL', 'AL_HEAL', 'AL_BLESSING', 'AL_INCAGI',
          'PR_MAGNIFICAT', 'HP_ASSUMPTIO'}


def arrow_setting(root, relative, stack=()):
    assert relative not in stack
    result = None
    for number, line in enumerate((root / relative).read_text().splitlines(), 1):
        line = line.split('//', 1)[0].strip()
        if ':' not in line:
            continue
        key, value = (x.strip() for x in line.split(':', 1))
        if key == 'import':
            result = arrow_setting(root, value, (*stack, relative)) or result
        elif key == 'arrow_decrement':
            result = {'value': int(value), 'source': relative, 'line': number}
    return result


def main():
    sys.dont_write_bytecode = True
    root = Path('/home/rathena/rathena')
    assert sys.platform == 'linux' and root.is_dir(), 'Installed Linux source required; no action taken'
    spec = importlib.util.spec_from_file_location('gamedb', '/root/faithro/deploy/web/tools/build_gamedb.py')
    builder = importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)
    body = lambda rel: builder.collect_body(root, rel)
    all_skills = builder.merge_by_id(body('db/pre-re/skill_db.yml') + body('db/import/skill_db.yml'))
    skills = {e['Name']: {key: e[key] for key in ['Id', 'MaxLevel', 'Requires', 'HitCount', 'Duration1'] if key in e}
              for e in all_skills.values() if e['Name'] in WANTED}
    assert set(skills) == WANTED
    items = builder.merge_by_id(body('db/pre-re/item_db.yml') + body('db/import/item_db.yml'))
    ids = {e['AegisName']: item for item, e in items.items()}
    wanted_items = {1750, 501, 504, 505}
    for skill in skills.values():
        for cost in skill.get('Requires', {}).get('ItemCost', []):
            cost['ItemId'] = ids[cost['Item']]; wanted_items.add(cost['ItemId'])
    offers = []
    for path, content in builder.npc_sources(root, ('npc/pre-re/scripts_main.conf',)).items():
        if content is None:
            continue
        for number, line in enumerate(content.decode(errors='replace').splitlines(), 1):
            line = line.split('//', 1)[0]
            if '\tshop\t' not in line:
                continue
            for item, price in re.findall(r'(\d+):(-?\d+)', line.split('\t')[-1]):
                item, price = int(item), int(price)
                if item in wanted_items:
                    offers.append({'item_id': item, 'price': items[item].get('Buy', 0) if price < 0 else price,
                                   'source': path, 'line': number})
    prices = {item: {'name': items[item]['Name'],
                     'min_literal_shop_price': min((row['price'] for row in offers if row['item_id'] == item), default=None)}
              for item in sorted(wanted_items)}
    paths = ['db/pre-re/skill_db.yml', 'db/import/skill_db.yml', 'db/pre-re/item_db.yml',
             'db/import/item_db.yml', 'src/map/skill.cpp', 'src/map/battle.cpp', 'conf/import/battle_conf.txt']
    arrow = arrow_setting(root, 'conf/battle_athena.conf')
    assert arrow is not None
    paths += ['conf/battle_athena.conf', arrow['source']]
    print(json.dumps({'timestamp_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      'skills': skills, 'items': prices, 'literal_shop_offers': offers,
                      'arrow_decrement': arrow,
                      'source_sha256': {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in paths},
                      'production_mutations': False, 'sql_queries': 0, 'combats_executed': 0,
                      'limitations': ['Database base requirements; runtime modifiers/exemptions remain separate.',
                                      'Literal NPC prices before discounts; shop access is not exercised by this collector.',
                                      'HitCount is not ammunition quantity or count of resource-charge events.']}, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
