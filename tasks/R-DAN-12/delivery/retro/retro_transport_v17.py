"""Transport only: authenticated service proxy and root-only native grader handoff.

Scientific requests, original Unix framing, service identity and grader code are
unchanged. Credentials/configuration and grading spool files stay root-private.
"""
import argparse
import hashlib
import hmac
import http.server
import json
import os
from pathlib import Path
import socket
import stat
import struct
import time
import secrets
import threading
import urllib.error
import urllib.request
import urllib.parse

ROOT=Path('/run/pkscience-retro')
FRAME_LIMIT=2*1024**2
RESPONSE_LIMIT=4*1024**3+2*FRAME_LIMIT+8


def root_only():
    if os.getuid()!=0 or os.geteuid()!=0:raise PermissionError('Trusted root transport required')
    os.umask(0o077)
    ROOT.mkdir(mode=0o700,exist_ok=True)
    info=ROOT.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid!=0:raise RuntimeError('Untrusted transport directory')
    ROOT.chmod(0o700)


def exact(stream,n):
    value=bytearray()
    while len(value)<n:
        chunk=stream.recv(min(65536,n-len(value)))
        if not chunk:raise EOFError('Incomplete original grader frame')
        value.extend(chunk)
    return bytes(value)


def frame(stream):
    prefix=exact(stream,4);size=struct.unpack('!I',prefix)[0]
    if size>FRAME_LIMIT:raise ValueError('Oversized original grader frame')
    payload=exact(stream,size)
    return prefix+payload,json.loads(payload)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise RuntimeError('Unexpected service redirect')


def signed_headers(token,method,path,body):
    stamp=str(int(time.time()));nonce=secrets.token_hex(16);digest=hashlib.sha256(body or b'').hexdigest()
    value='\n'.join([method,path,stamp,nonce,digest]).encode()
    signature=hmac.new(token.encode(),value,hashlib.sha256).hexdigest()
    return {'X-Retro-Time':stamp,'X-Retro-Nonce':nonce,'X-Retro-Body':digest,'X-Retro-Signature':signature}


"""Role-authenticated proxy for author 1.0.17 grader peer authentication.

This function replaces only proxy_server in a copied, hash-recorded transport.
The unmodified native handler authenticates the actual upstream socket peer.
"""
def proxy_server(config, address=None):
    import hashlib
    import hmac
    import http.client
    import http.server
    import secrets
    import threading
    import time
    import urllib.error
    import urllib.parse
    import urllib.request

    public = config['mode'] == 'service-gateway'
    roles = ('agent', 'grader')
    if public:
        parsed = urllib.parse.urlsplit(config['upstream'])
        if (parsed.scheme != 'http' or parsed.hostname != '127.0.0.1'
                or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password):
            raise ValueError('Gateway must target original loopback service')
        tokens = config['role_tokens']
        if set(tokens) != set(roles) or tokens['agent'] == tokens['grader']:
            raise ValueError('Distinct role capabilities required')
    else:
        if not config['upstream'].startswith('https://') or config['role'] not in roles:
            raise ValueError('Authenticated HTTPS role client required')
        tokens = {config['role']: config['token']}
    if any(not isinstance(t, str) or len(t) < 40 for t in tokens.values()):
        raise ValueError('Invalid trial capability')

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            raise RuntimeError('Unexpected service redirect')

    class BoundHTTP(urllib.request.HTTPHandler):
        def __init__(self, source):
            super().__init__(); self.source = source
        def http_open(self, request):
            def connection(host, **kwargs):
                return http.client.HTTPConnection(host, source_address=(self.source, 0), **kwargs)
            return self.do_open(connection, request)

    def opener(role):
        handlers = [urllib.request.ProxyHandler({}), NoRedirect()]
        if public:
            handlers.append(BoundHTTP('127.0.0.2' if role == 'grader' else '127.0.0.1'))
        return urllib.request.build_opener(*handlers)

    clients = {r: opener(r) for r in tokens}
    nonces, lock = {}, threading.Lock()

    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.0'
        def log_message(self, *args):
            pass
        def do_GET(self):
            self.proxy()
        def do_POST(self):
            self.proxy()
        def proxy(self):
            if not self.path.startswith('/') or self.path.startswith('//'):
                self.send_error(400); return
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if size < 0 or size > 32 * 1024**2:
                    self.send_error(413); return
                role = self.headers.get('X-Retro-Role') if public else config['role']
                if role not in tokens:
                    self.send_error(403); return
                token = tokens[role]
                if public:
                    stamp = self.headers.get('X-Retro-Time', '')
                    nonce = self.headers.get('X-Retro-Nonce', '')
                    digest = self.headers.get('X-Retro-Body', '')
                    signature = self.headers.get('X-Retro-Signature', '')
                    value = '\n'.join([role, self.command, self.path, stamp, nonce, digest]).encode()
                    expected = hmac.new(token.encode(), value, hashlib.sha256).hexdigest()
                    if (not stamp.isdigit() or abs(time.time()-int(stamp)) > 60
                            or len(nonce) != 32 or len(digest) != 64
                            or not hmac.compare_digest(expected, signature)):
                        self.send_error(403); return
                    with lock:
                        now = time.time()
                        for old in [n for n,t in nonces.items() if now-t > 120]:
                            del nonces[old]
                        identity = (role, nonce)
                        if identity in nonces:
                            self.send_error(403); return
                        nonces[identity] = now
                # Defense in depth: only the grader capability reaches grading routes.
                if role != 'grader' and urllib.parse.urlsplit(self.path).path.startswith('/grading/'):
                    self.send_error(403); return
                body = self.rfile.read(size) if self.command == 'POST' else None
                body_digest = hashlib.sha256(body or b'').hexdigest()
                if public and not hmac.compare_digest(body_digest, digest):
                    self.send_error(403); return
                headers = {'Content-Type': self.headers.get('Content-Type', 'application/json'),
                           'Accept-Encoding': 'identity'}
                if not public:
                    stamp, nonce = str(int(time.time())), secrets.token_hex(16)
                    value = '\n'.join([role,self.command,self.path,stamp,nonce,body_digest]).encode()
                    headers.update({'X-Retro-Role': role, 'X-Retro-Time': stamp, 'X-Retro-Nonce': nonce,
                                    'X-Retro-Body': body_digest,
                                    'X-Retro-Signature': hmac.new(token.encode(),value,hashlib.sha256).hexdigest()})
                req = urllib.request.Request(config['upstream']+self.path,data=body,headers=headers,method=self.command)
                try:
                    response = clients[role].open(req,timeout=1800)
                except urllib.error.HTTPError as error:
                    response = error
                with response:
                    self.send_response(response.status)
                    for name in ('Content-Type','Content-Length'):
                        if response.headers.get(name):
                            self.send_header(name,response.headers[name])
                    self.end_headers()
                    while chunk := response.read1(65536):
                        self.wfile.write(chunk);self.wfile.flush()
            except (OSError,ValueError,RuntimeError):
                self.close_connection = True
    address = address or (('0.0.0.0',20768) if public else ('127.0.0.1',20765))
    return http.server.ThreadingHTTPServer(address,Handler)



def main_grader(directory=None):
    """Keep native_bridge.relay's local root-only Unix endpoint intact."""
    directory=Path(directory or '/run/retro-grader');directory.mkdir(mode=0o700,exist_ok=True)
    info=directory.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid!=0:raise RuntimeError('Untrusted native socket directory')
    directory.chmod(0o700)
    with socket.socket(socket.AF_UNIX) as listener:
        listener.bind(str(directory/'grader.sock'));(directory/'grader.sock').chmod(0o600);listener.listen(2)
        while True:
            connection,_=listener.accept()
            with connection:
                _,uid,_=struct.unpack('3i',connection.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
                if uid!=0:continue
                raw,request=frame(connection)
                if request.get('action')!='grade':raise ValueError('Only original grading handoff accepted')
                # Exactly one request per trial; never resume against new P state.
                with (ROOT/'request.frame').open('xb') as output:output.write(raw)
                (ROOT/'request.ready').write_text('ready\n')
                deadline=time.monotonic()+29000
                while not (ROOT/'response.ready').exists():
                    if (ROOT/'error').exists():raise RuntimeError('Trusted grading transport failed')
                    if time.monotonic()>deadline:raise TimeoutError('Original grading transport deadline exceeded')
                    time.sleep(.2)
                receipt=json.loads((ROOT/'response.ready').read_text())
                payload=ROOT/'response.frame'
                if payload.stat().st_size!=receipt['bytes'] or receipt['bytes']>RESPONSE_LIMIT:raise ValueError('Incomplete grading response')
                digest=hashlib.sha256()
                with payload.open('rb') as source:
                    while chunk:=source.read(65536):digest.update(chunk)
                if digest.hexdigest()!=receipt['sha256']:raise ValueError('Corrupt grading response')
                with payload.open('rb') as source:
                    while chunk:=source.read(65536):connection.sendall(chunk)
                return


def grader_request(native_socket='/run/retro-grader/grader.sock'):
    """Connect as root to the original isolated grader; retain its framed bytes."""
    path=ROOT/'request.frame';raw=path.read_bytes();path.unlink()
    if len(raw)<4 or len(raw)>FRAME_LIMIT+4 or struct.unpack('!I',raw[:4])[0]!=len(raw)-4:raise ValueError('Invalid request frame')
    result=ROOT/'response.frame';temporary=ROOT/'response.partial'
    with socket.socket(socket.AF_UNIX) as connection,temporary.open('xb') as output:
        connection.settimeout(29000);connection.connect(str(native_socket));connection.sendall(raw)
        size=0;digest=hashlib.sha256()
        while chunk:=connection.recv(65536):
            size+=len(chunk)
            if size>RESPONSE_LIMIT:raise ValueError('Oversized grader response')
            output.write(chunk);digest.update(chunk)
    temporary.replace(result)
    (ROOT/'response.ready').write_text(json.dumps({'bytes':size,'sha256':digest.hexdigest()}))


def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['proxy','main-grader','grader-request']);a=p.parse_args();root_only()
    if a.mode=='proxy':proxy_server(json.loads((ROOT/'proxy.json').read_text())).serve_forever()
    elif a.mode=='main-grader':main_grader()
    else:grader_request()
if __name__=='__main__':main()
