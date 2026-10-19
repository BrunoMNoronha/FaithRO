#!/usr/bin/env python3
"""Short, resource-limited character creation QA on Linux. No production SQL.

Creates a fresh MariaDB and login/char servers inside private network, PID and mount
namespaces. Production sources are mounted read-only. All QA data is temporary.
Requires existing systemd-run, unshare, MariaDB tools and installed rAthena binaries.
Default mode does not launch map-server. --npc-checks and --service-checks add
unchanged NPC dialogs in a world without monster spawns. Never installs packages
or copies player accounts. --candidate-checks compares the installed NPCs with
two explicit patches applied only to private temporary copies.
--onboarding-checks exercises real inventory potion use and the reviewed lottery
text, patching only an old private copy or testing an exact deployed candidate unchanged.
--lottery-recovery-checks restores the reviewed NPC backup only inside the private lab.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time

SOURCE = Path('/home/rathena/rathena')
SERVICES = ['rathena-login','rathena-char','rathena-map','rathena-web','faithro-web']


def output(args, **kwargs):
    return subprocess.check_output(args, text=True, **kwargs).strip()


def pids():
    return {name:int(output(['systemctl','show',name,'-p','MainPID','--value'])) for name in SERVICES}


def namespace():
    return os.readlink('/proc/self/ns/net')


def inner(folder, parent_net, npc_checks=False, service_checks=False, candidate_checks=False, onboarding_checks=False, recovery_checks=False):
    onboarding_checks=onboarding_checks or recovery_checks
    folder=Path(folder).resolve()
    assert folder.parent==Path('/tmp') and folder.name.startswith('faithro-char-qa-')
    assert parent_net and namespace()!=parent_net, 'Private network namespace required'
    assert os.getpid()==1, 'Private PID namespace required'
    output(['ip','link','set','lo','up'])
    interfaces=sorted(row['ifname'] for row in json.loads(output(['ip','-j','link','show'])))
    assert interfaces==['lo'], 'Only isolated loopback permitted'
    subprocess.run(['mount','--bind',str(SOURCE),str(SOURCE)],check=True)
    subprocess.run(['mount','-o','remount,bind,ro',str(SOURCE)],check=True)
    assert output(['findmnt','-n','-o','OPTIONS','-T',str(SOURCE)]).split(',').count('ro')==1
    # Hide the production SQL socket as a second barrier in addition to private TCP.
    if Path('/run/mysqld').is_dir():
        subprocess.run(['mount','-t','tmpfs','-o','size=1m','tmpfs','/run/mysqld'],check=True)
    os.chdir(folder)
    shutil.copytree(SOURCE/'conf',folder/'conf',ignore=shutil.ignore_patterns('import'))
    (folder/'conf/import').mkdir()
    (folder/'conf/import/packet_conf.txt').touch()
    for path in (SOURCE/'conf/import-tmpl').glob('*.yml'):
        shutil.copy2(path,folder/'conf/import'/path.name)
    if (SOURCE/'conf/msg_conf/import').is_dir():
        shutil.copytree(SOURCE/'conf/msg_conf/import',folder/'conf/msg_conf/import')
    for name in ['db','sql-files']:
        (folder/name).symlink_to(SOURCE/name,target_is_directory=True)
    # rAthena changes cwd to its executable's directory; use real copies, not symlinks.
    for name in ['login-server','char-server']:
        shutil.copy2(SOURCE/name,folder/name)
    children=[];handles=[]
    token=secrets.token_hex(8)
    db_password=secrets.token_hex(12)
    player_password=secrets.token_hex(8)
    auth_password=secrets.token_hex(8)
    secret_values=[token,db_password,player_password,auth_password]
    datadir=folder/'mysql';socket=folder/'mysql.sock'
    def command(args, input_text=None):
        result=subprocess.run(args,input=input_text,text=True,capture_output=True,timeout=60)
        if result.returncode:
            # Details stay inside the temporary lab; never print credentials or SQL.
            raise RuntimeError(f'{Path(args[0]).name} failed with exit {result.returncode}')
        return result.stdout
    def sql(query):
        return command(['mariadb','--no-defaults','--socket='+str(socket),'-uroot','-N','-B'],query)
    def spawn(args, logfile):
        handle=(folder/logfile).open('wb');handles.append(handle)
        proc=subprocess.Popen(args,stdout=handle,stderr=subprocess.STDOUT,cwd=folder,
                              env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        children.append(proc);return proc
    def wait_for(predicate, proc, label, seconds=35):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            if proc.poll() is not None:raise RuntimeError(label+' exited before readiness')
            if predicate():return
            time.sleep(.25)
        raise RuntimeError(label+' readiness timeout')
    def log(name):
        return re.sub(r'\x1b\[[0-9;]*m','',(folder/name).read_text(errors='replace'))
    try:
        command(['mariadb-install-db','--no-defaults','--datadir='+str(datadir),
                 '--auth-root-authentication-method=normal','--skip-test-db','--user=root',
                 '--innodb-buffer-pool-size=32M','--innodb-log-file-size=8M'])
        database=spawn(['mariadbd','--no-defaults','--user=root','--datadir='+str(datadir),
                        '--socket='+str(socket),'--pid-file='+str(folder/'mysql.pid'),
                        '--bind-address=127.0.0.1','--port=3306','--innodb-buffer-pool-size=32M',
                        '--innodb-log-file-size=8M','--max-connections=24','--performance-schema=OFF',
                        '--skip-name-resolve','--log-error='+str(folder/'mysql-error.log')],'mysql-console.log')
        wait_for(lambda: socket.exists(),database,'MariaDB')
        end=time.monotonic()+10
        while True:
            try:sql('SELECT 1;');break
            except RuntimeError:
                if time.monotonic()>end:raise
                time.sleep(.25)
        sql('CREATE DATABASE ragnarok; CREATE DATABASE ragnarok_log;')
        sql('USE ragnarok;\n'+(SOURCE/'sql-files/main.sql').read_text())
        sql('USE ragnarok_log;\n'+(SOURCE/'sql-files/logs.sql').read_text())
        sql(f"CREATE USER 'qa'@'127.0.0.1' IDENTIFIED BY '{db_password}'; "
            "GRANT ALL ON ragnarok.* TO 'qa'@'127.0.0.1'; "
            "GRANT ALL ON ragnarok_log.* TO 'qa'@'127.0.0.1'; "
            f"UPDATE ragnarok.login SET userid='qa_inter',user_pass='{auth_password}' WHERE account_id=1; "
            f"INSERT INTO ragnarok.login(account_id,userid,user_pass,sex,email,group_id) VALUES "
            f"(2000001,'qa_player','{player_password}','M','qa@example.invalid',0);")
        dbconf=[]
        for role in ['login_server','char_server','map_server','web_server','ipban_db','log_db']:
            dbconf += [f'{role}_ip: 127.0.0.1',f'{role}_port: 3306',f'{role}_id: qa',
                       f'{role}_pw: {db_password}',f'{role}_db: '+('ragnarok_log' if role=='log_db' else 'ragnarok')]
        (folder/'conf/import/inter_conf.txt').write_text('\n'.join(dbconf)+'\n')
        (folder/'conf/import/faithro_auth.txt').write_text(f'userid: qa_inter\npasswd: {auth_password}\n')
        (folder/'conf/import/login_conf.txt').write_text('bind_ip: 127.0.0.1\nuse_MD5_passwords: no\nnew_account: no\n')
        character_conf=(SOURCE/'conf/import/char_conf.txt').read_text()
        assert 'start_items_pre: 1201,1,2:2301,1,16:501,100,0' in character_conf
        (folder/'conf/import/char_conf.txt').write_text(character_conf+'\nlogin_ip: 127.0.0.1\nchar_ip: 127.0.0.1\nbind_ip: 127.0.0.1\n')
        # Capture public gameplay settings before hiding the production import directory.
        for name in ['battle_conf.txt','log_conf.txt']:
            (folder/'conf/import'/name).write_bytes((SOURCE/'conf/import'/name).read_bytes())
        for name in ['inter_conf.txt','faithro_auth.txt','login_conf.txt','char_conf.txt']:
            (folder/'conf/import'/name).chmod(0o600)
        # Even an accidental absolute import can only see the private lab credentials.
        subprocess.run(['mount','--bind',str(folder/'conf/import'),str(SOURCE/'conf/import')],check=True)
        subprocess.run(['mount','-o','remount,bind,ro',str(SOURCE/'conf/import')],check=True)
        login=spawn([str(folder/'login-server')],'login.log')
        wait_for(lambda:'ready' in log('login.log').lower(),login,'login-server')
        character=spawn([str(folder/'char-server')],'char.log')
        wait_for(lambda:'The char-server is ready' in log('char.log'),character,'char-server')
        wait_for(lambda:'Connected to login-server' in log('char.log'),character,'char/login link')
        sys.dont_write_bytecode=True
        bundled=Path(__file__).with_name('bot')
        sys.path.insert(0,str(bundled.parent) if bundled.is_dir() else '/root/faithro/deploy/tools')
        from bot.client import Session
        from bot import protocol as P
        session=Session(host='127.0.0.1',char_host='127.0.0.1',timeout=8)
        ids=[]
        try:
            session.login('qa_player',player_password,retries=0)
            server=session.login_ok.servers[0]
            session._connect('127.0.0.1',server.port,'char')
            session.send(P.pack_ch_enter(session.login_ok))
            session._read_raw(4,8)
            end=time.monotonic()+10
            while time.monotonic()<end:
                pid,frame=session.read_packet(8)
                if pid==P.HC_ACCEPT_ENTER:break
                session._char_chatter(pid,frame)
            else:raise RuntimeError('Character list not received')
            for slot in [0,1]:
                session.send(P.pack_ch_make_char('IsolatedQA'+str(slot),slot,session.me.sex))
                end=time.monotonic()+10
                while time.monotonic()<end:
                    pid,frame=session.read_packet(8)
                    if pid==P.HC_ACCEPT_MAKECHAR:
                        ids.append(P.unpack_character_info(frame,2).char_id);break
                    if pid==P.HC_REFUSE_MAKECHAR:raise RuntimeError('QA character creation refused')
                    session._char_chatter(pid,frame)
                else:raise RuntimeError('Character creation timed out')
        finally:session.close()
        rows=sql('SELECT char_id,nameid,amount,equip,identify FROM ragnarok.inventory ORDER BY char_id,nameid;')
        inventory=[list(map(int,line.split('\t'))) for line in rows.splitlines()]
        for char_id in ids:
            actual=[r[1:] for r in inventory if r[0]==char_id]
            assert actual==[[501,100,0,1],[1201,1,2,1],[2301,1,16,1]], actual
        assert len(ids)==2 and len(set(ids))==2
        npc_result=None
        if npc_checks or service_checks or candidate_checks or onboarding_checks:
            import importlib.util
            helper_name=('isolated_onboarding_checks.py' if onboarding_checks else
                         'isolated_candidate_checks.py' if candidate_checks else
                         'isolated_service_checks.py' if service_checks else 'isolated_npc_checks.py')
            spec=importlib.util.spec_from_file_location('_npc_qa',Path(__file__).with_name(helper_name))
            helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
            npc_result=helper.run(folder,SOURCE,sql,spawn,wait_for,log,player_password,
                                  **({'recovery':True} if recovery_checks else {}))
        print(json.dumps({'status':'passed','private_network':True,'network_interfaces':interfaces,
                          'private_pid_namespace':True,'production_sources_readonly':True,
                          'fresh_database':True,'production_accounts_copied':False,
                          'qa_characters_created':len(ids),'inventory':inventory,
                          'starting_red_potions_per_character':100,'knife_and_shirt_preserved':True,
                          'map_server_started':npc_checks or service_checks or candidate_checks or onboarding_checks,'combats_executed':0,
                          'npc_checks':npc_result if npc_checks else None,
                          'service_checks':npc_result if service_checks else None,
                          'candidate_checks':npc_result if candidate_checks else None,
                          'onboarding_checks':npc_result if onboarding_checks else None,
                          'client_modules_from_temporary_bundle':bundled.is_dir(),
                          'player_performance_metrics':False}))
    except Exception as error:
        # Only initialization errors, never raw SQL, account packets or passwords.
        message=str(error)
        for secret in secret_values:message=message.replace(secret,'[redacted]')
        diagnostics={}
        for name in ['login.log','char.log','map.log','mysql-error.log']:
            if (folder/name).is_file():
                excerpt='\n'.join(log(name).splitlines()[-24:])
                errors=[line for line in log(name).splitlines() if '[Error]' in line or '[SQL Error]' in line or 'script error' in line]
                if errors:excerpt+='\nINITIALIZATION_ERRORS:\n'+'\n'.join(errors[:20])
                for secret in secret_values:excerpt=excerpt.replace(secret,'[redacted]')
                excerpt=re.sub(r'login_id[12]:-?\d+','login_id:[redacted]',excerpt)
                diagnostics[name]=excerpt
        print(json.dumps({'status':'failed','error':message,'diagnostics':diagnostics,'combats_executed':0}))
        raise SystemExit(1)
    finally:
        for proc in reversed(children):
            if proc.poll() is None:
                proc.terminate()
                try:proc.wait(timeout=4)
                except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=4)
        for handle in handles:handle.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inner',type=Path)
    parser.add_argument('--parent-net')
    modes=parser.add_mutually_exclusive_group()
    modes.add_argument('--npc-checks',action='store_true')
    modes.add_argument('--service-checks',action='store_true')
    modes.add_argument('--candidate-checks',action='store_true')
    modes.add_argument('--onboarding-checks',action='store_true')
    modes.add_argument('--lottery-recovery-checks',action='store_true')
    args=parser.parse_args()
    if args.inner:
        inner(args.inner,args.parent_net,args.npc_checks,args.service_checks,args.candidate_checks,args.onboarding_checks,args.lottery_recovery_checks);return
    if sys.platform!='linux' or os.geteuid()!=0:
        raise SystemExit('Run on Linux as root; no action taken.')
    required=['systemd-run','unshare','ip','mount','findmnt','mariadb-install-db','mariadbd','mariadb']
    if args.candidate_checks or args.onboarding_checks or args.lottery_recovery_checks:required.append('git')
    assert all(shutil.which(p) for p in required), 'Existing isolation/MariaDB tools required'
    available=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))
    memory=512 if args.npc_checks or args.service_checks or args.candidate_checks or args.onboarding_checks or args.lottery_recovery_checks else 384
    runtime=600 if args.candidate_checks else 420 if args.service_checks else 300 if args.npc_checks or args.onboarding_checks or args.lottery_recovery_checks else 180
    assert available>=(memory+384)*1024, 'Insufficient available RAM for isolated check plus reserve'
    before=pids();assert all(before.values())
    conf=SOURCE/'conf/import/char_conf.txt'
    digest=hashlib.sha256(conf.read_bytes()).hexdigest()
    parent=namespace()
    with tempfile.TemporaryDirectory(prefix='faithro-char-qa-',dir='/tmp') as folder:
        result=subprocess.run(['systemd-run','--quiet','--wait','--pipe','--collect',
            '--unit=faithro-char-qa-'+secrets.token_hex(4),
            '-p','CPUQuota=25%','-p',f'MemoryMax={memory}M','-p','MemorySwapMax=0',
            '-p','TasksMax=64','-p',f'RuntimeMaxSec={runtime}','-p','TimeoutStopSec=5',
            '-p','KillMode=control-group','-p','Nice=15',
            'unshare','--mount','--propagation','private','--net','--pid','--fork','--mount-proc',
            sys.executable,'-B',str(Path(__file__).resolve()),'--inner',folder,'--parent-net',parent,
            *(['--npc-checks'] if args.npc_checks else []),
            *(['--service-checks'] if args.service_checks else []),
            *(['--candidate-checks'] if args.candidate_checks else []),
            *(['--onboarding-checks'] if args.onboarding_checks else []),
            *(['--lottery-recovery-checks'] if args.lottery_recovery_checks else [])],
            text=True,capture_output=True,timeout=runtime+20)
        lines=[line for line in result.stdout.splitlines() if line.startswith('{')]
        data=json.loads(lines[-1]) if lines else {'status':'failed','error':'No structured result from isolated process'}
        if not lines:
            data['diagnostic']='\n'.join(line for line in result.stderr.splitlines() if any(word in line for word in
                ['AssertionError','Permission denied','unshare:','Failed','Traceback','RuntimeError']))[-1500:]
        data.update(production_service_pids_unchanged=pids()==before,
                    production_char_config_unchanged=hashlib.sha256(conf.read_bytes()).hexdigest()==digest,
                    resource_limits={'cpu_percent':25,'memory_MiB':memory,'max_seconds':runtime},
                    production_mutations=False,temporary_lab_removed_after_exit=True)
    print(json.dumps(data))
    if result.returncode or data['status']!='passed' or not data['production_service_pids_unchanged'] or not data['production_char_config_unchanged']:
        raise SystemExit(1)


if __name__=='__main__':main()
