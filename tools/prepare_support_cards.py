"""Prepare pending support build cards locally; never overwrite observations.

Inputs are the read-only installed-data records. No SSH, SQL or game clients.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / 'design-audit/mvp-threat-review'
SLOTS = ('head_top', 'head_mid', 'head_low', 'armor', 'garment', 'shoes',
         'right_hand', 'left_hand', 'accessory1', 'accessory2')


def prepare():
    installed_path = HERE / 'support-installed-data.json'
    installed = json.loads(installed_path.read_text(encoding='utf-8'))
    snapshot = json.loads((ROOT / 'design-audit/post-deploy-review/snapshot.json').read_text(encoding='utf-8'))
    cards = []
    for build in snapshot['builds']:
        if build['class'] not in installed['panels'] or build['purpose'] != 'MVP':
            continue
        level = build['level']; name = build['class']
        used = sum(sum(1 + (n + 9) // 10 for n in range(1, value)) for value in build['stats_SAVIDL'])
        assert used == build['used'] <= snapshot['budgets'][str(level)]
        equipment = {'armor': 2304, 'garment': 2504, 'shoes': 2404, 'right_hand': build['weapon_id']}
        prices = {}
        family = installed['panels'][name]['second']
        for item_id in equipment.values():
            item = installed['gear'][str(item_id)]
            jobs = item.get('Jobs', {})
            assert jobs.get(family, jobs.get('All', not jobs)), (name, item_id)
            assert not item.get('Classes') and item.get('Gender', 'Both') in ('Both', None)
            assert item.get('EquipLevelMin', 1) <= level <= item.get('EquipLevelMax', 255)
            offers = [row['price'] for row in installed['literal_normal_shop_offers'] if row['item_id'] == item_id]
            assert offers, ('No verified normal shop offer', item_id)
            prices[str(item_id)] = min(offers)
        card = {
            'schema_version': 1, 'status': 'pending_build_card_not_observation',
            'purpose': 'controlled_MVP_duo_support_baseline',
            'actor': {'role': 'tester', 'group_id': 0, 'is_bot': False},
            'build': {'class': name, 'base_level': level, 'job_level': 70,
                      'stats_SAVIDL': build['stats_SAVIDL'],
                      'equipment': [{'slot': slot, 'item_id': equipment.get(slot, 0), 'refine': 0, 'cards': []} for slot in SLOTS],
                      'skills': installed['panels'][name]['skills']},
            'status_points_used': used, 'status_points_budget': snapshot['budgets'][str(level)],
            'skill_points': installed['panels'][name]['points_spent'],
            'skill_points_budget': installed['panels'][name]['points_budget'],
            'equipment_compatible': True, 'normal_shop_prices_before_discount': prices,
            'equipment_purchase_total_before_discount': sum(prices.values()),
            'observed_panel': {'hp': None, 'sp': None, 'aspd': None, 'weight': None, 'max_weight': None},
            'actual_skills_cast_and_results': None, 'consumables_and_cash_record': None,
            'support_source_sha256': hashlib.sha256(installed_path.read_bytes()).hexdigest(),
            'limitations': ['Baseline equipment is obtainable, but survival and usefulness are untested.',
                            'Prerequisite skills are allocated; their use must be declared and reconciled.',
                            'Skill availability does not establish effectiveness against bosses.',
                            'Copy before use; complete separate cash/consumable records for each participant.'],
        }
        cards.append((HERE / f'support-{name.lower()}-{level}.json', card))
    assert len(cards) == 8
    assert not any(path.exists() for path, _ in cards), 'Refusing to overwrite existing support cards'
    for path, card in cards:
        with path.open('x', encoding='utf-8') as handle:
            handle.write(json.dumps(card, ensure_ascii=False, indent=2) + '\n')
    return len(cards)


if __name__ == '__main__':
    print(f'{prepare()} pending support cards prepared; no combat executed.')
