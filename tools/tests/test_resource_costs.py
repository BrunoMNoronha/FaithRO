import copy
import hashlib
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import analyze_resource_costs as tool
import analyze_balance_session as sessions


@pytest.fixture
def catalog():
    return json.loads(tool.CATALOG.read_bytes())


def plan(*skills):
    return {'catalog_sha256': hashlib.sha256(tool.CATALOG.read_bytes()).hexdigest(),
            'basis': 'hypothetical_charge_counts', 'basic_arrow_charge_events': 0,
            'skills': [{'skill': name, 'level': level, 'sp_charge_events': count,
                        'item_charge_events': items, 'ammo_charge_events': ammo}
                       for name, level, count, items, ammo in skills]}


def calculate(value, catalog):
    return tool.calculate(value, catalog, hashlib.sha256(tool.CATALOG.read_bytes()).hexdigest())


def test_double_strafe_two_hits_does_not_double_arrow_consumption(catalog):
    p = plan(('AC_DOUBLE', 10, 100, 0, 100))
    result = calculate(p, catalog)
    assert catalog['skills']['AC_DOUBLE']['HitCount'] == 2
    assert result['base_sp_charge_total'] == 1200
    assert result['items'] == [{'item_id': 1750, 'quantity': 100, 'unit_price_before_discount': 1, 'replacement_value': 100}]
    assert result['player_performance_metrics'] is result['automatic_balance_changes'] is False


def test_mixed_support_reagents_and_level_costs(catalog):
    result = calculate(plan(('MG_SAFETYWALL', 10, 10, 10, 0), ('SA_LANDPROTECTOR', 5, 10, 10, 0)), catalog)
    assert result['base_sp_charge_total'] == 900
    assert {row['item_id']: row['quantity'] for row in result['items']} == {715: 10, 717: 20}
    assert result['replacement_value_before_discount'] == 18000


def test_sp_and_item_charge_counts_are_independent(catalog):
    result = calculate(plan(('MG_SAFETYWALL', 10, 5, 0, 0)), catalog)
    assert result['base_sp_charge_total'] == 200 and result['items'] == []


@pytest.mark.parametrize('mutate,match', [
    (lambda p: p.update(catalog_sha256='wrong'), 'catálogo'),
    (lambda p: p.update(basic_arrow_charge_events=True), 'inteiro'),
    (lambda p: p['skills'][0].update(level=11), 'nível'),
    (lambda p: p['skills'][0].update(sp_charge_events=-1), 'inteiro'),
    (lambda p: p['skills'][0].update(skill='UNKNOWN'), 'desconhecida'),
    (lambda p: p['skills'].append(copy.deepcopy(p['skills'][0])), 'duplicada'),
    (lambda p: p['skills'][0].update(item_charge_events=1), 'sem requisito'),
])
def test_invalid_plans_rejected(catalog, mutate, match):
    p = plan(('AC_DOUBLE', 10, 1, 0, 1)); mutate(p)
    with pytest.raises(sessions.InvalidSession, match=match): calculate(p, catalog)


def test_changed_arrow_flag_requires_review(catalog):
    catalog['arrow_decrement']['value'] = 0
    with pytest.raises(sessions.InvalidSession, match='flag de munição'):
        calculate(plan(), catalog)


def test_missing_price_stays_unknown_not_free(catalog):
    catalog['items']['678']['min_literal_shop_price'] = None
    result = calculate(plan(('ASC_EDP', 5, 1, 1, 0)), catalog)
    assert result['replacement_value_before_discount'] is None
    assert result['items'][0]['replacement_value'] is None


def test_incomplete_level_schedule_refused(catalog):
    catalog['skills']['MG_SAFETYWALL']['Requires']['SpCost'] = []
    with pytest.raises(sessions.InvalidSession, match='por nível incompleto'):
        calculate(plan(('MG_SAFETYWALL', 10, 1, 0, 0)), catalog)


def test_cannot_charge_arrows_for_a_reagent_only_skill(catalog):
    with pytest.raises(sessions.InvalidSession, match='flecha sem requisito'):
        calculate(plan(('PF_SPIDERWEB', 1, 1, 1, 1)), catalog)


def test_invalid_negative_vendor_price_refused(catalog):
    catalog['items']['1750']['min_literal_shop_price'] = -1
    with pytest.raises(sessions.InvalidSession, match='literal_shop_price'):
        calculate(plan(('AC_DOUBLE', 10, 1, 0, 1)), catalog)
