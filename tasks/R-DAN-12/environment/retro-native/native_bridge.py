"""Root-only handoff to the unchanged verifier image in the same Compose trial.

No Docker socket, host extension, network listener, or solver-provided score.
The socket transports a session locator and grading configuration only.
"""
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import stat
import struct
import subprocess
import sys
import tarfile
import tempfile
import time

ROOT = Path('/run/retro-grader')
SOCKET = ROOT / 'grader.sock'
LOGS = Path('/logs/verifier')
LIMIT = 2 * 1024 * 1024
ENV_KEYS = ('RETRO_JUDGE_API_KEY', 'RETRO_JUDGE_URL', 'RETRO_JUDGE_MODEL',
            'RETRO_JUDGE_EXPECTED_MODEL_ID', 'RETRO_JUDGE_EXPECTED_FINGERPRINT',
            'RETRO_JUDGE_MAX_TOKENS', 'RETRO_SCORE_TRACE',
            'RETRO_JUDGE_HTTP_ATTEMPTS', 'RETRO_JUDGE_HTTP_IDLE_TIMEOUT',
            'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY',
            'http_proxy', 'https_proxy', 'all_proxy', 'no_proxy',
            'SSL_CERT_FILE', 'SSL_CERT_DIR', 'REQUESTS_CA_BUNDLE')


def require_root():
    if os.getuid() != 0 or os.geteuid() != 0:
        raise RuntimeError('ROOT_GRADING_HANDOFF_REQUIRED')


def process_start(pid):
    # The command field may contain spaces and parentheses.
    return Path('/proc/' + str(pid) + '/stat').read_text().rsplit(')', 1)[1].split()[19]


def protected(directory):
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    info = directory.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0:
        raise RuntimeError('UNTRUSTED_GRADING_DIRECTORY')
    directory.chmod(0o700)


def frame_send(connection, value):
    raw = json.dumps(value, allow_nan=False).encode()
    if len(raw) > LIMIT:
        raise RuntimeError('GRADING_REQUEST_TOO_LARGE')
    connection.sendall(struct.pack('!I', len(raw)) + raw)


def exact(connection, size):
    result = bytearray()
    while len(result) < size:
        piece = connection.recv(min(65536, size - len(result)))
        if not piece:
            raise RuntimeError('GRADING_CHANNEL_CLOSED')
        result.extend(piece)
    return bytes(result)


def frame_receive(connection):
    size = struct.unpack('!I', exact(connection, 4))[0]
    if size > LIMIT:
        raise RuntimeError('GRADING_REQUEST_TOO_LARGE')
    return json.loads(exact(connection, size))


def peer_is_root(connection):
    _, uid, _ = struct.unpack('3i', connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
    if uid != 0:
        raise RuntimeError('ROOT_PEER_REQUIRED')


def session_locator():
    file = Path('/workspace/outputs/variants/open/session.json')
    for parent in file.parents:
        if parent.exists() and parent.is_symlink():
            raise RuntimeError('SESSION_POINTER_LINK_REJECTED')
    try:
        descriptor = os.open(file, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return None
    with os.fdopen(descriptor, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > 65536:
            raise RuntimeError('SESSION_POINTER_INVALID')
        value = json.loads(stream.read(65537))
        if not isinstance(value, dict):
            raise RuntimeError('SESSION_POINTER_INVALID')
        import re
        if (not re.fullmatch(r'open-[a-f0-9]{32}', value.get('session_id', ''))
                or value.get('variant') != 'open'
                or not isinstance(value.get('coordinator_id'), str)
                or not value['coordinator_id'].strip()):
            raise RuntimeError('SESSION_POINTER_INVALID')
        return value


def stop_solver_processes():
    # Native shared lifecycle keeps main alive. Retire its unprivileged work
    # before handing off, while leaving the isolated original P-service alive.
    for _ in range(10):
        victims = []
        for entry in Path('/proc').iterdir():
            if not entry.name.isdigit():
                continue
            try:
                status = (entry / 'status').read_text()
                state = next(line for line in status.splitlines() if line.startswith('State:')).split()[1]
                if state in ('Z', 'X'):
                    continue
                uids = next(line for line in status.splitlines() if line.startswith('Uid:')).split()[1:]
                if '1000' in uids:
                    victims.append(int(entry.name))
            except (FileNotFoundError, ProcessLookupError, PermissionError):
                pass
        if not victims:
            return
        for pid in victims:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        time.sleep(0.05)
    raise RuntimeError('SOLVER_PROCESSES_NOT_RETIRED')


def copy_logs_to(connection, code):
    # Only normal files produced inside the isolated grader leave it.
    with tempfile.TemporaryFile() as stream:
        with tarfile.open(fileobj=stream, mode='w') as archive:
            for file in sorted(LOGS.rglob('*')):
                if file.is_file() and not file.is_symlink():
                    archive.add(file, arcname=str(file.relative_to(LOGS)), recursive=False)
        size = stream.tell()
        stream.seek(0)
        accumulator = hashlib.sha256()
        while block := stream.read(65536):
            accumulator.update(block)
        digest = accumulator.hexdigest()
        stream.seek(0)
        frame_send(connection, {'accepted': True, 'exit_code': code,
            'archive_bytes': size, 'archive_sha256': digest})
        while block := stream.read(65536):
            connection.sendall(block)
        frame_send(connection, {'complete': True, 'archive_sha256': digest})


def serve():
    require_root()
    sys.path.insert(0, '/opt/retro/main')
    import binding
    record = binding.initialize()
    protected(ROOT)
    protected(LOGS)
    with socket.socket(socket.AF_UNIX) as listener:
        listener.bind(str(SOCKET))
        SOCKET.chmod(0o600)
        listener.listen(2)
        (ROOT / 'ready.json').write_text(json.dumps({'schema': 'retro-native-grader/1',
            'trial_id': record['trial_id'], 'instance_id': record['instance_id'],
            'pid': os.getpid(), 'process_start': process_start(os.getpid())}))
        completed = False
        while True:
            connection, _ = listener.accept()
            with connection:
                peer_is_root(connection)
                request = frame_receive(connection)
                if request == {'action': 'health'}:
                    frame_send(connection, {'ready': True})
                    continue
                if completed:
                    frame_send(connection, {'accepted': False, 'reason': 'GRADING_ALREADY_REQUESTED'})
                    continue
                completed = True
                if set(request) != {'action', 'locator', 'environment'} or request['action'] != 'grade':
                    raise RuntimeError('INVALID_GRADING_REQUEST')
                environment = request['environment']
                if not isinstance(environment, dict) or set(environment) - set(ENV_KEYS) or any(not isinstance(v, str) for v in environment.values()):
                    raise RuntimeError('INVALID_GRADING_ENVIRONMENT')
                binding.check_service()
                pointer = request['locator']
                if pointer is not None:
                    output = Path('/workspace/outputs/variants/open')
                    protected(output)
                    (output / 'session.json').write_text(json.dumps(pointer))
                # The original /tests/test.sh and scientific implementation are
                # already bundled in the exact pinned verifier image.
                env = dict(os.environ, **environment)
                env.pop('RETRO_SERVICE_BINDING_SOURCE', None)
                env['RETRO_SERVICE_BINDING_SOURCE'] = '/run/retro-platform/service.json'
                try:
                    with (LOGS / 'grader-process.log').open('wb') as log:
                        run = subprocess.run(['/bin/bash', '/tests/test.sh'], env=env,
                            cwd='/tests', stdin=subprocess.DEVNULL, stdout=log,
                            stderr=subprocess.STDOUT, timeout=28800)
                    code = run.returncode
                except subprocess.TimeoutExpired:
                    code = 124
                    (LOGS / 'reward.txt').unlink(missing_ok=True)
                    (LOGS / 'reward.json').unlink(missing_ok=True)
                binding.check_service()
                (LOGS / 'native-handoff.json').write_text(json.dumps({
                    'schema': 'retro-native-grader/1', 'exit_code': code,
                    'original_service_instance_id': record['instance_id'],
                    'trial_id': record['trial_id'], 'grading_container': socket.gethostname(),
                    'platform_extension_required': False}))
                copy_logs_to(connection, code)


def relay():
    require_root()
    protected(LOGS)
    for name in ('reward.txt', 'reward.json'):
        (LOGS / name).unlink(missing_ok=True)
    try:
        _relay()
    except BaseException:
        (LOGS / 'reward.txt').unlink(missing_ok=True)
        (LOGS / 'reward.json').unlink(missing_ok=True)
        raise


def _relay():
    import shutil
    stop_solver_processes()
    request = {'action': 'grade', 'locator': session_locator(),
               'environment': {key: os.environ[key] for key in ENV_KEYS if key in os.environ}}
    with tempfile.TemporaryFile() as payload, socket.socket(socket.AF_UNIX) as connection:
        connection.settimeout(29000)
        connection.connect(str(SOCKET))
        frame_send(connection, request)
        result = frame_receive(connection)
        if result.get('accepted') is not True:
            raise RuntimeError('ISOLATED_GRADER_REJECTED_HANDOFF')
        remaining = result.get('archive_bytes')
        if type(remaining) is not int or not 0 < remaining <= 4 * 1024**3:
            raise RuntimeError('INVALID_GRADER_ARCHIVE_SIZE')
        digest = hashlib.sha256()
        while remaining:
            block = exact(connection, min(65536, remaining))
            payload.write(block); digest.update(block); remaining -= len(block)
        checksum = digest.hexdigest()
        if (checksum != result.get('archive_sha256') or frame_receive(connection) !=
                {'complete': True, 'archive_sha256': checksum}):
            raise RuntimeError('INCOMPLETE_GRADER_TRANSFER')
        payload.seek(0)
        with tempfile.TemporaryDirectory(prefix='retro-grade-') as temporary:
            stage = Path(temporary)
            seen = set()
            with tarfile.open(fileobj=payload, mode='r:') as archive:
                for member in archive:
                    relative = Path(member.name)
                    name = relative.as_posix()
                    if (not member.isfile() or relative.is_absolute() or '..' in relative.parts
                            or name in seen or name in ('', '.')):
                        raise RuntimeError('INVALID_GRADER_LOG_MEMBER')
                    seen.add(name)
                    target = stage / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with target.open('xb') as output:
                        shutil.copyfileobj(archive.extractfile(member), output)
                    target.chmod(0o600)
                    os.utime(target, (member.mtime, member.mtime), follow_symlinks=False)
            # Copy diagnostic logs even on a grading error, but commit no reward.
            for file in sorted(stage.rglob('*')):
                if file.is_file() and str(file.relative_to(stage)) not in ('reward.txt', 'reward.json'):
                    target = LOGS / file.relative_to(stage)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file, target)
                    target.chmod(0o600)
            if result.get('exit_code') != 0:
                raise RuntimeError('ISOLATED_GRADING_FAILED: see grader-process.log')
            reward = stage / 'reward.txt'
            if not reward.is_file() or reward.read_bytes() not in (b'0\n', b'1\n') or (stage / 'reward.json').exists():
                raise RuntimeError('ISOLATED_REWARD_INVALID_OR_MISSING')
            pending = LOGS / '.reward.pending'
            pending.write_bytes(reward.read_bytes()); pending.chmod(0o600)
            pending.replace(LOGS / 'reward.txt')


def health():
    require_root()
    ready = json.loads((ROOT / 'ready.json').read_text())
    info = SOCKET.lstat()
    if (not stat.S_ISSOCK(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077
            or process_start(ready['pid']) != ready['process_start']):
        raise RuntimeError('GRADER_NOT_READY')
    sys.path.insert(0, '/opt/retro/main')
    import binding
    record = binding.check_service()
    if (ready['trial_id'], ready['instance_id']) != (record['trial_id'], record['instance_id']):
        raise RuntimeError('GRADER_ORIGINAL_SERVICE_CHANGED')


def start_main():
    require_root()
    subprocess.run([sys.executable, '-I', '-B', '/opt/retro-native/cleanup_agent_view_v17.py'], check=True)
    protected(Path('/tests'))
    protected(LOGS)
    os.execv('/usr/local/bin/python', ['/usr/local/bin/python', '-I', '-B',
        '/opt/retro/main/entrypoint.py', 'container-start', 'sleep', 'infinity'])


if __name__ == '__main__':
    actions = {'serve': serve, 'relay': relay, 'health': health, 'start-main': start_main}
    actions[sys.argv[1]]()
