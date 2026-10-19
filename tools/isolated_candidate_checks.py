"""Compare installed and candidate NPCs only inside isolated_char_check's lab.

No production SQL, fights, accounts copied or production file writes. The same
private database is reused across two sequential map-server instances. Candidate
patches are checked and applied only after the baseline instance has stopped.
"""
import hashlib
from itertools import product
from pathlib import Path
import re
import shutil
import subprocess
import time

PREFIX='npc/custom/faithro/ptbr/custom/'
FILES=['npc/other/Global_Functions.txt','npc/mapflag/town.txt',
       *[PREFIX+p for p in ['healer.txt','warper.txt','etc/quest_warper.txt','itemmall.txt']]]
PATCHES={'healer-sp-candidate.patch':PREFIX+'healer.txt',
         'warpra-price-preview-candidate.patch':PREFIX+'etc/quest_warper.txt'}
COLS='seq level base_int gear zeny hp maxhp sp maxsp blessing agi blessing_ms agi_ms hd clock_s dungeon_off mapname x y'.split()

HARNESS=r'''
-	script	QA_CandidateObserver	-1,{
 end;
OnPCLoginEvent:
 if (strcharinfo(0) != "IsolatedQA0") { detachrid; end; }
 addtimer 200,"QA_CandidateObserver::OnObserve";
 detachrid; end;
OnObserve:
 query_sql("SELECT seq,action,level,money,int_value,gear,users,gm_base,gm_depth,dungeon_off FROM qa_candidate_command WHERE id=1",.@seq,.@action,.@level,.@money,.@int,.@gear,.@users,.@base,.@depth,.@off);
 if (.@seq > @QA_seq) {
  if (.@action == 1) {
   sc_end SC_BLESSING; sc_end SC_INCREASEAGI; @HD=0;
   if (getequipid(EQI_ACC_L)>0) unequip EQI_ACC_L;
   if (getequipid(EQI_ACC_R)>0) unequip EQI_ACC_R;
   if (countitem(2648)) delitem 2648,countitem(2648);
   if (.@level == 1) jobchange Job_Novice;
   else jobchange Job_Sniper;
   BaseLevel=.@level;
   statusup2 bInt,.@int-readparam(bInt);
   if (.@gear) { getitem 2648,1; equip 2648; }
   Zeny=.@money; percentheal 100,100; heal 1-Hp,-Sp;
   warp "prontera",161,192;
  }
  if (.@action == 2) { percentheal 100,100; heal 1-Hp,-Sp; }
  if (.@action == 3) {
   jobchange Job_Sniper; BaseLevel=.@level; Zeny=.@money;
   $QW_DW_OFF=.@off; $QW_TW_OFF=0; $QW_MapUserShow=.@users;
   $QW_AW_PRICE=.@base; $QW_AW_FEE=.@depth;
   ##QWS_T_Unlock=1; ##QWS_D_Unlock=16384;
   warp "prontera",147,173;
  }
  @QA_seq=.@seq;
 }
 getmapxy(.@map$,.@x,.@y,BL_PC);
 query_sql("INSERT INTO qa_candidate_samples(seq,level,base_int,gear,zeny,hp,maxhp,sp,maxsp,blessing,agi,blessing_ms,agi_ms,hd,clock_s,dungeon_off,mapname,x,y) VALUES ("+@QA_seq+","+BaseLevel+","+readparam(bInt)+","+isequipped(2648)+","+Zeny+","+Hp+","+MaxHp+","+Sp+","+MaxSp+","+getstatus(SC_BLESSING,1)+","+getstatus(SC_INCREASEAGI,1)+","+getstatus(SC_BLESSING,5)+","+getstatus(SC_INCREASEAGI,5)+","+@HD+","+gettimetick(2)+","+$QW_DW_OFF+",'"+.@map$+"',"+.@x+","+.@y+")");
 addtimer 200,"QA_CandidateObserver::OnObserve";
 detachrid; end;
}
'''


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(folder, source, sql):
    assert Path('/proc/1/comm').read_text().strip().startswith('python')
    assert folder.resolve().parent==Path('/tmp') and folder.name.startswith('faithro-char-qa-')
    for rel in FILES:
        p=folder/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/rel,p)
    for p in (source/'npc').rglob('*.yml'):
        target=folder/p.relative_to(source);target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():target.symlink_to(p)
    (folder/'npc/qa-candidates.txt').write_bytes(HARNESS.encode('cp1252'))
    p=folder/'npc/pre-re/scripts_main.conf';p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(''.join('npc: '+rel+'\n' for rel in FILES+['npc/qa-candidates.txt']))
    texts=[(source/rel).read_text(encoding='cp1252') for rel in FILES]
    maps={m for text in texts for m in re.findall(r'^(\w+),\d+,\d+',text,re.M)}
    maps.update(re.findall(r'^(\w+)\s+mapflag\s+town',texts[1],re.M))
    maps.update(['jupe_cave','juperos_01','juperos_02','jupe_core'])
    for rel in ['db/pre-re/achievement_db.yml','db/import/achievement_db.yml']:
        if (source/rel).exists():maps.update(re.findall(r'^\s+Map:\s*([\w@-]+)',(source/rel).read_text(),re.M))
    (folder/'conf/maps_athena.conf').write_text(''.join('map: '+m+'\n' for m in sorted(maps)))
    for template in (source/'conf/import-tmpl').glob('*.txt'):
        p=folder/'conf/import'/template.name
        if not p.exists():p.touch()
    (folder/'conf/import/map_conf.txt').write_text('import: conf/import/faithro_auth.txt\nchar_ip: 127.0.0.1\nmap_ip: 127.0.0.1\nbind_ip: 127.0.0.1\n')
    columns='id INT PRIMARY KEY,seq INT,action INT,level INT,money INT,int_value INT,gear INT,users INT,gm_base INT,gm_depth INT,dungeon_off INT'
    sql('USE ragnarok; CREATE TABLE qa_candidate_command('+columns+'); INSERT INTO qa_candidate_command VALUES(1,0,0,99,100000,1,0,1,0,0,1); '+
        'CREATE TABLE qa_candidate_samples(id INT PRIMARY KEY AUTO_INCREMENT,'+
        ','.join(k+(' VARCHAR(30) NOT NULL' if k=='mapname' else ' BIGINT NOT NULL') for k in COLS)+'); '+
        "INSERT INTO mapreg(varname,`index`,value) VALUES('$QW_DW_OFF',0,'1'),('$QW_MapUserShow',0,'1');")
    shutil.copy2(source/'map-server',folder/'map-server')
    return sorted(maps)


def apply_candidates(folder):
    # No caller-controlled filenames: only these two versioned patch artifacts.
    records={}
    for name,rel in PATCHES.items():
        patch=Path(__file__).with_name(name)
        text=patch.read_text(encoding='utf-8')
        expected='server/'+rel
        assert text.startswith('--- a/'+expected+'\n+++ b/'+expected+'\n'), name
        assert text.count('\n--- ')==0 and text.count('\n+++ ')==1, name
        assert 'new file mode' not in text and 'deleted file mode' not in text, name
        target=folder/rel
        assert target.is_file() and not target.is_symlink() and target.resolve().is_relative_to(folder.resolve())
        temporary=folder/name
        temporary.write_text(text.replace('--- a/server/','--- a/',1).replace('+++ b/server/','+++ b/',1))
        before=digest(target)
        for args in [['git','apply','--check',str(temporary)],['git','apply',str(temporary)]]:
            result=subprocess.run(args,cwd=folder,text=True,capture_output=True)
            assert result.returncode==0, {'patch':name,'git_apply_error':result.stderr[:500]}
        assert digest(target)!=before,name
        records[name]={'sha256':digest(patch),'target':rel,'before_sha256':before,'after_sha256':digest(target)}
    return records


class Client:
    def __init__(self, sql, password):
        from bot.client import Session
        from bot.actions import Actions
        self.sql=sql;self.seq=0;self.transcripts={}
        self.s=Session(host='127.0.0.1',char_host='127.0.0.1',map_host='127.0.0.1',timeout=10)
        self.s.login('qa_player',password,retries=1)
        self.s.enter_char(slot=0);self.s.enter_map(retries=0);self.s.pump(.5)
        self.actions=Actions(self.s)

    def state(self):
        self.s.pump(.25)
        row=self.sql('SELECT '+','.join(COLS)+' FROM ragnarok.qa_candidate_samples ORDER BY id DESC LIMIT 1;').rstrip('\r\n').split('\t')
        assert len(row)==len(COLS),('Candidate observer missing',row)
        return {k:(v if k=='mapname' else int(v)) for k,v in zip(COLS,row)}

    def command(self, action, **options):
        self.seq+=1
        values={'level':99,'money':100000,'int_value':1,'gear':0,'users':1,'gm_base':0,'gm_depth':0,'dungeon_off':0,**options}
        assert all(type(v) is int and v>=0 for v in values.values())
        self.sql('UPDATE ragnarok.qa_candidate_command SET '+','.join(f'{k}={v}' for k,v in {'seq':self.seq,'action':action,**values}.items())+' WHERE id=1;')
        end=time.monotonic()+8
        while time.monotonic()<end:
            value=self.state()
            if value['seq']==self.seq:return value
        raise AssertionError('Candidate command timeout')

    def heal(self):
        from bot import protocol as P
        npc=self.actions.find_npc('Curandeira#prt')
        # Every healer setup warps within two cells; no walking can consume cooldown.
        assert self.s.me.map=='prontera' and max(abs(self.s.me.x-npc.x),abs(self.s.me.y-npc.y))<=2
        self.s.send(P.pack_npc_click(npc.aid))
        return self.state()

    def warp(self, key, depth):
        text=self.actions.talk('Warpra#32',choices=['Teleporte para calabou','Caverna de Juperos','Nível '+str(depth+1)],timeout=3)
        menu=list(self.s.dialog.menu);self.transcripts[key]=list(text)
        return self.state(),menu

    def close(self):
        try:
            if self.s.phase=='map':self.s.quit(timeout=5)
        finally:self.s.close()


def shared_fee(level):
    return 0 if level<=99 else 25000 if level<200 else 50000


def preview(menu, depth):
    option=next(text for text in menu if text.startswith('Nível '+str(depth+1)))
    match=re.search(r' -> (\d+)$',option)
    return int(match[1]) if match else 0


def check_heal(client, level, intelligence, gear, candidate, cooldown=False):
    before=client.command(1,level=level,int_value=intelligence,gear=gear)
    assert before['base_int']==intelligence and before['gear']==gear,before
    after=client.heal()
    buffs=10 if level<=99 else 0
    assert after['hp']==after['maxhp'] and after['zeny']==before['zeny'],(before,after)
    assert [after['blessing'],after['agi']]==[buffs,buffs],after
    if buffs:assert all(235000<=after[k]<=240000 for k in ['blessing_ms','agi_ms']),after
    assert after['hd']-after['clock_s'] in [2,3],after
    if candidate:assert after['sp']==after['maxsp'],(before,after)
    result={'level':level,'natural_int':intelligence,'morpheus_ring_2648_equipped':bool(gear),
            'sp':after['sp'],'maxsp':after['maxsp'],'shortfall':after['maxsp']-after['sp'],
            'blessing_level':after['blessing'],'agi_level':after['agi'],
            'blessing_ms':after['blessing_ms'],'agi_ms':after['agi_ms'],'free':True}
    if cooldown:
        damaged=client.command(2)
        assert damaged['clock_s']<after['hd'],('Missed cooldown test window',damaged,after)
        blocked=client.heal()
        assert blocked['hp']<blocked['maxhp'] and blocked['sp']<blocked['maxsp'] and blocked['hd']==after['hd'],blocked
        deadline=time.monotonic()+5
        while client.state()['clock_s']<after['hd']:
            assert time.monotonic()<deadline,'Cooldown wait timeout'
        refreshed=client.heal()
        assert refreshed['hp']==refreshed['maxhp'] and refreshed['sp']==refreshed['maxsp'] and refreshed['zeny']==before['zeny'],refreshed
        assert [refreshed['blessing'],refreshed['agi']]==[buffs,buffs],refreshed
        if buffs:assert all(235000<=refreshed[k]<=240000 for k in ['blessing_ms','agi_ms']),refreshed
        result.update(cooldown_blocked_early_click=True,healed_after_cooldown=True,buffs_refreshed_without_sp_deficit=True)
    return result


def phase(folder, sql, spawn, wait_for, log, password, candidate):
    server=spawn([str(folder/'map-server')],'map.log')
    wait_for(lambda:'Map-server connected to char-server' in log('map.log') and "Server is 'ready'" in log('map.log'),server,'candidate map-server',seconds=80)
    assert '[Error]' not in log('map.log') and '[SQL Error]' not in log('map.log')
    client=Client(sql,password)
    try:
        if candidate:
            healer=[check_heal(client,*case,True,cooldown=True) for case in
                    [(1,1,0),(99,1,0),(99,90,0),(99,1,1),(99,90,1),
                     (100,1,0),(100,90,1),(255,1,0),(255,90,1)]]
            cases=list(product([99,100,199,200,255],[0,1],[0,1],[0,1]))
        else:
            healer=[check_heal(client,*case,False) for case in [(99,1,0),(99,90,1)]]
            assert all(row['shortfall']>0 for row in healer),healer
            cases=[(100,1,0,0),(200,1,0,0)]
        warps=[]
        for level,users,depth,priced in cases:
            base,per_depth=(3000,700) if priced else (0,0)
            before=client.command(3,level=level,users=users,gm_base=base,gm_depth=per_depth)
            expected=shared_fee(level)+base+depth*per_depth
            after,menu=client.warp(f'{level}-{users}-{depth}-{priced}',depth)
            assert after['mapname']==('juperos_02' if depth else 'juperos_01'),after
            assert (after['x'],after['y'])==((36,60) if depth else (53,247)),after
            assert before['zeny']-after['zeny']==expected,(before,after,expected)
            shown=preview(menu,depth)
            if candidate:assert shown==expected,(menu,expected)
            else:assert shown==0 and expected>0,(menu,expected)
            assert all(('[' in item)==bool(users) for item in menu if item.startswith('Nível ')),menu
            warps.append({'level':level,'show_users':bool(users),'depth':depth,'gm_base':base,'gm_per_depth':per_depth,
                          'expected':expected,'displayed':shown,'net_debit':before['zeny']-after['zeny'],'menu':menu})
        insufficient=[]
        if candidate:
            for level in [99,100,199,200,255]:
                expected=shared_fee(level)+3000+700
                before=client.command(3,level=level,money=expected-1,gm_base=3000,gm_depth=700)
                after,menu=client.warp('insufficient-'+str(level),1)
                assert after['mapname']=='prontera' and after['zeny']==before['zeny'],(before,after)
                assert preview(menu,1)==expected,(menu,expected)
                assert 'não tem' in ' '.join(client.transcripts['insufficient-'+str(level)])
                insufficient.append({'level':level,'price':expected,'balance_preserved':after['zeny'],'warp_blocked':True})
        client.command(3,level=255,dungeon_off=1)
        client.actions.talk('Warpra#32',choices=[],timeout=3)
        disabled_menu=list(client.s.dialog.menu)
        assert not any('calabou' in item.lower() for item in disabled_menu),disabled_menu
        assert client.state()['dungeon_off']==1
        assert '[Error]' not in log('map.log') and '[SQL Error]' not in log('map.log'),'NPC runtime errors'
        assert re.search(r"'0' Spawn sets",log('map.log')),'World must have zero spawn sets'
        return {'healer':healer,'warpra':warps,'insufficient_funds':insufficient,
                'dungeon_disabled_menu':disabled_menu,'map_errors':0,'spawn_sets':0,'transcripts':client.transcripts}
    finally:
        client.close()
        if server.poll() is None:
            server.terminate();server.wait(timeout=15)


def run(folder, source, sql, spawn, wait_for, log, player_password):
    maps=prepare(folder,source,sql)
    original={rel:digest(source/rel) for rel in FILES}
    baseline=phase(folder,sql,spawn,wait_for,log,player_password,False)
    assert all(digest(folder/rel)==sha for rel,sha in original.items())
    (folder/'map.log').rename(folder/'baseline-map.log')
    patches=apply_candidates(folder)
    sql('UPDATE ragnarok.qa_candidate_command SET seq=0,action=0 WHERE id=1; TRUNCATE ragnarok.qa_candidate_samples;')
    candidate=phase(folder,sql,spawn,wait_for,log,player_password,True)
    assert all(digest(source/rel)==sha for rel,sha in original.items()),'Installed source changed'
    assert all(digest(folder/rel)==sha for rel,sha in original.items() if rel not in PATCHES.values())
    return {'status':'passed','baseline':baseline,'candidate':candidate,'patches_applied_to_private_copies':patches,
            'source_file_sha256':original,'loaded_maps':maps,'healer_candidate_cases':len(candidate['healer']),
            'warpra_candidate_cases':len(candidate['warpra']),'insufficient_funds_cases':len(candidate['insufficient_funds']),
            'production_npcs_changed':False,'persistent_server_created':False,'combats_executed':0,'player_performance_metrics':False}
