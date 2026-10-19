"""Service NPC QA, exclusively inside isolated_char_check's temporary namespaces.

Installed NPC bytes are unchanged. A separate QA observer seeds synthetic levels,
funds and unlocks and records native character variables in the fresh lab database.
No combat, production SQL, production client or player-performance measurements.
"""
import hashlib
from pathlib import Path
import re
import shutil
import time

HARNESS = r'''
-	script	QA_ServiceObserver	-1,{
 end;
OnPCLoginEvent:
 if (strcharinfo(0) != "IsolatedQA0") end;
 addtimer 200,"QA_ServiceObserver::OnObserve";
 detachrid;
 end;
OnObserve:
 query_sql("SELECT seq,action,level,money FROM qa_command WHERE id=1",.@seq,.@action,.@level,.@money);
 if (.@seq > @QA_seq) {
  if (.@action == 1) {
   jobchange Job_Sniper; BaseLevel=.@level; Zeny=.@money;
   sc_end SC_BLESSING; sc_end SC_INCREASEAGI; @HD=0;
   percentheal 100,100; heal 1-Hp,-Sp;
   lastwarp$=""; lastwarpx=0; lastwarpy=0;
   ##QWS_T_Unlock=0; ##QWS_D_Unlock=0; $QW_DW_OFF=1;
   warp "prontera",158,190;
  }
  if (.@action == 2) warp "prontera",158,190;
  if (.@action == 3) warp "prontera",154,282;
  if (.@action == 4) warp "prontera",147,173;
  if (.@action == 5) { $QW_DW_OFF=0; ##QWS_T_Unlock=3; ##QWS_D_Unlock=16384; }
  if (.@action == 6) { percentheal 100,100; heal 1-Hp,-Sp; }
  if (.@action == 7) Zeny=.@money;
  @QA_seq=.@seq;
 }
 getmapxy(.@map$,.@x,.@y,BL_PC);
 query_sql("INSERT INTO qa_service_snapshots(seq,level,zeny,hp,maxhp,sp,maxsp,blessing,agi,blessing_ms,agi_ms,hd,city_fee,dungeon_fee,town_unlock,dungeon_unlock,dungeon_off,poison,arrow,blue,redgem,yellowgem,bluegem,acid,fire,mapname,x,y,lastwarp) VALUES ("+@QA_seq+","+BaseLevel+","+Zeny+","+Hp+","+MaxHp+","+Sp+","+MaxSp+","+getstatus(SC_BLESSING,1)+","+getstatus(SC_INCREASEAGI,1)+","+getstatus(SC_BLESSING,5)+","+getstatus(SC_INCREASEAGI,5)+","+@HD+","+callfunc("F_FaithRO_WarpFee","prontera")+","+callfunc("F_FaithRO_WarpFee","juperos_01")+","+##QWS_T_Unlock+","+##QWS_D_Unlock+","+$QW_DW_OFF+","+countitem(678)+","+countitem(1750)+","+countitem(505)+","+countitem(716)+","+countitem(715)+","+countitem(717)+","+countitem(7136)+","+countitem(7135)+",'"+.@map$+"',"+.@x+","+.@y+",'"+lastwarp$+"')");
 addtimer 500,"QA_ServiceObserver::OnObserve";
 // Native end sends CLOSE_DIALOG while a RID is attached. Keep observation
 // silent so it cannot overwrite the client's buy/sell prompt or shop list.
 detachrid;
 end;
}
'''

COLUMNS='seq level zeny hp maxhp sp maxsp blessing agi blessing_ms agi_ms hd city_fee dungeon_fee town_unlock dungeon_unlock dungeon_off poison arrow blue redgem yellowgem bluegem acid fire mapname x y lastwarp'.split()


def run(folder, source, sql, spawn, wait_for, log, player_password):
    assert Path('/proc/1/comm').read_text().strip().startswith('python')
    assert folder.resolve().parent==Path('/tmp') and folder.name.startswith('faithro-char-qa-')
    prefix='npc/custom/faithro/ptbr/custom/'
    files=['npc/other/Global_Functions.txt','npc/mapflag/town.txt',
           *[prefix+p for p in ['healer.txt','warper.txt','etc/quest_warper.txt','itemmall.txt']]]
    hashes={name:hashlib.sha256((source/name).read_bytes()).hexdigest() for name in files}
    for rel in files:
        dest=folder/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/rel,dest)
    for path in (source/'npc').rglob('*.yml'):
        dest=folder/path.relative_to(source);dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists():dest.symlink_to(path)
    (folder/'npc/qa-services.txt').write_bytes(HARNESS.encode('cp1252'))
    main=folder/'npc/pre-re/scripts_main.conf';main.parent.mkdir(parents=True,exist_ok=True)
    main.write_text(''.join('npc: '+name+'\n' for name in files+['npc/qa-services.txt']))
    texts=[(source/rel).read_text(encoding='cp1252') for rel in files]
    maps={name for text in texts for name in re.findall(r'^(\w+),\d+,\d+',text,re.M)}
    maps.update(re.findall(r'^(\w+)\s+mapflag\s+town',texts[1],re.M))
    maps.update(['jupe_cave','juperos_01','juperos_02','jupe_core'])
    for rel in ['db/pre-re/achievement_db.yml','db/import/achievement_db.yml']:
        if (source/rel).exists():maps.update(re.findall(r'^\s+Map:\s*([\w@-]+)',(source/rel).read_text(),re.M))
    maps=sorted(maps)
    (folder/'conf/maps_athena.conf').write_text(''.join('map: '+name+'\n' for name in maps))
    for template in (source/'conf/import-tmpl').glob('*.txt'):
        path=folder/'conf/import'/template.name
        if not path.exists():path.touch()
    (folder/'conf/import/map_conf.txt').write_text('import: conf/import/faithro_auth.txt\nchar_ip: 127.0.0.1\nmap_ip: 127.0.0.1\nbind_ip: 127.0.0.1\n')
    sql('USE ragnarok; CREATE TABLE qa_command(id INT PRIMARY KEY,seq INT,action INT,level INT,money INT); '+
        'INSERT INTO qa_command VALUES(1,0,0,1,0); CREATE TABLE qa_service_snapshots(id INT PRIMARY KEY AUTO_INCREMENT,'+
        ','.join(name+(' VARCHAR(30) NOT NULL' if name in ['mapname','lastwarp'] else ' BIGINT NOT NULL') for name in COLUMNS)+'); '+
        "INSERT INTO mapreg(varname,`index`,value) VALUES('$QW_DW_OFF',0,'1'),('$QW_MapUserShow',0,'1');")
    shutil.copy2(source/'map-server',folder/'map-server')
    server=spawn([str(folder/'map-server')],'map.log')
    wait_for(lambda:'Map-server connected to char-server' in log('map.log') and "Server is 'ready'" in log('map.log'),server,'isolated service map-server',seconds=80)
    assert '[Error]' not in log('map.log') and '[SQL Error]' not in log('map.log'), 'Map initialization errors'
    from bot.client import Session, BotError
    from bot.actions import Actions
    from bot import protocol as P
    session=Session(host='127.0.0.1',char_host='127.0.0.1',map_host='127.0.0.1',timeout=10)
    actions=Actions(session);transcripts={};seq=0

    def snapshot():
        session.pump(.7)
        row=sql('SELECT '+','.join(COLUMNS)+' FROM ragnarok.qa_service_snapshots ORDER BY id DESC LIMIT 1;').rstrip('\r\n').split('\t')
        assert len(row)==len(COLUMNS), ('Observer missing',row)
        return {k:(v if k in ['mapname','lastwarp'] else int(v)) for k,v in zip(COLUMNS,row)}

    def command(action, level=99, money=100000):
        nonlocal seq
        seq+=1
        sql(f'UPDATE ragnarok.qa_command SET seq={seq},action={action},level={level},money={money} WHERE id=1;')
        end=time.monotonic()+8
        while time.monotonic()<end:
            value=snapshot()
            if value['seq']==seq:return value
        raise AssertionError('QA command not acknowledged')

    def talk(key, npc, choices):
        transcripts[key]=actions.talk(npc,choices=choices,timeout=2)
        return snapshot()

    def check_purchase(key,npc,items,price,counts):
        before=snapshot()
        try:result=actions.buy(npc,items)
        except BotError as error:
            raise AssertionError({'purchase':key,'message':str(error),'waiting':session.dialog.waiting,
                                  'transcript':session.dialog.transcript,'unhandled_packet_ids':session.unhandled,
                                  'snapshot':snapshot()}) from error
        after=snapshot()
        assert result==0 and before['zeny']-after['zeny']==price,(key,result,before,after)
        for name,amount in counts.items():assert after[name]-before[name]==amount,(key,name,before,after)
        return {'result':result,'spent':before['zeny']-after['zeny'],'received':counts,
                'displayed_prices':{str(item.item_id):item.price for item in session.dialog.shop if item.item_id in dict(items)}}

    try:
        session.login('qa_player',player_password,retries=1)
        session.enter_char(slot=0);session.enter_map(retries=0);session.pump(1)
        healer=[]
        for level in [99,100]:
            before=command(1,level)
            npc=actions.find_npc('Curandeira#prt');actions.approach(npc,within=2)
            session.send(P.pack_npc_click(npc.aid));after=snapshot()
            assert after['zeny']==before['zeny'] and after['hp']==after['maxhp'],(before,after)
            # Installed order heals before Blessing raises max SP. Record that actual
            # shortfall instead of silently treating the healer as full post-buff SP.
            assert before['maxsp']<=after['sp']<=after['maxsp'],(before,after)
            if level==100:assert after['sp']==after['maxsp'],after
            assert [after['blessing'],after['agi']]==([10,10] if level==99 else [0,0]),after
            if level==99:assert all(235000<=after[k]<=240000 for k in ['blessing_ms','agi_ms']),after
            healer.append({'level':level,'free_full_hp':True,'restored_sp':after['sp'],'pre_buff_maxsp':before['maxsp'],
                           'post_buff_maxsp':after['maxsp'],'sp_shortfall_after_buff':after['maxsp']-after['sp'],
                           'blessing_level':after['blessing'],'agi_level':after['agi'],
                           'blessing_ms_remaining':after['blessing_ms'],'agi_ms_remaining':after['agi_ms']})

        fees=[]
        for level,fee in [(99,0),(100,25000),(199,25000),(200,50000),(255,50000)]:
            before=command(1,level)
            assert before['city_fee']==0 and before['dungeon_fee']==fee,before
            after=talk('warper_dungeon_'+str(level),'Teleportadora#prt',[4,'Juperos','Juperos 1'])
            assert after['mapname']=='juperos_01' and (after['x'],after['y'])==(53,247),after
            assert before['zeny']-after['zeny']==fee and after['lastwarp']=='juperos_01',(before,after)
            fees.append({'level':level,'city_fee':before['city_fee'],'dungeon_fee_received':before['zeny']-after['zeny']})

        command(2);before=snapshot()
        last=talk('warper_last','Teleportadora#prt',[1])
        assert last['mapname']=='juperos_01' and before['zeny']-last['zeny']==50000,(before,last)
        command(2);command(7,money=49999);before=snapshot()
        blocked=talk('warper_insufficient','Teleportadora#prt',[1])
        assert blocked['mapname']=='prontera' and blocked['zeny']==49999 and blocked['lastwarp']=='juperos_01',blocked
        command(7,money=0)
        city=talk('warper_city_zero_funds','Teleportadora#prt',[2,'Alberta'])
        assert city['mapname']=='alberta' and city['zeny']==0 and (city['x'],city['y'])==(28,234),city

        command(1,100);command(4)
        unlocked=talk('warpra_unlock','Warpra#32',[])
        assert unlocked['town_unlock']==1 and 'desbloqueado' in ' '.join(transcripts['warpra_unlock']),unlocked
        talk('warpra_disabled_menu','Warpra#32',[])
        disabled_menu=list(session.dialog.menu)
        assert not any('calabou' in x.lower() for x in disabled_menu),disabled_menu
        before=snapshot()
        town=talk('warpra_free_town','Warpra#32',['Teleporte para cidades','Prontera'])
        assert town['mapname']=='prontera' and town['zeny']==before['zeny'],town
        warpra=[]
        for level,fee in [(100,25000),(200,50000)]:
            command(1,level);command(4);command(5);before=snapshot()
            after=talk('warpra_dungeon_'+str(level),'Warpra#32',['Teleporte para calabou','Caverna de Juperos','Nível 1'])
            assert after['mapname']=='juperos_01' and before['zeny']-after['zeny']==fee,(before,after)
            level_menu=next(line for line in transcripts['warpra_dungeon_'+str(level)] if line.startswith('[menu]') and 'Nível 1' in line)
            warpra.append({'level':level,'net_cost_no_refund':before['zeny']-after['zeny'],
                           'destination_menu':level_menu,'shared_tariff_displayed':str(fee) in level_menu})

        command(1,99);command(3)
        purchases={}
        purchases['poison']=check_purchase('poison','Street Dealer',[(678,1)],50000,{'poison':1})
        purchases['blue']=check_purchase('blue','Street Dealer',[(505,1)],5000,{'blue':1})
        purchases['arrow']=check_purchase('arrow','Munições',[(1750,10)],100,{'arrow':10})
        purchases['gems_and_ad']=check_purchase('gems_and_ad','Vendedor Alquimista',[(715,1),(716,1),(717,1),(7136,1),(7135,1)],2800,
                                               {'redgem':1,'yellowgem':1,'bluegem':1,'acid':1,'fire':1})
        command(7,money=49999);before=snapshot()
        result=actions.buy('Street Dealer',[(678,1)]);after=snapshot()
        assert result!=0 and after['zeny']==before['zeny'] and after['poison']==before['poison'],(result,before,after)
        assert all(hashlib.sha256((folder/rel).read_bytes()).hexdigest()==digest for rel,digest in hashes.items())
        assert '[Error]' not in log('map.log') and '[SQL Error]' not in log('map.log'), 'Service runtime errors'
        return {'status':'passed','loaded_maps':maps,'map_errors':0,'installed_npc_files_unmodified':hashes,
                'healer':healer,'warper_level_boundaries':fees,
                'warper_routes':{'last_destination_recharged':50000,'insufficient_funds_no_debit_or_warp':True,
                                 'city_free_at_level_255_with_zero_funds':True},
                'warpra':{'real_town_unlock':True,'production_dungeon_off_reproduced':1,'disabled_menu':disabled_menu,
                          'town_free':True,'dungeon_unlock_seeded_only_in_lab':True,'enabled_dungeon_costs':warpra},
                'purchases':purchases,'purchase_insufficient_funds_preserves_inventory_and_zeny':True,
                'findings':[{'id':'healer-sp-before-blessing','confidence':'high',
                             'observed_shortfall':healer[0]['sp_shortfall_after_buff'],
                             'candidate':'Heal after buffs; patch prepared only, not applied or runtime-tested'},
                            {'id':'warpra-shared-tariff-omitted-from-menu','confidence':'high',
                             'currently_exposed_in_production':False,
                             'observed':warpra,'candidate':'Include shared tariff in level menu; production dungeons remain disabled'}],
                'transcripts':transcripts,'combats_executed':0,'player_performance_metrics':False}
    finally:
        if session.phase=='map':
            try:session.quit(timeout=5)
            except Exception:pass
        session.close()
