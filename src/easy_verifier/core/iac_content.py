"""Infrastructure YAML recognised by content (T094, FR-076, DDR-0012).

A ``.yml``/``.yaml`` file that no name pattern places fills a source role by
what it contains: a Kubernetes manifest (a document with top-level
``apiVersion`` and ``kind``), a Compose file (``services:`` entries with an
``image``/``build``, or Compose v1's top-level service names each with one)
or a CloudFormation template (``AWSTemplateFormatVersion``, or ``Resources``
entries typed ``AWS::...``).

The check is line-based on top-level keys, with no YAML parser (NFR: no new
dependency): a line at column 0 is a top-level key, the first indented level
under it holds its direct child keys. Only the shape is read, never a value,
so a Secret manifest's data is not looked at here (excerpts redact it).
"""

from __future__ import annotations

import re

K8S = "k8s-manifest"
COMPOSE = "container-config"
CLOUD = "cloud-template"

_KEY = re.compile(
    r"""^ *(?P<key>"[^"]+"|'[^']+'|[^\s#\-:?][^:#]*?)\s*:"""
    r"""(?:\s+(?P<rest>.*))?$"""
)
_DOCUMENT_BREAK = re.compile(r"^(?:---|\.\.\.)(?:\s|$)")

_CI_KEYS = frozenset({"script", "before_script", "stage", "steps", "runs-on"})
"""Child keys a CI job has and a Compose service never does: a GitLab job
named ``build:`` with an ``image:`` is not a Compose v1 service."""

_CI_TOP_LEVEL = frozenset({"stages", "jobs", "on", "workflow", "include", "pipelines"})


def classify(text: str) -> frozenset[str]:
    """The roles whose content shape ``text`` has (possibly none or several)."""
    found: set[str] = set()
    for document in _documents(text):
        found |= _classify_document(document)
    return frozenset(found)


def _documents(text: str) -> list[list[str]]:
    documents: list[list[str]] = [[]]
    for line in text.lstrip("﻿").splitlines():
        if _DOCUMENT_BREAK.match(line):
            documents.append([])
        elif line.strip() and not line.lstrip().startswith("#"):
            documents[-1].append(line.rstrip())
    return [document for document in documents if document]


def _classify_document(lines: list[str]) -> set[str]:
    top = _entries(lines, 0)
    keys = {key for key, _, _ in top}
    found: set[str] = set()
    is_manifest = {"apiVersion", "kind"} <= keys
    if is_manifest:
        found.add(K8S)
    if "AWSTemplateFormatVersion" in keys or any(
        key == "Resources" and _has_aws_type(body) for key, _, body in top
    ):
        found.add(CLOUD)
    if any(key == "services" and _has_service(body) for key, _, body in top):
        found.add(COMPOSE)
    elif not is_manifest and not keys & _CI_TOP_LEVEL:
        # Compose v1: each top-level key is a service.
        if any(_is_service(body) for _, _, body in top):
            found.add(COMPOSE)
    return found


def _entries(lines: list[str], indent: int) -> list[tuple[str, str, list[str]]]:
    """``(key, inline value, body lines)`` for the keys at exactly ``indent``;
    the body is every following line indented deeper."""
    entries: list[tuple[str, str, list[str]]] = []
    current: tuple[str, str, list[str]] | None = None
    for line in lines:
        depth = len(line) - len(line.lstrip(" "))
        match = _KEY.match(line) if depth == indent else None
        if match is not None and not line.lstrip().startswith("- "):
            current = (
                match.group("key").strip("\"'"),
                (match.group("rest") or "").strip(),
                [],
            )
            entries.append(current)
        elif depth > indent or line.lstrip().startswith("-"):
            if current is not None:
                current[2].append(line)
        else:
            current = None
    return entries


def _children(body: list[str]) -> list[tuple[str, str, list[str]]]:
    """Direct child keys of a block: those at its first indentation level."""
    indents = [len(line) - len(line.lstrip(" ")) for line in body]
    return _entries(body, min(indents)) if indents and min(indents) > 0 else []


def _is_service(body: list[str]) -> bool:
    keys = {key for key, _, _ in _children(body)}
    return bool(keys & {"image", "build"}) and not keys & _CI_KEYS


def _has_service(body: list[str]) -> bool:
    return any(_is_service(entry) for _, _, entry in _children(body))


def _has_aws_type(body: list[str]) -> bool:
    return any(
        key == "Type" and value.strip("\"'").startswith("AWS::")
        for _, _, entry in _children(body)
        for key, value, _ in _children(entry)
    )
