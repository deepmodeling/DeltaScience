from __future__ import annotations

import argparse
import json
import resource
import sys
import time
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--resources", type=Path, default=Path("/workspace/resources"))
    parser.add_argument("--output", type=Path, default=Path("/workspace/outputs/design.json"))
    parser.add_argument("--witness", type=Path, default=Path(__file__).with_name("witness.json"))
    args = parser.parse_args()
    started = time.monotonic()
    sys.path.insert(0, str(args.resources))
    from forward import TrapNetwork
    model = TrapNetwork(args.resources / "network.json")
    orientation = np.array(json.loads(args.witness.read_text())["orientation"])
    target = model.process_target(orientation)
    residual = lambda vector: (model.process_operator(vector.reshape(model.zone_count, 3)) - target).ravel()
    refinement = least_squares(residual, np.zeros(3 * model.zone_count), bounds=(-1.0, 1.0),
                               ftol=1e-12, xtol=1e-12, gtol=1e-12)
    if not refinement.success or np.linalg.norm(refinement.fun, ord=np.inf) > 1e-8:
        raise RuntimeError("Continuous refinement did not converge")
    design = model.design(orientation, refinement.x.reshape(model.zone_count, 3))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(design, allow_nan=False) + "\n")
    print(json.dumps({"implementation": "Gold A: direct private witness plus bounded least-squares refinement",
                      "seconds": time.monotonic() - started, "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                      "residual_inf": float(np.max(np.abs(refinement.fun))), "evaluations": refinement.nfev}))


if __name__ == "__main__":
    main()
