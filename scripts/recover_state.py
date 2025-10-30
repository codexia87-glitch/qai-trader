"""Recover project session from `.qai_state.json`.

Features:
- --show: print saved state
- --restore-checkpoints: attempt to inspect known checkpoint files (pytorch/json)
- --resume: re-run the last script recorded in the state (prompts unless --yes)
"""
from pathlib import Path
import sys
import json
import argparse
import subprocess
import os

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.utils.checkpoint_manager import load_state, save_state
from typing import Optional, List, Dict
import getpass
import datetime
import socket
import platform
import hmac
import hashlib


def _autoload_checkpoint(path: Path, meta: dict) -> object:
    """Attempt to autoload a PyTorch checkpoint using available model factories.

    Returns a Trainer instance on success or raises an ImportError/RuntimeError on failure.
    This function tries to infer the model type from metadata or filename.
    """
    # infer model hint from metadata first, then filename
    model_hint = None
    if meta and isinstance(meta, dict):
        model_hint = meta.get("model")
    if not model_hint:
        name = path.stem.lower()
        if "lstm" in name:
            model_hint = "lstm"

    if model_hint == "lstm":
        # Lazy import PyTorch, model factory and Trainer
        try:
            from src.ai.models import create_lstm_model
            from src.ai.pytorch_trainer import Trainer
        except Exception as e:
            raise ImportError(f"Cannot import model/trainer for autoload: {e}")

        try:
            import torch
            import torch.optim as optim
        except Exception as e:
            raise ImportError(f"PyTorch is required to autoload checkpoint: {e}")

        # create a model_factory with a default small configuration
        def model_factory():
            return create_lstm_model(input_size=1, hidden_size=32, num_layers=1, output_size=1)

        # attach an optimizer_factory so Trainer.load can restore optimizer state
        def optimizer_factory(params):
            return optim.Adam(params, lr=1e-3)

        setattr(model_factory, "optimizer_factory", optimizer_factory)

        # load
        trainer = Trainer.load(path, model_factory)
        return trainer

    raise RuntimeError(f"Unknown model hint for autoload: {model_hint}")


def verify_audit_log(key: str, path: Optional[Path] = None) -> (int, int, int, List[Dict[str, str]]):
    """Verify audit.log HMACs using the provided key.

    Returns a tuple (total, verified, failed, failures)
    where `failures` is a list of dicts with keys: line (int), reason (str), preview (str).
    """
    p = path or (project_root / "audit.log")
    total = verified = failed = 0
    failures: List[Dict[str, str]] = []
    if not p.exists():
        return (0, 0, 0, failures)
    try:
        with p.open("r", encoding="utf-8") as af:
            for i, line in enumerate(af, start=1):
                raw = line.rstrip("\n")
                sline = raw.strip()
                if not sline:
                    continue
                total += 1
                try:
                    entry = json.loads(sline)
                except Exception:
                    failed += 1
                    failures.append({"line": i, "reason": "INVALID JSON", "preview": sline[:200]})
                    continue
                sig = entry.pop("hmac", None)
                if not sig:
                    failed += 1
                    failures.append({"line": i, "reason": "MISSING_HMAC", "preview": json.dumps(entry)[:200]})
                    continue
                try:
                    msg = json.dumps(entry, sort_keys=True, ensure_ascii=False).encode("utf-8")
                    expected = hmac.new(key.encode("utf-8"), msg, hashlib.sha256).hexdigest()
                    if not hmac.compare_digest(expected, sig):
                        failed += 1
                        failures.append({"line": i, "reason": "HMAC_MISMATCH", "preview": json.dumps(entry)[:200]})
                    else:
                        verified += 1
                except Exception as e:
                    failed += 1
                    failures.append({"line": i, "reason": f"VERIFICATION_ERROR: {e}", "preview": json.dumps(entry)[:200]})
    except Exception:
        return (0, 0, 1, failures)
    return (total, verified, failed, failures)


def inspect_checkpoint(path: Path) -> None:
    print("-", path)
    if not path.exists():
        print("  -> MISSING")
        return
    suffix = path.suffix.lower()
    if suffix in (".pt", ".pth"):
        try:
            import torch

            data = torch.load(path, map_location="cpu")
            if isinstance(data, dict):
                keys = list(data.keys())
                print("  -> keys:", keys)
                if "epoch" in data:
                    print(f"  -> epoch: {data.get('epoch')}")
                if "training_stats" in data:
                    print(f"  -> training_stats: {data.get('training_stats')}")
            else:
                print("  -> loaded object of type:", type(data))
        except Exception as e:
            print("  -> cannot inspect (torch missing or load failed):", e)
    elif suffix == ".json":
        try:
            with path.open("r", encoding="utf-8") as f:
                j = json.load(f)
            print("  -> json keys:", list(j.keys()))
        except Exception as e:
            print("  -> failed to read json:", e)
    else:
        # try generic JSON
        try:
            with path.open("r", encoding="utf-8") as f:
                j = json.load(f)
            print("  -> json keys:", list(j.keys()))
        except Exception:
            print("  -> file exists (no special inspector). size=", path.stat().st_size)


def resume_script(state: dict, yes: bool = False) -> int:
    last = state.get("last_script")
    if not last:
        print("No last_script recorded in state.")
        return 1
    # resolve
    cand = Path(last)
    if not cand.is_absolute():
        cand = project_root / last
    if not cand.exists():
        print("Recorded last_script not found:", cand)
        return 1

    last_args = state.get("last_args") or {}
    cmd = [sys.executable, str(cand)]
    for k, v in last_args.items():
        flag = "--" + str(k).replace("_", "-")
        if isinstance(v, bool):
            if v:
                cmd.append(flag)
        elif v is None:
            continue
        else:
            cmd.append(flag)
            cmd.append(str(v))

    print("Will run:", " ".join(cmd))
    if not yes:
        ok = input("Run the command above? [y/N]: ").strip().lower() == "y"
        if not ok:
            print("Aborted by user.")
            return 2

    return subprocess.call(cmd, cwd=project_root)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--show", action="store_true")
    p.add_argument("--restore-checkpoints", action="store_true")
    p.add_argument("--auto-load", action="store_true", help="Attempt to automatically load PyTorch checkpoints (LSTM) when found")
    p.add_argument("--verify-only", action="store_true", help="Only verify audit.log HMACs and exit with 0 if all valid, 1 if any invalid")
    p.add_argument("--verbose", action="store_true", help="Verbose output for verification failures")
    p.add_argument("--resume", action="store_true", help="Re-run the last script recorded in the state")
    p.add_argument("--yes", action="store_true", help="Auto-confirm prompts when resuming")
    args = p.parse_args()

    state = load_state()

    # CI: verify-only mode -- run audit.log HMAC verification and exit with 0/1
    if args.verify_only:
        key = os.environ.get("QAI_HMAC_KEY")
        if not key:
            print("QAI_HMAC_KEY not set; cannot verify audit.log")
            sys.exit(1)
        total, verified, failed, failures = verify_audit_log(key)
        print(f"Audit verify summary: total={total}, verified={verified}, failed={failed}")
        if args.verbose and failures:
            for f in failures:
                print(f"[audit][line {f['line']}] {f['reason']} preview={f['preview']}")
        sys.exit(0 if failed == 0 else 1)

    # If the user requested a show or restore and an HMAC key is present,
    # perform an integrity check of the append-only audit.log file.
    if (args.show or args.restore_checkpoints) and os.environ.get("QAI_HMAC_KEY"):
        key = os.environ.get("QAI_HMAC_KEY")
        total, verified, failed, failures = verify_audit_log(key)
        if total == 0:
            print("No audit.log found to verify.")
        else:
            print("Verifying audit.log integrity using QAI_HMAC_KEY...")
            print(f"Audit verify summary: total={total}, verified={verified}, failed={failed}")
            if args.verbose and failures:
                for f in failures:
                    print(f"[audit][line {f['line']}] {f['reason']} preview={f['preview']}")

    if args.show:
        print(json.dumps(state, indent=2, ensure_ascii=False))

    if args.restore_checkpoints or args.auto_load:
        # If auto-load is requested and an HMAC key is present, verify audit.log first
        if args.auto_load and os.environ.get("QAI_HMAC_KEY"):
            key = os.environ.get("QAI_HMAC_KEY")
            total_v, verified_v, failed_v = verify_audit_log(key)
            if failed_v:
                red = "\033[91m"
                end = "\033[0m"
                print(f"{red}Audit integrity compromised — operation aborted{end}")
                sys.exit(3)

        cks = state.get("checkpoints", [])
        if not cks:
            print("No checkpoints recorded in state.")
        for ck in cks:
            pth = Path(ck.get("path"))
            if not pth.is_absolute():
                pth = project_root / pth
            print("Checkpoint:", ck.get("type"), "->", pth)
            inspect_checkpoint(pth)
            # Try autoload if requested and file looks like a PyTorch checkpoint
            if args.auto_load and pth.exists() and pth.suffix.lower() in (".pt", ".pth"):
                try:
                    trainer = _autoload_checkpoint(pth, ck.get("meta") or {})
                    print(f"Successfully auto-loaded Trainer from {pth}")
                    try:
                        print(f" trainer.epoch={trainer.epoch}, training_stats_keys={list(trainer.training_stats.keys())}")
                    except Exception:
                        pass
                except Exception as e:
                    print(f"Auto-load failed for {pth}: {e}")

    if args.resume:
        # Before resuming, if HMAC key is set verify audit.log; abort on failures
        if os.environ.get("QAI_HMAC_KEY"):
            key = os.environ.get("QAI_HMAC_KEY")
            total_v, verified_v, failed_v = verify_audit_log(key)
            if failed_v:
                red = "\033[91m"
                end = "\033[0m"
                print(f"{red}Audit integrity compromised — operation aborted{end}")
                sys.exit(4)

        # If last run had live trading enabled, ALWAYS require explicit confirmation
        # (ignore --yes for safety). Show a clear red security warning.
        last_args = state.get("last_args") or {}
        if last_args.get("live"):
            red = "\033[91m"
            end = "\033[0m"
            print(f"{red}SECURITY WARNING: The last recorded run had live trading enabled.{end}")
            print(f"{red}Resuming may send real orders to your broker and cause financial loss. Confirm manually to proceed.{end}")
            # Always prompt regardless of --yes
            ok = input("Type 'I UNDERSTAND' to proceed with resuming the live session: ").strip()
            if ok != "I UNDERSTAND":
                print("Resume aborted by user due to live mode (confirmation not given).")
                sys.exit(2)

            # Record audit entry: username, ts (UTC), and the checkpoint being restored (if any)
            try:
                st = load_state()
                username = None
                try:
                    username = getpass.getuser()
                except Exception:
                    username = (os.environ.get("USER") or os.environ.get("USERNAME") or "unknown")

                now = datetime.datetime.utcnow().isoformat() + "Z"
                # choose the last checkpoint entry if present
                last_ck = None
                cks = st.get("checkpoints") or []
                if cks:
                    last_ck = cks[-1]

                # gather host/platform/uid info for traceability
                try:
                    hostname = socket.gethostname()
                except Exception:
                    hostname = None
                try:
                    uid = os.getuid()
                except Exception:
                    # Windows or environments without getuid
                    uid = None
                try:
                    plat = platform.platform()
                except Exception:
                    plat = None

                audit_entry = {
                    "action": "resume_live",
                    "user": username,
                    "uid": uid,
                    "hostname": hostname,
                    "platform": plat,
                    "ts": now,
                    "restored_checkpoint": last_ck,
                }

                # compute HMAC signature over canonical JSON (sorted keys)
                hmac_key = os.environ.get("QAI_HMAC_KEY")
                sig = None
                if hmac_key:
                    try:
                        msg = json.dumps(audit_entry, sort_keys=True, ensure_ascii=False).encode("utf-8")
                        sig = hmac.new(hmac_key.encode("utf-8"), msg, hashlib.sha256).hexdigest()
                    except Exception as e:
                        print("Warning: failed to compute HMAC for audit entry:", e)
                        sig = None
                else:
                    print("Warning: QAI_HMAC_KEY not set; audit entries will not be HMAC-signed")

                # attach signature to the stored entry and to the append-only line
                signed_entry = dict(audit_entry)
                signed_entry["hmac"] = sig

                # save into .qai_state.json (include signature)
                st.setdefault("audit_log", []).append(signed_entry)
                save_state(st)
                print("Audit recorded to .qai_state.json")

                # Also append an audit line to project-root audit.log (append-only)
                try:
                    audit_log_path = project_root / "audit.log"
                    with audit_log_path.open("a", encoding="utf-8") as af:
                        af.write(json.dumps(signed_entry, ensure_ascii=False) + "\n")
                    print(f"Audit appended to {audit_log_path}")
                except Exception as e:
                    print("Warning: failed to append to audit.log:", e)
            except Exception as e:
                print("Warning: failed to record audit entry:", e)
        rc = resume_script(state, yes=args.yes)
        sys.exit(rc)


if __name__ == "__main__":
    main()
