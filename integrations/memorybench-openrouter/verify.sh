#!/usr/bin/env bash
set -euo pipefail

readonly EXPECTED_COMMIT="118209a746d97d0d85e5a7234267f0b6962857e9"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly MEMORYBENCH_DIR="${1:-}"

if [[ -z "${MEMORYBENCH_DIR}" || ! -d "${MEMORYBENCH_DIR}/.git" ]]; then
  echo "usage: $0 /path/to/clean-memorybench-checkout" >&2
  exit 2
fi

actual_commit="$(git -C "${MEMORYBENCH_DIR}" rev-parse HEAD)"
if [[ "${actual_commit}" != "${EXPECTED_COMMIT}" ]]; then
  echo "expected MemoryBench ${EXPECTED_COMMIT}; found ${actual_commit}" >&2
  exit 1
fi

git -C "${MEMORYBENCH_DIR}" diff --quiet
git -C "${MEMORYBENCH_DIR}" diff --cached --quiet
git -C "${MEMORYBENCH_DIR}" apply --check "${SCRIPT_DIR}/memorybench-openrouter.patch"
git -C "${MEMORYBENCH_DIR}" apply "${SCRIPT_DIR}/memorybench-openrouter.patch"

(
  cd "${MEMORYBENCH_DIR}"
  bun install --frozen-lockfile
  bun test src/utils/models.test.ts src/judges/openrouter.test.ts
  bunx tsc --noEmit
)

