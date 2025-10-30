"""Tests for versioned signal schema validation (Sprint 2).

These tests exercise the v1 schema validation logic.
"""
import json
import re

from src.bridge.signal_schema import (
    validate_signal_dict,
    loads,
    dumps,
    SignalV1,
    CURRENT_VERSION,
)


def test_validate_valid_signal():
    data = {
        "version": "1",
        "symbol": "EURUSD",
        "side": "BUY",
        "volume": 0.1,
        "sl_pts": 30,
        "tp_pts": 60,
    }
    sig = validate_signal_dict(data)
    assert isinstance(sig, SignalV1)
    assert sig.version == CURRENT_VERSION
    assert sig.symbol == "EURUSD"
    assert sig.sl_pts == 30
    assert sig.tp_pts == 60


def test_validate_missing_required():
    data = {"version": "1", "symbol": "EURUSD", "side": "BUY"}
    try:
        validate_signal_dict(data)
        assert False, "expected validation error for missing volume"
    except ValueError as e:
        assert "volume" in str(e)


def test_validate_invalid_side():
    data = {"symbol": "EURUSD", "side": "LONG", "volume": 0.1}
    try:
        validate_signal_dict(data)
        assert False, "expected validation error for invalid side"
    except ValueError as e:
        assert "side" in str(e)


def test_loads_and_dumps_roundtrip():
    data = {"symbol": "EURUSD", "side": "SELL", "volume": 0.05}
    sig = validate_signal_dict(data)
    s = dumps(sig)
    # Should be valid JSON and contain version
    obj = json.loads(s)
    assert obj.get("version") == "1"
    # loads should parse back
    sig2 = loads(s)
    assert isinstance(sig2, SignalV1)
    assert sig2.symbol == "EURUSD"


def test_invalid_types():
    bad = {"symbol": "EURUSD", "side": "BUY", "volume": "not_a_number"}
    try:
        validate_signal_dict(bad)
        assert False, "expected validation error for volume type"
    except ValueError as e:
        assert "volume" in str(e)
