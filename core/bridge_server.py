"""
FastAPI Bridge Server for MT5 EA Integration
==============================================

This server runs on Mac (0.0.0.0:8443) and provides:
- /health: health check endpoint
- /next: get next trading signal from queue
- /feedback: (optional) receive trade execution feedback from EA

Authentication:
- LAN token-only: If client IP is in TOKEN_ONLY_NETS and sends valid
  X-QAI-Token header, allow without HMAC.
- HMAC: For all other clients, require X-QAI-Token, X-QAI-TS, and
  X-QAI-Sig headers with valid HMAC signature.

Usage:
    env QAI_TOKEN=xxx QAI_HMAC_SECRET=yyy \\
        python -m uvicorn core.bridge_server:app --host 0.0.0.0 --port 8443
"""
from __future__ import annotations

import os
import hmac
import hashlib
import time
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from ipaddress import ip_address, ip_network, IPv4Address, IPv6Address

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# ============================================================================
# Configuration
# ============================================================================

# Get credentials from environment
QAI_TOKEN = os.getenv("QAI_TOKEN", "")
QAI_HMAC_SECRET = os.getenv("QAI_HMAC_SECRET", "")

if not QAI_TOKEN:
    logger.warning("QAI_TOKEN not set - authentication will fail!")
if not QAI_HMAC_SECRET:
    logger.warning("QAI_HMAC_SECRET not set - HMAC authentication will fail!")

# Token-only authentication for these subnets (LAN)
TOKEN_ONLY_NETS = [
    "127.0.0.0/8",      # Localhost
    "192.168.0.0/24",   # Common home network
    "192.168.1.0/24",   # Common home network
    "10.0.0.0/8",       # Private network
    "172.16.0.0/12",    # Private network
]

# Anti-replay: reject requests with timestamps older than this
MAX_TS_DRIFT_SECONDS = 300  # 5 minutes

# Signal queue directory (resolve to absolute path at runtime)
def get_signal_queue_dir() -> Path:
    """Get signal queue directory path."""
    sig_dir = os.getenv("SIGNAL_QUEUE_DIR", "example_signals")
    if os.path.isabs(sig_dir):
        return Path(sig_dir)
    return Path.cwd() / sig_dir

# Recent timestamps cache for anti-replay (simple in-memory cache)
# In production, use Redis or similar
recent_timestamps: Dict[str, float] = {}
MAX_TIMESTAMP_CACHE = 10000

# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="QAI Trader Bridge",
    description="Bridge server for MT5 EA integration",
    version="1.0.0"
)


# ============================================================================
# Helper Functions
# ============================================================================

def _get_client_ip(request: Request) -> str:
    """Extract client IP from request, considering X-Forwarded-For."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the first IP in the chain
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _is_lan_ip(ip_str: str) -> bool:
    """Check if IP is in TOKEN_ONLY_NETS (LAN whitelist)."""
    try:
        client_ip = ip_address(ip_str)
        for net_str in TOKEN_ONLY_NETS:
            if client_ip in ip_network(net_str):
                return True
        return False
    except ValueError:
        return False


def _verify_hmac(token: str, timestamp: str, signature: str, body: bytes = b"") -> bool:
    """Verify HMAC signature.
    
    Expected signature format: HMAC-SHA256(secret, token + "|" + ts + "|" + body)
    """
    if not QAI_HMAC_SECRET:
        logger.error("HMAC secret not configured")
        return False
    
    # Construct message: token|ts|body
    message = f"{token}|{timestamp}|".encode("utf-8") + body
    
    # Compute expected signature
    expected = hmac.new(
        QAI_HMAC_SECRET.encode("utf-8"),
        message,
        hashlib.sha256
    ).hexdigest()
    
    # Constant-time comparison
    return hmac.compare_digest(signature, expected)


def _check_timestamp_replay(timestamp: str, signature: str) -> bool:
    """Check if timestamp has been used before (anti-replay).
    
    Returns True if valid (not replayed), False if replayed.
    """
    global recent_timestamps
    
    # Parse timestamp
    try:
        ts_float = float(timestamp)
    except ValueError:
        return False
    
    # Check if too old or in future
    now = time.time()
    if abs(now - ts_float) > MAX_TS_DRIFT_SECONDS:
        logger.warning(f"Timestamp drift too large: {ts_float} vs {now}")
        return False
    
    # Check if signature already used
    cache_key = f"{timestamp}:{signature}"
    if cache_key in recent_timestamps:
        logger.warning(f"Replay detected: {cache_key}")
        return False
    
    # Add to cache
    recent_timestamps[cache_key] = ts_float
    
    # Cleanup old entries (simple LRU)
    if len(recent_timestamps) > MAX_TIMESTAMP_CACHE:
        # Remove oldest 20%
        sorted_items = sorted(recent_timestamps.items(), key=lambda x: x[1])
        to_remove = len(sorted_items) // 5
        for key, _ in sorted_items[:to_remove]:
            del recent_timestamps[key]
    
    return True


async def _require_auth(request: Request) -> None:
    """Authenticate request using token-only or HMAC.
    
    Raises HTTPException if authentication fails.
    """
    client_ip = _get_client_ip(request)
    is_lan = _is_lan_ip(client_ip)
    
    # Get headers
    token = request.headers.get("X-QAI-Token", "")
    timestamp = request.headers.get("X-QAI-TS", "")
    signature = request.headers.get("X-QAI-Sig", "")
    
    # Check token
    if not token:
        logger.error(f"Missing token from {client_ip}")
        raise HTTPException(status_code=401, detail="missing_token")
    
    if token != QAI_TOKEN:
        logger.error(f"Invalid token from {client_ip}: {token[:10]}...")
        raise HTTPException(status_code=403, detail="invalid_token")
    
    # LAN token-only mode
    if is_lan:
        logger.info(f"LAN authentication OK for {client_ip} (token-only)")
        return
    
    # Non-LAN: require HMAC
    if not timestamp or not signature:
        logger.error(f"Missing HMAC headers from {client_ip}")
        raise HTTPException(
            status_code=401, 
            detail="missing_hmac_headers"
        )
    
    # Check timestamp replay
    if not _check_timestamp_replay(timestamp, signature):
        raise HTTPException(
            status_code=409,
            detail="timestamp_replay_or_drift"
        )
    
    # Verify HMAC
    body = await request.body()
    if not _verify_hmac(token, timestamp, signature, body):
        logger.error(f"Invalid HMAC signature from {client_ip}")
        raise HTTPException(status_code=403, detail="invalid_signature")
    
    logger.info(f"HMAC authentication OK for {client_ip}")


def _get_next_signal() -> Optional[Dict[str, Any]]:
    """Get next signal from queue directory.
    
    Looks for .sig.json files in signal queue dir, reads the oldest one,
    and moves it to archived/ subdirectory.
    
    Returns signal dict or None if queue is empty.
    """
    queue_dir = get_signal_queue_dir()
    logger.debug(f"Looking for signals in: {queue_dir}")
    logger.debug(f"Queue dir exists: {queue_dir.exists()}")
    
    if not queue_dir.exists():
        logger.warning(f"Queue directory does not exist: {queue_dir}")
        queue_dir.mkdir(parents=True, exist_ok=True)
        return None
    
    # Find all .sig.json files
    signal_files = sorted(queue_dir.glob("*.sig.json"))
    logger.debug(f"Found {len(signal_files)} .sig.json files")
    
    # Also check .sig files (legacy text format)
    sig_files = sorted(queue_dir.glob("*.sig"))
    logger.debug(f"Found {len(sig_files)} .sig files")
    
    all_files = signal_files + sig_files
    if not all_files:
        logger.debug("No signal files found")
        return None
    
    # Take oldest file
    signal_file = all_files[0]
    
    try:
        # Read signal
        if signal_file.suffix == ".json":
            with open(signal_file, "r") as f:
                signal_data = json.load(f)
        else:
            # Parse legacy .sig format
            signal_data = _parse_legacy_sig(signal_file)
        
        # Archive the file
        archive_dir = queue_dir / "archived"
        archive_dir.mkdir(exist_ok=True)
        archived_path = archive_dir / signal_file.name
        
        # Handle duplicate names
        counter = 1
        while archived_path.exists():
            stem = signal_file.stem
            archived_path = archive_dir / f"{stem}_{counter}{signal_file.suffix}"
            counter += 1
        
        signal_file.rename(archived_path)
        logger.info(f"Processed signal: {signal_file.name} -> archived")
        
        return signal_data
    
    except Exception as e:
        logger.error(f"Error reading signal {signal_file}: {e}")
        # Move to archived with error suffix
        archive_dir = queue_dir / "archived"
        archive_dir.mkdir(exist_ok=True)
        error_path = archive_dir / f"ERROR_{signal_file.name}"
        signal_file.rename(error_path)
        return None


def _parse_legacy_sig(file_path: Path) -> Dict[str, Any]:
    """Parse legacy .sig text format to dict."""
    data = {}
    with open(file_path, "r") as f:
        for line in f:
            line = line.strip()
            if "=" in line:
                key, value = line.split("=", 1)
                data[key.strip()] = value.strip()
    
    # Convert to standard format
    return {
        "version": "1",
        "symbol": data.get("symbol", ""),
        "side": data.get("side", ""),
        "volume": float(data.get("volume", 0)),
        "price": float(data["price"]) if data.get("price") else None,
        "sl_pts": int(data["sl_pts"]) if data.get("sl_pts") else None,
        "tp_pts": int(data["tp_pts"]) if data.get("tp_pts") else None,
        "ts": data.get("ts", ""),
    }


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint - no authentication required."""
    return {
        "status": "ok",
        "service": "qai-bridge",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "queue_dir": str(get_signal_queue_dir().resolve()),
        "token_configured": bool(QAI_TOKEN),
        "hmac_configured": bool(QAI_HMAC_SECRET),
    }


@app.get("/next")
async def get_next_signal(request: Request):
    """Get next trading signal from queue.
    
    Returns:
        - 200 with signal data if available
        - 200 with {"status": "empty"} if queue is empty
        - 401/403 if authentication fails
    """
    # Authenticate
    await _require_auth(request)
    
    # Get next signal
    signal = _get_next_signal()
    
    if signal is None:
        return {
            "status": "empty",
            "message": "No signals in queue",
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    return {
        "status": "ok",
        "signal": signal,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/feedback")
async def receive_feedback(request: Request):
    """Receive trade execution feedback from EA.
    
    Expected payload:
        {
            "signal_id": "...",
            "status": "executed|failed",
            "order_ticket": 123456,
            "execution_price": 1.2345,
            "message": "...",
            "timestamp": "..."
        }
    """
    # Authenticate
    await _require_auth(request)
    
    # Parse body
    try:
        feedback = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"invalid_json: {e}")
    
    # Log feedback (in production, store to database)
    logger.info(f"Feedback received: {json.dumps(feedback)}")
    
    # TODO: Store feedback to database or queue for processing
    
    return {
        "status": "ok",
        "message": "Feedback received",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom exception handler for better error messages."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "detail": exc.detail,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


# ============================================================================
# Startup/Shutdown
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Log startup information."""
    logger.info("=" * 60)
    logger.info("QAI Trader Bridge Server Starting")
    logger.info("=" * 60)
    logger.info(f"Token configured: {bool(QAI_TOKEN)}")
    logger.info(f"HMAC secret configured: {bool(QAI_HMAC_SECRET)}")
    logger.info(f"Signal queue directory: {get_signal_queue_dir()}")
    logger.info(f"Token-only networks: {TOKEN_ONLY_NETS}")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Log shutdown information."""
    logger.info("QAI Trader Bridge Server Shutting Down")
