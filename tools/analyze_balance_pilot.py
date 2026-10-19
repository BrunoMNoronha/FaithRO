#!/usr/bin/env python3
"""Gate a declared three-class pilot; never runs the game or promotes synthetic data."""
import argparse
import json
import math
from pathlib import Path
import sys

import analyze_balance_session as sessions

ROOT=Path(__file__).resolve().parents[1]
KIT=ROOT/'design-audit/balance-session-kit'
PROTOCOL_ID='faithro-juperos2-progression-v2'
CLASSES=frozenset(('Sniper','Assassin_Cross','High_Wizard'))


def gate(records):
    if len(records)!=3:
        raise sessions.InvalidSession('piloto exige três sessões, uma por classe')
    found=set();ids=set();intervals=[];results=[]
    for s in records:
        result=sessions.analyze(s)
        name=s['build']['class']
        if name not in CLASSES or name in found:
            raise sessions.InvalidSession('piloto exige Sniper, SinX e HW sem duplicar classes')
        found.add(name)
        if s['status']!='observed' or s['environment']!='isolated_test' or s['actor']['role']!='tester':
            raise sessions.InvalidSession('piloto aceita somente ensaios reais em ambiente isolado')
        if s.get('protocol_id')!=PROTOCOL_ID:
            raise sessions.InvalidSession('versão de protocolo incompatível')
        identifier=s.get('session_id')
        if not isinstance(identifier,str) or not identifier.strip() or identifier in ids:
            raise sessions.InvalidSession('session_id único e preenchido obrigatório')
        ids.add(identifier)
        if s['kind']!='farm' or s['map']!='juperos_02' or s['build']['base_level']!=99:
            raise sessions.InvalidSession('piloto deve iniciar em 99 em Juperos 2')
        if abs(result['elapsed_seconds']-1800)>5:
            raise sessions.InvalidSession('piloto exige 30 minutos corridos por sessão')
        if s.get('level_observation',{}).get('mode')!='progression':
            raise sessions.InvalidSession('piloto mede progressão desde 99, sem fingir nível constante')
        if s.get('attributes_changed_during_session') is not False or s.get('equipment_changed_during_session') is not False:
            raise sessions.InvalidSession('não distribuir atributos nem mudar equipamento dentro da sessão')
        expected=json.loads((KIT/f'template-{name.lower()}-99.json').read_text(encoding='utf-8'))
        if s['build']!=expected['build']:
            raise sessions.InvalidSession('build difere da ficha de referência do piloto')
        if s['buff_rules']['outside_support'] is not False:
            raise sessions.InvalidSession('piloto solo não aceita suporte externo')
        buffs=s.get('self_buffs_used')
        if not isinstance(buffs,list):
            raise sessions.InvalidSession('registrar os buffs próprios usados, ou lista vazia')
        for buff in buffs:
            amount=sessions.integer(buff['level'],'self_buff.level',1)
            if amount>s['build']['skills'].get(buff['skill'],0):
                raise sessions.InvalidSession('buff próprio não consta nas habilidades da build')
            if buff['skill']=='ASC_EDP' and not any(x['item_id']==678 and x['consumed']>0 for x in s['consumables']):
                raise sessions.InvalidSession('EDP usado sem Poison Bottle reconciliada')
        panel=s.get('observed_panel',{})
        for field in ['hp','sp','aspd','weight','max_weight']:
            value=panel.get(field)
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0:
                raise sessions.InvalidSession('preencher painel real de HP/SP/ASPD/peso')
        if panel['hp']<=0 or panel['max_weight']<=0 or panel['weight']>panel['max_weight']:
            raise sessions.InvalidSession('painel de sobrevivência/peso inconsistente')
        intervals.append((sessions.timestamp(s['timing']['started_at'],'start'),
                          sessions.timestamp(s['timing']['ended_at'],'end')))
        results.append(dict(result,class_name=name,session_id=identifier))
    for previous,current in zip(sorted(intervals),sorted(intervals)[1:]):
        if current[0]<previous[1]:
            raise sessions.InvalidSession('piloto deve ser sequencial, sem sobrepor sessões')
    return {'status':'pilot_records_consistent','protocol_id':PROTOCOL_ID,'sessions':results,
            'comparison_basis':'progression_from_common_level_99_start_not_fixed_level_dps',
            'recommendation':'Repetir antes de balancear; uma sessão por classe não prova superioridade.',
            'automatic_balance_changes':False,'player_performance_metrics':False,
            'provenance':'declared_records_not_server_authenticated'}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sessions',nargs='+',type=Path)
    args=parser.parse_args(argv)
    try:
        result=gate([json.loads(p.read_text(encoding='utf-8')) for p in args.sessions])
    except (OSError,ValueError,KeyError,TypeError) as error:
        print('Piloto não liberado: '+str(error),file=sys.stderr);return 2
    print(json.dumps(result,ensure_ascii=False,indent=2));return 0


if __name__=='__main__':raise SystemExit(main())
