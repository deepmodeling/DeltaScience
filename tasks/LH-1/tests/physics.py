"""Native precise-QA/QH physics pipeline; no scoring is performed here.

VMEC2000, booz_xform, NEO, SIMPLE and SIMSOPT do the physical calculations.
Each case declares its field periods, QS helicity, radial samples, weights
and magnetic-well intervals.
``read_native_outputs`` can read completed runs without tracing particles again.
The VMEC template ``input.vmec`` is beside this module.

``evaluate`` uses an empty, caller-owned working directory.  The optional
settings ``vmec_program``, ``neo_program``, ``simple_program``, ``mpi_program``,
``vmec_ranks``, ``simple_threads`` and ``timeout_seconds`` select executables
and resources; they do not change the physics settings.
"""
from __future__ import annotations

import math
import os
from pathlib import Path
import re
import subprocess
import time

import numpy as np

from evaluation_support import (CandidateFailure, EvaluationError, check_runtime,
                                run_native, validate_boundary, report_worker_failure)


MINOR_RADIUS = 1.7
AXIS_FIELD = 5.7
N_ALPHA = 4096
ALPHA_SEEDS = (2026091301, 2026091302)
ALPHA_TIME = 0.2
S_LAUNCH = 0.25
SAMPLE_GRID = 512
NEO_TARGETS = (0.2, 0.4, 0.6, 0.8)


def _scaled_modes(boundary: dict) -> tuple[list[dict], float]:
    """Use SIMSOPT's mean cross-section area to set the minor radius."""
    from simsopt.geo import SurfaceRZFourier

    modes = boundary["modes"]
    nfp = boundary["nfp"]
    max_m = max(mode["m"] for mode in modes)
    max_n = max(abs(mode["n"]) for mode in modes)
    ntheta, nphi = max(512, 8 * (max_m + 1)), max(256, 8 * (max_n + 1))
    surface = SurfaceRZFourier(
        nfp=nfp, stellsym=True,
        mpol=max_m, ntor=max_n,
        quadpoints_phi=np.arange(nphi) / (nphi * nfp),
        quadpoints_theta=np.arange(ntheta) / ntheta,
    )
    surface.rc[:] = 0
    surface.zs[:] = 0
    for mode in modes:
        surface.set_rc(mode["m"], mode["n"], mode["rbc"])
        surface.set_zs(mode["m"], mode["n"], mode["zbs"])
    radius = float(surface.minor_radius())
    if not math.isfinite(radius) or radius <= 0:
        raise CandidateFailure("The boundary has no finite positive minor radius")
    scale = float(MINOR_RADIUS / radius)
    return [dict(mode, rbc=mode["rbc"] * scale, zbs=mode["zbs"] * scale)
            for mode in modes], scale


def _vmec_input(boundary: dict) -> tuple[str, float]:
    modes, scale = _scaled_modes(boundary)
    mpol = max(15, 2 * max(mode["m"] for mode in modes) + 5)
    ntor = max(14, 2 * max(abs(mode["n"]) for mode in modes) + 4)
    template = (Path(__file__).parent / "input.vmec").read_text()
    fields = {"NFP": boundary["nfp"], "MPOL": mpol, "NTOR": ntor,
              "NTHETA": max(96, 4 * mpol), "NZETA": max(96, 4 * ntor)}
    for key, value in fields.items():
        template = re.sub(rf"\b{key}\s*=\s*\d+", f"{key} = {value}", template, count=1)
    template = re.sub(r"\bPHIEDGE\s*=\s*[^\s,]+",
                      f"PHIEDGE = {AXIS_FIELD * math.pi * MINOR_RADIUS**2!r}",
                      template, count=1)
    lines = [template.rsplit("/", 1)[0].rstrip()]
    for mode in modes:
        lines.append(f'  RBC({mode["n"]},{mode["m"]}) = {mode["rbc"]!r}, '
                     f'ZBS({mode["n"]},{mode["m"]}) = {mode["zbs"]!r}')
    return "\n".join(lines + ["/", ""]), scale


def _neo_indices(ns: int) -> list[int]:
    """Zero-based Boozer half-grid indices nearest the four NEO surfaces."""
    from fractions import Fraction

    indices = []
    for target in NEO_TARGETS:
        x = Fraction(str(target)) * (ns - 1) - Fraction(1, 2)
        lo = math.floor(x)
        indices.append(lo if x - lo <= lo + 1 - x else lo + 1)
    return indices


def _neo_control(indices: list[int], mboz: int, nboz: int) -> str:
    values = [
        "boozmn_eq.nc", "neo_out.eq", str(len(indices)), " ".join(map(str, indices)),
        str(max(300, 4 * mboz)), str(max(300, 4 * nboz)),
        "0", "0", "150", "1", "0.005", "100", "75", "500",
        "2000", "0", "1", "0", "0", "2", "0", "0", "0", "0", "0",
    ]
    tail = ["0", "neo_cur.eq", "200", "2", "0"]
    return "\n".join(["'#'"] * 3 + values + ["'#'"] * 3 + tail) + "\n"


def _inverse_cdf(weights: np.ndarray, u: np.ndarray) -> np.ndarray:
    cdf = np.concatenate([[0.0], np.cumsum(weights)])
    cdf /= cdf[-1]
    k = np.clip(np.searchsorted(cdf, u, side="right") - 1, 0, len(weights) - 1)
    return k + (u - cdf[k]) / (cdf[k + 1] - cdf[k])


def _alpha_starts(wout: Path) -> np.ndarray:
    """SIMPLE launch coordinates sampled by volume on the s=.25 shell."""
    from netCDF4 import Dataset

    with Dataset(wout) as ds:
        v = ds.variables
        ns, nfp = int(v["ns"][:]), int(v["nfp"][:])
        gmnc = np.asarray(v["gmnc"][:])
        xm, xn = np.asarray(v["xm_nyq"][:]), np.asarray(v["xn_nyq"][:])
    s_half = (np.arange(1, ns) - 0.5) / (ns - 1)
    hi = int(np.searchsorted(s_half, S_LAUNCH))
    lo = hi - 1
    t = (S_LAUNCH - s_half[lo]) / (s_half[hi] - s_half[lo])
    g = (1 - t) * gmnc[1 + lo] + t * gmnc[1 + hi]
    theta = 2 * np.pi * (np.arange(SAMPLE_GRID) + 0.5) / SAMPLE_GRID
    zeta = 2 * np.pi / nfp * (np.arange(SAMPLE_GRID) + 0.5) / SAMPLE_GRID
    cm, sm = np.cos(np.outer(theta, xm)), np.sin(np.outer(theta, xm))
    cn, sn = np.cos(np.outer(xn, zeta)), np.sin(np.outer(xn, zeta))
    jac = np.abs(np.einsum("tk,k,kz->tz", cm, g, cn, optimize=True)
                 + np.einsum("tk,k,kz->tz", sm, g, sn, optimize=True)).T
    rows = []
    for seed in ALPHA_SEEDS:
        u = np.random.Generator(np.random.PCG64DXSM(seed)).random((N_ALPHA // len(ALPHA_SEEDS), 3))
        z = _inverse_cdf(jac.sum(axis=1), u[:, 0])
        cell = np.minimum(z.astype(int), SAMPLE_GRID - 1)
        th = np.array([_inverse_cdf(jac[c], np.array([x]))[0] for c, x in zip(cell, u[:, 1])])
        rows.append(np.column_stack([np.full(len(u), S_LAUNCH), th * (theta[1] - theta[0]),
                                     z * (zeta[1] - zeta[0]), np.ones(len(u)), 2 * u[:, 2] - 1]))
    return np.vstack(rows)


def _simple_input(field_scale: float) -> str:
    return f"""&config
netcdffile = 'wout.nc'
isw_field_type = 2
integmode = 1
npoiper2 = 256
relerr = 1d-13
multharm = 5
ns_s = 5
ns_tp = 5
startmode = 2
ntestpart = {N_ALPHA}
sbeg = {S_LAUNCH}d0
trace_time = {ALPHA_TIME}d0
ntimstep = 10001
n_e = 2
n_d = 3.97259969d0
facE_al = 1d0
vmec_B_scale = {field_scale!r}
vmec_RZ_scale = 1d0
contr_pp = -1d10
tcut = -1d0
class_plot = .False.
fast_class = .False.
swcoll = .False.
deterministic = .True.
/
"""


def _run(command: list[str], directory: Path, env: dict, deadline: float) -> None:
    run_native(command, directory, directory / "log.txt",
               deadline - time.monotonic(), env=env)


def _boozer(wout: Path, output: Path) -> tuple[float, list[int], int, int]:
    import booz_xform

    b = booz_xform.Booz_xform()
    b.verbose = 0
    b.read_wout(str(wout))
    ns = b.ns_in + 1
    indices = _neo_indices(ns)
    b.compute_surfs = sorted(set([0, 1] + indices))
    b.mboz, b.nboz = 4 * b.mpol, 4 * b.ntor
    b.run()
    b.write_boozmn(str(output))
    i00 = int(np.flatnonzero((np.asarray(b.xm_b) == 0) & (np.asarray(b.xn_b) == 0))[0])
    b00 = np.asarray(b.bmnc_b)[i00]
    axis_field = float(1.5 * b00[0] - 0.5 * b00[1])
    return axis_field, [index + 2 for index in indices], b.mboz, b.nboz


def read_native_outputs(workdir: Path, settings: dict, *, elapsed_seconds: float | None = None) -> dict:
    """Map a completed run's native files to metrics without rerunning solvers.

    Read the four requested NEO surfaces and the SIMPLE particle outcomes.
    ``elapsed_seconds`` records the total run duration when available.
    Unresolved trajectories are reported separately from observed losses.
    """
    from netCDF4 import Dataset
    from simsopt.mhd import QuasisymmetryRatioResidual, Vmec

    workdir = Path(workdir)
    wout = workdir / "vmec_attempt1" / "wout_eq.nc"
    with Dataset(wout) as ds:
        variables = ds.variables
        ier = int(variables["ier_flag"][:])
        residuals = [float(variables[key][:]) for key in ("fsqr", "fsqz", "fsql")]
    if ier != 0:
        raise CandidateFailure(f"VMEC reported ier_flag={ier}; see {wout}")
    vmec = Vmec(str(wout), verbose=False)
    s = np.asarray(settings["qs"]["surfaces"])
    weights = np.asarray(settings["qs"]["weights"])
    diagnostic = QuasisymmetryRatioResidual(
        vmec, s, helicity_m=1, helicity_n=settings["qs"]["helicity_n"], weights=weights,
        ntheta=max(63, 4 * int(vmec.wout.mpol)), nphi=max(64, 4 * int(vmec.wout.ntor)),
    )
    result = diagnostic.compute()
    table = np.loadtxt(workdir / "neo" / "neo_out.eq", ndmin=2)[:4]
    if len(table) != len(NEO_TARGETS):
        raise EvaluationError(f"NEO reported {len(table)} of {len(NEO_TARGETS)} requested surfaces")
    with np.errstate(invalid="raise"):
        eps = table[:, 1] ** (2.0 / 3.0)
    exits = np.loadtxt(workdir / "simple" / "orbit_exit_code.dat", ndmin=2)
    if len(exits) != N_ALPHA:
        raise EvaluationError(f"SIMPLE reported {len(exits)} of {N_ALPHA} particle trajectories")
    codes = exits[:, 1].astype(int)
    lost = np.isin(codes, (1, 2)) & (exits[:, 2] <= ALPHA_TIME)
    unresolved = ~((codes == 0) | lost)
    ns = int(vmec.wout.ns)
    metrics = {
        "aspect": float(vmec.aspect()),
        "mean_iota": float(vmec.mean_iota()),
        "vacuum_well": float(vmec.vacuum_well()),
        "qs": float(result.total),
        "eps_eff": eps.tolist(),
        "eps_eff_max": float(np.max(eps)),
        "f_alpha": float(np.count_nonzero(lost) / len(exits)),
        "alpha_not_confined_fraction": float((np.count_nonzero(lost) + np.count_nonzero(unresolved)) / len(exits)),
        "alpha_lost": int(np.count_nonzero(lost)),
        "alpha_unresolved": int(np.count_nonzero(unresolved)),
        "alpha_count": int(len(exits)),
    }
    if settings["well_intervals"]:
        # Landreman-Paul's IntervalWell.J, with only the optimizer wrapper removed.
        # Source: 024_QH_nfp4_A8_magwell_refiningBestFrom019/simsopt_driver, lines 21-37.
        from scipy.interpolate import interp1d

        dVds = 4 * np.pi**2 * np.abs(vmec.wout.gmnc.T[1:, 0])
        derivative = interp1d(vmec.s_half_grid, dVds, fill_value="extrapolate")
        for name, (smin, smax) in settings["well_intervals"].items():
            inner, outer = derivative(smin), derivative(smax)
            metrics[name] = float(-(outer - inner) / (smax - smin) / (0.5 * (outer + inner)))
    diagnostics = {
        "iota_axis": float(vmec.iota_axis()),
        "iota_edge": float(vmec.iota_edge()),
        "iota_surfaces": ((np.arange(ns - 1) + 0.5) / (ns - 1)).tolist(),
        "iota_profile": np.asarray(vmec.wout.iotas[1:]).tolist(),
        "qs_surfaces": s.tolist(),
        "qs_weights": weights.tolist(),
        "qs_per_surface": np.asarray(result.profile).tolist(),
        "neo_surfaces": ((table[:, 0] - 1.5) / (ns - 1)).tolist(),
        "neo_floating_point_notices": [
            line for line in (workdir / "neo" / "log.txt").read_text().splitlines() if "IEEE_" in line
        ],
        "vmec_ier_flag": ier,
        "vmec_force_residuals": residuals,
    }
    return {"metrics": metrics, "diagnostics": diagnostics, "elapsed_seconds": elapsed_seconds}


def evaluate(boundary: dict, workdir: Path, settings: dict) -> dict:
    """Run the case's fixed QS physics chain and return native metrics and profiles."""
    boundary = validate_boundary(boundary, settings["nfp"],
                                 allow_duplicates=False, require_origin=True)
    started = time.monotonic()
    deadline = started + float(settings.get("timeout_seconds", 8 * 3600))
    workdir = Path(workdir).resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    check_runtime([settings.get("mpi_program", "mpirun"),
                   settings.get("vmec_program", "xvmec2000"),
                   settings.get("neo_program", "xneo"),
                   settings.get("simple_program", "simple.x")], [
        ("numpy", ()), ("netCDF4", ("Dataset",)),
        ("simsopt.geo", ("SurfaceRZFourier",)),
        ("simsopt.mhd", ("Vmec", "QuasisymmetryRatioResidual")),
        ("booz_xform", ("Booz_xform",)), ("scipy.interpolate", ("interp1d",))],
        required_files=[Path(__file__).with_name("input.vmec")])
    vmec_dir = workdir / "vmec_attempt1"
    vmec_dir.mkdir()
    input_text, scale = _vmec_input(boundary)
    (vmec_dir / "input.eq").write_text(input_text)
    env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
    _run([settings.get("mpi_program", "mpirun"), "--allow-run-as-root", "--use-hwthread-cpus", "--bind-to", "none",
          "-np", str(settings.get("vmec_ranks", 8)), settings.get("vmec_program", "xvmec2000"),
          "input.eq"], vmec_dir, env, deadline)
    if "Try increasing NITER or PRE_NITER" in (vmec_dir / "log.txt").read_text():
        raise CandidateFailure(f"VMEC reports an exhausted iteration limit; see {vmec_dir / 'log.txt'}")
    wout = vmec_dir / "wout_eq.nc"
    from netCDF4 import Dataset
    with Dataset(wout) as ds:
        ier = int(ds.variables["ier_flag"][:])
    if ier != 0:
        raise CandidateFailure(f"VMEC reported ier_flag={ier}; see {vmec_dir / 'log.txt'}")

    boozmn = workdir / "boozmn_eq.nc"
    axis_field, neo_indices, mboz, nboz = _boozer(wout, boozmn)
    neo_dir = workdir / "neo"
    neo_dir.mkdir()
    (neo_dir / "boozmn_eq.nc").symlink_to(boozmn)
    (neo_dir / "neo_in.eq").write_text(_neo_control(neo_indices, mboz, nboz))
    _run([settings.get("neo_program", "xneo"), "eq"], neo_dir, env, deadline)

    simple_dir = workdir / "simple"
    simple_dir.mkdir()
    (simple_dir / "wout.nc").symlink_to(wout)
    (simple_dir / "simple.in").write_text(_simple_input(AXIS_FIELD / axis_field))
    np.savetxt(simple_dir / "start.dat", _alpha_starts(wout), fmt="%.17e")
    simple_env = dict(env, OMP_NUM_THREADS=str(settings.get("simple_threads", 24)),
                      GFORTRAN_UNBUFFERED_PRECONNECTED="y")
    _run([settings.get("simple_program", "simple.x"), "simple.in"], simple_dir, simple_env, deadline)
    result = read_native_outputs(workdir, settings)
    result["diagnostics"].update(boundary_scale=scale, boozer_axis_field=axis_field)
    result["elapsed_seconds"] = time.monotonic() - started
    return result
