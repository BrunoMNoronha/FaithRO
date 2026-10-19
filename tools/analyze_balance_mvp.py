"""Validate declared MVP attempts and 24/36-attempt panels offline.

No SSH, SQL, clients or automatic balancing. Unit tests are not combat evidence.
"""
import argparse
from collections import Counter, defaultdict
import copy
import json
from pathlib import Path
import sys

import analyze_balance_session as sessions

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / 'design-audit/balance-session-kit'
SUPPORT = ROOT / 'design-audit/mvp-threat-review'
PROTOCOL = 'faithro-mvp-party-v1'
TARGETS = {1086: ('gtb', 99, 'prt_sewb4'), 1039: ('baphomet', 150, 'prt_maze03'),
           1751: ('randgris', 255, 'odin_tem03'), 1832: ('ifrit', 255, 'thor_v03')}
SUPPORTS = ('High_Priest', 'Professor')


def require(condition, message):
    if not condition:
        raise sessions.InvalidSession(message)


def template(target, support=None):
    """Pending input only. Both participants use the same observed party counter."""
    require(target in TARGETS and support in (None, *SUPPORTS), 'alvo/suporte desconhecido')
    name, level, map_name = TARGETS[target]
    attacker = json.loads((KIT / f'template-mvp-{name}.json').read_text(encoding='utf-8'))
    members = [('attacker', attacker)]
    if support:
        healer = copy.deepcopy(attacker)
        card = json.loads((SUPPORT / f'support-{support.lower()}-{level}.json').read_text(encoding='utf-8'))
        healer['build'] = card['build']
        members.append(('support', healer))
    for member_id, record in members:
        record.update(map=map_name, protocol_id=PROTOCOL, session_id=None,
                      party={'size': len(members), 'support_class': support},
                      skills_used=[], received_buffs=[], buff_observations_complete=False,
                      ammunition_item_id=1750 if member_id == 'attacker' else 0)
        record['kills_counter']['scope'] = 'party_shared' if support else 'individual'
        record['mvp_attempt']['outcome_scope'] = 'party' if support else 'participant'
    return {'schema_version': 1, 'protocol_id': PROTOCOL, 'status': 'pending',
            'attempt_id': None, 'monster_id': target, 'support_class': support,
            'combat_timing': {'started_at': None, 'ended_at': None, 'elapsed_seconds': None},
            'outcome': None, 'target_kills': None, 'summon_kills': None,
            'participants': [{'member_id': key, 'session': value} for key, value in members],
            'transfers': [], 'notes': ['Preencher somente após ensaio real isolado; não publicar identificadores de jogadores.',
                                      'Mesmo contador observado de chefe+invocações nas duas fichas; não somar duas vezes.',
                                      'Transferências internas precisam constar dos dois ledgers. Sem entrada/saída externa durante o ensaio.',
                                      'Custos de compra e valor de estoque consumido são medidas separadas.']}


def analyze(attempt):
    try:
        return _analyze(attempt)
    except (KeyError, TypeError, AttributeError) as error:
        raise sessions.InvalidSession(f'estrutura de tentativa inválida: {error}') from None


def _analyze(a):
    require(type(a['schema_version']) is int and a['schema_version'] == 1 and a['protocol_id'] == PROTOCOL,
            'versão de protocolo incompatível')
    require(a['status'] in ('observed', 'synthetic'), 'tentativa pendente')
    require(isinstance(a['attempt_id'], str) and bool(a['attempt_id'].strip()), 'attempt_id obrigatório')
    require(type(a['monster_id']) is int and a['monster_id'] in TARGETS, 'alvo desconhecido')
    support = a['support_class']
    require(support in (None, *SUPPORTS), 'suporte desconhecido')
    expected = template(a['monster_id'], support)
    require(isinstance(a['participants'], list) and len(a['participants']) == len(expected['participants']),
            'número de participantes incompatível')
    members = {entry['member_id']: entry['session'] for entry in a['participants']}
    require(set(members) == ({'attacker', 'support'} if support else {'attacker'}), 'participantes duplicados/inválidos')
    counter_kills = sessions.integer(a['target_kills'], 'target_kills') + sessions.integer(a['summon_kills'], 'summon_kills')
    require(a['target_kills'] <= 1, 'uma ficha por chefe')
    combat = a['combat_timing']
    duration = sessions.integer(combat['elapsed_seconds'], 'combat.elapsed_seconds', 1)
    start = sessions.timestamp(combat['started_at'], 'combat.start')
    end = sessions.timestamp(combat['ended_at'], 'combat.end')
    require(end > start and abs((end - start).total_seconds() - duration) <= 5 and duration <= 600,
            'combate deve caber em 600 segundos e conferir com o relógio')
    if a['outcome'] == 'timeout':
        require(duration >= 595, 'timeout antes do limite de combate')
    results = {}; ids = set(); intervals = []; counts = []; buffs = []
    for entry in expected['participants']:
        key = entry['member_id']; record = members[key]; reference = entry['session']
        require(record['status'] == a['status'], 'status dos participantes diverge')
        require(record['actor'] == {'role': 'tester', 'group_id': 0, 'is_bot': False}
                and type(record['actor']['group_id']) is int and type(record['actor']['is_bot']) is bool,
                'somente testador isolado sem equipe/bot')
        require(record['environment'] == 'isolated_test' and record['kind'] == 'mvp', 'ensaio deve ser MVP isolado')
        require(record['build'] == reference['build'] and record['map'] == reference['map'], 'build/mapa difere do controle')
        require(record['party'] == reference['party'], 'party diverge da condição declarada')
        require(record['protocol_id'] == PROTOCOL, 'protocolo do participante diverge')
        sid = record['session_id']
        require(isinstance(sid, str) and sid.strip() and sid not in ids, 'session_id único obrigatório')
        ids.add(sid)
        require(record['attributes_changed_during_session'] is False and record['equipment_changed_during_session'] is False,
                'não alterar atributos/equipamentos durante a tentativa')
        require(record['buff_rules']['outside_support'] is False and record['buff_observations_complete'] is True,
                'declarar buffs completos e ausência de suporte fora da party')
        require(sessions.integer(record['ammunition_item_id'], 'ammunition_item_id') == reference['ammunition_item_id'], 'munição difere do controle')
        if key == 'attacker':
            require(any(row['item_id'] == 1750 for row in record['consumables']), 'reconciliar inventário de flechas')
        for field in ('hp', 'sp', 'aspd', 'weight', 'max_weight'):
            value = record['observed_panel'][field]
            require(type(value) in (int, float) and value == value and abs(value) != float('inf') and value >= 0,
                    'painel observado obrigatório')
        panel = record['observed_panel']
        require(panel['hp'] > 0 and 0 < panel['max_weight'] >= panel['weight'] and panel['aspd'] <= 197,
                'painel observado incompatível')
        require(record.get('level_observation') is not None, 'níveis inicial/final obrigatórios')
        objective = record['mvp_attempt']
        require(objective == dict(reference['mvp_attempt'], outcome=a['outcome'], target_kills=a['target_kills']),
                'objetivo do participante diverge')
        require(record['kills_counter'].get('scope') == reference['kills_counter']['scope'], 'escopo do contador diverge')
        result = sessions.analyze(record)
        require(result['kills'] == counter_kills, 'contador deve separar chefe e invocações sem duplicar')
        counts.append(record['kills_counter'])
        t = record['timing']; interval = (sessions.timestamp(t['started_at'], 'session.start'), sessions.timestamp(t['ended_at'], 'session.end'))
        require(interval[0] <= start < end <= interval[1], 'combate fora da sessão operacional')
        intervals.append(interval)
        used = {}
        require(isinstance(record['skills_used'], list) and isinstance(record['self_buffs_used'], list)
                and isinstance(record['received_buffs'], list), 'registrar habilidades e buffs')
        for skill in record['skills_used']:
            level = sessions.integer(skill['level'], 'skill.level', 1)
            require(skill['skill'] not in used and level <= record['build']['skills'].get(skill['skill'], 0),
                    'habilidade usada duplicada ou fora da build')
            used[skill['skill']] = (level, sessions.integer(skill['casts'], 'skill.casts', 1))
        for buff in record['self_buffs_used']:
            require(buff['skill'] in used and sessions.integer(buff['level'], 'buff.level', 1) == used[buff['skill']][0], 'buff próprio sem uso declarado')
        for buff in record['received_buffs']:
            buffs.append((key, buff))
        results[key] = dict(result, skills_used=used)
    require(all(interval == intervals[0] for interval in intervals), 'dupla deve usar a mesma janela operacional')
    require(all(counter == counts[0] for counter in counts), 'dupla deve compartilhar o mesmo contador observado')
    if a['outcome'] == 'death':
        require(sum(r['deaths'] for r in results.values()) > 0, 'derrota da party exige ao menos uma morte registrada')
    applications = Counter()
    for receiver, buff in buffs:
        source = buff['source_member']
        require(source in members and source != receiver, 'origem de buff fora da party')
        skill = buff['skill']; uses = results[source]['skills_used']
        require(skill in uses and sessions.integer(buff['level'], 'buff.level', 1) == uses[skill][0], 'buff recebido sem habilidade usada na origem')
        applications[source, skill] += sessions.integer(buff['applications'], 'buff.applications', 1)
    for (source, skill), amount in applications.items():
        require(amount <= results[source]['skills_used'][skill][1], 'buffs recebidos excedem aplicações declaradas')
    incoming = Counter(); outgoing = Counter(); item_in = Counter(); item_out = Counter()
    require(isinstance(a['transfers'], list), 'registrar transferências internas')
    for transfer in a['transfers']:
        sender, receiver = transfer['from'], transfer['to']
        require(sender in members and receiver in members and sender != receiver, 'transferência fora da party')
        amount = sessions.integer(transfer['zeny'], 'transfer.zeny')
        incoming[receiver] += amount; outgoing[sender] += amount
        require(isinstance(transfer['items'], list), 'itens transferidos devem ser lista')
        seen = set()
        for item in transfer['items']:
            item_id = sessions.integer(item['item_id'], 'transfer.item_id', 1)
            require(item_id not in seen, 'item transferido duplicado')
            seen.add(item_id)
            quantity = sessions.integer(item['amount'], 'transfer.amount', 1)
            item_in[receiver, item_id] += quantity; item_out[sender, item_id] += quantity
        require(amount > 0 or bool(seen), 'transferência vazia')
    for key, record in members.items():
        require(record['cash']['external_in'] == incoming[key] and record['cash']['external_out'] == outgoing[key],
                'transferências de zeny não fecham; financiamento externo durante o ensaio não é permitido')
        inventory = {row['item_id']: row for row in record['consumables']}
        required_items = {item for member, item in (*item_in.keys(), *item_out.keys()) if member == key}
        require(required_items <= inventory.keys(), 'item transferido ausente do inventário')
        for item_id, row in inventory.items():
            require(row['other_in'] == item_in[key, item_id] and row['other_out'] == item_out[key, item_id],
                    'transferências de itens não fecham')
    sinks = sum(sum(record['cash'][field] for field in ('npc_purchases', 'transport_fees', 'refine_fees', 'other_sinks')) for record in members.values())
    return {'status': a['status'], 'attempt_id': a['attempt_id'], 'monster_id': a['monster_id'],
            'condition': support or 'solo', 'outcome': a['outcome'], 'target_kills': a['target_kills'],
            'summon_kills': a['summon_kills'], 'combat_seconds': duration,
            'operational_seconds': int((intervals[0][1] - intervals[0][0]).total_seconds()),
            'party_deaths': sum(r['deaths'] for r in results.values()),
            'cash_net': sum(r['activity_cash_net'] for r in results.values()), 'npc_sinks': sinks,
            'consumption_replacement_value': sum(r['consumables_used_replacement_value'] for r in results.values()),
            'internal_transfers_cancelled': True, 'cash_and_consumption_are_separate': True,
            'player_performance_metrics': False, 'automatic_balance_changes': False,
            'provenance': 'declared_records_not_server_authenticated'}


def gate(records):
    results = [analyze(row) for row in records]
    require(bool(results) and all(row['status'] == 'observed' for row in results), 'painel aceita somente ensaios reais declarados')
    require(len({row['attempt_id'] for row in results}) == len(results), 'attempt_id duplicado')
    session_ids = [member['session']['session_id'] for row in records for member in row['participants']]
    require(len(set(session_ids)) == len(session_ids), 'session_id reutilizado entre tentativas')
    conditions = {row['condition'] for row in results}
    require('solo' in conditions and conditions <= {'solo', *SUPPORTS} and len(conditions) in (2, 3),
            'painel exige solo e uma ou duas classes de suporte separadas')
    counts = Counter((row['monster_id'], row['condition']) for row in results)
    require(counts == Counter({(target, condition): 3 for target in TARGETS for condition in conditions}),
            'painel incompleto: três tentativas por alvo/condição, incluindo falhas')
    intervals = sorted((sessions.timestamp(a['participants'][0]['session']['timing']['started_at'], 'start'),
                        sessions.timestamp(a['participants'][0]['session']['timing']['ended_at'], 'end')) for a in records)
    require(all(current[0] >= previous[1] for previous, current in zip(intervals, intervals[1:])), 'tentativas devem ser sequenciais')
    grouped = defaultdict(list)
    for row in results:
        grouped[row['monster_id'], row['condition']].append(row)
    summary = []
    for (target, condition), rows in sorted(grouped.items()):
        outcomes = Counter(row['outcome'] for row in rows); wins = outcomes['victory']
        sinks = sum(row['npc_sinks'] for row in rows)
        consumed = sum(row['consumption_replacement_value'] for row in rows)
        summary.append({'monster_id': target, 'condition': condition, 'attempts': len(rows),
                        'outcomes': dict(outcomes), 'npc_sinks_all_attempts': sinks,
                        'npc_sinks_per_victory_including_failures': round(sinks / wins, 3) if wins else None,
                        'consumption_value_all_attempts': consumed,
                        'consumption_value_per_victory_including_failures': round(consumed / wins, 3) if wins else None})
    return {'status': 'declared_mvp_panel_consistent', 'attempts': len(results), 'groups': summary,
            'player_performance_metrics': False, 'automatic_balance_changes': False,
            'limitations': ['Três repetições não demonstram superioridade de classe ou causalidade.',
                            'Consistência declarada não autentica observação; não foi medido DPS individual.',
                            'Custos/itens fecham pelos registros declarados; o protocolo não infere consumo pelo nome da skill.']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--panel', action='store_true')
    parser.add_argument('files', nargs='+', type=Path)
    args = parser.parse_args(argv)
    try:
        records = [json.loads(path.read_text(encoding='utf-8')) for path in args.files]
        require(args.panel or len(records) == 1, 'usar --panel para múltiplas tentativas')
        result = gate(records) if args.panel else analyze(records[0])
    except (OSError, ValueError, KeyError, TypeError) as error:
        print('MVP não apurado: ' + str(error), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
