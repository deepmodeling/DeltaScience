"""Version-gated integration; old task snapshots retain their old runtime behavior."""
import json
from pathlib import Path
import secrets
import shlex

REVISION = 'author-1.0.17-role-proxy-v1'
PRIVATE = '/run/pkscience-retro'
MODULE = PRIVATE + '/retro_transport.py'


def install(cls):
    if getattr(cls, '_pkscience_v17_installed', False):
        return
    old_put, old_transport, old_native = cls._put, cls._transport, cls._native_files

    def enabled(self):
        return bool(self._retro and self._retro.get('runtime_revision') == REVISION)

    async def put(self, env, source, target, mode='0444'):
        await old_put(self,env,source,target,mode)
        if enabled(self) and target == '/opt/retro/pservice/http_service.py':
            native = self._payload/'environment/retro-native'
            for name in ('public_stock_view_v17.py','native_gold_stock_v16.py'):
                await old_put(self,env,native/name,'/opt/retro/pservice/'+name,'0444')
            # Native peer authentication is unchanged. Only the signed grader
            # gateway binds this source address; the agent uses 127.0.0.1.
            script = ("from pathlib import Path; p=Path('/etc/hosts'); s=p.read_text(); "
                      "assert not any('grader' in l.split()[1:] for l in s.splitlines() if l.strip() and not l.startswith('#')); "
                      "p.write_text(s+'\\n127.0.0.2 grader\\n')")
            await self._checked(env,'python3 -I -B -c '+shlex.quote(script),idempotent=False)

    async def transport(self, env, mode, upstream):
        if not enabled(self):
            return await old_transport(self,env,mode,upstream)
        if not hasattr(self,'_grader_capability_v17'):
            self._grader_capability_v17 = secrets.token_hex(32)
        if mode == 'service-gateway':
            config = dict(mode=mode,upstream=upstream,role_tokens={
                'agent':self._capability,'grader':self._grader_capability_v17})
        else:
            role = 'grader' if env is self._components.get('grader') else 'agent'
            config = dict(mode=mode,upstream=upstream,role=role,
                          token=self._grader_capability_v17 if role=='grader' else self._capability)
        await self._checked(env,'mkdir -p '+PRIVATE+' && chmod 700 '+PRIVATE)
        await old_put(self,env,self._payload/'retro_transport_v17.py',MODULE,'0500')
        await self._bytes(env,json.dumps(config).encode(),PRIVATE+'/proxy.json')
        await self._spawn(env,['python3','-I','-B',MODULE,'proxy'],mode)

    async def native_files(self, env):
        await old_native(self, env)
        if enabled(self):
            # Compose bind mounts must also be realized in API-created sandboxes.
            await env.upload_dir(self._payload/'environment/views/open','/workspace/task')
            await self._checked(env,'chown -R root:root /workspace/task && find /workspace/task -type d -exec chmod 755 {} + && find /workspace/task -type f -exec chmod 444 {} +')
            if env is self._components.get('grader'):
                await env.upload_dir(self._payload/'environment/reward-overlay','/tests')
                await self._checked(env,'chown -R root:root /tests && find /tests -type d -exec chmod 755 {} + && find /tests -type f -exec chmod 444 {} +')

    cls._put, cls._transport, cls._native_files = put, transport, native_files
    cls._pkscience_v17_installed = True
