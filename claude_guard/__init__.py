"""
claude-guard: lightweight guardrails for Claude agents.

Usage:
    from claude_guard import Guard
    g = Guard()
    result = g.check("send_email", {"to": "boss@company.com"}, rules)
    if not result["safe"]:
        raise RuntimeError(result["reason"])
"""

import re
import json
import sqlite3
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

__version__ = "0.1.0"
__all__ = ["Guard"]

# ─── Injection patterns ────────────────────────────────────────────────────────

_INJECTION_PATTERNS = [
    # Classic override attempts
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"disregard\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"forget\s+(all\s+)?(previous|prior|above)\s+instructions?",
    r"override\s+(all\s+)?(previous|prior|above)\s+instructions?",
    # Role hijack
    r"you\s+are\s+now\s+(a\s+|an\s+)?(?!helpful)",
    r"act\s+as\s+(if\s+you\s+are\s+|a\s+)?(?:DAN|jailbreak|evil|uncensored)",
    r"pretend\s+(you\s+are|to\s+be)\s+(?:an?\s+)?(?:AI|assistant|model)\s+(?:without|with\s+no)",
    # Jailbreak triggers
    r"\bDAN\b",
    r"do\s+anything\s+now",
    r"jailbreak",
    r"remove\s+(your\s+)?(restrictions?|limitations?|filters?|guardrails?)",
    r"bypass\s+(your\s+)?(safety|restrictions?|rules?|policy|guidelines?)",
    # System prompt extraction
    r"(print|repeat|show|reveal|output|tell me|what (are|is) (your|the))\s+(your\s+)?(system\s+prompt|instructions?|rules?|context)",
    r"ignore\s+(the\s+)?(system\s+)?(prompt|instructions?|rules?)",
    # Context stuffing signals
    r"]\s*\n\s*\[.*?\bsystem\b",
    r"<\s*/?system\s*>",
    # Encoded bypass attempts (base64-ish trigger words)
    r"aWdub3Jl",   # "ignore" in base64
    r"c3lzdGVt",   # "system" in base64
]

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in _INJECTION_PATTERNS]


# ─── Rule evaluators ──────────────────────────────────────────────────────────

def _eval_rule(action: str, params: dict, rule: dict) -> dict | None:
    """
    Evaluate a single rule against the action/params.
    Returns {safe: False, reason: str} if blocked, None if rule doesn't apply or allows.

    Rule schema:
        {
          "action": "send_email" | "*",          # action name or wildcard
          "condition": {                          # optional param checks
            "field": "to",
            "op": "contains" | "equals" | "matches" | "not_in" | "in",
            "value": "example.com"
          },
          "block": true,                         # if condition matches, block
          "reason": "No external emails allowed"
        }
    """
    # Check action match
    rule_action = rule.get("action", "*")
    if rule_action != "*" and rule_action != action:
        return None

    condition = rule.get("condition")
    matched = True  # no condition = always matches

    if condition:
        field = condition.get("field")
        op = condition.get("op", "equals")
        value = condition.get("value")
        param_val = params.get(field, "")

        if op == "equals":
            matched = str(param_val) == str(value)
        elif op == "contains":
            matched = str(value).lower() in str(param_val).lower()
        elif op == "not_contains":
            matched = str(value).lower() not in str(param_val).lower()
        elif op == "matches":
            matched = bool(re.search(str(value), str(param_val), re.IGNORECASE))
        elif op == "in":
            allowed = value if isinstance(value, list) else [value]
            matched = str(param_val) in [str(v) for v in allowed]
        elif op == "not_in":
            # allowlist: block if param is NOT in the allowed list
            allowed_vals = value if isinstance(value, list) else [value]
            matched = str(param_val) not in [str(v) for v in allowed_vals]
        elif op == "gt":
            try:
                matched = float(param_val) > float(value)
            except (TypeError, ValueError):
                matched = False
        elif op == "lt":
            try:
                matched = float(param_val) < float(value)
            except (TypeError, ValueError):
                matched = False
        else:
            matched = False

    if matched and rule.get("block", False):
        return {
            "safe": False,
            "reason": rule.get("reason", f"Action '{action}' blocked by rule"),
        }

    return None


# ─── Guard class ─────────────────────────────────────────────────────────────

class Guard:
    """
    Lightweight guardrails for Claude agents.

    Args:
        db_path: Path to SQLite audit log. Defaults to ~/.claude_guard/audit.db
        auto_log: If True, Guard.check() automatically logs every decision.
    """

    def __init__(self, db_path: str | Path | None = None, auto_log: bool = True):
        if db_path is None:
            default_dir = Path.home() / ".claude_guard"
            default_dir.mkdir(parents=True, exist_ok=True)
            db_path = default_dir / "audit.db"
        self._db_path = Path(db_path)
        self._auto_log = auto_log
        self._init_db()

    # ── Database ────────────────────────────────────────────────────────────

    def _init_db(self) -> None:
        """Create audit log table if it doesn't exist."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts         TEXT    NOT NULL,
                    action     TEXT    NOT NULL,
                    safe       INTEGER NOT NULL,
                    reason     TEXT,
                    metadata   TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ts ON audit_log(ts)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_action ON audit_log(action)")
            conn.commit()

    # ── Core API ─────────────────────────────────────────────────────────────

    def check(self, action: str, params: dict, rules: list[dict]) -> dict:
        """
        Check whether an action is safe given a list of rules.

        Args:
            action: Name of the action being performed (e.g. "send_email").
            params: Dict of action parameters (e.g. {"to": "x@y.com", "body": "..."}).
            rules:  List of rule dicts (see README for schema).

        Returns:
            {"safe": bool, "reason": str}
        """
        if not isinstance(params, dict):
            params = {}

        for rule in rules:
            result = _eval_rule(action, params, rule)
            if result is not None:
                if self._auto_log:
                    self.log(action, result, {"params_hash": _hash_params(params)})
                return result

        outcome = {"safe": True, "reason": "No rules matched — action allowed"}
        if self._auto_log:
            self.log(action, outcome, {"params_hash": _hash_params(params)})
        return outcome

    def inject_detect(self, text: str) -> bool:
        """
        Detect prompt injection patterns in text.

        Scans for override attempts, role hijacks, jailbreak triggers,
        and system-prompt extraction patterns.

        Args:
            text: Any string to scan (user input, tool output, etc.)

        Returns:
            True if injection detected, False if clean.
        """
        if not isinstance(text, str):
            return False
        for pattern in _COMPILED_PATTERNS:
            if pattern.search(text):
                return True
        return False

    def log(self, action: str, result: dict, metadata: dict | None = None) -> int:
        """
        Write an audit entry to the SQLite log.

        Args:
            action:   Action name.
            result:   The dict returned by check() or any {safe, reason} dict.
            metadata: Optional extra context (will be JSON-serialised).

        Returns:
            Row id of the inserted record.
        """
        ts = datetime.now(timezone.utc).isoformat()
        safe = 1 if result.get("safe", True) else 0
        reason = result.get("reason", "")
        meta_json = json.dumps(metadata) if metadata else None

        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO audit_log (ts, action, safe, reason, metadata) VALUES (?,?,?,?,?)",
                (ts, action, safe, reason, meta_json),
            )
            conn.commit()
            return cursor.lastrowid

    def recent_logs(self, limit: int = 50) -> list[dict]:
        """Return the most recent audit entries as dicts."""
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def blocked_count(self, action: str | None = None) -> int:
        """Count blocked actions (optionally filter by action name)."""
        with sqlite3.connect(self._db_path) as conn:
            if action:
                (count,) = conn.execute(
                    "SELECT COUNT(*) FROM audit_log WHERE safe=0 AND action=?", (action,)
                ).fetchone()
            else:
                (count,) = conn.execute(
                    "SELECT COUNT(*) FROM audit_log WHERE safe=0"
                ).fetchone()
        return count


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _hash_params(params: dict) -> str:
    """Short hash of params for audit trail (no PII in logs by default)."""
    serialised = json.dumps(params, sort_keys=True, default=str)
    return hashlib.sha256(serialised.encode()).hexdigest()[:12]
