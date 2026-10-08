"""The optional ``frontend-a11y`` pack (T049, DDR-0008 §4, FR-053).

Area #19 (accessibility, responsive UX, browser compatibility), five checks
over markup text, never rendered or run:

* images with no text alternative (WCAG 2.2 SC 1.1.1; ``alt=""`` is allowed);
* form controls with no accessible name (SC 1.3.1 / 4.1.2);
* ``aria-hidden`` on a focusable element (SC 4.1.2);
* HTML entry documents with no viewport, or one that disables zoom
  (SC 1.4.4 / 1.4.10);
* no declared browser support (browserslist or equivalent).

An element whose attributes are partly unknown (a spread, an object bind, a
server-template expression inside the tag) is named as not verifiable, never
counted as missing; a check with nothing verifiable to judge abstains. Which
files hold markup, which tags and attributes matter and how each framework
spells them are the registry's data (``registry/packs/frontend-a11y.toml``),
never this module's: here is only the generic lexing of a tag.

The pack runs only when ``roles.active_packs`` names it.
"""

from __future__ import annotations

import bisect
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from functools import lru_cache

from ..core.judge import RATING_RULES
from ..core.metrics import PACK_METRICS
from ..core.models import (
    DimensionContext,
    DimensionDescriptor,
    Excerpt,
    SampledMetric,
    SourceMiss,
    SourceRole,
)
from ..core.redact import redact
from ..core.registry import load_pack
from ..core.roles import _matcher
from ..dimensions import _code_extract

NAME = "frontend-a11y"

PURPOSE = (
    "Optional frontend accessibility pack, active only when configured or "
    "picked: gather images without a text alternative, form controls without "
    "a name, aria-hidden on focusable elements (WCAG 2.2), the viewport of "
    "HTML entry documents and the declared browser support, from markup text; "
    "nothing is rendered, so contrast and what a component renders are not "
    "examined."
)

MARKUP = "markup files (the pack's markup_files)"
ENTRIES = "HTML entry documents (the pack's viewport_entries)"
BROWSERS = "browser-support declarations (the pack's browser_support)"

ROLES: tuple[SourceRole, ...] = (
    SourceRole(name=MARKUP, patterns=()),
    SourceRole(name=ENTRIES, patterns=()),
    SourceRole(name=BROWSERS, patterns=()),
)
"""Pseudo-roles credited by the scan: markup read, an entry document read,
browser support declared."""

SOURCES_SOUGHT: tuple[str, ...] = tuple(item.name for item in ROLES)

MAX_FILES = 500
"""Markup files read, in path order; the rest are counted and disclosed. The
same cap bounds entry documents and browser-support files."""

MAX_TAG_CHARS = 4000
"""A tag not closed within this many characters is not a tag."""

MAX_LISTED = 20
"""Sites named in one derivation; the rest are counted."""

CONTEXT_LINES = 1

(
    IMAGE_METRIC,
    CONTROL_METRIC,
    HIDDEN_METRIC,
    VIEWPORT_METRIC,
    BROWSER_METRIC,
) = PACK_METRICS[NAME]

UNRESOLVED_SCOPE_REASON = (
    "not examined: the {scope} scope could not be resolved "
    "(its required selector was not supplied)"
)

_TAG = re.compile(r"<(/?)([A-Za-z][\w:.-]*)")
_NAME = re.compile(r"[^\s=>\"'`{}/]+")
_SHORTHAND = re.compile(r"\{\s*([A-Za-z_$][\w$]*)\s*\}")
_QUOTED = re.compile(r"\"[^\"]*\"|'[^']*'")
_INT = re.compile(r"[{\s\"']*(-?\d+)[}\s\"']*")


@dataclass(frozen=True)
class _Patterns:
    markup: tuple[str, ...]
    excluded: tuple[str, ...]
    comments: tuple[re.Pattern[str], ...]
    bindings: tuple[re.Pattern[str], ...]
    dynamic: tuple[re.Pattern[str], ...]
    images: frozenset[str]
    alt: frozenset[str]
    controls: frozenset[str]
    unnamed_types: frozenset[str]
    names: frozenset[str]
    labels: frozenset[str]
    label_for: frozenset[str]
    focusable: frozenset[str]
    focusable_href: frozenset[str]
    hidden: frozenset[str]
    entries: tuple[str, ...]
    default_entries: tuple[str, ...]
    viewport: tuple[re.Pattern[str], ...]
    zoom: tuple[re.Pattern[str], ...]
    browsers: tuple[tuple[str, re.Pattern[str]], ...]


@lru_cache(maxsize=1)
def _patterns() -> _Patterns:
    fields = load_pack(NAME).fields

    def values(name: str) -> tuple[str, ...]:
        return tuple(value for cited in fields[name] for value in cited.value)

    def words(name: str) -> frozenset[str]:
        return frozenset(value.lower() for value in values(name))

    def regexes(name: str) -> tuple[re.Pattern[str], ...]:
        return tuple(re.compile(item) for item in values(name))

    pairs = (item.split("=", 1) for item in values("browser_support"))
    return _Patterns(
        markup=values("markup_files"),
        excluded=values("markup_excluded"),
        comments=regexes("comments"),
        bindings=regexes("attribute_bindings"),
        dynamic=regexes("dynamic_attributes"),
        images=words("image_tags"),
        alt=words("alt_attributes"),
        controls=words("form_controls"),
        unnamed_types=words("unnamed_input_types"),
        names=words("name_attributes"),
        labels=words("label_tags"),
        label_for=words("label_for_attributes"),
        focusable=words("focusable_tags"),
        focusable_href=words("focusable_with_href"),
        hidden=words("aria_hidden_attributes"),
        entries=values("viewport_entries"),
        default_entries=values("viewport_default_entries"),
        viewport=regexes("viewport_declarations"),
        zoom=regexes("zoom_disabled"),
        browsers=tuple((glob, re.compile(body)) for glob, body in pairs),
    )


# ---------------------------------------------------------------------------
# lexing


def blank_comments(text: str) -> str:
    """``text`` with every registry comment replaced by spaces, newlines kept,
    so line numbers do not move."""
    for pattern in _patterns().comments:
        text = pattern.sub(lambda m: re.sub(r"[^\n]", " ", m.group()), text)
    return text


@dataclass(frozen=True)
class Tag:
    name: str
    line: int
    closing: bool
    self_closing: bool
    attrs: dict[str, tuple[str, str]] = field(default_factory=dict)
    """Plain attribute name -> ``(kind, text)``; kind is ``literal`` (quoted
    or unquoted text), ``expr`` (a ``{...}`` expression) or ``bare``."""
    dynamic: bool = False
    """An attribute in the tag is unknown statically (registry
    ``dynamic_attributes``): a missing one is not verifiable."""


def tags(text: str) -> list[Tag]:
    """The element tags of ``text`` in order, names as written: the
    registry's tag lists are lowercase DOM names, so a capitalised component
    (``<Input>``, ``<Image>``) is never one of them. An opening
    ``<`` right after an identifier or a closing bracket (``i<input``) is a
    comparison, not a tag; a closing ``</`` never is (``Email</label>``)."""
    patterns = _patterns()
    starts = [0] + [m.end() for m in re.finditer("\n", text)]
    found = []
    for match in _TAG.finditer(text):
        at = match.start()
        closing = bool(match.group(1))
        if not closing and at and (text[at - 1].isalnum() or text[at - 1] in "_$)]"):
            continue
        after = match.end()
        if after < len(text) and not (text[after].isspace() or text[after] in "/>"):
            continue
        parsed = _attributes(text, after)
        if parsed is None:
            continue
        end, attrs, self_closing = parsed
        raw = _QUOTED.sub('""', text[at:end])
        found.append(
            Tag(
                name=match.group(2),
                line=bisect.bisect_right(starts, at),
                closing=closing,
                self_closing=self_closing,
                attrs={_plain(k, patterns): v for k, v in attrs},
                dynamic=any(p.search(raw[1:]) for p in patterns.dynamic),
            )
        )
    return found


def _attributes(text: str, i: int):
    """``(end, [(name, (kind, text))], self_closing)`` of the tag whose name
    ends at ``i``, or ``None`` when it does not close in time."""
    limit = min(len(text), i + MAX_TAG_CHARS)
    attrs: list[tuple[str, tuple[str, str]]] = []
    while i < limit:
        c = text[i]
        if c.isspace():
            i += 1
        elif c == ">":
            return i + 1, attrs, False
        elif text.startswith("/>", i):
            return i + 2, attrs, True
        elif c == "{":
            end = _balanced(text, i, limit)
            if end is None:
                return None
            short = _SHORTHAND.fullmatch(text[i:end])
            if short:
                attrs.append((short.group(1), ("expr", text[i:end])))
            i = end
        elif text.startswith("<%", i):
            end = text.find("%>", i, limit)
            if end < 0:
                return None
            i = end + 2
        elif c in "\"'`":
            end = text.find(c, i + 1, limit)
            if end < 0:
                return None
            i = end + 1
        else:
            name = _NAME.match(text, i)
            if name is None:
                i += 1
                continue
            i = name.end()
            j = i
            while j < limit and text[j].isspace():
                j += 1
            if j < limit and text[j] == "=":
                parsed = _value(text, j + 1, limit)
                if parsed is None:
                    return None
                i, value = parsed
            else:
                value = ("bare", "")
            attrs.append((name.group(), value))
    return None


def _value(text: str, i: int, limit: int):
    while i < limit and text[i].isspace():
        i += 1
    if i >= limit:
        return None
    c = text[i]
    if c in "\"'`":
        end = text.find(c, i + 1, limit)
        return None if end < 0 else (end + 1, ("literal", text[i + 1 : end]))
    if c == "{":
        end = _balanced(text, i, limit)
        return None if end is None else (end, ("expr", text[i:end]))
    end = i
    while end < limit and not text[end].isspace() and text[end] != ">":
        end += 1
    return end, ("literal", text[i:end])


def _balanced(text: str, i: int, limit: int) -> int | None:
    """One past the ``}`` closing the ``{`` at ``i``; quoted text skipped."""
    depth = 0
    while i < limit:
        c = text[i]
        if c in "\"'`":
            end = text.find(c, i + 1, limit)
            if end < 0:
                return None
            i = end
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return None


def _plain(name: str, patterns: _Patterns) -> str:
    lowered = name.lower()
    for binding in patterns.bindings:
        match = binding.fullmatch(lowered)
        if match:
            return match.group("name")
    return lowered


# ---------------------------------------------------------------------------
# checks


@dataclass
class _Check:
    """One markup check: violations, verified-fine count, not-verifiable."""

    hits: list[tuple[str, int, str]] = field(default_factory=list)
    fine: int = 0
    unknown: list[tuple[str, int, str]] = field(default_factory=list)


def _literal(value: tuple[str, str] | None) -> str | None:
    if value is None or value[0] == "expr":
        return None
    return value[1].strip().lower()


def _check_file(path: str, found: list[Tag], images, controls, hidden) -> None:
    patterns = _patterns()
    fors = {
        (kind, text.strip())
        for t in found
        for k, (kind, text) in t.attrs.items()
        if k in patterns.label_for
    }
    dynamic_for = any(kind == "expr" for kind, _text in fors)
    in_label = 0
    for tag in found:
        if tag.name in patterns.labels:
            if tag.closing:
                in_label = max(0, in_label - 1)
            elif not tag.self_closing:
                in_label += 1
        if tag.closing:
            continue
        site = (path, tag.line, f"<{tag.name}>")
        attrs = tag.attrs
        if tag.name in patterns.images:
            if patterns.alt & attrs.keys():
                images.fine += 1
            else:
                (images.unknown if tag.dynamic else images.hits).append(site)
        if tag.name in patterns.controls:
            kind = attrs.get("type")
            if _literal(kind) in patterns.unnamed_types:
                pass
            elif patterns.names & attrs.keys() or in_label:
                controls.fine += 1
            elif "id" in attrs and (attrs["id"][0], attrs["id"][1].strip()) in fors:
                # a literal id named by a literal for, or the same expression
                # in both (htmlFor={id} ... id={id})
                controls.fine += 1
            elif (
                tag.dynamic
                or (kind is not None and kind[0] == "expr")
                or ("id" in attrs and (attrs["id"][0] == "expr" or dynamic_for))
            ):
                controls.unknown.append(site)
            else:
                controls.hits.append(site)
        hidden_attr = next((attrs[k] for k in patterns.hidden if k in attrs), None)
        if hidden_attr is not None:
            state = _hidden_state(hidden_attr)
            focus = None if tag.dynamic else _focusable(tag, patterns)
            if state is False or focus is False:
                hidden.fine += 1
            elif state and focus:
                hidden.hits.append(site)
            else:
                hidden.unknown.append(site)


def _hidden_state(value: tuple[str, str]) -> bool | None:
    kind, text = value
    if kind == "bare":
        return True
    word = text.strip().strip("{}").strip().strip("\"'").lower()
    if word in ("true", "false"):
        return word == "true"
    return None if kind == "expr" else False


def _focusable(tag: Tag, patterns: _Patterns) -> bool | None:
    attrs = tag.attrs
    tabindex = attrs.get("tabindex")
    if tabindex is not None:
        number = _INT.fullmatch(tabindex[1])
        if number is None:
            return None
        return int(number.group(1)) >= 0
    native = tag.name in patterns.focusable or (
        tag.name in patterns.focusable_href and "href" in attrs
    )
    if tag.name in patterns.controls and _literal(attrs.get("type")) == "hidden":
        native = False
    if native and "disabled" in attrs:
        kind, text = attrs["disabled"]
        if kind != "expr" or text.replace(" ", "") == "{true}":
            return False
        return None
    return native


# ---------------------------------------------------------------------------
# scan


@dataclass
class _Scan:
    markup: list[tuple[str, list[str]]]
    markup_total: int
    images: _Check
    controls: _Check
    hidden: _Check
    entries: list[str]
    viewport_hits: list[tuple[str, int, str]]
    defaulted: int
    browser_files: list[str]
    declared_in: list[tuple[str, int]]
    texts: dict[str, list[str]]
    """Lines of every markup and entry file read, for the excerpts."""


def collect(context: DimensionContext) -> Iterator[Excerpt]:
    """Yield the lines around each site found, for the agent."""
    if context.resolved_scope is None and context.scope != "project":
        reason = UNRESOLVED_SCOPE_REASON.format(scope=context.scope)
        for source in SOURCES_SOUGHT:
            context.sources_missing.append(SourceMiss(source=source, reason=reason))
        return

    scan = getattr(context, "a11y_scan", None)
    if scan is None:
        # Once per context, before the first yield: the budget may call
        # ``collect`` once per tier and stop pulling at any yield.
        scan = _scan(context)
        context.a11y_scan = scan
        context.whole_file = _metrics(scan)
    _record_roles(context, scan)

    sites = [
        *scan.images.hits,
        *scan.controls.hits,
        *scan.hidden.hits,
        *scan.viewport_hits,
    ]
    for path in sorted({path for path, _n, _l in sites}):
        lines = scan.texts[path]
        yield from _windows(path, lines, [n for p, n, _l in sites if p == path])


def _scan(context: DimensionContext) -> _Scan:
    patterns = _patterns()
    scope_files = tuple(getattr(context.resolved_scope, "files", ()) or ())
    excluded = _matcher(patterns.excluded)
    shipped = sorted(p for p in scope_files if not excluded(p))

    is_markup = _matcher(patterns.markup)
    candidates = [p for p in shipped if is_markup(p)]
    markup: list[tuple[str, list[str]]] = []
    images, controls, hidden = _Check(), _Check(), _Check()
    for path in candidates[:MAX_FILES]:
        text = context.read_source(path)
        if text is None:
            continue
        markup.append((path, _lines(text)))
        _check_file(path, tags(blank_comments(text)), images, controls, hidden)

    texts = {path: "\n".join(lines) for path, lines in markup}
    is_entry = _matcher(patterns.entries)
    is_default = _matcher(patterns.default_entries)
    entries = [p for p in shipped if is_entry(p) or is_default(p)][:MAX_FILES]
    viewport_hits, defaulted, read_entries = [], 0, []
    for path in entries:
        text = texts[path] if path in texts else context.read_source(path)
        if text is None:
            continue
        read_entries.append(path)
        texts[path] = text
        clean = blank_comments(text)
        zoom = min(
            (m.start() for p in patterns.zoom for m in p.finditer(clean)), default=None
        )
        if zoom is not None:
            line = clean.count("\n", 0, zoom) + 1
            viewport_hits.append((path, line, "zoom disabled"))
        elif any(p.search(clean) for p in patterns.viewport):
            pass
        elif is_default(path):
            defaulted += 1
        else:
            viewport_hits.append((path, 1, "no viewport"))

    rules = [(_matcher((glob,)), regex) for glob, regex in patterns.browsers]
    browser_files = [p for p in shipped if any(m(p) for m, _r in rules)][:MAX_FILES]
    declared_in = []
    for path in browser_files:
        text = context.read_source(path)
        if not text:
            continue
        for applies, regex in rules:
            match = regex.search(text) if applies(path) else None
            if match:
                declared_in.append((path, text.count("\n", 0, match.start()) + 1))
                break
    return _Scan(
        markup,
        len(candidates),
        images,
        controls,
        hidden,
        read_entries,
        viewport_hits,
        defaulted,
        browser_files,
        declared_in,
        {path: _lines(text) for path, text in texts.items()},
    )


# ---------------------------------------------------------------------------
# metrics


def _sc(metric: str) -> str:
    """The first cited criterion of ``metric``'s rule, as ``label <url>``."""
    citation = RATING_RULES[NAME][metric].metric_citation[0]
    return f"{citation.label} {citation.url}"


def _metrics(scan: _Scan) -> tuple[SampledMetric, ...]:
    where = f"in {len(scan.markup)} markup file(s)"
    if scan.markup_total > len(scan.markup):
        where += (
            f" (the first {len(scan.markup)} of {scan.markup_total} in path "
            "order were read)"
        )
    scanned = [path for path, _lines in scan.markup]
    no_markup = (
        "no in-scope markup file (the pack's markup_files, tests and build "
        "output excluded) was read, so there is no markup to judge"
    )
    checks = (
        (IMAGE_METRIC, scan.images, "image element(s) without alt", "an image"),
        (
            CONTROL_METRIC,
            scan.controls,
            "form control(s) without a label, aria-label, aria-labelledby or title",
            "a form control that needs a name",
        ),
        (
            HIDDEN_METRIC,
            scan.hidden,
            "focusable element(s) carrying aria-hidden",
            "an aria-hidden element",
        ),
    )
    metrics = []
    for metric, check, what, element in checks:
        if not scan.markup:
            metrics.append(_abstain(metric, no_markup))
            continue
        unknown = _unknown(check.unknown)
        judged = check.fine + len(check.hits)
        if not judged:
            metrics.append(
                _abstain(
                    metric,
                    f"no verifiable {element} was found {where}, so there is "
                    f"nothing to judge{unknown}",
                )
            )
            continue
        metrics.append(
            _count(
                metric,
                check.hits,
                f"{what}, of {judged} verifiable {where}",
                f"matched textually against the pack's registry patterns; "
                f"components are not followed{unknown}; {_sc(metric)}",
                scanned,
            )
        )

    if not scan.entries:
        metrics.append(
            _abstain(
                VIEWPORT_METRIC,
                "no HTML entry document (the pack's viewport_entries or "
                "viewport_default_entries) was found in scope, so there is no "
                "viewport to judge",
            )
        )
    else:
        default = (
            f"; {scan.defaulted} framework entry(ies) rely on the framework's "
            "default viewport"
            if scan.defaulted
            else ""
        )
        metrics.append(
            _count(
                VIEWPORT_METRIC,
                scan.viewport_hits,
                f"entry document(s) with no viewport or with zoom disabled, of "
                f"{len(scan.entries)} read{default}",
                f"zoom capped below 200 % fails resize text; {_sc(VIEWPORT_METRIC)}",
                scan.entries,
            )
        )

    if not scan.markup:
        metrics.append(_abstain(BROWSER_METRIC, no_markup))
    elif scan.declared_in:
        path, line = scan.declared_in[0]
        metrics.append(
            SampledMetric(
                name=BROWSER_METRIC,
                value=0,
                abstention=None,
                computed_from=(redact(path),),
                derivation=(
                    f"browser support declared at {redact(path)}:{line} (the "
                    "pack's browser_support)"
                ),
            )
        )
    else:
        checked = scan.browser_files or scanned
        metrics.append(
            SampledMetric(
                name=BROWSER_METRIC,
                value=1,
                abstention=None,
                computed_from=tuple(sorted({redact(p) for p in checked})),
                derivation=(
                    f"no browser-support declaration (a browserslist query, a "
                    f"package.json browserslist key, a Babel targets option or "
                    f"a Vite build.target) in {len(scan.browser_files)} "
                    "candidate file(s)"
                ),
            )
        )
    return tuple(metrics)


def _unknown(sites: list[tuple[str, int, str]]) -> str:
    if not sites:
        return ""
    sites = sorted(set(sites))
    listed = ", ".join(f"{redact(p)}:{n} ({k})" for p, n, k in sites[:MAX_LISTED])
    more = f" and {len(sites) - MAX_LISTED} more" if len(sites) > MAX_LISTED else ""
    return (
        f"; {len(sites)} not verifiable (a spread, object bind or template "
        f"expression in the tag): {listed}{more}"
    )


def _count(name, sites, what, method, scanned) -> SampledMetric:
    """Paths are cited and listed as the pack's ``files_read`` holds them:
    redacted (a file name can look like a secret, core/pipeline.py)."""
    sites = sorted(set(sites))
    listed = ", ".join(
        f"{redact(p)}:{n} ({label})" for p, n, label in sites[:MAX_LISTED]
    )
    more = f" and {len(sites) - MAX_LISTED} more" if len(sites) > MAX_LISTED else ""
    cited = sorted({redact(p) for p in ({p for p, _n, _l in sites} or set(scanned))})
    return SampledMetric(
        name=name,
        value=len(sites),
        abstention=None,
        computed_from=tuple(cited),
        derivation=f"{len(sites)} {what}: {listed or 'none'}{more}; {method}",
    )


def _abstain(name: str, reason: str) -> SampledMetric:
    return SampledMetric(
        name=name, value=None, abstention=reason, computed_from=(), derivation=""
    )


def _record_roles(context: DimensionContext, scan: _Scan) -> None:
    filled = {
        MARKUP: bool(scan.markup),
        ENTRIES: bool(scan.entries),
        BROWSERS: bool(scan.declared_in),
    }
    reasons = {
        MARKUP: "not found: no readable in-scope file matches the pack's markup_files",
        ENTRIES: "not found: no readable in-scope file matches the pack's "
        "viewport_entries or viewport_default_entries",
        BROWSERS: f"no browser-support declaration was found in the "
        f"{len(scan.browser_files)} candidate file(s) read",
    }
    recorded = {m.source for m in context.sources_missing}
    for source, found in filled.items():
        if found and source not in context.sources_found:
            context.sources_found.append(source)
        elif not found and source not in recorded:
            context.sources_missing.append(
                SourceMiss(source=source, reason=reasons[source])
            )


def _lines(text: str) -> list[str]:
    return [line.removesuffix("\r") for line in text.split("\n")]


def _windows(path: str, lines: list[str], hits: list[int]) -> Iterator[Excerpt]:
    spans: list[list[int]] = []
    for line in sorted(set(hits)):
        start = max(1, line - CONTEXT_LINES)
        end = min(len(lines), line + CONTEXT_LINES)
        if spans and start <= spans[-1][1] + 1:
            spans[-1][1] = max(spans[-1][1], end)
        else:
            spans.append([start, end])
    for start, end in spans:
        excerpt = _code_extract._excerpt(path, lines, start - 1, end - 1)
        if excerpt is not None:
            yield excerpt


DESCRIPTOR = DimensionDescriptor(
    name=NAME,
    purpose=PURPOSE,
    sources_sought=SOURCES_SOUGHT,
    collect=collect,
    roles=ROLES,
)
