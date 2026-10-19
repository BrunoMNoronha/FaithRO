"""Generate pending, local-only session sheets from verified installed data.
Never overwrite recorded measurements; templates must be copied before filling.
"""
import json
import hashlib
from pathlib import Path

HERE=Path(__file__).resolve().parent


def write_new(path, data):
    with path.open('x',encoding='utf-8') as handle:
        handle.write(json.dumps(data,ensure_ascii=False,indent=2)+'\n')


def prepare():
    installed=json.loads((HERE/'installed-data.json').read_text(encoding='utf-8'))
    review=json.loads((HERE.parent/'balance-review-20261019/snapshot.json').read_text(encoding='utf-8'))
    curve_hash=hashlib.sha256((HERE.parents[1]/'docs/progressao.csv').read_bytes()).hexdigest()
    families={'Lord_Knight':'Knight','Paladin':'Crusader','Sniper':'Hunter','Assassin_Cross':'Assassin',
              'High_Wizard':'Wizard','High_Priest':'Priest','Champion':'Monk','Professor':'Sage',
              'Creator':'Alchemist','Whitesmith':'Blacksmith','Stalker':'Rogue','Clown':'BardDancer','Gypsy':'BardDancer'}
    gear_checks=[]
    for build in review['builds']:
        for item_id in [2304,2404,2504,build['weapon_id']]:
            item=installed['gear'][str(item_id)];family=families[build['class']]
            allowed=item['Jobs']
            job_ok=(allowed.get(family,allowed.get('All',False)) if allowed else True)
            level_ok=(item.get('EquipLevelMin') or 1)<=build['level']<=(item.get('EquipLevelMax') or 255)
            sex='Female' if build['class']=='Gypsy' else 'Male'
            sex_ok=not item['Gender'] or item['Gender']==sex
            assert job_ok and level_ok and sex_ok, (build,item)
            assert not item['Classes'], 'Review non-default class restrictions explicitly'
            gear_checks.append({'class':build['class'],'level':build['level'],'purpose':build['purpose'],
                                'item_id':item_id,'compatible':True})
    slots=['head_top','head_mid','head_low','armor','garment','shoes','right_hand','left_hand','accessory1','accessory2']
    maps={99:'juperos_02',150:'abbey03',200:'thor_v01',255:'lhz_dun03'}
    templates=[]
    for build in review['builds']:
        if build['class'] not in installed['skills'] or build['purpose']!='PvM':continue
        class_name=build['class'];level=build['level']
        equipment_ids={'armor':2304,'garment':2504,'shoes':2404,'right_hand':build['weapon_id']}
        session={'schema_version':1,'status':'pending','kind':'farm','environment':'isolated_test',
                 'protocol_id':'faithro-juperos2-progression-v2' if level==99 else 'faithro-farm-panel-v2',
                 'session_id':None,'attributes_changed_during_session':False,'equipment_changed_during_session':False,
                 'level_observation':{'mode':'progression' if level<255 else 'fixed','start':level,'end':None},
                 'exp_progress':{'start_level':level,'start_exp':None,'end_level':None,'end_exp':None,'curve_sha256':curve_hash} if level<255 else None,
                 'map':maps[level],'actor':{'role':'tester','group_id':0,'is_bot':False},
                 'administrative_operations_present':False,
                 'build':{'class':class_name,'base_level':level,'job_level':70,
                          'stats_SAVIDL':build['stats_SAVIDL'],
                          'equipment':[{'slot':slot,'item_id':equipment_ids.get(slot,0),'refine':0,'cards':[]} for slot in slots],
                          'skills':installed['skills'][class_name]['skills']},
                 'observed_panel':{'hp':None,'sp':None,'aspd':None,'weight':None,'max_weight':None},
                 'buff_rules':{'outside_support':False,'record_self_buffs':True},
                 'self_buffs_used':None,
                 'timing':{'source':'session_stopwatch','elapsed_seconds':None,'started_at':None,'ended_at':None,
                           'includes_travel_sales_recovery':True},
                 'kills_counter':{'method':'manual_tally','start':None,'end':None,
                                  'calibration':{'known_kills':10,'counter_increase':None}},
                 'deaths':None,'exp_gained':None,'exp_measurement':'cumulative_counter_or_level_curve' if level<255 else 'not_applicable_at_level_cap',
                 'cash':{key:None for key in ['start','end','npc_sales','quest_rewards','npc_purchases','transport_fees',
                                              'refine_fees','other_sinks','external_in','external_out']},
                 'consumables_complete':False,'consumables':[],
                 'notes':['Copiar para arquivo de medição antes de preencher.',
                          'status observed somente após sessão real; synthetic somente para testes de software.',
                          'Preencher 0 nos movimentos ausentes; não estimar valores desconhecidos.',
                          'Registrar bônus reais da arma, passivas e buffs no painel.',
                          'Inventário: quantidades e preço efetivo por fornecedor; não usar Buy genérico para loja custom.']}
        filename=f'template-{class_name.lower()}-{level}.json'
        write_new(HERE/filename,session)
        templates.append({'class':class_name,'level':level,'file':filename,'map':maps[level]})
    targets=[{'id':1086,'name':'GOLDEN_BUG','level':99,'file':'template-mvp-gtb.json'},
             {'id':1039,'name':'BAPHOMET','level':150,'file':'template-mvp-baphomet.json'},
             {'id':1751,'name':'RANDGRIS','level':255,'file':'template-mvp-randgris.json'},
             {'id':1832,'name':'IFRIT','level':255,'file':'template-mvp-ifrit.json'}]
    for target in targets:
        mvp=json.loads((HERE/f"template-sniper-{target['level']}.json").read_text(encoding='utf-8'))
        mvp.update(kind='mvp',map='RECORD_ACTUAL_MAP',
                   protocol_id='faithro-mvp-panel-v2',
                   mvp_attempt={'monster_id':target['id'],'outcome':None,'target_kills':None},
                   party={'size':None,'support_class':None},
                   notes=mvp['notes']+['Uma ficha por tentativa: victory, death, timeout ou abandoned.',
                                       'Não misturar mortes de invocações com vitória sobre o MVP.'])
        write_new(HERE/target['file'],mvp)
    plan={'schema_version':1,'status':'prepared_not_executed','reference':{'exp_rate':300,'max_level':255,'stat_cap':185,'aspd_cap':197},
          'source_snapshot':installed['timestamp_utc'],'gear_checks':gear_checks,'templates':templates,
          'pilot':{'protocol_id':'faithro-juperos2-progression-v2','sessions':3,'duration_minutes_each':30,'classes':list(installed['skills']),
                   'base_level':99,'map':'juperos_02','total_minutes':90,
                   'comparison_basis':'progression_from_common_start_not_fixed_level_dps',
                   'gate':'Only proceed after timing, counters, cash and consumables reconcile.'},
          'farm_panel':{'primary_routes':maps,'additional_routes':[{'level':150,'map':'man_fild02'},{'level':255,'map':'tha_t09'}],
                        'classes':list(installed['skills']),'repetitions':3,'minutes_per_session':30,
                        'cells':18,'sessions':54,'total_hours':27,
                        'pilot_counts_toward_repetitions_if_valid':True},
          'mvp_panel':{'targets':targets,
                       'modes':['solo','duo'],'support_options':['High_Priest','Professor'],
                       'attempts_per_target_mode':3,'attempt_limit_minutes':10,
                       'attempts':24,'combat_time_limit_hours':4,
                       'notes':['Control targets at 99/150; final targets at 255. Record exact build per attempt.',
                                'Support options are alternatives; testing both separately expands the panel.',
                                'Preparation and reset time are additional; none executed by this package.']},
          'acceptance':['No production combat or gameplay changes by preparation scripts.',
                        'No performance results until real timed sessions are recorded.',
                        'No build/route comparison if equipment, buffs or buying rules differ without disclosure.',
                        'Account for every declared cash movement and consumable before publishing rates.',
                        'Treat failure, timeout and inability to survive as results, not missing successes.'],
          'limitations':['Tool checks declared-data consistency, not authenticity of observations.',
                         'Skill legality and equipment compatibility were checked for these prepared panels only.',
                         'The kit does not provision an isolated server, create characters or run battles.']}
    write_new(HERE/'plan.json',plan)
    print(f'Prepared {len(templates)} farm templates, four MVP templates, {len(gear_checks)} equipment checks.')


if __name__=='__main__':prepare()
