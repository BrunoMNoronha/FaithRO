import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import analyze_balance_mvp as mvp
import analyze_balance_session as sessions
import prepare_mvp_party as prepare


def filled(target=1086, support='High_Priest', number=0, status='synthetic', outcome='victory'):
    a = mvp.template(target, support)
    start = datetime(2026, 10, 19, 10, tzinfo=timezone(timedelta(hours=-3))) + timedelta(minutes=12 * number)
    a.update(status=status, attempt_id=f'unit-test-{number}', outcome=outcome,
             target_kills=int(outcome == 'victory'), summon_kills=2,
             combat_timing={'started_at': (start + timedelta(minutes=1)).isoformat(),
                            'ended_at': (start + timedelta(minutes=11)).isoformat(), 'elapsed_seconds': 600})
    for entry in a['participants']:
        s = entry['session']
        s.update(status=status, session_id=f'unit-test-{number}-{entry["member_id"]}',
                 deaths=int(outcome == 'death' and entry['member_id'] == 'attacker'),
                 consumables_complete=True, self_buffs_used=[], buff_observations_complete=True,
                 observed_panel={'hp': 9000, 'sp': 1000, 'aspd': 170, 'weight': 500, 'max_weight': 3000})
        s['timing'].update(elapsed_seconds=660, started_at=start.isoformat(), ended_at=(start + timedelta(minutes=11)).isoformat())
        s['kills_counter'].update(start=0, end=a['target_kills'] + a['summon_kills'])
        s['kills_counter']['calibration']['counter_increase'] = 10
        s['mvp_attempt'].update(outcome=outcome, target_kills=a['target_kills'])
        s['cash'] = {key: 0 for key in s['cash']}
        s['cash'].update(start=10000, end=9900, npc_purchases=100)
        s['consumables'] = [{'item_id': 501, 'start': 10, 'end': 9, 'purchased': 0, 'looted': 0,
                             'sold': 0, 'other_in': 0, 'other_out': 0, 'consumed': 1, 'unit_replacement_cost': 50}]
        if entry['member_id'] == 'attacker':
            s['consumables'].append(dict(s['consumables'][0], item_id=1750, start=100, end=98, consumed=2, unit_replacement_cost=1))
        s['level_observation']['end'] = s['build']['base_level']
        if s['exp_progress'] is not None:
            s['exp_progress'].update(start_exp=90, end_exp=100, end_level=s['build']['base_level'])
    return a


@pytest.fixture
def attempt():
    return filled()


def test_shared_kills_and_party_costs_not_double_counted(attempt):
    result = mvp.analyze(attempt)
    assert (result['target_kills'], result['summon_kills']) == (1, 2)
    assert result['npc_sinks'] == 200 and result['cash_net'] == -200
    assert result['consumption_replacement_value'] == 102
    assert result['cash_and_consumption_are_separate'] is True
    assert result['player_performance_metrics'] is result['automatic_balance_changes'] is False


def test_zeny_and_item_transfer_cancel_between_members(attempt):
    attacker, support = [entry['session'] for entry in attempt['participants']]
    attacker['cash'].update(end=8900, external_out=1000)
    support['cash'].update(end=10900, external_in=1000)
    attacker['consumables'][0].update(end=7, other_out=2)
    support['consumables'][0].update(end=11, other_in=2)
    attempt['transfers'] = [{'from': 'attacker', 'to': 'support', 'zeny': 1000, 'items': [{'item_id': 501, 'amount': 2}]}]
    result = mvp.analyze(attempt)
    assert result['cash_net'] == -200 and result['consumption_replacement_value'] == 102


def test_support_surviving_party_defeat_is_not_forced_to_invent_a_death():
    a = filled(outcome='death')
    assert a['participants'][1]['session']['deaths'] == 0
    assert mvp.analyze(a)['party_deaths'] == 1


def test_party_death_without_any_member_death_rejected():
    a = filled(outcome='death'); a['participants'][0]['session']['deaths'] = 0
    with pytest.raises(sessions.InvalidSession, match='ao menos uma morte'):
        mvp.analyze(a)


@pytest.mark.parametrize('mutate,match', [
    (lambda a: a.update(status='pending'), 'pendente'),
    (lambda a: a.update(summon_kills=8), 'contador'),
    (lambda a: a['participants'][1]['session']['kills_counter'].update(start=1, end=4), 'mesmo contador'),
    (lambda a: a['participants'][0]['session']['consumables'].pop(), 'flechas'),
    (lambda a: a['participants'][1]['session']['build']['stats_SAVIDL'].__setitem__(0, 185), 'build/mapa'),
    (lambda a: a['participants'][0]['session']['actor'].update(group_id=99), 'equipe/bot'),
    (lambda a: a['participants'][0]['session']['actor'].update(is_bot=True), 'equipe/bot'),
    (lambda a: a['participants'][1]['session'].update(buff_observations_complete=False), 'buffs completos'),
    (lambda a: a['participants'][0]['session']['cash'].update(end=10900, external_in=1000), 'financiamento externo'),
    (lambda a: a['participants'][1]['session']['consumables'][0].update(end=11, other_in=2), 'transferências de itens'),
    (lambda a: a['participants'][0]['session']['observed_panel'].update(aspd=198), 'painel observado'),
    (lambda a: a['participants'][0]['session']['timing'].update(started_at='2026-10-19T10:02:00-03:00', elapsed_seconds=540), 'fora da sessão'),
    (lambda a: a['combat_timing'].update(elapsed_seconds=601), '600 segundos'),
])
def test_invalid_attempts_rejected(attempt, mutate, match):
    mutate(attempt)
    with pytest.raises(sessions.InvalidSession, match=match):
        mvp.analyze(attempt)


def test_buff_source_casts_must_match(attempt):
    attacker, support = [entry['session'] for entry in attempt['participants']]
    attacker['received_buffs'] = [{'source_member': 'support', 'skill': 'AL_BLESSING', 'level': 10, 'applications': 1}]
    with pytest.raises(sessions.InvalidSession, match='habilidade usada na origem'):
        mvp.analyze(attempt)
    support['skills_used'] = [{'skill': 'AL_BLESSING', 'level': 10, 'casts': 1}]
    assert mvp.analyze(attempt)['status'] == 'synthetic'
    attacker['received_buffs'][0]['applications'] = 2
    with pytest.raises(sessions.InvalidSession, match='excedem'):
        mvp.analyze(attempt)


def panel(supports):
    return [filled(target, support, number, 'observed', ('victory', 'death', 'timeout')[repetition])
            for number, (target, support, repetition) in enumerate(
                (target, support, repetition) for target in mvp.TARGETS
                for support in [None, *supports] for repetition in range(3))]


@pytest.mark.parametrize('supports,count', [(['High_Priest'], 24), (list(mvp.SUPPORTS), 36)])
def test_complete_panels_keep_supports_separate_and_include_failure_costs(supports, count):
    result = mvp.gate(panel(supports))
    assert result['attempts'] == count and len(result['groups']) == count // 3
    assert all(row['outcomes'] == {'victory': 1, 'death': 1, 'timeout': 1} for row in result['groups'])
    assert all(row['npc_sinks_per_victory_including_failures'] == (300 if row['condition'] == 'solo' else 600) for row in result['groups'])
    assert result['automatic_balance_changes'] is False


@pytest.mark.parametrize('case,match', [('incomplete', 'incompleto'), ('duplicate', 'attempt_id duplicado'),
                                      ('overlap', 'sequenciais'), ('synthetic', 'reais declarados'),
                                      ('session_id', 'reutilizado')])
def test_bad_panels_rejected(case, match):
    records = panel(['High_Priest'])
    if case == 'incomplete': records.pop()
    if case == 'duplicate': records[1]['attempt_id'] = records[0]['attempt_id']
    if case == 'overlap': records[1] = filled(1086, None, 0, 'observed'); records[1]['attempt_id'] = 'unique'; records[1]['participants'][0]['session']['session_id'] = 'unique-session'
    if case == 'session_id': records[1]['participants'][0]['session']['session_id'] = records[0]['participants'][0]['session']['session_id']
    if case == 'synthetic':
        records[0]['status'] = 'synthetic'
        for member in records[0]['participants']: member['session']['status'] = 'synthetic'
    with pytest.raises(sessions.InvalidSession, match=match): mvp.gate(records)


def test_pending_cli_outputs_no_metrics(tmp_path, capsys):
    path = tmp_path / 'pending.json'
    assert prepare.main(['--target', '1086', '--support', 'High_Priest', '--output', str(path)]) == 0
    capsys.readouterr()
    assert mvp.main([str(path)]) == 2
    result = capsys.readouterr()
    assert not result.out and 'pendente' in result.err
    before = path.read_bytes()
    assert prepare.main(['--target', '1086', '--support', 'solo', '--output', str(path)]) == 2
    assert path.read_bytes() == before


def test_shared_counter_never_becomes_individual_player_metric():
    a = filled()
    s = a['participants'][0]['session']
    s.update(status='observed', environment='production_observation', actor={'role': 'player', 'group_id': 0, 'is_bot': False})
    assert sessions.analyze(s)['eligible_for_player_metrics'] is False


def test_single_player_cannot_claim_shared_counter():
    a = filled(support=None)
    s = a['participants'][0]['session']; s['kills_counter']['scope'] = 'party_shared'
    with pytest.raises(sessions.InvalidSession, match='resultado da dupla'):
        sessions.analyze(s)


def test_party_size_must_be_an_integer():
    s = filled()['participants'][0]['session']; s['party']['size'] = 2.0
    with pytest.raises(sessions.InvalidSession, match='party 2'):
        sessions.analyze(s)


def test_no_wins_keeps_cost_per_victory_unknown():
    records = panel(['Professor'])
    for a in records:
        a.update(outcome='timeout', target_kills=0)
        for member in a['participants']:
            s = member['session']; s['deaths'] = 0
            s['mvp_attempt'].update(outcome='timeout', target_kills=0)
            s['kills_counter']['end'] = a['summon_kills']
    result = mvp.gate(records)
    assert all(row['npc_sinks_per_victory_including_failures'] is None for row in result['groups'])
    assert all(row['consumption_value_per_victory_including_failures'] is None for row in result['groups'])


def test_undeclared_transfer_item_is_not_silently_dropped(attempt):
    attempt['transfers'] = [{'from': 'attacker', 'to': 'support', 'zeny': 0, 'items': [{'item_id': 717, 'amount': 1}]}]
    with pytest.raises(sessions.InvalidSession, match='ausente do inventário'):
        mvp.analyze(attempt)


def test_timeout_must_reach_combat_limit():
    a = filled(outcome='timeout')
    a['combat_timing'].update(elapsed_seconds=500, ended_at='2026-10-19T10:09:20-03:00')
    with pytest.raises(sessions.InvalidSession, match='timeout antes'):
        mvp.analyze(a)


def test_party_shared_counter_cannot_be_used_for_farm():
    s = filled()['participants'][0]['session']; s['kind'] = 'farm'
    with pytest.raises(sessions.InvalidSession, match='somente no protocolo de MVP'):
        sessions.analyze(s)
