"""need-priority hooks, run as Taskwarrior runs them, against a throwaway task dir and a fake
`task` (it logs its calls and serves an export).

- on-exit does nothing for a command that changed no task (a report): no `task export`, no
  write, no log. It used to export every pending task and rewrite need.rc on every command.
- When tasks changed, on-exit rewrites need.rc only if the filter differs, and then touches
  config/.cmx_stale so tw rebuilds a cmx set that includes need.
- An unset filter (fresh install: need.rc ships it empty) is filled after any command.
- on-add only assigns priority; the filter is on-exit's job (on-add's copy missed
  additional.filters).
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
ARGS = ['api:2', 'args:task count', 'command:count', 'rc:/x/.taskrc', 'data:/x', 'version:2.6.2']

NEED_RC = '''span=2
lookahead=2d
lookback=1w
priority.1.auto=+urgent
priority.3.auto=proj:home
context.need.read=OLD
'''


@pytest.fixture
def sandbox(tmp_path):
    task_dir = tmp_path / 'task'
    (task_dir / 'config').mkdir(parents=True)
    (task_dir / 'config' / 'need.rc').write_text(NEED_RC)
    bin_ = tmp_path / 'bin'
    bin_.mkdir()
    calls = tmp_path / 'task-calls'
    export = tmp_path / 'export.json'
    export.write_text(json.dumps([{'uuid': 'a', 'priority': '3'}, {'uuid': 'b', 'priority': '5'}]))
    fake = bin_ / 'task'
    fake.write_text(f'#!/bin/sh\necho "$*" >> {calls}\ncat {export}\n')
    fake.chmod(0o755)
    env = dict(os.environ, TW_TASK_DIR=str(task_dir), PATH=f"{bin_}:/usr/bin:/bin")
    env.pop('TW_DEBUG', None)

    class S:
        pass
    s = S()
    s.dir, s.calls, s.export = task_dir, calls, export
    s.need = task_dir / 'config' / 'need.rc'
    s.marker = task_dir / 'config' / '.cmx_stale'
    s.log = task_dir / 'logs' / 'debug' / 'on-exit.log'
    s.run = lambda hook, stdin='': subprocess.run(
        [sys.executable, str(REPO / hook)] + ARGS, input=stdin, capture_output=True, text=True,
        env=env, timeout=30)
    s.filter = lambda: next(l for l in s.need.read_text().splitlines()
                            if l.startswith('context.need.read='))
    return s


def test_exit_after_a_report_does_nothing(sandbox):
    r = sandbox.run('on-exit_need-priority.py', '')
    assert r.returncode == 0 and r.stdout == ''
    assert not sandbox.calls.exists()
    assert sandbox.need.read_text() == NEED_RC
    assert not sandbox.marker.exists() and not sandbox.log.exists()


def test_exit_fills_an_unset_filter_even_after_a_report(sandbox):
    sandbox.need.write_text(NEED_RC.replace('context.need.read=OLD', 'context.need.read='))
    sandbox.run('on-exit_need-priority.py', '')           # first command after a fresh install
    assert sandbox.filter().startswith('context.need.read=( priority:3 or priority:4 )')
    assert sandbox.marker.exists()


def test_exit_after_a_change_updates_and_marks_cmx(sandbox):
    r = sandbox.run('on-exit_need-priority.py', '{"uuid":"a","priority":"3"}\n')
    assert r.returncode == 0
    assert sandbox.filter() == ('context.need.read=( priority:3 or priority:4 ) or '
                                '( due.before:today+2d and due.after:today-1w ) or '
                                '( scheduled.before:today+2d and sched.after:today-1w )')
    assert sandbox.marker.exists()
    assert len(sandbox.log.read_text().splitlines()) == 1
    assert 'priority.1.auto=+urgent' in sandbox.need.read_text()     # the rest kept


def test_exit_with_an_unchanged_filter_writes_nothing(sandbox):
    sandbox.run('on-exit_need-priority.py', '{"uuid":"a"}\n')
    sandbox.marker.unlink()
    before = sandbox.need.stat().st_mtime_ns
    sandbox.run('on-exit_need-priority.py', '{"uuid":"b"}\n')
    assert sandbox.need.stat().st_mtime_ns == before
    assert not sandbox.marker.exists()


def test_exit_includes_additional_filters(sandbox):
    sandbox.need.write_text(NEED_RC + 'additional.filters=+next\n')
    sandbox.run('on-exit_need-priority.py', '{"uuid":"a"}\n')
    assert sandbox.filter().endswith(' or +next')


def test_exit_with_no_pending_tasks_clears_the_filter(sandbox):
    sandbox.export.write_text('[]')
    sandbox.run('on-exit_need-priority.py', '{"uuid":"a","status":"completed"}\n')
    assert sandbox.filter() == 'context.need.read='


@pytest.mark.parametrize('task,priority', [
    ({'description': 'fix roof', 'project': 'home'}, '3'),
    ({'description': 'pay now', 'tags': ['urgent']}, '1'),
    ({'description': 'whatever'}, '4'),
    ({'description': 'old style', 'priority': 'H'}, '2'),
    ({'description': 'mine', 'priority': '5'}, '5'),
])
def test_add_assigns_priority_and_leaves_the_filter(sandbox, task, priority):
    r = sandbox.run('on-add_need-priority.py', json.dumps(task) + '\n')
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)['priority'] == priority
    assert not sandbox.calls.exists()                   # no export during an add
    assert sandbox.filter() == 'context.need.read=OLD'
