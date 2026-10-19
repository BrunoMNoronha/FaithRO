#!/usr/bin/env python3
"""Validate explicitly timed FaithRO sessions. No network or database access.

Usage: python tools/analyze_balance_session.py session.json
Outputs cash flow and resource use separately, preventing double charging purchases.
Pending templates and uncalibrated kill counters cannot produce performance metrics.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sys


class InvalidSession(ValueError):
    pass


TRANS_CLASSES = frozenset(('Lord_Knight','Lord_Knight2','Paladin','Paladin2','Sniper',
                          'Assassin_Cross','High_Wizard','High_Priest','Champion','Professor',
                          'Creator','Whitesmith','Stalker','Clown','Gypsy'))
EQUIPMENT_SLOTS = frozenset(('head_top','head_mid','head_low','armor','garment','shoes',
                             'right_hand','left_hand','accessory1','accessory2'))
CURVE_FILE = Path(__file__).resolve().parents[1]/'docs/progressao.csv'


def integer(value, field, minimum=0):
    if type(value) is not int or not minimum <= value <= 2**63 - 1:
        raise InvalidSession(f"{field}: inteiro >= {minimum} obrigatório")
    return value


def timestamp(value, field):
    try:
        result = datetime.fromisoformat(value)
    except (ValueError, TypeError):
        raise InvalidSession(f"{field}: data ISO com fuso obrigatória") from None
    if result.utcoffset() is None:
        raise InvalidSession(f"{field}: fuso obrigatório")
    return result


def progression_exp(progress, curve):
    """Net progress, including death losses. Not gross EXP awarded by monsters."""
    lo=integer(progress['start_level'],'exp_progress.start_level',1)
    hi=integer(progress['end_level'],'exp_progress.end_level',1)
    if hi<lo or hi>=255:
        raise InvalidSession('progresso pela curva exige níveis crescentes abaixo do cap 255')
    start=integer(progress['start_exp'],'exp_progress.start_exp')
    end=integer(progress['end_exp'],'exp_progress.end_exp')
    if start>=curve[lo] or end>=curve[hi]:
        raise InvalidSession('EXP parcial fora da faixa do nível')
    return sum(curve[level] for level in range(lo,hi))+end-start


def analyze(session):
    try:
        return _analyze(session)
    except (KeyError, TypeError, AttributeError) as error:
        raise InvalidSession(f"campo obrigatório ausente ou estrutura inválida: {error}") from None


def _analyze(s):
    if type(s['schema_version']) is not int or s['schema_version'] != 1:
        raise InvalidSession('schema_version incompatível')
    status = s['status']
    if status not in ('observed', 'synthetic'):
        raise InvalidSession('sessão pendente: preencher medições antes de apurar')
    if s['kind'] not in ('farm', 'mvp'):
        raise InvalidSession('kind deve ser farm ou mvp')
    actor = s['actor']
    group = integer(actor['group_id'], 'actor.group_id')
    if type(actor['is_bot']) is not bool or actor['is_bot']:
        raise InvalidSession('bot não pode compor métricas de jogadores')
    if s['environment'] not in ('isolated_test', 'production_observation'):
        raise InvalidSession('ambiente desconhecido')
    if actor['role'] == 'player':
        if group != 0:
            raise InvalidSession('equipe não pode compor métricas de jogadores')
    elif actor['role'] == 'tester':
        if s['environment'] != 'isolated_test':
            raise InvalidSession('testador só pode registrar ensaio isolado')
    else:
        raise InvalidSession('papel de conta desconhecido')
    if s['administrative_operations_present'] is not False:
        raise InvalidSession('excluir operações administrativas e repetir a sessão')

    build = s['build']
    level = integer(build['base_level'], 'build.base_level', 1)
    job_level = integer(build['job_level'], 'build.job_level', 1)
    if level > 255 or job_level > 70:
        raise InvalidSession('limites do painel: base 255, job 70')
    if build['class'] not in TRANS_CLASSES or not isinstance(s['map'],str) or not re.fullmatch(r'[a-z0-9_@-]{1,16}',s['map']):
        raise InvalidSession('classe e mapa obrigatórios')
    if len(build['stats_SAVIDL']) != 6:
        raise InvalidSession('informar seis atributos em ordem SAVIDL')
    for value in build['stats_SAVIDL']:
        integer(value, 'atributo', 1)
        if value > 185:
            raise InvalidSession('atributo natural acima de 185')
    budget = 48+52+sum((n+14)//5 for n in range(2,level+1))
    used_points = sum(sum(1+(n+9)//10 for n in range(1,value)) for value in build['stats_SAVIDL'])
    if used_points > budget:
        raise InvalidSession(f'build excede orçamento de atributos: {used_points} > {budget}')
    if not build['equipment']:
        raise InvalidSession('registrar equipamento completo, incluindo ausência de peças')
    slots = [item['slot'] for item in build['equipment']]
    if len(slots) != len(EQUIPMENT_SLOTS) or set(slots) != EQUIPMENT_SLOTS:
        raise InvalidSession('registrar todos os slots sem duplicar, usando item_id 0 para vazio')
    for item in build['equipment']:
        integer(item['item_id'], 'equipment.item_id')
        integer(item['refine'], 'equipment.refine')
        if not isinstance(item['cards'], list):
            raise InvalidSession('registrar cartas por slot, usando lista vazia quando não houver')
        for card in item['cards']:
            integer(card, 'equipment.card', 1)
        if not item['item_id'] and (item['refine'] or item['cards']):
            raise InvalidSession('slot vazio não pode ter refino ou cartas')
    if not build['skills']:
        raise InvalidSession('registrar habilidades e níveis usados')
    for name,value in build['skills'].items():
        if not name:
            raise InvalidSession('nome de habilidade obrigatório')
        integer(value,'skill.'+name,1)

    timing = s['timing']
    if timing['source'] != 'session_stopwatch' or timing['includes_travel_sales_recovery'] is not True:
        raise InvalidSession('usar cronômetro da sessão incluindo deslocamento/venda/recuperação')
    seconds = integer(timing['elapsed_seconds'], 'timing.elapsed_seconds', 1)
    start = timestamp(timing['started_at'], 'started_at')
    end = timestamp(timing['ended_at'], 'ended_at')
    if end <= start or abs((end-start).total_seconds() - seconds) > 5:
        raise InvalidSession('cronômetro diverge dos limites declarados da sessão')

    counter = s['kills_counter']
    if counter['method'] not in ('manual_tally', 'validated_quest_counter', 'validated_instrument'):
        raise InvalidSession('linhas de drop/log não são contador de abates')
    calibration = counter['calibration']
    expected = integer(calibration['known_kills'], 'calibration.known_kills', 10)
    if integer(calibration['counter_increase'], 'calibration.counter_increase') != expected:
        raise InvalidSession('contador reprovado na calibração de abates conhecidos')
    kills = integer(counter['end'], 'kills.end') - integer(counter['start'], 'kills.start')
    if kills < 0:
        raise InvalidSession('contador de abates reiniciado durante a sessão')
    deaths = integer(s['deaths'], 'deaths')
    exp = s['exp_gained']
    observed_levels=s.get('level_observation')
    if observed_levels is not None:
        observed_start=integer(observed_levels['start'],'level_observation.start',1)
        observed_end=integer(observed_levels['end'],'level_observation.end',1)
        if observed_start!=level or not observed_start<=observed_end<=255:
            raise InvalidSession('níveis observados incompatíveis com a build inicial')
        if observed_levels['mode'] not in ('progression','fixed'):
            raise InvalidSession('declarar modo progression ou fixed')
        if observed_levels['mode']=='fixed' and observed_start!=observed_end:
            raise InvalidSession('sessão subiu de nível: não é comparação em nível fixo')
    progress=s.get('exp_progress')
    if progress is not None:
        if progress['curve_sha256']!=hashlib.sha256(CURVE_FILE.read_bytes()).hexdigest():
            raise InvalidSession('curva de EXP difere da referência da sessão')
        curve={int(row['nivel']):int(row['exp_trans_para_proximo']) for row in
               csv.DictReader(CURVE_FILE.read_text(encoding='utf-8-sig').splitlines())}
        calculated=progression_exp(progress,curve)
        if progress['start_level']!=level:
            raise InvalidSession('nível inicial da EXP difere da build')
        if observed_levels is not None and progress['end_level']!=observed_levels['end']:
            raise InvalidSession('nível final da EXP difere do observado')
        if exp is not None and exp!=calculated:
            raise InvalidSession('ganho declarado diverge do progresso calculado pela curva')
        exp=calculated
    if exp is not None:
        integer(exp, 'exp_gained',-(2**63-1))
        if s['exp_measurement'] != 'cumulative_counter_or_level_curve':
            raise InvalidSession('EXP exige contador acumulado ou cálculo pela curva entre níveis')
    if level==255 and (exp is not None or progress is not None):
        raise InvalidSession('no cap 255 registrar EXP como desconhecida/não aplicável; não inventar ganho efetivo')

    cash = s['cash']
    fields = ['start','end','npc_sales','quest_rewards','npc_purchases','transport_fees',
              'refine_fees','other_sinks','external_in','external_out']
    c = {name:integer(cash[name], 'cash.'+name) for name in fields}
    delta = c['end']-c['start']
    expected_delta = (c['npc_sales']+c['quest_rewards']+c['external_in']-c['npc_purchases']
                      -c['transport_fees']-c['refine_fees']-c['other_sinks']-c['external_out'])
    if delta != expected_delta:
        raise InvalidSession(f'zeny não reconciliado: saldo mudou {delta}, movimentos somam {expected_delta}')
    activity_cash = delta-c['external_in']+c['external_out']
    consumed_value = 0
    seen = set()
    for entry in s['consumables']:
        item_id = integer(entry['item_id'], 'consumable.item_id', 1)
        if item_id in seen:
            raise InvalidSession('consumível duplicado')
        seen.add(item_id)
        inventory = {name:integer(entry[name], f'item {item_id}.{name}') for name in
                     ['start','end','purchased','looted','sold','other_in','other_out','consumed','unit_replacement_cost']}
        available = inventory['start']+inventory['purchased']+inventory['looted']+inventory['other_in']
        accounted = inventory['end']+inventory['sold']+inventory['other_out']+inventory['consumed']
        if available != accounted:
            raise InvalidSession(f'item {item_id}: inventário não reconciliado; não duplicar venda/consumo')
        consumed_value += inventory['consumed']*inventory['unit_replacement_cost']
    if s['consumables_complete'] is not True:
        raise InvalidSession('declarar todos os consumíveis, inclusive estoque inicial usado')

    attempts = None
    counter_scope = counter.get('scope', 'individual')
    outcome_scope = 'participant'
    if counter_scope not in ('individual', 'party_shared'):
        raise InvalidSession('escopo do contador desconhecido')
    if s['kind'] == 'mvp':
        attempts = s['mvp_attempt']
        outcome_scope = attempts.get('outcome_scope', 'participant')
        if outcome_scope not in ('participant', 'party'):
            raise InvalidSession('escopo do resultado de MVP desconhecido')
        if outcome_scope == 'party' and (type(s.get('party', {}).get('size')) is not int or s['party']['size'] != 2 or counter_scope != 'party_shared'):
            raise InvalidSession('resultado da dupla exige party 2 e contador compartilhado')
        if outcome_scope == 'participant' and counter_scope != 'individual':
            raise InvalidSession('contador compartilhado exige resultado da dupla')
        integer(attempts['monster_id'], 'mvp.monster_id', 1)
        target_kills = integer(attempts['target_kills'], 'mvp.target_kills')
        if target_kills > 1:
            raise InvalidSession('uma ficha por tentativa de MVP')
        if attempts['outcome'] not in ('victory','death','timeout','abandoned'):
            raise InvalidSession('resultado de MVP inválido')
        if attempts['outcome'] == 'death' and deaths == 0 and outcome_scope == 'participant':
            raise InvalidSession('derrota por morte exige registrar a morte')
        if attempts['outcome'] == 'victory' and (target_kills != 1 or kills < 1):
            raise InvalidSession('vitória exige abate do MVP alvo, não apenas invocações')
        if attempts['outcome'] != 'victory' and target_kills:
            raise InvalidSession('resultado de falha incompatível com abate do MVP alvo')
    elif counter_scope != 'individual':
        raise InvalidSession('contador compartilhado permitido somente no protocolo de MVP')
    hour_factor = 3600/seconds
    return {
        'schema_version':1, 'status':status, 'kind':s['kind'], 'map':s['map'],
        'provenance':'declared_session_data_not_server_verified',
        'build_status_points_used':used_points, 'build_status_points_budget':budget,
        'level_observation':observed_levels,
        'fixed_level_comparison_eligible':observed_levels is not None and observed_levels['start']==observed_levels['end'],
        'exp_basis':'net_progress_including_losses' if exp is not None else 'unknown_or_not_applicable',
        'eligible_for_player_metrics':status == 'observed' and actor['role'] == 'player' and s['environment'] == 'production_observation' and counter_scope == 'individual',
        'elapsed_seconds':seconds, 'kills':kills, 'kills_per_hour':round(kills*hour_factor, 3),
        'exp_gained':exp, 'exp_per_hour':None if exp is None else round(exp*hour_factor, 3),
        'deaths':deaths, 'cash_delta':delta, 'external_net':c['external_in']-c['external_out'],
        'activity_cash_net':activity_cash, 'activity_cash_net_per_hour':round(activity_cash*hour_factor, 3),
        'consumables_used_replacement_value':consumed_value,
        'cash_and_consumption_are_separate':True,
        'limitation':'Saldo de caixa não é lucro total. Não subtrair consumo novamente de compras já debitadas; inclui estoque inicial e loot usado na avaliação de recursos.',
        'mvp_attempt':attempts,
        'kill_counter_scope':counter_scope, 'mvp_outcome_scope':outcome_scope,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session', type=Path)
    args = parser.parse_args(argv)
    try:
        result = analyze(json.loads(args.session.read_text(encoding='utf-8')))
    except (OSError, ValueError) as error:
        print(f'Sessão não apurada: {error}', file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
