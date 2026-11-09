"""Push an already committed task branch without placing credentials in URLs/logs."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--repo', type=Path, required=True)
parser.add_argument('--branch', required=True)
parser.add_argument('--ref', default='HEAD')
args = parser.parse_args()
values = {}
for line in Path('/cantor/keys/.env').read_text().splitlines():
    if '=' in line and not line.strip().startswith('#'):
        key, value = line.strip().removeprefix('export ').split('=', 1)
        values[key.strip()] = value.strip().strip('\"\'')
env = dict(os.environ, CANTOR_TASK_GH_KEY=values['GH_KEY'], GIT_TERMINAL_PROMPT='0')
with tempfile.TemporaryDirectory(prefix='cantor-task-git-') as temporary:
    askpass = Path(temporary) / 'askpass'
    askpass.write_text('#!/bin/sh\ncase "$1" in *Username*) printf %s x-access-token;; *) printf %s "$CANTOR_TASK_GH_KEY";; esac\n')
    askpass.chmod(0o700)
    subprocess.run(['git', '-C', str(args.repo), '-c', 'credential.helper=',
        '-c', 'core.askPass=' + str(askpass), 'push', 'origin',
        args.ref + ':refs/heads/' + args.branch], env=env, check=True)
