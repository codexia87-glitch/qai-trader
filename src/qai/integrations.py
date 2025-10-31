"""External integration utilities for QAI Trader."""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

try:
    import boto3  # type: ignore
except Exception:  # pragma: no cover
    boto3 = None

try:
    import pandas as pd  # type: ignore
except Exception:  # pragma: no cover
    pd = None

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None

from .logging_utils import append_signed_audit


class IntegrationsManager:
    """Handle dataset import/export and optional external hooks."""

    def __init__(
        self,
        *,
        audit_log: Optional[Path] = None,
        session_id: Optional[str] = None,
        hmac_key: Optional[str] = None,
        s3_client: Optional[Any] = None,
    ) -> None:
        self.audit_log = audit_log
        self.session_id = session_id
        self.hmac_key = hmac_key
        if s3_client is not None:
            self._s3_client = s3_client
        elif boto3 is not None:
            self._s3_client = boto3.client("s3")
        else:
            self._s3_client = None

    # ------------------------------------------------------------------
    # CSV helpers
    # ------------------------------------------------------------------
    def export_csv(self, rows: Sequence[Dict[str, Any]], path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames: List[str] = []
        for row in rows:
            for key in row.keys():
                if key not in fieldnames:
                    fieldnames.append(key)
        with path.open("w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames or ["value"], extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        self._audit("export_complete", {"format": "csv", "path": str(path)})
        return path

    def import_csv(self, path: Path) -> List[Dict[str, Any]]:
        path = Path(path)
        with path.open("r", newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            data = [dict(row) for row in reader]
        self._audit("import_complete", {"format": "csv", "path": str(path)})
        return data

    # ------------------------------------------------------------------
    # Parquet helpers
    # ------------------------------------------------------------------
    def export_parquet(self, rows: Sequence[Dict[str, Any]], path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if pd is not None:
            df = pd.DataFrame(list(rows))
            df.to_parquet(path, index=False)
        else:
            # Fallback to JSON content for environments without pandas/pyarrow
            path.write_text(json.dumps(list(rows), indent=2, ensure_ascii=False), encoding="utf-8")
        self._audit("export_complete", {"format": "parquet", "path": str(path)})
        return path

    def import_parquet(self, path: Path) -> List[Dict[str, Any]]:
        path = Path(path)
        if pd is not None:
            df = pd.read_parquet(path)
            data = df.to_dict(orient="records")
        else:
            data = json.loads(path.read_text(encoding="utf-8"))
        self._audit("import_complete", {"format": "parquet", "path": str(path)})
        return data

    # ------------------------------------------------------------------
    # S3 helpers
    # ------------------------------------------------------------------
    def upload_s3(self, local_path: Path, bucket: str, key: str) -> None:
        if self._s3_client is None:
            raise RuntimeError("boto3 is not available; cannot upload to S3")
        self._s3_client.upload_file(str(local_path), bucket, key)
        self._audit("export_complete", {"format": "s3", "bucket": bucket, "key": key})

    def download_s3(self, bucket: str, key: str, local_path: Path) -> Path:
        if self._s3_client is None:
            raise RuntimeError("boto3 is not available; cannot download from S3")
        local_path = Path(local_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        self._s3_client.download_file(bucket, key, str(local_path))
        self._audit("import_complete", {"format": "s3", "bucket": bucket, "key": key})
        return local_path

    # ------------------------------------------------------------------
    # CI hook helper
    # ------------------------------------------------------------------
    def trigger_ci_hook(self, payload: Dict[str, Any], *, url: Optional[str] = None, env_var: str = "CI_HOOK_URL") -> None:
        target = url or os.environ.get(env_var)
        if not target:
            raise ValueError("No CI hook URL provided")
        if requests is not None:
            requests.post(target, json=payload, timeout=10)
        self._audit("ci_hook_triggered", {"url": target, "payload": payload})

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _audit(self, event: str, extra: Dict[str, Any]) -> None:
        if self.audit_log is None:
            return
        payload = {
            "module": "qai.integrations",
            "event": event,
            "session_id": self.session_id,
        }
        payload.update(extra)
        append_signed_audit(payload, audit_log=self.audit_log, session_id=self.session_id, hmac_key=self.hmac_key)
