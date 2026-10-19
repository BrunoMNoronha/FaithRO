"""Installed items, active normal shop prices and prerequisite-complete skill panels.
Read-only; run with python3 -B - over SSH. Does not instantiate a game client.
"""
import datetime
import importlib.util
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode=True
R=Path('/home/rathena/rathena')
spec=importlib.util.spec_from_file_location('builder','/root/faithro/deploy/web/tools/build_gamedb.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
items=b.merge_by_id(b.collect_body(R,'db/pre-re/item_db.yml')+b.collect_body(R,'db/import/item_db.yml'))
tree={e['Job']:e for e in b.collect_body(R,'db/pre-re/skill_tree.yml')}
for e in b.collect_body(R,'db/import/skill_tree.yml'):
    tree.setdefault(e['Job'],{}).update(e)
panels={
 'Sniper':{'first':'Archer','second':'Hunter','requested':{'AC_DOUBLE':10,'AC_CONCENTRATION':10,'SN_SHARPSHOOTING':5,'SN_SIGHT':10,'SN_WINDWALK':10}},
 'Assassin_Cross':{'first':'Thief','second':'Assassin','requested':{'TF_DOUBLE':10,'TF_MISS':10,'AS_KATAR':10,'AS_SONICBLOW':10,'AS_CLOAKING':3,'ASC_KATAR':5,'ASC_EDP':5}},
 'High_Wizard':{'first':'Mage','second':'Wizard','requested':{'MG_SRECOVERY':10,'MG_SIGHT':1,'MG_COLDBOLT':5,'MG_FROSTDIVER':1,'MG_LIGHTNINGBOLT':4,'WZ_JUPITEL':5,'WZ_STORMGUST':10,'WZ_QUAGMIRE':5,'HW_MAGICPOWER':10,'HW_SOULDRAIN':10}},
}
for name,panel in panels.items():
    nodes={};owners={}
    for job in ['Novice',panel['first'],panel['second'],name]:
        for node in tree[job].get('Tree',[]):
            nodes[node['Name']]=node;owners[node['Name']]=job
    allocation={};stack=set()
    def require(skill,level):
        if allocation.get(skill,0)>=level:return
        assert skill not in stack, 'cycle in skill prerequisites'
        node=nodes[skill];assert level<=node['MaxLevel']
        stack.add(skill)
        for req in node.get('Requires',[]):require(req['Name'],req['Level'])
        stack.remove(skill);allocation[skill]=level
    require('NV_BASIC',9)
    for skill,level in panel['requested'].items():require(skill,level)
    spent={'novice':0,'first':0,'second':0}
    for skill,level in allocation.items():
        bucket='novice' if owners[skill]=='Novice' else 'first' if owners[skill]==panel['first'] else 'second'
        spent[bucket]+=level
    assert spent['novice']<=9 and spent['first']<=49 and spent['second']<=69
    panel.update(skills=allocation,points_spent=spent,points_budget={'novice':9,'first':49,'second':69},
                 assumptions={'first_job_level_before_change':50,'second_job_level':70})

sources=b.npc_sources(R,('npc/pre-re/scripts_main.conf',))
stock=[]
for path,content in sources.items():
    if content is None:continue
    for number,line in enumerate(content.decode(errors='replace').splitlines(),1):
        line=line.split('//',1)[0]
        if '\tshop\t' not in line:continue
        parts=line.split('\t');shopname=parts[2] if len(parts)>2 else '?'
        for item,price in re.findall(r'(\d+):(-?\d+)',parts[-1]):
            item,price=int(item),int(price)
            if item not in items:continue
            if price<0:price=int(items[item].get('Buy',0))
            sell=int(items[item].get('Sell',int(items[item].get('Buy',0))//2))
            stock.append({'item_id':item,'price':price,'npc_sell':sell,'npc':shopname,'source':path,'line':number})
wanted=[501,504,505,601,715,717,678,1750,7135,7136]
prices=[]
for item_id in wanted:
    offers=[row for row in stock if row['item_id']==item_id]
    prices.append({'item_id':item_id,'name':items[item_id]['Name'],'offers':offers,
                   'min_price':min((x['price'] for x in offers),default=None),
                   'max_price':max((x['price'] for x in offers),default=None)})
gear_ids=[2304,2404,2504,1158,1408,1708,1253,1608,1804,1550,1306,1355,1904,1953]
gear={i:{k:items[i].get(k) for k in ['Id','AegisName','Name','Type','SubType','Jobs','Classes','Gender','EquipLevelMin','EquipLevelMax','Locations','Script']} for i in gear_ids}
arbitrage=[]
for item in {r['item_id'] for r in stock}:
    offers=[row for row in stock if row['item_id']==item]
    cheapest=min(offers,key=lambda x:x['price'])
    if cheapest['npc_sell']*124//100>cheapest['price']*76//100:
        arbitrage.append(dict(cheapest,discount_buy=cheapest['price']*76//100,overcharge_sell=cheapest['npc_sell']*124//100))
print(json.dumps({'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  'skills':panels,'gear':gear,'prices':prices,'normal_shop_entries':len(stock),
                  'arbitrage_candidates':arbitrage,'missing_include_paths':[p for p,c in sources.items() if c is None],
                  'limitations':['only literal active shop declarations; scripted traders/barters/cash shops excluded',
                                 'Prices are before character discounts; source includes may contain runtime restrictions.']},ensure_ascii=True))
