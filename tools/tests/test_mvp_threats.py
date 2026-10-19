import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('mvp_threats', Path(__file__).resolve().parents[1] / 'collect_mvp_threats.py')
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


def row(mob=1751, label='Valkyrie@MG_THUNDERSTORM', rate=10000, level=20):
    return f'{mob},{label},attack,21,{level},{rate},1500,5000,no,target,attackpcge,2,,,,,,,'


def test_conditional_chance_delay_and_monster_level_cap():
    result = tool.skill_rows(row(rate=7000, level=93), 'db/test.txt', rate=200, delay=150, max_level=50)[0]
    assert result['conditional_chance_per_10000'] == 10000
    assert result['recast_delay_ms'] == 7500
    assert result['effective_level'] == 50
    assert result['condition'] == 'attackpcge' and result['condition_value'] == '2'
    assert result['cast_ms'] == 1500 and result['cancelable'] is False


def test_zero_database_chance_matches_installed_minimum():
    assert tool.skill_rows(row(rate=0), 'db/test.txt')[0]['conditional_chance_per_10000'] == 1


def test_import_clear_removes_prior_specific_skills():
    original = tool.skill_rows(row(), 'db/pre-re.txt')
    clear = tool.skill_rows(row(label='clear'), 'db/import.txt')
    replacement = tool.skill_rows(row(rate=2000), 'db/import.txt')
    merged = tool.merge_rows([original, clear, replacement])
    assert len(merged[1751]) == 1
    assert merged[1751][0]['conditional_chance_per_10000'] == 2000


def test_attack_and_chase_declarations_remain_separate():
    parsed = tool.skill_rows(row() + '\n' + row().replace(',attack,', ',chase,'), 'db/test.txt')
    assert [r['state'] for r in parsed] == ['attack', 'chase']


def test_global_skills_refuse_incomplete_reconstruction():
    with pytest.raises(AssertionError, match='Global monster'):
        tool.skill_rows(row(mob=-1), 'db/test.txt')


def test_malformed_skill_row_refused():
    with pytest.raises(AssertionError, match='Unexpected skill row'):
        tool.skill_rows('1751,broken', 'db/test.txt')


def test_recursive_config_import_order_and_secret_exclusion(tmp_path):
    (tmp_path / 'base.conf').write_text('mob_skill_rate: 100\npassword: secret\nimport: override.conf\n')
    (tmp_path / 'override.conf').write_text('mob_skill_rate: 150 // local\n')
    result = tool.config_values(tmp_path, 'base.conf', {'mob_skill_rate'})
    assert result == {'mob_skill_rate': {'value': '150', 'source': 'override.conf', 'line': 1}}


def test_recursive_config_cycle_refused(tmp_path):
    (tmp_path / 'base.conf').write_text('import: base.conf\n')
    with pytest.raises(AssertionError, match='Cyclic'):
        tool.config_values(tmp_path, 'base.conf', set())
