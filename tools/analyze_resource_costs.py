"""Calculate database base costs for explicitly counted charge events, offline.

No simulation of casts, SP regeneration, exemptions or combat performance.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

import analyze_balance_session as sessions

CATALOG = Path(__file__).resolve().parents[1] / 'design-audit/resource-recovery-review/installed-costs.json'


def at_level(value, level, label):
    if isinstance(value, list):
        matches = [row['Amount'] for row in value if row['Level'] == level]
        if len(matches) != 1:
            raise sessions.InvalidSession('custo por nível incompleto: ' + label)
        value = matches[0]
    return sessions.integer(value, label)


def calculate(plan, catalog, catalog_sha256):
    if plan['catalog_sha256'] != catalog_sha256:
        raise sessions.InvalidSession('catálogo difere da referência do plano')
    if plan['basis'] not in ('hypothetical_charge_counts', 'declared_charge_counts'):
        raise sessions.InvalidSession('declarar a origem das contagens de cobrança')
    if not isinstance(plan['skills'], list):
        raise sessions.InvalidSession('skills deve ser lista')
    if catalog['arrow_decrement']['value'] != 1:
        raise sessions.InvalidSession('flag de munição exige revisão específica')
    sp = 0; items = Counter(); rows = []; seen = set()
    basic = sessions.integer(plan['basic_arrow_charge_events'], 'basic_arrow_charge_events')
    items[1750] += basic
    for row in plan['skills']:
        name = row['skill']; level = sessions.integer(row['level'], 'skill.level', 1)
        if name not in catalog['skills'] or (name, level) in seen:
            raise sessions.InvalidSession('habilidade desconhecida ou linha duplicada')
        seen.add((name, level)); definition = catalog['skills'][name]
        if level > definition['MaxLevel']:
            raise sessions.InvalidSession('nível de habilidade acima do instalado')
        counts = {kind: sessions.integer(row[kind + '_charge_events'], kind + '_charge_events') for kind in ('sp', 'item', 'ammo')}
        req = definition.get('Requires', {})
        if counts['sp'] and 'SpCost' not in req:
            raise sessions.InvalidSession('custo SP não modelado para habilidade')
        cost_sp = at_level(req.get('SpCost', 0), level, name + '.SpCost') * counts['sp']
        sp += cost_sp
        costs = [entry for entry in req.get('ItemCost', []) if 'Level' not in entry or entry['Level'] == level]
        if counts['item'] and not costs:
            raise sessions.InvalidSession('cobrança de item sem requisito instalado')
        for cost in costs:
            items[cost['ItemId']] += sessions.integer(cost['Amount'], 'ItemCost.Amount') * counts['item']
        ammo = at_level(req.get('AmmoAmount', 0), level, name + '.AmmoAmount')
        if counts['ammo'] and (not req.get('Ammo', {}).get('Arrow') or not ammo):
            raise sessions.InvalidSession('cobrança de flecha sem requisito instalado')
        items[1750] += ammo * counts['ammo']
        rows.append({'skill': name, 'level': level, 'base_sp': cost_sp, 'charge_events': counts})
    output = []
    for item, amount in sorted(items.items()):
        if not amount:
            continue
        price = catalog['items'][str(item)]['min_literal_shop_price']
        if price is not None:
            price = sessions.integer(price, 'literal_shop_price')
        output.append({'item_id': item, 'quantity': amount, 'unit_price_before_discount': price,
                       'replacement_value': None if price is None else amount * price})
    total = sum(row['replacement_value'] for row in output) if all(row['replacement_value'] is not None for row in output) else None
    return {'status': 'calculated_base_costs_not_gameplay', 'basis': plan['basis'], 'base_sp_charge_total': sp,
            'items': output, 'replacement_value_before_discount': total, 'skills': rows,
            'player_performance_metrics': False, 'automatic_balance_changes': False,
            'limitations': ['Charge counts are inputs, not inferred from casts/hits or authenticated by the server.',
                            'Base SP is not net SP lost: modifiers, regeneration, exchanges and failures are unmodeled.',
                            'Replacement value is separate from cash purchases; do not deduct both as the same expense.']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    args = parser.parse_args(argv)
    try:
        raw = CATALOG.read_bytes()
        result = calculate(json.loads(args.plan.read_text(encoding='utf-8')), json.loads(raw), hashlib.sha256(raw).hexdigest())
    except (OSError, ValueError, KeyError, TypeError) as error:
        print('Custo não calculado: ' + str(error), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
