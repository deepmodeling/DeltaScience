"""Add trial-bound readiness around the unchanged upstream HTTP handler."""
from __future__ import annotations

import os
import json
from pathlib import Path
import sys
from http.server import ThreadingHTTPServer

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from contract import read_policy, RUNTIME_ABI, STOCK_SHA256, GATEWAYS, PROTOCOL_VERSION, SERVICE_VERSION, gateway_ready, local_json, read_task

TASK, DIGEST = read_task(os.environ.get("RETRO_TASK_ROOT", "/workspace/task"))
if (not os.environ.get("RETRO_INSTANCE_ID") or not os.environ.get("RETRO_TRIAL_ID")
        or DIGEST != os.environ.get("RETRO_TASK_SHA256")):
    raise RuntimeError("SUPERVISED_START_REQUIRED")

APP = Path("/opt/retro/app")
sys.path[:0] = ["/opt/retro/bridge", str(APP), str(APP / "outputs/pureagent_p_v0_benchmark/runtime")]
import service as upstream

if upstream.task != TASK or read_task(os.environ.get("RETRO_TASK_ROOT", "/workspace/task"))[1] != DIGEST:
    raise RuntimeError("TASK_CHANGED_DURING_START")

upstream.p_server.Handler.environment.trace_dir = str(
    Path(os.environ.get("RETRO_STATE_ROOT", "/state")) / "traces")


def identity():
    return {"task_id": TASK["task_id"], "task_sha256": DIGEST,
            "instance_id": os.environ["RETRO_INSTANCE_ID"], "trial_id": os.environ["RETRO_TRIAL_ID"],
            "protocol_version": PROTOCOL_VERSION, "service_version": SERVICE_VERSION,
            "runtime_abi": RUNTIME_ABI, "policy_sha256": None,
            "stock_sha256": STOCK_SHA256, "initial_materials": TASK["initial_materials"]}


class Handler(upstream.Handler):
    def do_POST(self):
        if self.path != '/grading/stock-check':
            return super().do_POST()
        from native_gold_stock_v16 import handle_stock_request, NativeGoldStockError, MAX_REQUEST_BYTES
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= MAX_REQUEST_BYTES:
                raise ValueError('GRADING_STOCK_REQUEST_SIZE')
            def unique(pairs):
                value = {}
                for key, item in pairs:
                    if key in value:
                        raise ValueError('GRADING_STOCK_DUPLICATE_KEY')
                    value[key] = item
                return value
            payload = json.loads(self.rfile.read(size), object_pairs_hook=unique)
            response = handle_stock_request(payload, self.environment, identity(), self.client_address[0])
            self._json(200, response)
        except NativeGoldStockError as error:
            self._json(error.http_status, {'error': str(error)})
        except (ValueError, TypeError, KeyError):
            self._json(400, {'error': 'GRADING_STOCK_REQUEST_INVALID'})

    def do_GET(self):
        if self.path != "/health":
            return super().do_GET()
        read_policy(os.environ.get("RETRO_TASK_ROOT", "/workspace/task"), TASK)
        compute = {}
        for port in GATEWAYS:
            try:
                compute[port] = local_json("http://127.0.0.1:" + port + "/health")
            except (OSError, ValueError):
                compute[port] = {"status": "unavailable"}
        ready = all(gateway_ready(compute[port], providers, device)
                    for port, (providers, device) in GATEWAYS.items())
        self._json(200 if ready else 503, {"service": "retro-harbor-p", "mode": "service",
                   "limits": TASK["limits"], "compute": compute, "ready": ready, **identity()})

    def _json(self, status, payload):
        if self.path.startswith("/export/") and status == 200 and isinstance(payload, dict):
            payload = dict(payload, service_identity=identity())
            sid = payload.get('run_meta.json', {}).get('session')
            payload['harbor_binding'] = {'session_id': sid, 'variant': 'open',
                'task_id': TASK['task_id'], 'target_sha256': __import__('hashlib').sha256(
                    TASK['target']['target_smiles'].encode()).hexdigest()}
        return super()._json(status, payload)


from public_stock_view_v17 import install_handler as _install_visibility_handler
_install_visibility_handler(Handler)

if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 20765), Handler).serve_forever()
