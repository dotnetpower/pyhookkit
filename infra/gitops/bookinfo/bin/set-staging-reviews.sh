#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: infra/gitops/bookinfo/bin/set-staging-reviews.sh <v1|v2|v3>" >&2
  exit 1
fi

variant="$1"
case "$variant" in
  v1|v2|v3) ;;
  *)
    echo "unsupported reviews variant: $variant" >&2
    exit 1
    ;;
esac

script_dir="$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
bookinfo_dir="$(CDPATH='' cd -- "$script_dir/.." && pwd)"
staging_kustomization="$bookinfo_dir/overlays/staging/kustomization.yaml"
target_patch="reviews-${variant}-patch.yaml"

python - "$staging_kustomization" "$target_patch" <<'PY'
from pathlib import Path
import re
import sys

kustomization_path = Path(sys.argv[1])
target_patch = sys.argv[2]
content = kustomization_path.read_text()
pattern = re.compile(r'(^\s*-\s+path:\s+reviews-v[123]-patch\.yaml\s*$)', re.MULTILINE)
matches = pattern.findall(content)
if len(matches) != 1:
    raise SystemExit(
        f'expected exactly one active reviews patch in {kustomization_path}, found {len(matches)}'
    )
updated = pattern.sub(f'  - path: {target_patch}', content, count=1)
if updated != content:
    kustomization_path.write_text(updated)
PY

rendered_manifest="$(kubectl kustomize "$bookinfo_dir/overlays/staging")"
expected_image="docker.io/istio/examples-bookinfo-reviews-${variant}:1.20.2"

if ! grep -q "$expected_image" <<<"$rendered_manifest"; then
  echo "rendered staging overlay does not contain expected Reviews image: $expected_image" >&2
  exit 1
fi

echo "updated $staging_kustomization to use $target_patch"
