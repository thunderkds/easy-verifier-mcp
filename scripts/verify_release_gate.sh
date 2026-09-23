#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_root"

python_bin=${T017_PYTHON:-python}
if ! "$python_bin" -c 'import mcp' >/dev/null 2>&1; then
  for candidate in \
    "$repo_root/.venv/bin/python" \
    "/home/hungnguyenhuu/workspace/training/phuongbui/ai-training/travel_chatbot/.venv/bin/python"
  do
    if test -x "$candidate" && "$candidate" -c 'import mcp' >/dev/null 2>&1; then
      python_bin=$candidate
      break
    fi
  done
fi
"$python_bin" -m pytest tests/integration -q --tb=short
T017_REQUIRE_DOCKER=1 "$python_bin" -m pytest tests/integration -q --tb=short -k 'container'
bash scripts/verify_container.sh
T017_RUN_KPI=1 T017_CONTAINER_STATUS=PASS T017_INTEGRATION_STATUS=PASS \
  "$python_bin" -m pytest tests/integration/test_kpi_summary.py -q -s
printf 'RESULT integration=0 container=0 release=0\n'
