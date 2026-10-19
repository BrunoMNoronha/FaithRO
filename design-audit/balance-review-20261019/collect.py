"""Read-only snapshot; run over SSH with python3 -B -, never calls builder.main."""
import collections
import datetime
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import subprocess
import sys

sys.dont_write_bytecode = True
R = Path('/home/rathena/rathena')
spec = importlib.util.spec_from_file_location('gamedb', '/root/faithro/deploy/web/tools/build_gamedb.py')
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)

def sql(db, query):
    assert query.lstrip().upper().startswith(('SELECT ', 'SHOW '))
    out = subprocess.check_output(['mariadb', '-N', '-B', db, '-e', query], text=True)
    return [line.split('\t') for line in out.splitlines()]

def body(rel):
    return b.collect_body(R, rel)

def text(rel):
    return (R / rel).read_bytes().decode('cp1252' if '/ptbr/' in rel else 'utf-8', errors='replace')

I = b.merge_by_id(body('db/pre-re/item_db.yml') + body('db/import/item_db.yml'))
M = b.merge_by_id(body('db/pre-re/mob_db.yml') + body('db/import/mob_db.yml'))
items = {i['id']: i for i in b.build_items(I)}
rates = b.load_rates(R)
ratios = b.load_item_ratios(R, M)
mobs, drops = b.build_mobs(M, {e['AegisName']: k for k, e in I.items()},
                           {k: e.get('Type', 'Etc') for k, e in I.items()}, rates, ratios)
mob = {m['id']: m for m in mobs}
spawns = b.build_spawns(R)
sources = b.npc_sources(R)
z = collections.defaultdict(float)
for d in drops:
    if not d['mvp']:
        z[d['mob_id']] += d['rate_final'] / 10000 * items[d['item_id']]['sell']

# Compare every derived drop and spawn with the current website tables.
actual_drops = {tuple(map(int, row)) for row in sql('faithro_web',
    'SELECT mob_id,idx,item_id,rate,rate_final,mvp,steal_protected FROM mob_drops')}
expected_drops = {tuple(d[k] for k in ['mob_id','idx','item_id','rate','rate_final','mvp','steal_protected']) for d in drops}
actual_spawns = {(int(a), mp, int(n)) for a, mp, n in sql('faithro_web', 'SELECT mob_id,map,amount FROM mob_spawns')}
expected_spawns = {(s['mob_id'], s['map'], s['amount']) for s in spawns}
official = collections.Counter()
for rel, data in sources.items():
    if data is None or rel.endswith('mobs_x10.txt'):
        continue
    for line in data.decode(errors='replace').splitlines():
        m = b.SPAWN_RE.match(line)
        if m:
            official[(int(m[2]), m[1])] += int(m[3])

routes = []
for mp in ['juperos_01','juperos_02','abbey01','abbey03','lhz_dun03','thor_v01','thor_v03','tha_t09','man_fild02']:
    selected = [s for s in spawns if s['map'] == mp and s['mob_id'] in mob and not mob[s['mob_id']]['is_mvp']]
    n = sum(s['amount'] for s in selected)
    e = sum(s['amount'] * mob[s['mob_id']]['base_exp'] * rates['base_exp_rate']/100 for s in selected)/n
    value = sum(s['amount'] * z[s['mob_id']] for s in selected)/n
    routes.append({'map': mp, 'official_static_non_mvp': sum(official[s['mob_id'], mp] for s in selected),
                   'active_static_non_mvp': n, 'base_exp_per_kill': round(e), 'npc_sale_per_kill': round(value, 2),
                   'scenarios': [{'kills_per_hour_assumed': k, 'exp_G': round(k*e/1e9, 3),
                                  'gross_zeny_M': round(k*value/1e6, 3),
                                  'gross_with_overcharge10_M': round(k*value*1.24/1e6, 3)} for k in [150,300,600]],
                   'composition': [{'id':s['mob_id'], 'name':mob[s['mob_id']]['aegis'], 'amount':s['amount'],
                                    'hp':mob[s['mob_id']]['hp']} for s in selected]})

# All metrics below exclude team, bot (group 1), server accounts and admin item/zeny operations.
join = ' JOIN ragnarok.`char` c ON c.char_id=t.char_id JOIN ragnarok.login l ON l.account_id=c.account_id '
where = " l.group_id=0 AND l.sex<>'S' AND t.type<>'A' "
players = sql('ragnarok', "SELECT COUNT(DISTINCT l.account_id),COUNT(c.char_id),COALESCE(MAX(c.base_level),0),COALESCE(SUM(c.online),0) FROM login l LEFT JOIN `char` c USING(account_id) WHERE l.group_id=0 AND l.sex<>'S'")
zeny_logs = sql('ragnarok_log', 'SELECT t.type,COUNT(*),SUM(t.amount) FROM zenylog t'+join+'WHERE'+where+'GROUP BY t.type')
loot_logs = sql('ragnarok_log', 'SELECT t.type,COUNT(*),SUM(t.amount) FROM picklog t'+join+'WHERE'+where+'GROUP BY t.type')
mvp_logs = sql('ragnarok_log', "SELECT COUNT(*) FROM mvplog t JOIN ragnarok.`char` c ON c.char_id=t.kill_char_id JOIN ragnarok.login l USING(account_id) WHERE l.group_id=0 AND l.sex<>'S'")

# Budgeted candidates, without equipment stats. Job 70 is an explicit test assumption.
jobs = {}
for rel in ['db/pre-re/job_stats.yml','db/pre-re/job_basepoints.yml','db/pre-re/job_aspd.yml','db/pre-re/job_exp.yml','db/import/job_stats.yml']:
    for e in body(rel):
        for j, enabled in e.get('Jobs', {}).items():
            if enabled:
                jobs.setdefault(j, {}).update({k:v for k,v in e.items() if k!='Jobs'})
points = {e['Level']:e['Points'] for e in body('db/import/statpoint.yml')}
profiles = {'Lord_Knight':('SAVDIL','SVDAIL','2hSword',1158),
            'Paladin':('VSDAIL','VSIDAL','1hSpear',1408),
            'Sniper':('DAVISL','DAVLSI','Bow',1708),
            'Assassin_Cross':('SAVDIL','SVDIAL','Katar',1253),
            'High_Wizard':('IDVSAL','IVDSAL','Staff',1608),
            'High_Priest':('IVDSAL','VIDSAL','Staff',1608),
            'Champion':('SIDVAL','SIDVAL','Knuckle',1804),
            'Professor':('IDVSAL','VIDSAL','Book',1550),
            'Creator':('IVDSAL','IVDSAL','1hAxe',1306),
            'Whitesmith':('SAVDIL','SVDAIL','2hAxe',1355),
            'Stalker':('DAVISL','SAVDIL','Bow',1708),
            'Clown':('DIVASL','VDIASL','Musical',1904),
            'Gypsy':('DIVASL','VADISL','Whip',1953)}
names = dict(zip('SAVIDL', ['Str','Agi','Vit','Int','Dex','Luk']))
def cost(v): return sum(1+(n+9)//10 for n in range(1,v))
def allocate(order, level):
    budget = points[level]+52
    tier = {99:[99,90,70,40,20,1],150:[150,130,110,80,40,1],
            200:[185,170,140,110,60,1],255:[185,185,160,140,80,1]}[level]
    targets = dict(zip(order, tier))
    if sum(cost(v) for v in targets.values()) <= budget:
        return targets, sum(cost(v) for v in targets.values()), budget
    low, high = 0., 1.
    for _ in range(50):
        scale=(low+high)/2
        candidate={s:max(1,int(1+(v-1)*scale)) for s,v in targets.items()}
        if sum(cost(v) for v in candidate.values())<=budget: low=scale
        else: high=scale
    stats={s:max(1,int(1+(v-1)*low)) for s,v in targets.items()}
    used=sum(cost(v) for v in stats.values())
    assert used<=budget and max(stats.values())<=185
    return stats,used,budget
def base_stat(j,level,kind):
    key='Hp' if kind=='hp' else 'Sp'
    explicit={e['Level']:e[key] for e in j.get('Base'+key,[])}
    if level in explicit: return explicit[level]
    return (35 if kind=='hp' else 10)+math.floor(level*j.get(key+'Increase',500 if kind=='hp' else 100)/100)+sum(math.floor(j.get(key+'Factor',0)/100*n+.5) for n in range(2,level+1))
builds=[]
for name,(pvm,mvp,weapon,item_id) in profiles.items():
    j=jobs[name]
    bonus={s:sum(e.get(names[s],0) for e in j.get('BonusStats',[]) if e['Level']<=70) for s in names}
    for level in [99,150,200,255]:
        for purpose,order in [('PvM',pvm),('MVP',mvp)]:
            stats,used,budget=allocate(order,level)
            total={s:v+bonus[s] for s,v in stats.items()}
            hp=int(base_stat(j,level,'hp')*(1+total['V']/100)*1.25)
            sp=int(base_stat(j,level,'sp')*(1+total['I']/100)*1.25)
            delay=j['BaseASPD'][weapon]
            amotion=max(30,delay-delay*(4*total['A']+total['D'])//1000)
            builds.append({'class':name,'level':level,'purpose':purpose,'job_level_assumed':70,
                           'stats_SAVIDL':[stats[s] for s in 'SAVIDL'],'used':used,'budget':budget,
                           'hp_without_equipment_or_skills':hp,'sp_without_equipment_or_skills':sp,
                           'aspd_without_buffs_passives_or_shield':round(200-amotion/10,1),
                           'weapon_id':item_id,'weapon':items[item_id]['name']})

custom='npc/custom/faithro/ptbr/custom/'
shop=[]
for line in text(custom+'itemmall.txt').splitlines():
    if '\tshop\t' not in line or line.lstrip().startswith('//'): continue
    for item,price in re.findall(r'(\d+):(-?\d+)',line):
        item,price=int(item),int(price)
        if item in items:
            price=items[item]['buy'] if price<0 else price
            shop.append({'id':item,'name':items[item]['name'],'buy':price,'sell':items[item]['sell'],
                         'discount24_buy':price*76//100,'overcharge24_sell':items[item]['sell']*124//100})
paths=['conf/import/char_conf.txt','conf/import/battle_conf.txt','conf/import/log_conf.txt','db/import/statpoint.yml','db/import/job_stats.yml','db/import/mob_item_ratio.yml','npc/custom/faithro/optional.conf',
       custom+'quests/hunting_missions.txt',custom+'etc/monster_arena.txt',custom+'etc/lottery.txt',custom+'events/holiday/valentinesdayexp.txt',custom+'warper.txt',custom+'itemmall.txt']
checks={'ladder_not_loaded':custom+'events/mvp_ladder.txt' not in sources,
        'teams_not_loaded':all(custom+'battleground/'+f not in sources for f in ['bg_emp.txt','bg_pvp.txt']),
        'tine_invisible_controller':'\tscript\tFaithRO_ValentineBonus\t-1,' in text(custom+'events/holiday/valentinesdayexp.txt'),
        'arena_no_zeny_sale':'L_Sell:' not in text(custom+'etc/monster_arena.txt'),
        'lottery_guard':'if (#LID == $LID && #LW1 != 0) goto L_DoubleTicket;' in text(custom+'etc/lottery.txt'),
        'hunting_modifier6':'getbattleflag("job_exp_rate")/100,6;' in text(custom+'quests/hunting_missions.txt'),
        'starting_potions':'start_items_pre: 1201,1,2:2301,1,16:501,100,0' in text('conf/import/char_conf.txt')}
examples=[dict(d,mob=mob[d['mob_id']]['aegis'],item=items[d['item_id']]['name']) for d in drops if (mob[d['mob_id']]['aegis'],d['item_id']) in [('MAYA_PUPLE',969),('GOLDEN_BUG',969),('THANATOS',7444),('GEMINI',12040)]]
refine=[]
for e in body('db/pre-re/refine.yml') + body('db/import/refine.yml'):
    for lvl in e.get('Levels',[]):
        normal=[]
        for lv in lvl.get('RefineLevels',[]):
            for chance in lv.get('Chances',[]):
                if chance['Type']=='Normal': normal.append(dict(level=lv['Level'],**chance))
        refine.append({'group':e['Group'],'weapon_level':lvl['Level'],'normal':normal})
skill_names={'PA_SACRIFICE','MO_EXTREMITYFIST','CR_ACIDDEMONSTRATION','ASC_EDP','SN_SHARPSHOOTING','WZ_STORMGUST','HP_ASSUMPTIO','PF_SOULCHANGE','BA_POEMBRAGI'}
skills=[{k:v for k,v in e.items() if k in ['Id','Name','MaxLevel','CastTime','AfterCastActDelay','Cooldown','Requires']} for e in b.merge_by_id(body('db/pre-re/skill_db.yml')+body('db/import/skill_db.yml')).values() if e.get('Name') in skill_names]
source_paths=['src/map/mob.cpp','src/map/pc.cpp','src/map/status.cpp','src/map/battle.cpp','src/config/core.hpp']
result={'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'git_commit':subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip(),
        'checks':checks,'hashes':{p:hashlib.sha256((R/p).read_bytes()).hexdigest() for p in paths},
        'normalized_hashes':{p:hashlib.sha256(text(p).replace('\r\n','\n').encode()).hexdigest() for p in paths},
        'source_hashes':{p:hashlib.sha256((R/p).read_bytes()).hexdigest() for p in source_paths},
        'counts':{'items':len(items),'mobs':len(mobs),'drops':len(drops),'spawn_pairs':len(spawns)},
        'website':{'drop_rows_different':len(actual_drops^expected_drops),'spawn_rows_different':len(actual_spawns^expected_spawns)},
        'rates':rates,'maps':routes,'players':players,'player_zeny_logs':zeny_logs,'player_item_logs':loot_logs,'player_mvp_logs':mvp_logs,
        'budgets':{l:points[l]+52 for l in [99,150,200,255]},'cost_1_to_185':cost(185),'builds':builds,
        'shop':shop,'arbitrage_candidates':[x for x in shop if x['overcharge24_sell']>x['discount24_buy']],
        'reference_items':{k:items[k] for k in [501,503,504,505,506,601,715,717,678,1750,2304,2404,2504]},
        'refine':refine,'skills':skills,
        'warp_database':sql('ragnarok',"SELECT varname,value FROM mapreg WHERE varname IN ('$QW_DW_OFF','$QW_TW_OFF')"),
        'drop_examples':examples,
        'mvp':[dict(m,npc_sale_expected=round(z[m['id']],2)) for m in mobs if m['aegis'] in ['GOLDEN_BUG','BAPHOMET','RANDGRIS','IFRIT']],
        'normal_active_above100':[m for m in mobs if m['level']>100 and m['class']=='Normal' and not m['is_mvp'] and m['base_exp']>0 and m['id'] in {s['mob_id'] for s in spawns}]}
print(json.dumps(result,ensure_ascii=True))
