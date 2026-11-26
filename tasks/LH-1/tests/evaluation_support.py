"""Submission validation and conservative native-runtime error reporting."""
from __future__ import annotations

import importlib
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess


class SubmissionError(ValueError):
    """The submitted JSON violates the public boundary contract."""


class CandidateFailure(RuntimeError):
    """A documented physical failure or exhausted evaluation budget."""


class EvaluationError(RuntimeError):
    """The runtime failed, or a native failure cannot be attributed safely."""


def validate_boundary(boundary, nfp, *, allow_duplicates=False, require_origin=True):
    if not isinstance(boundary, dict):
        raise SubmissionError("Submit a JSON object")
    if type(boundary.get("nfp")) is not int or boundary["nfp"] != nfp:
        raise SubmissionError(f"This task requires integer nfp={nfp}")
    modes = boundary.get("modes")
    if not isinstance(modes, list) or not modes:
        raise SubmissionError("modes must be a nonempty list")
    canonical = {}
    for entry in modes:
        if not isinstance(entry, dict):
            raise SubmissionError("Each mode must be a JSON object")
        m, n = entry.get("m"), entry.get("n")
        if type(m) is not int or type(n) is not int:
            raise SubmissionError("m and n must be integers, excluding booleans")
        if m < 0 or (m == 0 and n < 0):
            raise SubmissionError("Use m>=0 and n>=0 when m=0")
        for key in ("rbc", "zbs"):
            value = entry.get(key)
            try:
                valid = type(value) in (int, float) and math.isfinite(value)
            except OverflowError:
                valid = False
            if not valid:
                raise SubmissionError(f"{key} must be a finite real number")
        if (m, n) in canonical and not allow_duplicates:
            raise SubmissionError(f"Duplicate Fourier mode ({m},{n})")
        canonical[m, n] = dict(entry)
    if (0, 0) in canonical and canonical[0, 0]["zbs"] != 0:
        raise SubmissionError("zbs(0,0) must be zero")
    if require_origin and ((0, 0) not in canonical or canonical[0, 0]["rbc"] <= 0):
        raise SubmissionError("rbc(0,0) must be present and positive")
    return dict(boundary, modes=list(canonical.values()))


def check_runtime(programs, modules, *, required_files=()):
    """Check executables, loadable libraries and Python APIs before any solve."""
    for program in programs:
        executable = shutil.which(program)
        if executable is None:
            raise EvaluationError(f"Required executable not found: {program}")
        # ldd does not apply to scripts. Check only native ELF executables.
        try:
            with Path(executable).open("rb") as stream:
                elf = stream.read(4) == b"\x7fELF"
            if elf:
                if shutil.which("ldd") is None:
                    raise EvaluationError("ldd is required to check native shared libraries")
                check = subprocess.run(["ldd", executable], capture_output=True,
                                       text=True, timeout=15)
                text = check.stdout + check.stderr
                if "not found" in text:
                    raise EvaluationError(f"Missing shared libraries for {program}: {text.strip()}")
                if check.returncode and not any(x in text for x in
                        ("not a dynamic executable", "statically linked")):
                    raise EvaluationError(f"Cannot check shared libraries for {program}: {text.strip()}")
        except (OSError, subprocess.SubprocessError) as error:
            raise EvaluationError(f"Cannot inspect {program}: {error}") from error
    for module, attributes in modules:
        try:
            imported = importlib.import_module(module)
            for attribute in attributes:
                getattr(imported, attribute)
        except Exception as error:
            raise EvaluationError(f"Required Python API unavailable: {module}: {error}") from error
    for path in required_files:
        try:
            with Path(path).open("rb") as stream:
                stream.read(1)
        except OSError as error:
            raise EvaluationError(f"Required evaluation input unavailable: {path}: {error}") from error


def _stop(process):
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def run_native(command, directory, logfile, timeout, *, env=None, worker_output=None,
               timeout_is_candidate=True):
    """Unknown nonzero exits never silently become a candidate's zero score."""
    directory, logfile = Path(directory), Path(logfile)
    if timeout <= 0:
        raise CandidateFailure("The physical evaluation time budget has expired")
    with logfile.open("w") as log:
        try:
            process = subprocess.Popen(command, cwd=directory, env=env, stdout=log,
                                       stderr=subprocess.STDOUT, start_new_session=True)
        except OSError as error:
            raise EvaluationError(f"Cannot start {command[0]}: {error}") from error
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired as error:
            _stop(process)
            failure = CandidateFailure if timeout_is_candidate else EvaluationError
            raise failure(f"{command[0]} exceeded {timeout:g} seconds; see {logfile}") from error
        except BaseException:
            _stop(process)
            raise
    if process.returncode:
        # Inspect structured worker failures before considering physics logs.
        if worker_output is not None:
            prefix = Path(worker_output)
            records = []
            try:
                for path in prefix.parent.glob(prefix.name + ".worker-*.json"):
                    records.append(json.loads(path.read_text()))
                candidate_only = bool(records) and all(
                    row.get("status") == "physics_failed" for row in records)
            except (OSError, ValueError, TypeError, AttributeError) as error:
                raise EvaluationError(f"Unreadable worker failure report; see {logfile}") from error
            if candidate_only and process.returncode == 65:
                raise CandidateFailure(f"Orbit worker reported a physical failure; see {logfile}")
        text = logfile.read_text(errors="replace")
        # This is the VMEC diagnostic already used by the original evaluator.
        if worker_output is None and "Try increasing NITER or PRE_NITER" in text:
            raise CandidateFailure(f"VMEC exhausted its iteration budget; see {logfile}")
        raise EvaluationError(f"Unclassified native exit {process.returncode} from {command[0]}; see {logfile}")


def report_worker_failure(output, error, *, candidate=False):
    rank = os.environ.get("OMPI_COMM_WORLD_RANK", os.environ.get("PMI_RANK", str(os.getpid())))
    path = Path(output).with_name(Path(output).name + f".worker-{rank}.json")
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps({"status": "physics_failed" if candidate else "evaluation_error",
                                     "error": f"{type(error).__name__}: {error}"}) + "\n")
    temporary.replace(path)
