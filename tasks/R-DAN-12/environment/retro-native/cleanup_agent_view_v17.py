#!/usr/bin/env python3
"""Remove answer hints and protect service resources before main starts.

This edits only the main container's filesystem. It never contacts P-service,
changes its stock policy, or claims to have rebuilt the underlying image.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile
from datetime import datetime, timezone


SCHEMA = "retro-agent-view-cleanup/1.0.17"
BENCHMARK = "opt/retro/app/outputs/pureagent_p_v0_benchmark/"
PROBLEMS = BENCHMARK + "01_problems"
DEPLOYMENT = BENCHMARK + "deployment/p_stock_deployment_manifest.json"
REGISTRY = BENCHMARK + "runtime/stock/p_reagent_registry.json"
SNAPSHOT_MANIFEST = BENCHMARK + "reagent_snapshot_manifest.json"
COMMON = "opt/retro/assets/stock/common_reagents.json"
LOCK = "opt/retro/resources.lock.json"
RECEIPT = "root/retro-agent-cleanup-v17.json"
SOURCE_TAGS = frozenset({
    "gold48_starting_material_supplement_20261023",
    "gold48_stereo_supplement_20261023",
})
MAX_JSON_BYTES = 128 * 1024 * 1024


class CleanupError(RuntimeError):
    """A stable error code, without scientific input or deleted-file contents."""


def _error(code: str):
    raise CleanupError(code)


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            _error("DUPLICATE_JSON_KEY")
        value[key] = item
    return value


def _json(raw: bytes):
    try:
        return json.loads(raw, object_pairs_hook=_pairs,
                          parse_constant=lambda _: _error("NONFINITE_JSON"))
    except (ValueError, UnicodeError) as exc:
        raise CleanupError("INVALID_JSON") from exc


def _bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode()


def _path(root: Path, relative: str) -> Path:
    part = PurePosixPath(relative)
    if part.is_absolute() or not part.parts or any(p in {".", ".."} for p in part.parts):
        _error("UNSAFE_PATH")
    # Startup runs before any untrusted process, and every existing component is
    # checked. No resolve() of a container child is used to follow a link.
    current = root
    for item in part.parts:
        current = current / item
        try:
            info = current.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode):
            _error("SYMLINK_REJECTED")
    return current


def _read(root: Path, relative: str, required: bool = False) -> bytes | None:
    file = _path(root, relative)
    try:
        descriptor = os.open(file, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        if required:
            _error("REQUIRED_FILE_MISSING")
        return None
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_JSON_BYTES:
            _error("UNSAFE_JSON_FILE")
        return stream.read(MAX_JSON_BYTES + 1)


def _inventory(root: Path, relative: str) -> tuple[list[str], list[str]]:
    """Validate the entire deletion subtree before deleting its first file."""
    path = _path(root, relative)
    try:
        info = path.lstat()
    except FileNotFoundError:
        return [], []
    if stat.S_ISREG(info.st_mode):
        return [relative], []
    if not stat.S_ISDIR(info.st_mode):
        _error("UNSAFE_DELETION_TARGET")
    files, directories = [], []
    for entry in sorted(os.scandir(path), key=lambda item: item.name):
        child_files, child_dirs = _inventory(root, relative + "/" + entry.name)
        files.extend(child_files)
        directories.extend(child_dirs)
    directories.append(relative)
    return files, directories


def _is_deleted_image_path(relative: str) -> bool:
    return (relative.startswith("app/outputs/pureagent_p_v0_benchmark/01_problems/")
            or relative == "app/outputs/pureagent_p_v0_benchmark/deployment/p_stock_deployment_manifest.json")


def _validate_lock(value):
    if (not isinstance(value, dict) or type(value.get("schema_version")) is not int
            or value["schema_version"] != 2 or type(value.get("total_bytes")) is not int
            or not isinstance(value.get("files"), list) or not value["files"]):
        _error("RESOURCE_LOCK_SCHEMA_INVALID")
    seen, total = set(), 0
    for entry in value["files"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("image_path"), str):
            _error("RESOURCE_LOCK_ENTRY_INVALID")
        name = entry["image_path"]
        parts = PurePosixPath(name)
        if (not name or parts.is_absolute() or ".." in parts.parts or "." in name.split("/")
                or name != parts.as_posix() or name in seen
                or type(entry.get("bytes")) is not int or entry["bytes"] < 0
                or not isinstance(entry.get("sha256"), str)
                or re.fullmatch(r"[a-f0-9]{64}", entry["sha256"]) is None):
            _error("RESOURCE_LOCK_ENTRY_INVALID")
        seen.add(name)
        total += entry["bytes"]
    if total != value["total_bytes"]:
        _error("RESOURCE_LOCK_TOTAL_INVALID")


def _has_tag(value) -> bool:
    if isinstance(value, str):
        return any(tag in value for tag in SOURCE_TAGS)
    if isinstance(value, list):
        return any(_has_tag(item) for item in value)
    if isinstance(value, dict):
        return any(_has_tag(key) or _has_tag(item) for key, item in value.items())
    return False


def _scrub_stock(value) -> int:
    if not isinstance(value, dict) or not isinstance(value.get("stock"), list):
        _error("STOCK_SCHEMA_INVALID")
    removed = 0
    for row in value["stock"]:
        if (not isinstance(row, dict)
                or not isinstance(row.get("canonical_smiles") or row.get("smiles"), str)
                or not (row.get("canonical_smiles") or row.get("smiles"))):
            _error("STOCK_ROW_INVALID")
        # These are the only fields changed. Molecule identities, stereochemistry,
        # ordering, membership and availability flags are retained byte-for-value.
        if isinstance(row.get("source"), str) and row["source"] in SOURCE_TAGS:
            del row["source"]
            removed += 1
        if isinstance(row.get("sources"), list):
            kept = [item for item in row["sources"] if not isinstance(item, str) or item not in SOURCE_TAGS]
            removed += len(row["sources"]) - len(kept)
            if kept != row["sources"]:
                row["sources"] = kept
    if _has_tag(value):
        _error("UNSUPPORTED_SOURCE_PROVENANCE")
    return removed


def _atomic_write(root: Path, relative: str, raw: bytes, mode: int):
    file = _path(root, relative)
    descriptor, temporary = tempfile.mkstemp(prefix=".retro-cleanup-", dir=file.parent)
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        # Parent directories are trusted: this runs before the agent starts.
        _path(root, relative)
        os.replace(temporary, file)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def cleanup(root: Path | str = Path("/"), dry_run: bool = False, *, owner_uid: int = 0, service_gid: int = 1001) -> dict:
    supplied = Path(root).absolute()
    if supplied.is_symlink() or not supplied.is_dir():
        _error("INVALID_ROOT")
    root = supplied.resolve(strict=True)
    if root == Path("/") and (os.getuid() != 0 or os.geteuid() != 0):
        _error("ROOT_REQUIRED")
    lock_raw = _read(root, LOCK, required=True)
    lock = _json(lock_raw)
    _validate_lock(lock)
    problem_path = _path(root, PROBLEMS)
    if problem_path.exists() and not problem_path.is_dir():
        _error("PROBLEM_TREE_NOT_DIRECTORY")
    files, directories = _inventory(root, PROBLEMS)
    deployment_files, deployment_dirs = _inventory(root, DEPLOYMENT)
    if deployment_dirs:
        _error("DEPLOYMENT_MANIFEST_NOT_FILE")
    files.extend(deployment_files)

    rewrites, source_count, stock_bytes, overlay_bytes = {}, 0, {}, {}
    # These exact code files are trusted, read-only task overlays in Compose.
    # Reconcile their runtime bytes with the image's older resource manifest;
    # no scientific backend/data resource is changed by this reconciliation.
    for relative in ("opt/retro/main/binding.py", "opt/retro/main/service_contract.py"):
        raw = _read(root, relative)
        if raw is not None:
            overlay_bytes[relative] = raw
    for relative in (COMMON,):
        raw = _read(root, relative)
        if raw is not None:
            value = _json(raw)
            count = _scrub_stock(value)
            source_count += count
            if count:
                rewrites[relative] = _bytes(value)
            stock_bytes[relative] = rewrites.get(relative, raw)

    # If main has a common-reagent view, keep its source-file hash consistent.
    # The registry itself is protected by permissions and is never rewritten.
    snapshot_raw = _read(root, SNAPSHOT_MANIFEST)
    if snapshot_raw is not None:
        snapshot = _json(snapshot_raw)
        if (not isinstance(snapshot, dict)
                or snapshot.get("schema_version") != "pureagent-p-v0-reagent-snapshot-manifest-1"
                or not isinstance(snapshot.get("source_sha256"), dict)
                or snapshot.get("snapshot_path") != "outputs/pureagent_p_v0_benchmark/runtime/stock/p_reagent_registry.json"):
            _error("STOCK_MANIFEST_SCHEMA_INVALID")
        before_snapshot = _bytes(snapshot)
        if REGISTRY in stock_bytes:
            snapshot["snapshot_sha256"] = hashlib.sha256(stock_bytes[REGISTRY]).hexdigest()
        if COMMON in stock_bytes:
            snapshot["source_sha256"]["common_reagents"] = hashlib.sha256(stock_bytes[COMMON]).hexdigest()
        if _bytes(snapshot) != before_snapshot:
            rewrites[SNAPSHOT_MANIFEST] = _bytes(snapshot)

    removed_entries = [row for row in lock["files"] if _is_deleted_image_path(row["image_path"])]
    lock["files"] = [row for row in lock["files"] if not _is_deleted_image_path(row["image_path"])]
    updated_entry = False
    for row in lock["files"]:
        relative = "opt/retro/" + row["image_path"]
        # Reject even untouched lock entries that point through a symlink.
        _path(root, relative)
        raw = rewrites.get(relative, stock_bytes.get(relative, overlay_bytes.get(relative)))
        if raw is not None:
            checksum = hashlib.sha256(raw).hexdigest()
            if row["bytes"] != len(raw) or row["sha256"] != checksum:
                updated_entry = True
                row.update(bytes=len(raw), sha256=checksum)
                if "upstream_unchanged" in row:
                    row["upstream_unchanged"] = False
    lock["total_bytes"] = sum(row["bytes"] for row in lock["files"])
    _validate_lock(lock)
    if removed_entries or rewrites or updated_entry:
        rewrites[LOCK] = _bytes(lock)

    protected = []
    if type(owner_uid) is not int or owner_uid < 0 or type(service_gid) is not int or service_gid < 0:
        _error("SERVICE_RESOURCE_OWNER_INVALID")
    template = BENCHMARK + "runtime/precedent/uspto50k_train_20260820/retro_templates_by_reaction.tsv"
    for relative in (REGISTRY, template):
        raw = _read(root, relative, required=True)
        file = _path(root, relative)
        info = file.stat()
        protected.append({"path": relative, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "uid": owner_uid, "gid": service_gid, "mode": "0440",
            "change_required": info.st_uid != owner_uid or info.st_gid != service_gid or stat.S_IMODE(info.st_mode) != 0o440})

    # Validate private receipt storage before making any edits.
    private = _path(root, "root")
    if private.exists() and (not private.is_dir() or private.stat().st_mode & 0o077):
        _error("RECEIPT_DIRECTORY_NOT_PRIVATE")
    if root == Path("/") and private.exists() and private.stat().st_uid != 0:
        _error("RECEIPT_DIRECTORY_NOT_ROOT_OWNED")
    previous_raw = _read(root, RECEIPT)
    previous = _json(previous_raw) if previous_raw is not None else {}
    if not isinstance(previous, dict) or (previous_raw is not None and previous.get("schema") != SCHEMA):
        _error("RECEIPT_SCHEMA_INVALID")
    for counter in ("removed_file_count_total", "removed_lock_entry_count_total", "removed_source_label_count_total"):
        if type(previous.get(counter, 0)) is not int or previous.get(counter, 0) < 0:
            _error("RECEIPT_SCHEMA_INVALID")
    changed = bool(files or directories or rewrites or any(item["change_required"] for item in protected))
    receipt = {
        "schema": SCHEMA,
        "status": "DRY_RUN" if dry_run else "CLEANED" if changed else "ALREADY_CLEAN",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "removed_file_count": len(files),
        "removed_lock_entry_count": len(removed_entries),
        "removed_source_label_count": source_count,
        "rewritten_file_count": len(rewrites),
        "removed_file_count_total": previous.get("removed_file_count_total", 0) + len(files),
        "removed_lock_entry_count_total": previous.get("removed_lock_entry_count_total", 0) + len(removed_entries),
        "removed_source_label_count_total": previous.get("removed_source_label_count_total", 0) + source_count,
        "resource_total_bytes": lock["total_bytes"],
        "resource_lock_sha256": hashlib.sha256(rewrites.get(LOCK, lock_raw)).hexdigest(),
        "changed_file_sha256": {name: hashlib.sha256(raw).hexdigest() for name, raw in rewrites.items()},
        "protected_resources": protected,
        "protected_resource_permission_changes": sum(item["change_required"] for item in protected),
        "registry_and_precedent_bytes_unchanged": True,
        "trusted_overlay_sha256": {name: hashlib.sha256(raw).hexdigest() for name, raw in overlay_bytes.items()},
        "pservice_changed": False,
        "underlying_image_rebuilt": False,
    }
    if dry_run:
        return receipt
    for relative, raw in rewrites.items():
        current = _path(root, relative)
        mode = stat.S_IMODE(current.stat().st_mode) & ~0o222
        _atomic_write(root, relative, raw, mode)
    for relative in files:
        _path(root, relative).unlink()
    for relative in directories:
        _path(root, relative).rmdir()
    for item in protected:
        file = _path(root, item["path"])
        descriptor = os.open(file, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            os.fchown(descriptor, owner_uid, service_gid)
            os.fchmod(descriptor, 0o440)
        finally:
            os.close(descriptor)
        if hashlib.sha256(_read(root, item["path"], required=True)).hexdigest() != item["sha256"]:
            _error("SERVICE_RESOURCE_BYTES_CHANGED")
    private.mkdir(mode=0o700, exist_ok=True)
    private.chmod(0o700)
    _atomic_write(root, RECEIPT, _bytes(receipt), 0o600)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("/"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        result = cleanup(args.root, dry_run=args.dry_run)
    except (CleanupError, OSError) as exc:
        code = str(exc) if isinstance(exc, CleanupError) else "FILESYSTEM_ERROR"
        parser.exit(2, "retro-agent-cleanup-v17: " + code + "\n")
    public_keys = ("schema", "status", "removed_file_count", "removed_lock_entry_count",
                   "removed_source_label_count", "rewritten_file_count")
    print(json.dumps({name: result[name] for name in public_keys}, sort_keys=True))


if __name__ == "__main__":
    main()
