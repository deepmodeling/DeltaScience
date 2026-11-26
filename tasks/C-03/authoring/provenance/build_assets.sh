#!/usr/bin/env bash
set -euo pipefail
source_dir="$(cd "$(dirname "$0")" && pwd)"
asset_python="${BCL_ASSET_PYTHON:-python3}"
output_dir="${1:-$source_dir/regenerated}"
mkdir -p "$output_dir"
"$asset_python" "$source_dir/prepare_assets.py" "$output_dir"
for stem in bcl2_6o0k_chainA bclxl_4qvx_chainA; do
  "$asset_python" -m meeko.cli.mk_prepare_receptor --read_pdb "$output_dir/${stem}_protein.pdb" -p "$output_dir/${stem}.pdbqt"
done
"$asset_python" - "$output_dir" <<'PYHASH'
import hashlib,json,sys
from pathlib import Path
p=Path(sys.argv[1]); m=p/'asset_manifest.json'; data=json.loads(m.read_text())
for f in sorted(p.glob('*.pdbqt')): data['hashes']['prepared/'+f.name]=hashlib.sha256(f.read_bytes()).hexdigest()
m.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
PYHASH
