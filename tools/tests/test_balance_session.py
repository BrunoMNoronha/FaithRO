import copy
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('balance_session', Path(__file__).resolve().parents[1]/'analyze_balance_session.py')
session_tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(session_tool)


@pytest.fixture
def session():
    return {
        'schema_version':1, 'status':'synthetic', 'kind':'farm', 'map':'juperos_02',
        'environment':'isolated_test', 'actor':{'role':'tester','group_id':99,'is_bot':False},
        'administrative_operations_present':False,
        'build':{'class':'Sniper','base_level':150,'job_level':70,
                 'stats_SAVIDL':[30,119,90,50,130,1],
                 'equipment':[{'slot':slot,'item_id':1708 if slot=='right_hand' else 0,'refine':0,'cards':[]}
                              for slot in sorted(session_tool.EQUIPMENT_SLOTS)],
                 'skills':{'AC_DOUBLE':10}},
        'timing':{'source':'session_stopwatch','elapsed_seconds':1800,
                  'started_at':'2026-10-19T10:00:00-03:00','ended_at':'2026-10-19T10:30:00-03:00',
                  'includes_travel_sales_recovery':True},
        'kills_counter':{'method':'manual_tally','start':0,'end':150,
                         'calibration':{'known_kills':10,'counter_increase':10}},
        'deaths':0, 'exp_gained':210000000, 'exp_measurement':'cumulative_counter_or_level_curve',
        'cash':{'start':100000,'end':485000,'npc_sales':450000,'quest_rewards':0,
                'npc_purchases':40000,'transport_fees':25000,'refine_fees':0,'other_sinks':0,
                'external_in':0,'external_out':0},
        'consumables_complete':True,
        'consumables':[{'item_id':504,'start':100,'end':80,'purchased':0,'looted':0,
                        'sold':0,'other_in':0,'other_out':0,'consumed':20,'unit_replacement_cost':1200}],
    }


def test_stopwatch_metrics_and_cash_not_double_charged(session):
    result = session_tool.analyze(session)
    assert result['kills_per_hour'] == 300
    assert result['exp_per_hour'] == 420000000
    assert result['activity_cash_net'] == 385000
    assert result['consumables_used_replacement_value'] == 24000
    assert result['status'] == 'synthetic'
    assert result['eligible_for_player_metrics'] is False


def test_external_transfers_do_not_become_farm_income(session):
    session['cash'].update(end=1485000,external_in=1000000)
    assert session_tool.analyze(session)['activity_cash_net'] == 385000


def test_resources_looted_or_already_owned_are_reported(session):
    session['consumables'][0].update(looted=10,consumed=30)
    assert session_tool.analyze(session)['consumables_used_replacement_value'] == 36000


def test_valid_observation_can_enter_player_metrics(session):
    session.update(status='observed',environment='production_observation',actor={'role':'player','group_id':0,'is_bot':False})
    assert session_tool.analyze(session)['eligible_for_player_metrics'] is True


@pytest.mark.parametrize('field,value', [
    ('status','pending'),('administrative_operations_present',True),('consumables_complete',False),
    ('environment','unknown'),('kind','unknown'),('deaths',True),('deaths',-1),('deaths',1.5),
])
def test_invalid_session_fields(session,field,value):
    session[field] = value
    with pytest.raises(session_tool.InvalidSession): session_tool.analyze(session)


@pytest.mark.parametrize('method', ['picklog_rows','mvplog_interval','drops_divided_by_chance'])
def test_log_counts_are_never_kill_counters(session,method):
    session['kills_counter']['method'] = method
    with pytest.raises(session_tool.InvalidSession,match='contador de abates'): session_tool.analyze(session)


def test_calibration_must_match_known_kills(session):
    session['kills_counter']['calibration']['counter_increase'] = 9
    with pytest.raises(session_tool.InvalidSession,match='calibração'): session_tool.analyze(session)


def test_counter_reset_rejected(session):
    session['kills_counter'].update(start=200,end=150)
    with pytest.raises(session_tool.InvalidSession,match='reiniciado'): session_tool.analyze(session)


@pytest.mark.parametrize('case',['timezone','clock_disagrees','zero_duration','log_time','exclude_recovery'])
def test_timing_requires_complete_explicit_session(session,case):
    t=session['timing']
    if case=='timezone': t['started_at']='2026-10-19T10:00:00'
    if case=='clock_disagrees': t['elapsed_seconds']=1700
    if case=='zero_duration': t['elapsed_seconds']=0
    if case=='log_time': t['source']='first_last_log'
    if case=='exclude_recovery': t['includes_travel_sales_recovery']=False
    with pytest.raises(session_tool.InvalidSession): session_tool.analyze(session)


def test_unreconciled_cash_rejected(session):
    session['cash']['end'] += 1
    with pytest.raises(session_tool.InvalidSession,match='zeny não reconciliado'): session_tool.analyze(session)


def test_sold_loot_cannot_also_be_consumed(session):
    session['consumables'][0]['sold'] = 20
    with pytest.raises(session_tool.InvalidSession,match='inventário não reconciliado'): session_tool.analyze(session)


def test_duplicate_inventory_item_rejected(session):
    session['consumables'].append(copy.deepcopy(session['consumables'][0]))
    with pytest.raises(session_tool.InvalidSession,match='duplicado'): session_tool.analyze(session)


@pytest.mark.parametrize('actor',[{'role':'player','group_id':99,'is_bot':False},
                                 {'role':'player','group_id':0,'is_bot':True}])
def test_staff_and_bots_cannot_enter_player_metrics(session,actor):
    session.update(status='observed',environment='production_observation',actor=actor)
    with pytest.raises(session_tool.InvalidSession): session_tool.analyze(session)


def test_partial_exp_across_levels_not_treated_as_total_gain(session):
    session['exp_measurement']='end_exp_minus_start_exp'
    with pytest.raises(session_tool.InvalidSession,match='EXP exige'): session_tool.analyze(session)


def test_missing_exp_stays_unknown(session):
    session['exp_gained']=None
    assert session_tool.analyze(session)['exp_per_hour'] is None


def test_failed_mvp_attempt_stays_failed(session):
    session.update(kind='mvp',deaths=1,mvp_attempt={'monster_id':1832,'outcome':'death','target_kills':0})
    assert session_tool.analyze(session)['mvp_attempt']['outcome']=='death'


def test_mvp_death_requires_recorded_death(session):
    session.update(kind='mvp',mvp_attempt={'monster_id':1832,'outcome':'death','target_kills':0})
    with pytest.raises(session_tool.InvalidSession,match='registrar a morte'): session_tool.analyze(session)


def test_cli_rejects_unfilled_template_without_output(tmp_path,capsys):
    p=tmp_path/'pending.json';p.write_text(json.dumps({'schema_version':1,'status':'pending'}))
    assert session_tool.main([str(p)])==2
    result=capsys.readouterr()
    assert not result.out
    assert 'pendente' in result.err


def test_unaffordable_build_rejected(session):
    session['build'].update(base_level=99,stats_SAVIDL=[185]*6)
    with pytest.raises(session_tool.InvalidSession,match='orçamento'): session_tool.analyze(session)


def test_missing_or_duplicate_equipment_slot_rejected(session):
    session['build']['equipment'][0]['slot'] = session['build']['equipment'][1]['slot']
    with pytest.raises(session_tool.InvalidSession,match='slots'): session_tool.analyze(session)


def test_cards_or_refines_on_empty_slots_rejected(session):
    empty=next(x for x in session['build']['equipment'] if x['item_id']==0)
    empty['cards']=[4001]
    with pytest.raises(session_tool.InvalidSession,match='slot vazio'): session_tool.analyze(session)


@pytest.mark.parametrize('field,value',[('base_level',256),('job_level',71)])
def test_level_limits(session,field,value):
    session['build'][field]=value
    with pytest.raises(session_tool.InvalidSession,match='limites'): session_tool.analyze(session)


def test_summons_cannot_prove_mvp_victory(session):
    session.update(kind='mvp',mvp_attempt={'monster_id':1832,'outcome':'victory','target_kills':0})
    with pytest.raises(session_tool.InvalidSession,match='MVP alvo'): session_tool.analyze(session)


def test_cli_synthetic_result_stays_labeled_synthetic(session,tmp_path,capsys):
    p=tmp_path/'synthetic.json';p.write_text(json.dumps(session),encoding='utf-8')
    assert session_tool.main([str(p)])==0
    result=json.loads(capsys.readouterr().out)
    assert result['status']=='synthetic'
    assert result['eligible_for_player_metrics'] is False


def test_mvp_map_placeholder_must_be_replaced(session):
    session['map']='RECORD_ACTUAL_MAP'
    with pytest.raises(session_tool.InvalidSession,match='mapa'): session_tool.analyze(session)
