from __future__ import annotations

import csv
import gzip
import io
import json
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath


class _BoundedRaw(io.RawIOBase):
    """Bound decompressed bytes before TextIOWrapper can allocate freely."""

    def __init__(self, source: io.BufferedIOBase, limit: int) -> None:
        self._source = source
        self._limit = int(limit)
        self._seen = 0

    def readable(self) -> bool:
        return True

    def readinto(self, buffer: bytearray) -> int:
        remaining = self._limit - self._seen
        if remaining < 0:
            raise ValueError(f"decompressed member exceeds {self._limit} bytes")
        requested = min(len(buffer), remaining + 1)
        data = self._source.read(requested)
        if not data:
            return 0
        self._seen += len(data)
        if self._seen > self._limit:
            raise ValueError(f"decompressed member exceeds {self._limit} bytes")
        buffer[: len(data)] = data
        return len(data)


def _safe_member(name: object) -> str:
    value = str(name or "")
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or "\\" in value:
        raise ValueError(f"unsafe ZIP member name: {value!r}")
    return value


def _read_csv_member(
    archive: zipfile.ZipFile,
    member: str,
    expected_columns: list[str],
    row_limit: int,
    byte_limit: int,
) -> tuple[list[dict], list[str]]:
    info = archive.getinfo(member)
    errors: list[str] = []
    rows: list[dict] = []
    with archive.open(info, "r") as raw:
        payload = gzip.GzipFile(fileobj=raw, mode="rb") if member.endswith(".gz") else raw
        with payload:
            bounded = io.BufferedReader(_BoundedRaw(payload, byte_limit))
            text = io.TextIOWrapper(bounded, encoding="utf-8-sig", newline="")
            reader = csv.DictReader(text)
            absent = sorted(set(expected_columns) - set(reader.fieldnames or []))
            if absent:
                return [], [f"missing columns: {absent}"]
            for index, row in enumerate(reader, 1):
                if index > row_limit:
                    return [], [f"row count exceeds {row_limit}"]
                rows.append(dict(row))
    return rows, errors


def load_evidence_bundle(path: Path, schema: dict) -> dict:
    """Load bounded ZIP members after central-directory preflight.

    An oversized member is never opened.  Only that submitted family is
    quarantined; other members remain independently scoreable.
    """
    spec = schema["evidence_bundle_zip"]
    result = {
        "families": [], "process": [], "rank_audits": [], "issues": [], "quarantined": [],
        "member_stats": [], "scanned_process_rows": 0, "scanned_rank_audit_rows": 0,
    }
    bundle_bytes = int(path.stat().st_size)
    if bundle_bytes > int(spec.get("max_bundle_bytes", 536870912)):
        # The ZIP is an index of independently scoreable families.  Its total
        # size is diagnostic only: members are still preflighted and bounded
        # before opening, so one oversized/unreferenced member must not erase
        # every otherwise valid family.
        result["issues"].append({
            "scope": "evidence_bundle",
            "message": (
                f"bundle bytes {bundle_bytes} exceeds advisory total "
                f"{int(spec.get('max_bundle_bytes', 536870912))}; applying member-local limits"
            ),
        })
    with zipfile.ZipFile(path, "r") as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        member_counts: dict[str, int] = {}
        for name in names:
            member_counts[name] = member_counts.get(name, 0) + 1
        if len(infos) > int(spec["max_members"]):
            result["issues"].append({
                "scope": "evidence_bundle",
                "message": (
                    f"ZIP member count {len(infos)} exceeds advisory total "
                    f"{spec['max_members']}; only manifest-referenced bounded members are read"
                ),
            })
        total_uncompressed = sum(int(info.file_size) for info in infos)
        if total_uncompressed > int(spec.get("max_total_uncompressed_bytes", 1073741824)):
            result["issues"].append({
                "scope": "evidence_bundle",
                "message": (
                    f"declared ZIP uncompressed bytes {total_uncompressed} exceeds advisory total "
                    f"{int(spec.get('max_total_uncompressed_bytes', 1073741824))}; "
                    "applying member-local decompression limits"
                ),
            })
        manifest_name = str(spec.get("manifest_member", "manifest.json"))
        manifest_info = archive.getinfo(manifest_name)
        if manifest_info.file_size > int(spec["max_manifest_bytes"]):
            raise ValueError("manifest exceeds byte limit")
        manifest = json.loads(archive.read(manifest_info).decode("utf-8"))
        # Early O03 runs emitted the documented family entries directly as a
        # JSON list, while the current exporter wraps the same entries in a
        # {"families": [...]} object.  The wrapper carries no scientific or
        # security information, so accept both encodings and keep all family,
        # member and row-level validation below unchanged.
        if isinstance(manifest, dict):
            entries = manifest.get("families", [])
        elif isinstance(manifest, list):
            entries = manifest
        else:
            entries = None
        if not isinstance(entries, list):
            raise ValueError("invalid or oversized family manifest")
        # Resource families are independent scoring components.  A stage can
        # legitimately contain several pathway, TF and communication families;
        # a stage-wide budget therefore creates a false dependency between
        # unrelated analyses.  Preflight each manifest identity separately.
        def component_key(entry: dict) -> tuple[str, str, str]:
            return (
                str(entry.get("stage", "")),
                str(entry.get("analysis_type", "")),
                str(entry.get("scope", "")),
            )

        component_counts = Counter(
            component_key(entry) for entry in entries if isinstance(entry, dict)
        )
        max_families_per_stage = int(spec["max_families"])
        over_family_budget_components = {
            key for key, count in component_counts.items()
            if count > max_families_per_stage
        }
        for key in sorted(over_family_budget_components):
            stage, analysis_type, scope = key
            result["issues"].append({
                "scope": "evidence_bundle_component_budget",
                "stage": stage,
                "analysis_type": analysis_type,
                "component_scope": scope,
                "observed_families": component_counts[key],
                "max_families": max_families_per_stage,
                "message": "only this evidence component was not opened; unrelated components remain scoreable",
            })
        component_family_totals: Counter[tuple[str, str, str]] = Counter()
        component_process_totals: Counter[tuple[str, str, str]] = Counter()
        component_rank_totals: Counter[tuple[str, str, str]] = Counter()
        over_row_budget_components: set[tuple[str, str, str]] = set()
        seen_keys: set[str] = set()
        for entry_index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                result["issues"].append({"scope": "bundle_manifest", "entry": entry_index,
                                         "message": "family entry is not an object"})
                continue
            family_key = str(entry.get("family_key", ""))
            if not family_key or family_key in seen_keys:
                result["issues"].append({"scope": "bundle_manifest", "entry": entry_index,
                                         "message": "empty or duplicate family_key"})
                continue
            seen_keys.add(family_key)
            entry_stage = str(entry.get("stage", ""))
            entry_component = component_key(entry)
            if (
                entry_component in over_family_budget_components
                or entry_component in over_row_budget_components
            ):
                continue
            try:
                family_member = _safe_member(entry.get("family_member"))
                process_member = _safe_member(entry.get("process_member"))
                is_pathway = str(entry.get("analysis_type", "")) == "pathway"
                rank_audit_raw = str(entry.get("rank_audit_member", "") or "").strip()
                rank_audit_member = _safe_member(rank_audit_raw) if is_pathway and rank_audit_raw else ""
            except ValueError as exc:
                result["quarantined"].append({
                    "family_key": family_key,
                    "reason": str(exc),
                    "load_action": "member_not_opened",
                })
                continue
            duplicate_members = [
                name for name in (family_member, process_member, rank_audit_member)
                if name
                if member_counts.get(name, 0) != 1
            ]
            if duplicate_members:
                result["quarantined"].append({
                    "family_key": family_key,
                    "reason": f"non-unique ZIP member names: {sorted(set(duplicate_members))}",
                    "load_action": "member_not_opened",
                })
                continue
            try:
                family_info = archive.getinfo(family_member)
                process_info = archive.getinfo(process_member)
                rank_audit_info = archive.getinfo(rank_audit_member) if rank_audit_member else None
            except KeyError as exc:
                result["quarantined"].append({"family_key": family_key,
                                               "reason": f"missing member: {exc}",
                                               "load_action": "member_not_opened"})
                continue
            limits = {
                "family": (family_info, int(spec["max_family_member_bytes"])),
                "process": (process_info, int(spec["max_process_member_bytes"])),
            }
            if rank_audit_info is not None:
                limits["rank_audit"] = (
                    rank_audit_info, int(spec["max_rank_audit_member_bytes"])
                )
            oversized = [name for name, (info, limit) in limits.items() if info.file_size > limit]
            if oversized:
                result["quarantined"].append({
                    "family_key": family_key,
                    "reason": "; ".join(
                        f"{name} member bytes {limits[name][0].file_size} exceeds {limits[name][1]}"
                        for name in oversized
                    ),
                    "load_action": "member_not_opened",
                })
                continue
            family_rows, family_errors = _read_csv_member(
                archive, family_member, schema["test_families_csv_gz"]["columns"],
                int(spec["max_family_rows"]),
                int(spec["max_family_member_bytes"]),
            )
            process_rows, process_errors = _read_csv_member(
                archive, process_member, schema["process_values_csv_gz"]["columns"],
                int(spec["max_process_rows"]),
                int(spec["max_process_member_bytes"]),
            )
            if rank_audit_member:
                rank_audit_rows, rank_audit_errors = _read_csv_member(
                    archive, rank_audit_member, schema["rank_audit_csv_gz"]["columns"],
                    int(spec["max_rank_audit_rows"]),
                    int(spec["max_rank_audit_member_bytes"]),
                )
            else:
                rank_audit_rows, rank_audit_errors = [], []
            if family_errors or process_errors or rank_audit_errors:
                result["quarantined"].append({
                    "family_key": family_key,
                    "reason": "; ".join(family_errors + process_errors + rank_audit_errors),
                    "load_action": "member_read_bounded_then_quarantined",
                })
                continue
            next_family_total = component_family_totals[entry_component] + len(family_rows)
            next_process_total = component_process_totals[entry_component] + len(process_rows)
            next_rank_audit_total = component_rank_totals[entry_component] + len(rank_audit_rows)
            if (
                next_family_total > int(spec.get("max_total_family_rows", 200000))
                or next_process_total > int(spec.get("max_total_process_rows", 500000))
                or next_rank_audit_total > int(spec.get("max_total_rank_audit_rows", 32768))
            ):
                # The submitted component is outside the public resource
                # contract.  Remove only rows already loaded for this same
                # manifest identity; unrelated components and stages survive.
                over_row_budget_components.add(entry_component)
                prior_keys = {
                    item["family_key"] for item in result["member_stats"]
                    if (
                        item.get("stage"), item.get("analysis_type"), item.get("scope")
                    ) == entry_component
                }
                if prior_keys:
                    result["families"] = [
                        row for row in result["families"]
                        if row.get("_submitted_family_key") not in prior_keys
                    ]
                    result["process"] = [
                        row for row in result["process"]
                        if row.get("_submitted_family_key") not in prior_keys
                    ]
                    result["rank_audits"] = [
                        row for row in result["rank_audits"]
                        if row.get("_submitted_family_key") not in prior_keys
                    ]
                    result["member_stats"] = [
                        item for item in result["member_stats"]
                        if item.get("family_key") not in prior_keys
                    ]
                result["quarantined"].append({
                    "family_key": "__component__:" + "|".join(entry_component),
                    "reason": (
                        f"component {entry_component!r} evidence row budget exceeded: "
                        f"family={next_family_total}, process={next_process_total}, "
                        f"rank_audit={next_rank_audit_total}"
                    ),
                    "trigger_family_key": family_key,
                    "load_action": "this_component_not_scored; unrelated_components_retained",
                })
                continue
            identity = {
                field: str(entry.get(field, ""))
                for field in ("stage", "analysis_type", "scope", "family_id")
            }
            identity["family_key"] = family_key
            mismatch = False
            for row in family_rows:
                if any(str(row.get(field, "")) != value for field, value in identity.items()
                       if field != "family_key"):
                    mismatch = True
                    break
            if mismatch:
                result["quarantined"].append({"family_key": family_key,
                                               "reason": "manifest identity does not match family rows",
                                               "load_action": "member_quarantined"})
                continue
            family_ids = {str(row.get("record_id", "")) for row in family_rows}
            if any(str(row.get("record_id", "")) not in family_ids for row in process_rows):
                result["quarantined"].append({"family_key": family_key,
                                               "reason": "process row links outside its family member",
                                               "load_action": "member_quarantined"})
                continue
            if is_pathway:
                try:
                    declared_rank_count = int(entry.get("rank_feature_count"))
                except (TypeError, ValueError):
                    declared_rank_count = -1
                audit_spec = schema["rank_audit_csv_gz"]
                minimum_rank_features = int(audit_spec.get("minimum_full_rank_features", 10000))
                rank_features = [str(row.get("feature_id", "")).strip() for row in rank_audit_rows]
                invalid_rank_values = 0
                role_members = {"top": set(), "bottom": set(), "hash_sample": set()}
                rank_positions: dict[str, int] = {}
                for row in rank_audit_rows:
                    observable = str(row.get("observable", "")).strip().lower() not in {
                        "", "0", "false", "no", "none", "nan"
                    }
                    if not observable or not str(row.get("method", "")).strip():
                        invalid_rank_values += 1
                        continue
                    for field in ("rank_position", "rank_value", "effect", "statistic", "n_units"):
                        try:
                            value = float(row.get(field, ""))
                        except (TypeError, ValueError):
                            invalid_rank_values += 1
                            break
                        if value != value or value in (float("inf"), float("-inf")):
                            invalid_rank_values += 1
                            break
                    feature = str(row.get("feature_id", "")).strip()
                    try:
                        rank_positions[feature] = int(float(row.get("rank_position", "")))
                    except (TypeError, ValueError):
                        invalid_rank_values += 1
                    roles = {value for value in str(row.get("audit_role", "")).split("|") if value}
                    if not roles or not roles.issubset(role_members):
                        invalid_rank_values += 1
                    for role in roles.intersection(role_members):
                        role_members[role].add(feature)
                digest_fields_valid = all(
                    len(str(entry.get(field, ""))) == 64
                    and all(ch in "0123456789abcdef" for ch in str(entry.get(field, "")).lower())
                    for field in ("rank_feature_set_sha256", "rank_order_sha256")
                )
                expected_top = int(audit_spec.get("top_count", 32))
                expected_bottom = int(audit_spec.get("bottom_count", 32))
                expected_hash = int(audit_spec.get("hash_sample_count", 64))
                top_positions = {rank_positions.get(feature) for feature in role_members["top"]}
                bottom_positions = {rank_positions.get(feature) for feature in role_members["bottom"]}
                if (
                    declared_rank_count < minimum_rank_features
                    or any(not feature for feature in rank_features)
                    or len(set(rank_features)) != len(rank_features)
                    or invalid_rank_values
                    or not digest_fields_valid
                    or len(role_members["top"]) != expected_top
                    or len(role_members["bottom"]) != expected_bottom
                    or len(role_members["hash_sample"]) != expected_hash
                    or top_positions != set(range(1, expected_top + 1))
                    or bottom_positions != set(
                        range(declared_rank_count - expected_bottom + 1, declared_rank_count + 1)
                    )
                ):
                    result["issues"].append({
                        "scope": "pathway_rank_audit",
                        "family_key": family_key,
                        "message": (
                            "compact pathway rank audit is absent or invalid; family/process rows remain "
                            "scoreable, while rank-audit-dependent design credit is unavailable: "
                            f"declared_features={declared_rank_count}, audit_rows={len(rank_audit_rows)}, "
                            f"minimum_features={minimum_rank_features}, unique_features={len(set(rank_features))}, "
                            f"invalid_values={invalid_rank_values}"
                        ),
                    })
                    rank_audit_rows = []
            for row in family_rows:
                row["_submitted_family_key"] = family_key
            for row in process_rows:
                row["_submitted_family_key"] = family_key
            for row in rank_audit_rows:
                row["_submitted_family_key"] = family_key
            result["families"].extend(family_rows)
            result["process"].extend(process_rows)
            result["rank_audits"].extend(rank_audit_rows)
            component_family_totals[entry_component] += len(family_rows)
            component_process_totals[entry_component] += len(process_rows)
            component_rank_totals[entry_component] += len(rank_audit_rows)
            result["scanned_process_rows"] += len(process_rows)
            result["scanned_rank_audit_rows"] += len(rank_audit_rows)
            result["member_stats"].append({
                "family_key": family_key,
                "stage": identity["stage"],
                "analysis_type": identity["analysis_type"],
                "scope": identity["scope"],
                "family_id": identity["family_id"],
                "family_member": family_member,
                "process_member": process_member,
                "rank_audit_member": rank_audit_member or None,
                "rank_feature_count": int(entry.get("rank_feature_count", 0)) if is_pathway else None,
                "rank_feature_set_sha256": entry.get("rank_feature_set_sha256") if is_pathway else None,
                "rank_order_sha256": entry.get("rank_order_sha256") if is_pathway else None,
                "family_rows": len(family_rows),
                "process_rows": len(process_rows),
                "rank_audit_rows": len(rank_audit_rows),
                "family_bytes": family_info.file_size,
                "process_bytes": process_info.file_size,
                "rank_audit_bytes": rank_audit_info.file_size if rank_audit_info is not None else 0,
            })
    return result
