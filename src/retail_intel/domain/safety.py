"""Untrusted-content defence (plan section 8): scan, quarantine and neutralise source text before any LLM sees it.

Web pages, titles, descriptions and reviews are attacker-controlled. This is a deterministic first line of defence
(heuristics, not a guarantee); agents must additionally be limited to allow-listed, typed tools.
"""

from __future__ import annotations

import re
import unicodedata
from typing import List

from pydantic import BaseModel, Field

_PATTERNS = [
    ("INSTRUCTION_OVERRIDE", re.compile(r"\b(ignore|disregard|forget|override)\b.{0,40}\b(previous|prior|above|earlier|all|system)\b.{0,30}\b(instruction|prompt|rule|message)s?\b", re.I | re.S)),
    ("ROLE_HIJACK", re.compile(r"\b(you are now|act as|pretend to be|from now on you)\b", re.I)),
    ("PROMPT_EXFILTRATION", re.compile(r"\b(reveal|print|show|repeat|output)\b.{0,30}\b(system prompt|instructions|hidden prompt|api key|secret|credential)s?\b", re.I | re.S)),
    ("CHAT_MARKUP", re.compile(r"(<\|im_start\|>|<\|im_end\|>|\[/?INST\]|^\s*(system|assistant)\s*:)", re.I | re.M)),
    ("ACTION_DIRECTIVE", re.compile(r"\b(set|change|update|match)\b.{0,30}\b(price|prices)\b.{0,20}\b(to|at)\b.{0,12}\$?\d", re.I | re.S)),
    ("EXFIL_URL", re.compile(r"\b(send|post|upload|forward)\b.{0,40}https?://", re.I | re.S)),
    ("HIDDEN_HTML", re.compile(r"(<script\b|display\s*:\s*none|visibility\s*:\s*hidden|font-size\s*:\s*0)", re.I)),
    ("TOOL_CALL_SYNTAX", re.compile(r"(\bfunction_call\b|<tool_call>|\"tool_name\"\s*:)", re.I)),
]
_ZERO_WIDTH = re.compile("[​‌‍⁠﻿‪-‮⁦-⁩]")
MAX_FIELD_CHARS = 4000


class ScanResult(BaseModel):
    suspicious: bool
    reasons: List[str] = Field(default_factory=list)
    hidden_chars_removed: int = 0
    truncated: bool = False


def scan_untrusted_text(text: str) -> ScanResult:
    reasons = [name for name, pat in _PATTERNS if pat.search(text)]
    hidden = len(_ZERO_WIDTH.findall(text))
    if hidden:
        reasons.append("HIDDEN_UNICODE")
    return ScanResult(suspicious=bool(reasons), reasons=sorted(set(reasons)), hidden_chars_removed=hidden,
                      truncated=len(text) > MAX_FIELD_CHARS)


def clean_text(text: str, max_chars: int = MAX_FIELD_CHARS) -> str:
    """Strip control and invisible characters, normalise, truncate."""
    t = unicodedata.normalize("NFKC", _ZERO_WIDTH.sub("", text))
    t = "".join(ch for ch in t if ch in "\n\t" or unicodedata.category(ch)[0] != "C")
    return t[:max_chars]


def wrap_for_llm(text: str, label: str = "source_text") -> str:
    """Delimit untrusted content so a prompt can instruct the model to treat it strictly as data."""
    body = clean_text(text).replace("</untrusted>", "[/untrusted]")
    return f'<untrusted label="{label}">\n{body}\n</untrusted>'


def should_quarantine(*texts: str) -> ScanResult:
    """Combine scans across several fields; any suspicious field quarantines the record (evidence is retained)."""
    reasons: List[str] = []
    hidden = 0
    truncated = False
    for t in texts:
        r = scan_untrusted_text(t or "")
        reasons += r.reasons
        hidden += r.hidden_chars_removed
        truncated = truncated or r.truncated
    return ScanResult(suspicious=bool(reasons), reasons=sorted(set(reasons)), hidden_chars_removed=hidden, truncated=truncated)
