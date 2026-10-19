"""Scoped, backed-up deployment of the lab-validated FaithRO lottery text fix.

Run only on the known VPS as root, receiving a validated JSON payload on stdin.
Stops/starts only rathena-map, refuses online characters and restores files on failure.
"""
import base64
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile
import time

SOURCE=Path('/home/rathena/rathena')
MIRROR=Path('/root/faithro/deploy/server')
FIXES=['npc/custom/faithro/ptbr/custom/etc/lottery.txt']
SERVICES=['rathena-login','rathena-char','rathena-map','rathena-web','faithro-web']
PROTECTED=['conf/import/battle_conf.txt','conf/import/char_conf.txt','db/import/job_stats.yml',
           'db/import/statpoint.yml','npc/custom/faithro/optional.conf']
LOG=Path('/var/log/rathena/map.log')


def run(args):
    result=subprocess.run(args,text=True,capture_output=True,timeout=75)
    if result.returncode:raise RuntimeError(Path(args[0]).name+' failed: '+str(result.returncode))
    return result.stdout.strip()


def sha(data):return hashlib.sha256(data).hexdigest()


def pids():return {name:int(run(['systemctl','show',name,'-p','MainPID','--value'])) for name in SERVICES}


def sql(query):return run(['mariadb','-N','-B','-e',query])


def decode(data):
    try:return data.decode('utf-8'),'utf-8'
    except UnicodeDecodeError:return data.decode('cp1252'),'cp1252'


def atomic(path,data,st):
    fd,name=tempfile.mkstemp(prefix='.faithro-npc-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as handle:
            handle.write(data);handle.flush();os.fsync(handle.fileno())
            os.fchmod(handle.fileno(),st.st_mode & 0o777)
            os.fchown(handle.fileno(),st.st_uid,st.st_gid)
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)


def position():
    st=LOG.stat();return st.st_ino,st.st_size


def log_after(mark):
    st=LOG.stat()
    with LOG.open('rb') as handle:
        if st.st_ino==mark[0] and st.st_size>=mark[1]:handle.seek(mark[1])
        return re.sub(r'\x1b\[[0-9;]*m','',handle.read().decode('utf-8',errors='replace'))


def wait_ready(mark):
    deadline=time.monotonic()+60
    while time.monotonic()<deadline:
        text=log_after(mark)
        if '[Error]' in text or '[SQL Error]' in text or 'script error' in text.lower():
            raise RuntimeError('New map-server log contains errors')
        active=run(['systemctl','show','rathena-map','-p','ActiveState','--value'])
        if active=='failed':raise RuntimeError('Map-server failed')
        if active=='active' and "Server is 'ready'" in text and 'Map-server connected to char-server' in text:
            time.sleep(2)
            text=log_after(mark)
            assert '[Error]' not in text and '[SQL Error]' not in text,'Errors after readiness'
            required=['exp=300x/300x','max_parameter=185','max_trans_parameter=185','max_aspd=197','aura_lv=255']
            assert all(part in text for part in required),'Runtime reference flags not confirmed'
            return [line for line in text.splitlines() if '[FaithRO]' in line and ('exp=' in line or 'max_parameter=' in line)]
        time.sleep(.5)
    raise RuntimeError('Map-server readiness timeout')


def main():
    assert sys.platform=='linux' and os.geteuid()==0,'Known Linux VPS as root required'
    import fcntl
    os.umask(0o077)
    payload=json.load(sys.stdin)
    assert sorted(payload)==sorted(FIXES),'Only the validated lottery NPC is allowed'
    with Path('/run/lock/faithro-deploy.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        before_pids=pids();assert all(before_pids.values()),'Services must be running'
        assert sql('SELECT COUNT(*) FROM ragnarok.`char` WHERE online<>0;')=='0','Online characters; maintenance refused'
        assert run(['timedatectl','show','-p','Timezone','--value'])=='America/Sao_Paulo'
        assert not any(x.startswith(b'TZ=') for x in Path('/proc/'+str(before_pids['rathena-map'])+'/environ').read_bytes().split(b'\0'))
        protected={rel:sha((SOURCE/rel).read_bytes()) for rel in PROTECTED}
        originals={};candidates={};stats={}
        for rel in FIXES:
            spec=payload[rel];candidate=base64.b64decode(spec['installed_base64'],validate=True)
            assert sha(candidate)==spec['after_sha256'],'Candidate hash differs from tested version'
            for root,label in [(SOURCE,'installed'),(MIRROR,'deploy')]:
                path=root/rel;assert path.is_file() and not path.is_symlink()
                originals[path]=path.read_bytes();stats[path]=path.stat()
                if label=='installed':
                    assert sha(originals[path])==spec['before_sha256'],'Installed source drift'
                    original_text,installed_encoding=decode(originals[path])
                    new_text=candidate.decode(installed_encoding)
                    assert original_text.count('O sorteio ao vivo acontece às 21h.')==1
                    assert original_text.count('OnClock2045:')==1
                    assert new_text==original_text.replace('O sorteio ao vivo acontece às 21h.','O sorteio ao vivo acontece às 20h45 (horário de São Paulo).')
                    assert sha(originals[path])=='4e1114ff73ca4add082087420ba7dbbba7dd9970b7adab9f30260c34d2eff819'
                    assert sha(candidate)=='9dbbb64a8e449fb6765ff246312b5e9491c688e96d4bd1848ca00e9b887b4119'
                    candidates[path]=candidate
                else:
                    mirror_text,mirror_encoding=decode(originals[path])
                    assert mirror_text.replace('\r\n','\n')==original_text.replace('\r\n','\n'),'Deploy mirror drift'
                    candidates[path]=new_text.encode(mirror_encoding)
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        backup=Path('/var/backups/faithro')/('npc-lottery-time-'+stamp+'.tar.gz')
        backup.parent.mkdir(parents=True,exist_ok=True)
        manifest={'created_at_utc':datetime.now(timezone.utc).isoformat(),
                  'files':{str(p):{'sha256':sha(data),'mode':oct(stats[p].st_mode & 0o777),
                                  'uid':stats[p].st_uid,'gid':stats[p].st_gid} for p,data in originals.items()}}
        with backup.open('xb') as archive:
            with tarfile.open(fileobj=archive,mode='w:gz') as tar:
                for path,data in originals.items():
                    prefix='installed' if path.is_relative_to(SOURCE) else 'deploy'
                    root=SOURCE if prefix=='installed' else MIRROR
                    info=tarfile.TarInfo(prefix+'/'+str(path.relative_to(root)))
                    info.size=len(data);info.mode=stats[path].st_mode & 0o777
                    info.uid=stats[path].st_uid;info.gid=stats[path].st_gid
                    tar.addfile(info,io.BytesIO(data))
                raw=json.dumps(manifest,indent=2).encode()
                info=tarfile.TarInfo('manifest.json');info.size=len(raw);info.mode=0o600
                tar.addfile(info,io.BytesIO(raw))
        with tarfile.open(backup,'r:gz') as tar:
            assert len(tar.getmembers())==3
            for path,data in originals.items():
                prefix='installed' if path.is_relative_to(SOURCE) else 'deploy'
                root=SOURCE if prefix=='installed' else MIRROR
                assert tar.extractfile(prefix+'/'+str(path.relative_to(root))).read()==data
        assert sql('SELECT COUNT(*) FROM ragnarok.`char` WHERE online<>0;')=='0','Online characters arrived; maintenance refused'
        started=datetime.now(timezone.utc).isoformat();tick=time.monotonic()
        stopped=False
        try:
            run(['systemctl','stop','rathena-map']);stopped=True
            assert pids()['rathena-map']==0
            for path,data in candidates.items():atomic(path,data,stats[path])
            mark=position()
            run(['systemctl','start','rathena-map'])
            runtime=wait_ready(mark)
            after_pids=pids()
            assert all(after_pids.values()) and all(after_pids[n]==before_pids[n] for n in SERVICES if n!='rathena-map')
            assert all(sha((SOURCE/rel).read_bytes())==digest for rel,digest in protected.items()),'Protected configuration changed'
            assert run(['timedatectl','show','-p','Timezone','--value'])=='America/Sao_Paulo'
            assert all(path.read_bytes()==data for path,data in candidates.items())
            print(json.dumps({'status':'deployed','backup':str(backup),'backup_sha256':sha(backup.read_bytes()),
                'window_started_utc':started,'window_seconds':round(time.monotonic()-tick,2),
                'restarted_services':['rathena-map'],'other_service_pids_unchanged':True,'runtime_selftest':runtime,
                'new_map_errors':0,'protected_configuration_unchanged':True,'lottery_schedule_preserved':'OnClock2045','lottery_text_aligned':True,
                'files':{str(path):{'before_sha256':sha(originals[path]),'after_sha256':sha(data)} for path,data in candidates.items()},
                'database_writes_by_deployer':False,'combats_executed':0,'rollback_used':False}))
        except Exception as error:
            if stopped:
                run(['systemctl','stop','rathena-map'])
                for path,data in originals.items():atomic(path,data,stats[path])
                mark=position();run(['systemctl','start','rathena-map']);wait_ready(mark)
            print(json.dumps({'status':'rolled_back' if stopped else 'failed_before_changes',
                              'backup':str(backup),'reason':str(error),'rollback_restored_files':stopped}))
            raise SystemExit(1)


if __name__=='__main__':main()
