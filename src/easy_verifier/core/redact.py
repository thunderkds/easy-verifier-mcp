"""Redaction seam (NFR-010, DDR-0001).

**This is a placeholder, not redaction.** :func:`redact` currently returns its
input unchanged. It exists so that the mandatory call site inside
:func:`easy_verifier.core.pipeline.run_dimension` is fixed *now*, before six
dimensions are written against the pipeline — T004 replaces the body of this one
function with the real detector (regex + entropy scan, fingerprint = masked
prefix + hash prefix) and every dimension inherits it with no change.

A partial detector was deliberately **not** shipped here: a half-built one is
worse than an obvious placeholder, because it looks finished.

The signature is T004's final signature. Do not change it.
"""

from __future__ import annotations


def redact(text: str) -> str:
    """Return ``text`` with detected secrets replaced by fingerprints.

    SEAM ONLY — identity passthrough until T004. Callers must not rely on the
    current behaviour; they must rely on the fact that this function is the one
    place evidence text passes through before it leaves the engine.
    """
    return text
