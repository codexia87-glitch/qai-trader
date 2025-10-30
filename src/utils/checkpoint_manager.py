"""Project-level checkpoint manager.

Creates and maintains a small `.qai_state.json` file at the project root
that tracks high-level project metadata (current sprint, completed tasks,
last commit hash, modified files, last script run and recorded checkpoints).

This module offers lightweight, dependency-free helpers intended for use by
CLI scripts in the repository. It uses git when available to collect commit
and working-tree status information, but will function without git.
"""
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
import subprocess
from typing import Any, Dict, List, Optional


DEFAULT_FILENAME = ".qai_state.json"


def _project_root() -> Path:
    # src/utils/checkpoint_manager.py -> project root = ../../..
    return Path(__file__).resolve().parents[2]


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _git_info(project_root: Path) -> Dict[str, Any]:
    info: Dict[str, Any] = {"last_commit": None, "modified_files": []}
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=project_root, capture_output=True, text=True)
        if r.returncode == 0:
            info["last_commit"] = r.stdout.strip()
    except Exception:
        # git not available
        return info

    try:
        s = subprocess.run(["git", "status", "--porcelain"], cwd=project_root, capture_output=True, text=True)
        if s.returncode == 0 and s.stdout:
            lines = [l.strip() for l in s.stdout.splitlines() if l.strip()]
            paths: List[str] = []
            for ln in lines:
                # format: XY <path>
                parts = ln.split(maxsplit=1)
                if len(parts) == 2:
                    paths.append(parts[1])
            info["modified_files"] = paths
    except Exception:
        # ignore
        pass

    return info


def default_state() -> Dict[str, Any]:
    return {
        "version": 1,
        "project": _project_root().name,
        "sprint": None,
        "completed_tasks": [],
        "last_commit": None,
        "modified_files": [],
        "last_script": None,
        "last_args": None,
        "last_run_ts": None,
        "checkpoints": [],
        "notes": None,
    }


def _state_path(path: Optional[Path]) -> Path:
    if path is None:
        return _project_root() / DEFAULT_FILENAME
    return path


def load_state(path: Optional[Path] = None) -> Dict[str, Any]:
    p = _state_path(path)
    if not p.exists():
        return default_state()
    try:
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data
    except Exception:
        # corrupt or unreadable -> return a fresh default but keep a backup
        try:
            backup = p.with_suffix(p.suffix + ".broken")
            p.rename(backup)
        except Exception:
            pass
        return default_state()


def save_state(state: Dict[str, Any], path: Optional[Path] = None) -> Path:
    p = _state_path(path)
    try:
        with p.open("w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        return p
    except Exception as e:
        raise


def record_script_run(
    script: str,
    args: Optional[Dict[str, Any]] = None,
    checkpoints: Optional[List[Dict[str, Any]]] = None,
    sprint: Optional[int] = None,
    completed_tasks: Optional[List[str]] = None,
    state_path: Optional[Path] = None,
) -> Path:
    """Update the project state with a script run and optional checkpoints.

    `script` should be a path relative to the project root (or an absolute path).
    `checkpoints` is a list of dicts with at least `path` and optional `type` and `meta`.
    The function updates git info if available and writes `.qai_state.json`.
    Returns the path written.
    """
    project_root = _project_root()
    st = load_state(state_path)

    # update simple fields
    st["last_script"] = str(script)
    st["last_args"] = args or {}
    st["last_run_ts"] = _now_iso()
    if sprint is not None:
        st["sprint"] = sprint
    if completed_tasks is not None:
        # merge unique
        existing = list(dict.fromkeys(st.get("completed_tasks", []) + completed_tasks))
        st["completed_tasks"] = existing

    # git info
    gi = _git_info(project_root)
    st["last_commit"] = gi.get("last_commit")
    st["modified_files"] = gi.get("modified_files", [])

    # store checkpoints
    if checkpoints:
        for ck in checkpoints:
            entry = dict(ck)
            entry.setdefault("ts", _now_iso())
            st.setdefault("checkpoints", []).append(entry)

    # persist
    return save_state(st, state_path)


def add_checkpoint(path: str, typ: Optional[str] = None, meta: Optional[Dict[str, Any]] = None, state_path: Optional[Path] = None) -> Path:
    st = load_state(state_path)
    entry = {"path": path, "type": typ or "unknown", "meta": meta or {}, "ts": _now_iso()}
    st.setdefault("checkpoints", []).append(entry)
    return save_state(st, state_path)


if __name__ == "__main__":
    # small CLI for quick inspection
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--show", action="store_true")
    p.add_argument("--state", type=str, default=None, help="Path to state file (optional)")
    args = p.parse_args()
    path = Path(args.state) if args.state else None
    state = load_state(path)
    print(json.dumps(state, indent=2, ensure_ascii=False))
