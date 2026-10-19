"""Read-only support skill prerequisites, point budgets, equipment and shop offers.

Run on the installed VPS with python3 -B -. No SQL, clients or combats.
"""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys


def main():
    sys.dont_write_bytecode = True
    root = Path('/home/rathena/rathena')
    assert sys.platform == 'linux' and root.is_dir(), 'Installed Linux source required; no action taken'
    spec = importlib.util.spec_from_file_location('gamedb', '/root/faithro/deploy/web/tools/build_gamedb.py')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    body = lambda path: builder.collect_body(root, path)
    tree = {entry['Job']: entry for entry in body('db/pre-re/skill_tree.yml')}
    imports = body('db/import/skill_tree.yml')
    assert not imports, 'Skill-tree imports need explicit merge review'
    panels = {
        'High_Priest': {'first': 'Acolyte', 'second': 'Priest', 'requested': {
            'AL_HEAL': 10, 'AL_BLESSING': 10, 'AL_INCAGI': 10, 'AL_PNEUMA': 1,
            'PR_MAGNIFICAT': 5, 'HP_ASSUMPTIO': 5, 'ALL_RESURRECTION': 4}},
        'Professor': {'first': 'Mage', 'second': 'Sage', 'requested': {
            'MG_SAFETYWALL': 10, 'SA_LANDPROTECTOR': 5, 'SA_DISPELL': 5,
            'PF_SOULCHANGE': 1, 'PF_SPIDERWEB': 1, 'PF_FOGWALL': 1}},
    }
    for name, panel in panels.items():
        nodes = {}; owners = {}
        for job in ['Novice', panel['first'], panel['second'], name]:
            for node in tree[job].get('Tree', []):
                nodes[node['Name']] = node; owners[node['Name']] = job
        allocation = {}; stack = set()

        def require(skill, level):
            if allocation.get(skill, 0) >= level:
                return
            assert skill not in stack, 'Cycle in prerequisites'
            node = nodes[skill]; assert level <= node['MaxLevel']
            stack.add(skill)
            for req in node.get('Requires', []):
                require(req['Name'], req['Level'])
            stack.remove(skill); allocation[skill] = level

        require('NV_BASIC', 9)
        for skill, level in panel['requested'].items():
            require(skill, level)
        spent = {'novice': 0, 'first': 0, 'second': 0}
        for skill, level in allocation.items():
            bucket = 'novice' if owners[skill] == 'Novice' else 'first' if owners[skill] == panel['first'] else 'second'
            spent[bucket] += level
        assert spent['novice'] <= 9 and spent['first'] <= 49 and spent['second'] <= 69, (name, spent)
        panel.update(skills=allocation, points_spent=spent, points_budget={'novice': 9, 'first': 49, 'second': 69})
    items = builder.merge_by_id(body('db/pre-re/item_db.yml') + body('db/import/item_db.yml'))
    skill_db = builder.merge_by_id(body('db/pre-re/skill_db.yml') + body('db/import/skill_db.yml'))
    allocated = {skill for panel in panels.values() for skill in panel['skills']}
    details = {entry['Name']: {key: entry[key] for key in ['Id', 'Name', 'MaxLevel', 'Requires', 'CastTime', 'AfterCastActDelay', 'Duration1'] if key in entry}
               for entry in skill_db.values() if entry['Name'] in allocated}
    item_ids = {entry['AegisName']: item for item, entry in items.items()}
    reagents = {item_ids[cost['Item']] for entry in details.values()
                for cost in entry.get('Requires', {}).get('ItemCost', [])}
    wanted = {2304, 2404, 2504, 1608, 1550, 505} | reagents
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
                if item in wanted:
                    offers.append({'item_id': item, 'price': items[item].get('Buy', 0) if price < 0 else price,
                                   'source': path, 'line': number})
    sources = ['db/pre-re/skill_tree.yml', 'db/import/skill_tree.yml', 'db/pre-re/item_db.yml', 'db/import/item_db.yml',
               'db/pre-re/skill_db.yml', 'db/import/skill_db.yml']
    print(json.dumps({'timestamp_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      'status': 'legal_support_panels_not_combat_results', 'panels': panels,
                      'gear': {item: items[item] for item in [2304, 2404, 2504, 1608, 1550]},
                      'skill_details': details,
                      'reagents': {item: {'name': items[item]['Name'], 'aegis': items[item]['AegisName']} for item in sorted(reagents)},
                      'literal_normal_shop_offers': offers,
                      'source_sha256': {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in sources},
                      'production_mutations': False, 'combats_executed': 0,
                      'limitations': ['Job change assumes first job 50, second job 70.',
                                      'Legal skill allocation does not prove a skill affects an MVP.',
                                      'Literal shop declaration may have access restrictions; barters and cash shops excluded.']}, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
