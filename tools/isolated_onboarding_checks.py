"""Native Red Potion use and validated lottery time text in the private QA lab.

Only an old temporary lottery copy receives the text patch; an exact deployed
candidate hash is tested unchanged. New synthetic characters
use one real inventory potion through the item-use packet; no battles or production SQL.
"""
import hashlib
from pathlib import Path
import re
import shutil
import struct
import subprocess
import time

LOTTERY='npc/custom/faithro/ptbr/custom/etc/lottery.txt'
COLS='char_id seq hp maxhp red potion_index knife shirt zeny'.split()
HARNESS=r'''
-	script	QA_Onboarding	-1,{
 end;
OnPCLoginEvent:
 if (strcharinfo(0)!="IsolatedQA0" && strcharinfo(0)!="IsolatedQA1") { detachrid; end; }
 addtimer 200,"QA_Onboarding::OnObserve";
 detachrid; end;
OnObserve:
 query_sql("SELECT seq,action FROM qa_onboarding_command WHERE id=1",.@seq,.@action);
 if (.@seq>@QA_seq) {
  if (.@action==1) {
   percentheal 100,100; heal 1-Hp,-Sp; Zeny=100000;
   if (strcharinfo(0)=="IsolatedQA0") {
    #LID=0; #LW1=0; #LW2=0; #LW3=0; #LW4=0; #LW5=0; #LW6=0;
   }
  }
  @QA_seq=.@seq;
 }
 getinventorylist;
 .@index=-1;
 for (.@i=0;.@i<@inventorylist_count;.@i++)
  if (@inventorylist_id[.@i]==501) .@index=@inventorylist_idx[.@i];
 query_sql("INSERT INTO qa_onboarding_samples(char_id,seq,hp,maxhp,red,potion_index,knife,shirt,zeny) VALUES ("+getcharid(0)+","+@QA_seq+","+Hp+","+MaxHp+","+countitem(501)+","+.@index+","+(getequipid(EQI_HAND_R)==1201)+","+(getequipid(EQI_ARMOR)==2301)+","+Zeny+")");
 addtimer 200,"QA_Onboarding::OnObserve";
 detachrid; end;
}
'''


def run(folder, source, sql, spawn, wait_for, log, player_password):
    assert Path('/proc/1/comm').read_text().strip().startswith('python')
    assert folder.resolve().parent==Path('/tmp') and folder.name.startswith('faithro-char-qa-')
    originals={}
    files=['npc/other/Global_Functions.txt',LOTTERY]
    for rel in files:
        path=folder/rel;path.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/rel,path)
        originals[rel]=hashlib.sha256(path.read_bytes()).hexdigest()
    patch=Path(__file__).with_name('lottery-time-candidate.patch')
    text=patch.read_text(encoding='utf-8')
    assert hashlib.sha256(patch.read_bytes()).hexdigest()=='2173300a3b2204c4d09ef78d0c7713f01fbee3a1ff77239814ed2c12ba047cf8'
    expected='server/'+LOTTERY
    assert text.startswith('--- a/'+expected+'\n+++ b/'+expected+'\n')
    assert text.count('\n--- ')==0 and text.count('\n+++ ')==1
    native=folder/'lottery-time-candidate.patch'
    # Installed NPCs use CP1252. Git must compare patch/context in that same encoding.
    native.write_bytes(text.replace('--- a/server/','--- a/',1).replace('+++ b/server/','+++ b/',1).encode('cp1252'))
    old_hash='4e1114ff73ca4add082087420ba7dbbba7dd9970b7adab9f30260c34d2eff819'
    deployed_hash='9dbbb64a8e449fb6765ff246312b5e9491c688e96d4bd1848ca00e9b887b4119'
    assert originals[LOTTERY] in (old_hash,deployed_hash),'Unreviewed lottery source drift'
    patch_applied=originals[LOTTERY]==old_hash
    if patch_applied:
        for args in [['git','apply','--check',str(native)],['git','apply',str(native)]]:
            p=subprocess.run(args,cwd=folder,text=True,capture_output=True)
            assert p.returncode==0,p.stderr[:400]
    assert hashlib.sha256((folder/LOTTERY).read_bytes()).hexdigest()==deployed_hash
    candidate=(folder/LOTTERY).read_text(encoding='cp1252')
    assert candidate.count('OnClock2045:')==1 and 'às 20h45 (horário de São Paulo).' in candidate
    assert 'às 21h.' not in candidate
    for path in (source/'npc').rglob('*.yml'):
        target=folder/path.relative_to(source);target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():target.symlink_to(path)
    (folder/'npc/qa-onboarding.txt').write_bytes(HARNESS.encode('cp1252'))
    p=folder/'npc/pre-re/scripts_main.conf';p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(''.join('npc: '+rel+'\n' for rel in files+['npc/qa-onboarding.txt']))
    maps={'prontera'}
    for rel in ['db/pre-re/achievement_db.yml','db/import/achievement_db.yml']:
        if (source/rel).exists():maps.update(re.findall(r'^\s+Map:\s*([\w@-]+)',(source/rel).read_text(),re.M))
    (folder/'conf/maps_athena.conf').write_text(''.join('map: '+m+'\n' for m in sorted(maps)))
    for template in (source/'conf/import-tmpl').glob('*.txt'):
        p=folder/'conf/import'/template.name
        if not p.exists():p.touch()
    (folder/'conf/import/map_conf.txt').write_text('import: conf/import/faithro_auth.txt\nchar_ip: 127.0.0.1\nmap_ip: 127.0.0.1\nbind_ip: 127.0.0.1\n')
    sql('USE ragnarok; CREATE TABLE qa_onboarding_command(id INT PRIMARY KEY,seq INT,action INT); INSERT INTO qa_onboarding_command VALUES(1,0,0); '+
        'CREATE TABLE qa_onboarding_samples(id INT PRIMARY KEY AUTO_INCREMENT,'+','.join(k+' BIGINT NOT NULL' for k in COLS)+');')
    shutil.copy2(source/'map-server',folder/'map-server')
    server=spawn([str(folder/'map-server')],'map.log')
    wait_for(lambda:'Map-server connected to char-server' in log('map.log') and "Server is 'ready'" in log('map.log'),server,'onboarding map-server',seconds=80)
    assert '[Error]' not in log('map.log') and '[SQL Error]' not in log('map.log')
    from bot.client import Session
    from bot.actions import Actions
    cases=[];lottery={};transcripts={}
    for slot in [0,1]:
        sql('UPDATE ragnarok.qa_onboarding_command SET seq=0,action=0 WHERE id=1;')
        s=Session(host='127.0.0.1',char_host='127.0.0.1',map_host='127.0.0.1',timeout=10)
        try:
            s.login('qa_player',player_password,retries=1);s.enter_char(slot=slot);s.enter_map(retries=0);s.pump(.5)
            def state():
                s.pump(.4)
                row=sql('SELECT '+','.join(COLS)+' FROM ragnarok.qa_onboarding_samples WHERE char_id='+str(s.me.char_id)+' ORDER BY id DESC LIMIT 1;').strip().split('\t')
                assert len(row)==len(COLS),row
                return dict(zip(COLS,map(int,row)))
            initial=state()
            assert initial['red']==100 and initial['knife']==1 and initial['shirt']==1 and initial['zeny']==0,initial
            sql('UPDATE ragnarok.qa_onboarding_command SET seq=1,action=1 WHERE id=1;')
            deadline=time.monotonic()+6
            while True:
                before=state()
                if before['seq']==1:break
                assert time.monotonic()<deadline
            assert before['hp']<before['maxhp'] and before['red']==100 and before['potion_index']>=0
            assert s.map_lengths.get(0x0439)==8 and s.map_lengths.get(0x01c8)==15
            acknowledgements=[]
            def item_ack(pid,frame):
                _,index,item,aid,amount,result=struct.unpack('<HhIIhB',frame)
                acknowledgements.append({'client_index':index,'item_id':item,'remaining':amount,'success':bool(result)})
            s.on(0x01c8,item_ack)
            index=before['potion_index']+2 # clif_parse_UseItem and clif_useitemack use +/- 2.
            s.send(struct.pack('<HHI',0x0439,index,s.me.account_id))
            s.wait_for(lambda:bool(acknowledgements),5,'native Red Potion acknowledgement')
            after=state();ack=acknowledgements[-1]
            assert ack['item_id']==501 and ack['success'] and ack['client_index']==index,ack
            assert after['red']==99 and after['hp']==after['maxhp'] and after['hp']>before['hp'],(before,after)
            assert after['knife']==after['shirt']==1 and after['zeny']==before['zeny']
            cases.append({'slot':slot,'initial_red_potions':100,'remaining_after_native_use':after['red'],
                          'hp_before':before['hp'],'hp_after':after['hp'],'maxhp':after['maxhp'],
                          'knife_and_shirt_preserved':True,'initial_zeny':initial['zeny'],'use_zeny_cost':0,'native_ack':ack})
            if slot==0:
                actions=Actions(s);cash=after['zeny']
                transcripts['purchase']=actions.talk('Loteria',choices=[2,1,1,1])
                bought=state()
                assert '20h45 (horário de São Paulo)' in ' '.join(transcripts['purchase'])
                assert '21h.' not in ' '.join(transcripts['purchase']) and cash-bought['zeny']==4750
                transcripts['duplicate']=actions.talk('Loteria',choices=[2])
                blocked=state()
                assert blocked['zeny']==bought['zeny'] and 'um bilhete por sorteio' in ' '.join(transcripts['duplicate'])
                lottery={'price':4750,'candidate_text_displayed':True,'duplicate_blocked_without_debit':True,
                         'draw_event_unchanged':'OnClock2045','local_timezone_offset':time.strftime('%z')}
            else:
                transcripts['second_character_duplicate']=Actions(s).talk('Loteria',choices=[2])
                blocked=state()
                assert blocked['zeny']==after['zeny'] and 'um bilhete por sorteio' in ' '.join(transcripts['second_character_duplicate'])
                lottery['same_account_second_character_blocked_without_debit']=True
        finally:
            try:
                if s.phase=='map':s.quit(timeout=5)
            finally:s.close()
    saved=[list(map(int,row.split('\t'))) for row in sql('SELECT char_id,amount FROM ragnarok.inventory WHERE nameid=501 ORDER BY char_id;').splitlines()]
    assert len(saved)==2 and all(row[1]==99 for row in saved),saved
    assert all(hashlib.sha256((source/rel).read_bytes()).hexdigest()==value for rel,value in originals.items())
    assert '[Error]' not in log('map.log') and '[SQL Error]' not in log('map.log')
    assert re.search(r"'0' Spawn sets",log('map.log'))
    return {'status':'passed','onboarding':cases,'saved_red_potion_amounts':[row[1] for row in saved],
            'lottery':lottery,'transcripts':transcripts,'patch_sha256':hashlib.sha256(patch.read_bytes()).hexdigest(),
            'installed_lottery_sha256':originals[LOTTERY],
            'lottery_source_variant':'old_source_patched_in_private_lab' if patch_applied else 'deployed_candidate_unchanged',
            'patch_applied_in_private_lab':patch_applied,
            'candidate_lottery_sha256':hashlib.sha256((folder/LOTTERY).read_bytes()).hexdigest(),
            'production_lottery_changed':False,'combats_executed':0,'player_performance_metrics':False}
