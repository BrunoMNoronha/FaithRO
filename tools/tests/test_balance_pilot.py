import copy
import json
from pathlib import Path
import sys

import pytest

TOOLS=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(TOOLS))
import analyze_balance_session as sessions
import analyze_balance_pilot as pilot


@pytest.fixture
def records():
    rows=[]
    for n,name in enumerate(['Sniper','Assassin_Cross','High_Wizard']):
        s=json.loads((pilot.KIT/f'template-{name.lower()}-99.json').read_text(encoding='utf-8'))
        s.update(status='observed',session_id='unit-test-'+name,deaths=0,consumables_complete=True,
                 self_buffs_used=[],observed_panel={'hp':9000,'sp':1000,'aspd':170,'weight':500,'max_weight':3000})
        s['cash']={key:0 for key in s['cash']}
        s['timing'].update(elapsed_seconds=1800,started_at=f'2026-10-19T{10+n:02}:00:00-03:00',ended_at=f'2026-10-19T{10+n:02}:30:00-03:00')
        s['kills_counter'].update(start=0,end=150);s['kills_counter']['calibration']['counter_increase']=10
        s['exp_progress'].update(start_exp=99000000,end_level=100,end_exp=2000000)
        s['level_observation']['end']=100
        rows.append(s)
    return rows


def test_three_consistent_progression_records_can_pass_without_balance_change(records):
    result=pilot.gate(records)
    assert result['status']=='pilot_records_consistent'
    assert result['automatic_balance_changes'] is False
    assert result['player_performance_metrics'] is False
    assert all(row['exp_gained']==3000000 for row in result['sessions'])
    assert all(row['fixed_level_comparison_eligible'] is False for row in result['sessions'])


def test_exp_crosses_level_boundary_using_full_curve():
    p={'start_level':99,'end_level':100,'start_exp':90,'end_exp':20}
    assert sessions.progression_exp(p,{99:100,100:200})==30


def test_death_loss_is_negative_net_progress():
    p={'start_level':99,'end_level':99,'start_exp':90,'end_exp':80}
    assert sessions.progression_exp(p,{99:100})==-10


def test_net_loss_is_preserved_in_hourly_metric(records):
    s=records[0];s['exp_progress'].update(end_level=99,end_exp=98000000)
    s['level_observation']['end']=99
    result=sessions.analyze(s)
    assert result['exp_gained']==-1000000 and result['exp_per_hour']==-2000000


@pytest.mark.parametrize('mutate,match',[
    (lambda s:s.update(status='synthetic'),'reais'),
    (lambda s:s.update(session_id=None),'session_id'),
    (lambda s:s.update(protocol_id='old'),'protocolo'),
    (lambda s:s.update(map='abbey03'),'Juperos'),
    (lambda s:s.update(attributes_changed_during_session=True),'atributos'),
    (lambda s:s['buff_rules'].update(outside_support=True),'suporte'),
    (lambda s:s.update(self_buffs_used=None),'buffs'),
    (lambda s:s['observed_panel'].update(hp=None),'painel'),
    (lambda s:s['observed_panel'].update(weight=4000),'peso'),
    (lambda s:s['level_observation'].update(mode='fixed'),'nível fixo'),
    (lambda s:s.update(exp_gained=1),'diverge'),
    (lambda s:s['exp_progress'].update(curve_sha256='wrong'),'curva'),
])
def test_incompatible_pilot_record_blocks_gate(records,mutate,match):
    mutate(records[0])
    with pytest.raises(sessions.InvalidSession,match=match):pilot.gate(records)


def test_missing_class_rejected(records):
    with pytest.raises(sessions.InvalidSession,match='três'):pilot.gate(records[:2])


def test_duplicate_class_rejected(records):
    records[1]=copy.deepcopy(records[0])
    with pytest.raises(sessions.InvalidSession,match='duplicar'):pilot.gate(records)


def test_overlapping_sessions_rejected(records):
    records[1]['timing']=copy.deepcopy(records[0]['timing'])
    with pytest.raises(sessions.InvalidSession,match='sobrepor'):pilot.gate(records)


def test_edp_requires_consumed_poison(records):
    records[1]['self_buffs_used']=[{'skill':'ASC_EDP','level':5}]
    with pytest.raises(sessions.InvalidSession,match='Poison Bottle'):pilot.gate(records)


def test_missing_observed_level_blocks_gate(records):
    records[0].pop('level_observation')
    with pytest.raises(sessions.InvalidSession,match='progressão'):pilot.gate(records)


def test_level_cap_does_not_fabricate_exp(records):
    s=json.loads((pilot.KIT/'template-sniper-255.json').read_text(encoding='utf-8'))
    s.update(status='synthetic',deaths=0,consumables_complete=True)
    s['cash']={k:0 for k in s['cash']}
    s['timing']=records[0]['timing'];s['kills_counter']=records[0]['kills_counter'];s['level_observation']['end']=255
    assert sessions.analyze(s)['exp_per_hour'] is None
    s.update(exp_gained=3000000,exp_measurement='cumulative_counter_or_level_curve')
    with pytest.raises(sessions.InvalidSession,match='cap 255'):sessions.analyze(s)


def test_partial_exp_at_or_above_threshold_is_invalid():
    with pytest.raises(sessions.InvalidSession,match='fora da faixa'):
        sessions.progression_exp({'start_level':99,'end_level':99,'start_exp':100,'end_exp':80},{99:100})


def test_gate_cli_refuses_pending_files_and_outputs_no_metrics(capsys):
    paths=[str(pilot.KIT/f'template-{name}-99.json') for name in ['sniper','assassin_cross','high_wizard']]
    assert pilot.main(paths)==2
    captured=capsys.readouterr()
    assert not captured.out and 'pendente' in captured.err
