#!/usr/bin/env python3
"""Score every routed delivery trace from its compact three-file context."""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import statistics
import threading
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

DELIVERY = Path("/PLACEHOLDER_SET_VIA_CLI")
OUT = Path("/PLACEHOLDER_SET_VIA_CLI")
MODEL = os.environ.get("RETRO_JUDGE_MODEL", "")
API_URL = os.environ.get("RETRO_JUDGE_URL", "")
MAX_WORKERS = 3
REPLICATES = 1
MAX_TOKENS = 32768
ADDITIONAL_INSTRUCTION = ""
SECTION_MAX = {
    "Q-STEP": 28,
    "Q-PRECEDENT": 10,
    "Q-SEL": 14,
    "Q-STEREO": 14,
    "Q-RPF": 14,
    "Q-CLOSE": 10,
    "Q-MULTI": 10,
}


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def save_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".{os.getpid()}.{threading.get_ident()}.tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    tmp.replace(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_")


def routed_rows() -> list[dict[str, Any]]:
    manifest = load_json(DELIVERY / "delivery_manifest.json")
    routed: list[dict[str, Any]] = []
    for row in manifest:
        task = DELIVERY / row["task_path"]
        context_path = task / "results/scoring_resources/v2/11_scores/llm_scoring_context.json"
        if not context_path.is_file():
            continue
        context = load_json(context_path)
        selected_route = context.get("selected_route_id")
        if context.get("status") == "READY_FOR_LLM" and selected_route:
            routed.append({**row, "evaluation_route_id": selected_route})
    return sorted(routed, key=lambda x: (x["family"], x["target"], x["repeat"], x["model_directory"]))


def expected_criterion_ids(packet: dict[str, Any]) -> set[str]:
    context = packet["files"]["results/scoring_resources/v2/11_scores/llm_scoring_context.json"]
    expected = {f"STEP::{step['step_id']}::{field}" for step in context["selected_route"]["steps"] for field in ("BOND_CHEMISTRY_6", "FORWARD_FEASIBILITY_3")}
    expected.update(f"CHECKPOINT::{item['section']}::{item['checkpoint_id']}" for item in context["checkpoints"])
    expected.update(("PROGRAM::Q-PRECEDENT", "PROGRAM::Q-CLOSE", "PROGRAM::Q-MULTI"))
    return expected


def reported_criterion_ids(text: str) -> list[str]:
    """Read only Markdown table criterion cells, preserving one value per row."""
    return [
        value.strip()
        for value in re.findall(
            r"^\|\s*((?:STEP|CHECKPOINT|PROGRAM)::[^|]+?)\s*\|",
            text,
            flags=re.M,
        )
    ]


def task_slug(row: dict[str, Any]) -> str:
    return "__".join((safe_name(row["family"]), safe_name(row["target"]), safe_name(row["model_directory"]), f"run{row['repeat']}"))


def report_filename(model: str) -> str:
    """Keep provider reports distinct while retaining the shared scorer."""
    return "score_answer_grok.md" if model.lower().startswith("grok") else "score_answer_gemini.md"


def make_packet(row: dict[str, Any]) -> dict[str, Any]:
    task = DELIVERY / row["task_path"]
    files: dict[str, Any] = {}
    file_hashes: dict[str, str] = {}
    required = (
        "rubrics.md",
        "results/answer.json",
        "results/scoring_resources/v2/11_scores/llm_scoring_context.json",
    )
    for rel in required:
        path = task / rel
        if not path.is_file():
            raise FileNotFoundError(path)
        files[rel] = path.read_text() if rel == "rubrics.md" else load_json(path)
        file_hashes[rel] = sha_bytes(path.read_bytes())
    return {
        "task_path": row["task_path"],
        "source_model": row["model_directory"],
        "source_repeat": row["repeat"],
        "family": row["family"],
        "target": row["target"],
        "evaluation_route_id": row["evaluation_route_id"],
        "evidence_scope": "Exactly three scoring inputs: self-contained rubric, submitted answer, and compact program-computed scoring context.",
        "file_hashes": file_hashes,
        "files": files,
    }


def build_prompt(packet: dict[str, Any]) -> str:
    base = (DELIVERY / "answer_scoring_prompt.md").read_text()
    file_access = """# Supplied file contents

You do not have filesystem access in this API call. The evidence packet below contains the exact contents of the files at the paths named in the scoring prompt. Treat the packet as those files and return the report in the scoring prompt's required format.
"""
    return base + "\n\n" + file_access + "\n# Evidence packet\n\n```json\n" + json.dumps(packet, ensure_ascii=False, separators=(",", ":")) + "\n```\n" + ADDITIONAL_INSTRUCTION


def extract_final_json(text: str) -> tuple[dict[str, Any] | None, list[str]]:
    candidates: list[dict[str, Any]] = []
    for raw in re.findall(r"```json\s*(.*?)\s*```", text, flags=re.I | re.S):
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and "section_scores" in value:
            candidates.append(value)
    if not candidates:
        stripped = text.strip()
        try:
            value = json.loads(stripped)
            if isinstance(value, dict) and "section_scores" in value:
                candidates.append(value)
        except json.JSONDecodeError:
            pass
    if not candidates:
        return None, ["final_json_missing"]
    value = candidates[-1]
    errors: list[str] = []
    expected_root_keys = {"score", "total_possible", "section_scores", "deductions", "caps_applied", "negative_checks", "evidence_files"}
    if set(value) != expected_root_keys:
        errors.append("final_json_root_keys_mismatch")
    sections = value.get("section_scores")
    try:
        if not isinstance(sections, list) or len(sections) != len(SECTION_MAX):
            raise ValueError("seven_sections_required")
        by_name = {item["section"]: item for item in sections}
        if set(by_name) != set(SECTION_MAX):
            raise ValueError("section_names_mismatch")
        numeric_scores = []
        for name, maximum in SECTION_MAX.items():
            item = by_name[name]
            if set(item) != {"section", "score", "max_score"}:
                errors.append(f"section_keys_mismatch:{name}")
            if item.get("max_score") != maximum:
                errors.append(f"max_score_mismatch:{name}")
            score = item.get("score")
            if not isinstance(score, (int, float)) or isinstance(score, bool) or not 0 <= score <= maximum:
                errors.append(f"invalid_score:{name}")
            else:
                numeric_scores.append(float(score))
        root = value.get("score")
        if not isinstance(root, (int, float)) or isinstance(root, bool):
            errors.append("numeric_root_score_required")
        elif len(numeric_scores) == len(SECTION_MAX) and abs(float(root) - round(sum(numeric_scores), 2)) > 0.011:
            errors.append("root_section_sum_mismatch")
        if value.get("total_possible") != 100:
            errors.append("total_possible_mismatch")
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(str(exc))
    return value, errors


def call_one(row: dict[str, Any], replicate: int, barrier: threading.Barrier | None = None) -> dict[str, Any]:
    slug = task_slug(row)
    task_out = OUT / "targets" / safe_name(row["family"]) / safe_name(row["target"]) / slug
    rep_out = task_out / f"replicate_{replicate}"
    response_path = rep_out / "response.json"
    if response_path.is_file():
        return load_json(response_path)
    packet_path = task_out / "context_packet.json"
    if packet_path.is_file():
        packet = load_json(packet_path)
    else:
        packet = make_packet(row)
        save_json(packet_path, packet)
    prompt = build_prompt(packet)
    (task_out / "request_prompt.txt").write_text(prompt)
    if barrier is not None:
        barrier.wait(timeout=30)
    started = time.time()
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": MAX_TOKENS,
    }
    request_meta = {
        "model": MODEL,
        "replicate": replicate,
        "task_path": row["task_path"],
        "prompt_sha256": sha_bytes(prompt.encode()),
        "prompt_characters": len(prompt),
        "max_tokens": MAX_TOKENS,
        "temperature": 0,
        "started_at_unix": started,
        "automatic_retries": 0,
    }
    save_json(rep_out / "request_meta.json", request_meta)
    result: dict[str, Any]
    try:
        request = urllib.request.Request(
            API_URL,
            data=json.dumps(payload, ensure_ascii=False).encode(),
            headers={"Authorization": "Bearer " + os.environ["DP_GPUGEEK_API_KEY"], "Content-Type": "application/json"},
            method="POST",
        )
        try:
            response = urllib.request.urlopen(request, timeout=1200)
            status = response.status
            raw_body = response.read()
        except urllib.error.HTTPError as http_error:
            status = http_error.code
            raw_body = http_error.read()
        finished = time.time()
        try:
            body = json.loads(raw_body.decode(errors="replace"))
        except (ValueError, UnicodeDecodeError):
            body = {"non_json_body_prefix": raw_body.decode(errors="replace")[:2000]}
        choice = (body.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        content = message.get("content") or ""
        parsed, validation_errors = extract_final_json(content)
        required_ids = expected_criterion_ids(packet)
        observed_rows = reported_criterion_ids(content)
        observed_ids = set(observed_rows)
        missing_ids = sorted(required_ids - observed_ids)
        duplicate_ids = sorted(identifier for identifier in required_ids if observed_rows.count(identifier) != 1)
        if missing_ids:
            validation_errors.append("criterion_rows_missing:" + ",".join(missing_ids))
        if duplicate_ids:
            validation_errors.append("criterion_rows_not_exactly_once:" + ",".join(duplicate_ids))
        result = {
            **request_meta,
            "finished_at_unix": finished,
            "elapsed_seconds": round(finished - started, 3),
            "http_status": status,
            "request_id": body.get("id"),
            "provider_model": body.get("model"),
            "finish_reason": choice.get("finish_reason"),
            "usage": body.get("usage"),
            "provider_error": body.get("error"),
            "response_text": content,
            "response_reasoning": message.get("reasoning_content"),
            "parsed_final_json": parsed,
            "score": parsed.get("score") if parsed else None,
            "validation_errors": validation_errors,
            "valid": status == 200 and choice.get("finish_reason") in ("stop", "end_turn") and not validation_errors,
        }
        (rep_out / report_filename(MODEL)).write_text(content)
    except Exception as exc:
        finished = time.time()
        result = {
            **request_meta,
            "finished_at_unix": finished,
            "elapsed_seconds": round(finished - started, 3),
            "error_type": type(exc).__name__,
            "error": str(exc)[:2000],
            "score": None,
            "validation_errors": ["transport_exception"],
            "valid": False,
        }
    save_json(response_path, result)
    return result


def concurrency_probe(rows: list[dict[str, Any]]) -> dict[str, Any]:
    row = rows[0]
    slug = task_slug(row)
    task_out = OUT / "targets" / safe_name(row["family"]) / safe_name(row["target"]) / slug
    packet = make_packet(row)
    save_json(task_out / "context_packet.json", packet)
    (task_out / "request_prompt.txt").write_text(build_prompt(packet))
    barrier = threading.Barrier(3)
    before = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(call_one, row, replicate, barrier) for replicate in (1, 2, 3)]
        results = [future.result() for future in futures]
    after = time.time()
    latest_start = max(item["started_at_unix"] for item in results)
    earliest_finish = min(item["finished_at_unix"] for item in results)
    sum_elapsed = sum(item["elapsed_seconds"] for item in results)
    wall = after - before
    report = {
        "task_path": row["task_path"],
        "replicates": 3,
        "valid_responses": sum(bool(item.get("valid")) for item in results),
        "all_http_200": all(item.get("http_status") == 200 for item in results),
        "simultaneously_in_flight": latest_start < earliest_finish,
        "start_spread_seconds": round(latest_start - min(item["started_at_unix"] for item in results), 3),
        "wall_seconds": round(wall, 3),
        "sum_individual_elapsed_seconds": round(sum_elapsed, 3),
        "parallelism_ratio": round(sum_elapsed / wall, 3) if wall else None,
        "provider_backend_serialization_not_directly_observable": True,
        "results": [{k: item.get(k) for k in ("replicate", "http_status", "request_id", "finish_reason", "elapsed_seconds", "score", "valid", "validation_errors")} for item in results],
    }
    save_json(OUT / "concurrency_probe.json", report)
    return report


def summarize(rows: list[dict[str, Any]], results: list[dict[str, Any]]) -> dict[str, Any]:
    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in results:
        by_task[item["task_path"]].append(item)
    task_summary = []
    for row in rows:
        items = sorted(by_task[row["task_path"]], key=lambda x: x["replicate"])
        scores = [float(x["score"]) for x in items if x.get("valid") and isinstance(x.get("score"), (int, float))]
        task_summary.append({
            "family": row["family"], "target": row["target"], "source_model": row["model_directory"],
            "source_repeat": row["repeat"], "task_path": row["task_path"], "evaluation_route_id": row["evaluation_route_id"],
            "scores": scores, "valid_n": len(scores), "mean": statistics.mean(scores) if scores else None,
            "population_sd": statistics.pstdev(scores) if len(scores) > 1 else (0.0 if scores else None),
            "range": max(scores) - min(scores) if scores else None,
            "replicates": [{k: x.get(k) for k in ("replicate", "score", "valid", "http_status", "finish_reason", "elapsed_seconds", "validation_errors")} for x in items],
        })
    summary = {
        "model": MODEL,
        "selection_rule": "Every task whose compact scoring context has status READY_FOR_LLM; no-route tasks are program-scored zero and excluded from provider calls.",
        "trace_count": len(rows),
        "expected_calls": len(rows) * REPLICATES,
        "completed_calls": len(results),
        "valid_calls": sum(bool(x.get("valid")) for x in results),
        "tasks": task_summary,
    }
    save_json(OUT / "score_summary.json", summary)
    return summary


def main() -> None:
    global DELIVERY, OUT, MODEL, API_URL, MAX_WORKERS, REPLICATES, MAX_TOKENS, ADDITIONAL_INSTRUCTION
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe-only", action="store_true")
    parser.add_argument("--run-all", action="store_true")
    parser.add_argument("--delivery-root", type=Path, default=DELIVERY)
    parser.add_argument("--assessment-root", type=Path, default=OUT)
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--api-url", default=API_URL)
    parser.add_argument("--max-workers", type=int, default=MAX_WORKERS)
    parser.add_argument("--replicates", type=int, default=REPLICATES)
    parser.add_argument("--max-tokens", type=int, default=MAX_TOKENS)
    parser.add_argument("--model-directory", help="Score only this exact source-model directory.")
    parser.add_argument("--additional-instruction", default="", help="Append a narrowly scoped formatting correction to the evaluator prompt.")
    args = parser.parse_args()
    if args.max_workers < 1 or args.replicates < 1 or args.max_tokens < 1024:
        parser.error("max-workers and replicates must be positive; max-tokens must be at least 1024")
    DELIVERY, OUT = args.delivery_root.resolve(), args.assessment_root.resolve()
    MODEL, API_URL = args.model, args.api_url
    MAX_WORKERS, REPLICATES, MAX_TOKENS = args.max_workers, args.replicates, args.max_tokens
    ADDITIONAL_INSTRUCTION = args.additional_instruction
    OUT.mkdir(parents=True, exist_ok=True)
    rows = routed_rows()
    if args.model_directory:
        rows = [row for row in rows if row["model_directory"] == args.model_directory]
        if not rows:
            parser.error("--model-directory did not match a routed task")
    save_json(OUT / "selection_manifest.json", {
        "selected_targets": sorted({(row["family"], row["target"]) for row in rows}),
        "trace_count": len(rows),
        "call_count": len(rows) * REPLICATES,
        "rows": rows,
        "source_model_counts": dict(Counter(row["model_directory"] for row in rows)),
        "scoring_prompt_sha256": sha_bytes((DELIVERY / "answer_scoring_prompt.md").read_bytes()),
    })
    if args.probe_only:
        print(json.dumps(concurrency_probe(rows), ensure_ascii=False, indent=2), flush=True)
        return
    if not args.run_all:
        parser.error("choose --probe-only or --run-all")
    jobs = [(row, replicate) for row in rows for replicate in range(1, REPLICATES + 1)]
    results: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = [pool.submit(call_one, row, replicate) for row, replicate in jobs]
        for index, future in enumerate(concurrent.futures.as_completed(futures), 1):
            try:
                item = future.result()
            except Exception as exc:
                item = {"valid": False, "score": None, "validation_errors": ["worker_exception"], "error_type": type(exc).__name__, "error": str(exc)[:2000]}
            results.append(item)
            save_json(OUT / "progress.json", {"completed": index, "total": len(jobs), "valid": sum(bool(x.get("valid")) for x in results), "updated_at_unix": time.time()})
    print(json.dumps(summarize(rows, results), ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
