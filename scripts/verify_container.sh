#!/usr/bin/env bash
set -euo pipefail

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

command -v docker >/dev/null || fail "docker is required"
command -v timeout >/dev/null || fail "GNU timeout is required"
docker compose version >/dev/null || fail "Docker Compose is required"
docker compose config --quiet

if ! docker info >/dev/null 2>&1; then
  if [[ "${EASY_VERIFIER_ALLOW_DOCKER_SKIP:-0}" == "1" ]]; then
    printf 'SKIP: Docker daemon is unavailable\n'
    exit 0
  fi
  fail "Docker daemon is unavailable"
fi

verify_root=$(mktemp -d "${TMPDIR:-/tmp}/easy-verifier-container.XXXXXX")
target_repo="$verify_root/target"
reports_dir="$target_repo/reports"
response_file="$verify_root/mcp-responses.jsonl"
container_id=""

cleanup() {
  if [[ -n "$container_id" ]]; then
    docker rm -f "$container_id" >/dev/null 2>&1 || true
  fi
  rm -rf "$verify_root"
}
trap cleanup EXIT

mkdir -p "$reports_dir"
printf '# Container verification target\n' >"$target_repo/README.md"
git -C "$target_repo" init --quiet
# The fixed container UID needs write access only to this deliberately isolated
# reports bind mount. The target root itself remains kernel-enforced read-only.
chmod 0777 "$reports_dir"

export COMPOSE_PROJECT_NAME="easy-verifier-t016-${RANDOM}"
export EASY_VERIFIER_REPO="$target_repo"
export EASY_VERIFIER_REPORTS="$reports_dir"

container_id=$(docker compose run --rm --detach --entrypoint sleep verifier 300)

uid=$(docker exec "$container_id" id -u)
[[ "$uid" != "0" ]] || fail "container runs as root"

if docker exec "$container_id" touch /workspace/NOPE >/dev/null 2>&1; then
  fail "target repository root is writable"
fi
docker exec "$container_id" touch /workspace/reports/ok
docker exec "$container_id" git -C /workspace status --short >/dev/null

[[ "$(docker inspect --format '{{.HostConfig.NetworkMode}}' "$container_id")" == "none" ]] ||
  fail "runtime network is not disabled"
[[ "$(docker inspect --format '{{.HostConfig.ReadonlyRootfs}}' "$container_id")" == "true" ]] ||
  fail "container root filesystem is writable"

inspect_json=$(docker inspect "$container_id")
python3 - "$inspect_json" <<'PY'
import json
import sys

container = json.loads(sys.argv[1])[0]
host = container["HostConfig"]
if host.get("CapAdd"):
    raise SystemExit("FAIL: capabilities were added")
if set(host.get("CapDrop") or ()) != {"ALL"}:
    raise SystemExit("FAIL: cap_drop is not exactly ALL")
if host.get("PortBindings"):
    raise SystemExit("FAIL: ports were published")
PY

printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"t016-verifier","version":"1"}}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"architecture","arguments":{"repo":"/workspace","scope":"project"}}}' \
  '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"write_report","arguments":{"repo":"/workspace","dimensions":["architecture"],"findings":[]}}}' |
  timeout 90s docker compose run --rm --no-tty verifier >"$response_file"

python3 - "$response_file" <<'PY'
import json
import pathlib
import sys

messages = {
    message["id"]: message
    for line in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
    if (message := json.loads(line)).get("id") is not None
}
if len(messages[2]["result"]["tools"]) != 10:
    raise SystemExit("FAIL: tools/list did not return exactly 10 tools")
for request_id in (3, 4):
    result = messages[request_id]["result"]
    if result.get("isError"):
        raise SystemExit(f"FAIL: tool request {request_id} returned an error")
PY

report_file=$(find "$reports_dir" -maxdepth 1 -type f -name '*.html' -print -quit)
[[ -n "$report_file" ]] || fail "write_report did not create an HTML report"
if grep -q '/workspace' "$report_file"; then
  fail "report leaks the container-internal repository path"
fi

printf 'PASS: uid=%s, tools=10, root=read-only, reports=writable, network=none, ports=none, caps=none\n' "$uid"
