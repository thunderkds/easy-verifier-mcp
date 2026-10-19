#!/usr/bin/env bash
# Build the linux/amd64 image tagged :<pyproject version> and :latest (arm64 is a later follow-up).
# Without flags it builds and loads the image locally; nothing is published.
#   --push                       publish to Docker Hub (operator only)
#   --push --replace-existing    publish over a version tag that already exists on Docker Hub.
#     Needed for 0.1.0: the user decided on 2026-10-19 (T118) to replace the 0.1.0 image built
#     2026-10-05 with one of the current code, keeping the version number.
set -euo pipefail

IMAGE_REPO="temvar/easy-verifier-mcp"
PLATFORMS="linux/amd64"

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

push=0
replace_existing=0
for arg in "$@"; do
  case "$arg" in
    --push) push=1 ;;
    --replace-existing) replace_existing=1 ;;
    *) fail "unknown argument: $arg (accepted: --push, --replace-existing)" ;;
  esac
done
if [[ "$replace_existing" == "1" && "$push" != "1" ]]; then
  fail "--replace-existing only applies together with --push"
fi

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_root"

command -v docker >/dev/null || fail "docker is required"
command -v git >/dev/null || fail "git is required"
docker buildx version >/dev/null 2>&1 || fail "docker buildx is required"

version=$(sed -n 's/^version = "\(.*\)"$/\1/p' pyproject.toml | head -n 1)
[[ -n "$version" ]] || fail "could not read version from pyproject.toml"

# Every compose service must use the image this script builds.
compose_images=$(sed -n 's/^[[:space:]]*image:[[:space:]]*\([^[:space:]]*\)[[:space:]]*$/\1/p' compose.yaml)
[[ -n "$compose_images" ]] || fail "compose.yaml names no image"
while IFS= read -r compose_image; do
  [[ "$compose_image" == "$IMAGE_REPO:$version" ]] \
    || fail "compose.yaml image '$compose_image' is not '$IMAGE_REPO:$version'"
done <<<"$compose_images"

if [[ -n "$(git status --porcelain)" ]]; then
  fail "working tree is dirty; commit or stash so the image matches a commit"
fi

# The builder must offer every platform we publish (currently amd64 only).
builder_info=$(docker buildx inspect 2>/dev/null) || fail "cannot inspect the current buildx builder"
for platform in ${PLATFORMS//,/ }; do
  grep -q "$platform" <<<"$builder_info" \
    || fail "current buildx builder does not support $platform"
done

if [[ "$push" == "1" && "$replace_existing" != "1" ]]; then
  if docker buildx imagetools inspect "$IMAGE_REPO:$version" >/dev/null 2>&1; then
    fail "$IMAGE_REPO:$version already exists on Docker Hub; pass --replace-existing to overwrite it"
  fi
fi

build_args=(
  docker buildx build
  --platform "$PLATFORMS"
  -t "$IMAGE_REPO:$version"
  -t "$IMAGE_REPO:latest"
)

if [[ "$push" == "1" ]]; then
  metadata_file=$(mktemp)
  trap 'rm -f "$metadata_file"' EXIT
  "${build_args[@]}" --metadata-file "$metadata_file" --push .
  printf 'Pushed %s and %s\n' "$IMAGE_REPO:$version" "$IMAGE_REPO:latest"
  sed -n 's/.*"containerimage.digest": *"\([^"]*\)".*/Digest: \1/p' "$metadata_file"
else
  "${build_args[@]}" --load .
  printf 'Local build: loaded %s and %s for %s; nothing was published (pass --push to publish).\n' \
    "$IMAGE_REPO:$version" "$IMAGE_REPO:latest" "$PLATFORMS"
fi
