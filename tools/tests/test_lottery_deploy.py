"""Offline refusal paths only: never connect to a host or operate a real service."""
import importlib.util
import io
import json
from pathlib import Path
import types

import pytest

spec = importlib.util.spec_from_file_location('lottery_deploy', Path(__file__).resolve().parents[1] / 'deploy_lottery_text.py')
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


def test_non_linux_refuses_before_reading_payload(monkeypatch):
    monkeypatch.setattr(tool.sys, 'platform', 'win32')
    monkeypatch.setattr(tool.sys, 'stdin', io.StringIO('invalid JSON'))
    with pytest.raises(AssertionError, match='Known Linux VPS'):
        tool.main()


@pytest.fixture
def isolated_deployer(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(tool.sys, 'platform', 'linux')
    monkeypatch.setattr(tool.os, 'geteuid', lambda: 0, raising=False)
    monkeypatch.setattr(tool.os, 'umask', lambda mask: None)
    monkeypatch.setitem(tool.sys.modules, 'fcntl', types.SimpleNamespace(flock=lambda *args: None, LOCK_EX=1, LOCK_NB=2))
    monkeypatch.setattr(tool.sys, 'stdin', io.StringIO(json.dumps({tool.FIXES[0]: {}})))

    def restricted_path(value):
        assert value == '/run/lock/faithro-deploy.lock', 'Unexpected filesystem access before refusal'
        return tmp_path / 'fake-lock'

    def forbidden_run(args):
        calls.append(args)
        raise AssertionError('Unexpected process execution')

    monkeypatch.setattr(tool, 'Path', restricted_path)
    monkeypatch.setattr(tool, 'run', forbidden_run)
    monkeypatch.setattr(tool, 'pids', lambda: {name: 1 for name in tool.SERVICES})
    return calls


def test_online_character_refuses_before_backup_files_or_service_stop(isolated_deployer, monkeypatch):
    monkeypatch.setattr(tool, 'sql', lambda query: '1')
    with pytest.raises(AssertionError, match='Online characters'):
        tool.main()
    assert isolated_deployer == []


def test_stopped_service_refuses_before_database_query(isolated_deployer, monkeypatch):
    monkeypatch.setattr(tool, 'pids', lambda: {name: 0 for name in tool.SERVICES})
    monkeypatch.setattr(tool, 'sql', lambda query: pytest.fail('Unexpected database query'))
    with pytest.raises(AssertionError, match='Services must be running'):
        tool.main()
    assert isolated_deployer == []


def test_wrong_timezone_refuses_before_file_changes(isolated_deployer, monkeypatch):
    monkeypatch.setattr(tool, 'sql', lambda query: '0')
    monkeypatch.setattr(tool, 'run', lambda args: 'UTC' if args == ['timedatectl', 'show', '-p', 'Timezone', '--value'] else pytest.fail('Unexpected process'))
    with pytest.raises(AssertionError):
        tool.main()
    assert isolated_deployer == []
