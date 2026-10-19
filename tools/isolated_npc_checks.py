"""NPC QA helper. Called only by the verified private-namespace character lab.

Uses unchanged installed NPC files and a separate QA control NPC. Quest completion
is seeded, not earned by fighting. Never starts a combat or connects to production SQL.
"""
import hashlib
import importlib.util
from pathlib import Path
import re
import shutil
import time

HARNESS = r'''
prontera,155,181,5	script	QA_Control	1_F_MARIA,{
 mes "[QA Control]";
 switch(select("LotterySetup:ArenaSetup:HuntCompleted:Snapshot:NextDraw:GoProntera:HuntFresh")) {
 case 1:
  Zeny=100000; #LID=0; #LW1=0; #LW2=0; #LW3=0; #LW4=0; #LW5=0; #LW6=0;
  close;
 case 2:
  Zeny=50000; #monster=10; #monpoints=1234; #heal=0;
  close2; warp "gon_test",53,104; end;
 case 3:
  Zeny=100000; #Mission_Delay=1; #Mission_Count=40; #Mission_Points=0; Mission_Total=0;
  Mission0=1002; Mission1=1007; Mission2=1008; Mission3=1010;
  Mission0_=40; Mission1_=40; Mission2_=40; Mission3_=40;
  close;
 case 4:
  query_sql("INSERT INTO qa_snapshots(zeny,monpoints,mission_count,mission_total,hunt_points,mission_delay,lid,draw,w1,w2,w3,w4,w5,w6,m0,m1,m2,m3) VALUES ("+Zeny+","+#monpoints+","+#Mission_Count+","+Mission_Total+","+#Mission_Points+","+#Mission_Delay+","+#LID+","+$LID+","+#LW1+","+#LW2+","+#LW3+","+#LW4+","+#LW5+","+#LW6+","+Mission0+","+Mission1+","+Mission2+","+Mission3+")");
  mes "QA_SNAPSHOT_SAVED"; close;
 case 5:
  donpcevent "lotterygenerator::OnClock2045"; close;
 case 6:
  close2; warp "prontera",155,180; end;
 case 7:
  #Mission_Delay=1; #Mission_Count=0; Mission0=0; Mission1=0; Mission2=0; Mission3=0;
  Mission0_=0; Mission1_=0; Mission2_=0; Mission3_=0;
  close;
 }
 end;
OnInit:
 query_sql("INSERT INTO qa_runtime(tine_id,controller_id,base_rate,job_rate,max_parameter) VALUES ("+getnpcid(0,"Tine")+","+getnpcid(0,"FaithRO_ValentineBonus")+","+getbattleflag("base_exp_rate")+","+getbattleflag("job_exp_rate")+","+getbattleflag("max_parameter")+")");
 end;
}
gon_test,53,104,5	duplicate(QA_Control)	QA_ControlArena	1_F_MARIA
'''


def run(folder, source, sql, spawn, wait_for, log, player_password):
    # The caller already verified namespaces, read-only source mounts and fresh SQL.
    assert Path('/proc/1/comm').read_text().strip().startswith('python')
    assert folder.resolve().parent==Path('/tmp') and folder.name.startswith('faithro-char-qa-')
    target='npc/custom/faithro/ptbr/custom/'
    relative=[target+p for p in ['etc/lottery.txt','etc/monster_arena.txt','quests/hunting_missions.txt','events/holiday/valentinesdayexp.txt']]
    files=['npc/other/Global_Functions.txt',*relative]
    hashes={name:hashlib.sha256((source/name).read_bytes()).hexdigest() for name in files}
    for rel in files:
        dest=folder/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/rel,dest)
    # Barter DB files are loaded independently of script includes, even in pre-re mode.
    for path in (source/'npc').rglob('*.yml'):
        dest=folder/path.relative_to(source);dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists():dest.symlink_to(path)
    (folder/'npc/qa.txt').write_bytes(HARNESS.encode('cp1252'))
    main=folder/'npc/pre-re/scripts_main.conf';main.parent.mkdir(parents=True,exist_ok=True)
    main.write_text(''.join('npc: '+name+'\n' for name in files+['npc/qa.txt']))
    maps=sorted({name for rel in relative for name in re.findall(r'^(\w+),\d+,\d+', (source/rel).read_text(encoding='cp1252'),re.M)})
    achievement_maps=set()
    for rel in ['db/pre-re/achievement_db.yml','db/import/achievement_db.yml']:
        if (source/rel).exists():
            achievement_maps.update(re.findall(r'^\s+Map:\s*([\w@-]+)',(source/rel).read_text(),re.M))
    maps=sorted(set(maps)|achievement_maps)
    (folder/'conf/maps_athena.conf').write_text(''.join('map: '+name+'\n' for name in maps))
    for template in (source/'conf/import-tmpl').glob('*.txt'):
        path=folder/'conf/import'/template.name
        if not path.exists():path.touch()
    (folder/'conf/import/map_conf.txt').write_text('import: conf/import/faithro_auth.txt\nchar_ip: 127.0.0.1\nmap_ip: 127.0.0.1\nbind_ip: 127.0.0.1\n')
    sql('USE ragnarok; CREATE TABLE qa_snapshots(id INT PRIMARY KEY AUTO_INCREMENT,'+
        ','.join(name+' BIGINT NOT NULL' for name in ['zeny','monpoints','mission_count','mission_total','hunt_points','mission_delay','lid','draw','w1','w2','w3','w4','w5','w6','m0','m1','m2','m3'])+'); '+
        'CREATE TABLE qa_runtime(tine_id BIGINT,controller_id BIGINT,base_rate BIGINT,job_rate BIGINT,max_parameter BIGINT);')
    shutil.copy2(source/'map-server',folder/'map-server')
    server=spawn([str(folder/'map-server')],'map.log')
    wait_for(lambda:'Map-server connected to char-server' in log('map.log') and "Server is 'ready'" in log('map.log'),server,'isolated map-server',seconds=80)
    assert '[Error]' not in log('map.log') and '[SQL Error]' not in log('map.log'), 'Map initialization errors'
    runtime=[list(map(int,row.split('\t'))) for row in sql('SELECT tine_id,controller_id,base_rate,job_rate,max_parameter FROM ragnarok.qa_runtime;').splitlines()]
    assert len(runtime)==2 and all(row[0]==0 and row[1]>0 and row[2:]==[30000,30000,185] for row in runtime), runtime
    spec=importlib.util.spec_from_file_location('_builder', '/root/faithro/deploy/web/tools/build_gamedb.py')
    b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
    active=b.npc_sources(source)
    removed=[target+'events/mvp_ladder.txt',target+'battleground/bg_emp.txt',target+'battleground/bg_pvp.txt']
    assert all(path not in active for path in removed)
    mobs=b.merge_by_id(b.collect_body(source,'db/pre-re/mob_db.yml')+b.collect_body(source,'db/import/mob_db.yml'))
    from bot.client import Session
    from bot.actions import Actions
    session=Session(host='127.0.0.1',char_host='127.0.0.1',map_host='127.0.0.1',timeout=10)
    transcripts={}
    columns=['zeny','monpoints','mission_count','mission_total','hunt_points','mission_delay','lid','draw','w1','w2','w3','w4','w5','w6','m0','m1','m2','m3']
    def snapshot():
        controller='QA_ControlArena' if session.me.map=='gon_test' else 'QA_Control'
        if session.me.map=='prontera':actions.walk_to(155,180)
        actions.talk(controller,choices=[4]);session.pump(.3)
        row=sql('SELECT '+','.join(columns)+' FROM ragnarok.qa_snapshots ORDER BY id DESC LIMIT 1;').strip()
        return dict(zip(columns,map(int,row.split('\t'))))
    try:
        session.login('qa_player',player_password,retries=1)
        session.enter_char(slot=0);session.enter_map(retries=0);session.pump(1)
        actions=Actions(session)
        actions.talk('QA_Control',choices=[1]);before=snapshot()
        transcripts['lottery_first']=actions.talk('Loteria',choices=[2,1,1,1]);first=snapshot()
        assert before['zeny']-first['zeny']==4750 and first['lid']==first['draw']
        numbers=[first['w'+str(i)] for i in range(1,7)]
        assert len(set(numbers))==6 and all(1<=n<=40 for n in numbers)
        transcripts['lottery_blocked']=actions.talk('Loteria',choices=[2]);second=snapshot()
        assert second['zeny']==first['zeny'] and second['lid']==first['lid']
        assert 'um bilhete por sorteio' in ' '.join(transcripts['lottery_blocked'])
        actions.talk('QA_Control',choices=[5]);session.pump(.5)
        transcripts['lottery_renew']=actions.talk('Loteria',choices=[2,1,3]);renew=snapshot()
        assert renew['zeny']==first['zeny']-4750 and renew['lid']==renew['draw'] and renew['lid']!=first['lid']
        assert [renew['w'+str(i)] for i in range(1,7)]==numbers

        actions.talk('QA_Control',choices=[2]);session.pump(1)
        arena_before=snapshot()
        transcripts['arena']=actions.talk('Treinador de Monstros',choices=[])
        menu=list(session.dialog.menu)
        assert not any('vender' in item.lower() for item in menu) and len(menu)==3, menu
        assert 'suspensa' in ' '.join(transcripts['arena'])
        arena_after=snapshot()
        assert arena_before['monpoints']==arena_after['monpoints']==1234
        assert arena_after['zeny']==arena_before['zeny']==50000
        actions.talk('QA_ControlArena',choices=[6]);session.pump(1)

        actions.talk('QA_Control',choices=[7])
        transcripts['hunt_new']=actions.talk('Missões de Caça',choices=[1]);assigned=snapshot()
        assigned_ids=[assigned['m'+str(i)] for i in range(4)]
        assert len(set(assigned_ids))==4 and 40<=assigned['mission_count']<=70
        text=(source/(target+'quests/hunting_missions.txt')).read_text(encoding='cp1252')
        pool=set(map(int,re.findall(r'\d+',re.search(r'setarray \.Pool\[0\],(.*?);',text,re.S)[1])))
        assert set(assigned_ids)<=pool
        actions.talk('QA_Control',choices=[3]);hunt_before=snapshot()
        transcripts['hunt_claim']=actions.talk('Missões de Caça',choices=[1]);claimed=snapshot()
        total_levels=sum(mobs[i]['Level'] for i in [1002,1007,1008,1010])
        expected_zeny=40*4*total_levels*6
        expected_points=3+total_levels//4//6
        clean_dialog=re.sub(r'\^[0-9A-Fa-f]{6}','','\n'.join(transcripts['hunt_claim']))
        shown_base=int(re.sub(r'\D','',re.search(r'EXP de Base:\s*([\d,.]+)',clean_dialog)[1]))
        shown_job=int(re.sub(r'\D','',re.search(r'EXP de Classe:\s*([\d,.]+)',clean_dialog)[1]))
        expected_base=40*sum(mobs[i].get('BaseExp',0) for i in [1002,1007,1008,1010])*300//5
        expected_job=40*sum(mobs[i].get('JobExp',0) for i in [1002,1007,1008,1010])*300//5
        assert shown_base==expected_base and shown_job==expected_job
        assert claimed['zeny']-hunt_before['zeny']==expected_zeny, (hunt_before,claimed,expected_zeny,transcripts['hunt_claim'])
        assert claimed['hunt_points']==expected_points and claimed['mission_total']==1
        assert claimed['mission_count']==0 and all(claimed['m'+str(i)]==0 for i in range(4))
        assert 43000<=claimed['mission_delay']-int(time.time())<=43200
        transcripts['hunt_cooldown']=actions.talk('Missões de Caça',choices=[1]);cooldown=snapshot()
        assert 'esperar' in ' '.join(transcripts['hunt_cooldown']) and cooldown['zeny']==claimed['zeny']
        assert all(hashlib.sha256((folder/rel).read_bytes()).hexdigest()==digest for rel,digest in hashes.items())
        assert '[Error]' not in log('map.log') and '[SQL Error]' not in log('map.log'), 'NPC runtime errors'
        return {'map_loaded':True,'loaded_maps':maps,'map_errors':0,
                'effective_base_exp_rate':runtime[0][2],'effective_job_exp_rate':runtime[0][3],'effective_max_parameter':runtime[0][4],
                'installed_npc_files_unmodified':hashes,
                'removed_includes_absent':removed,'tine_runtime_id':runtime[0][0],
                'valentine_controller_present':True,'removal_check_scope':'active include graph; runtime Tine check in loaded holiday file',
                'lottery':{'first_price':before['zeny']-first['zeny'],'duplicate_blocked_without_charge':True,
                           'new_draw_renewal_price':first['zeny']-renew['zeny'],'numbers_preserved_on_renewal':True},
                'arena':{'menu':menu,'sale_option_absent':True,'points_preserved':1234,'zeny_preserved':50000},
                'hunting':{'new_assignment_distinct_targets':assigned_ids,'new_assignment_count':assigned['mission_count'],
                           'seeded_completion_without_combats':True,'reward_zeny_expected':expected_zeny,
                           'reward_zeny_received':claimed['zeny']-hunt_before['zeny'],'reward_points':claimed['hunt_points'],
                           'reward_base_exp_displayed':shown_base,'reward_job_exp_displayed':shown_job,
                           'progress_cleared':True,'cooldown_seconds':claimed['mission_delay']-int(time.time()),'early_retry_blocked':True},
                'transcripts':transcripts,'combats_executed':0,'player_performance_metrics':False}
    finally:
        if session.phase=='map':
            try:session.quit(timeout=5)
            except Exception:pass
        session.close()
