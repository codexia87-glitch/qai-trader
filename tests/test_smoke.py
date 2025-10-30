"""
Smoke test: ensure package stubs import cleanly.

This test only imports packages under `src/` to validate packaging and basic syntax.
"""
import importlib


def test_import_all_submodules():
    # Import each submodule to ensure no syntax errors exist
    modules = [
        "src.data",
        "src.features",
        "src.events",
        "src.ai",
        "src.quant",
        "src.fundamentals",
        "src.bridge",
        "src.bridge.mt5_bridge",
        "src.risk",
        "src.utils",
    ]

    for m in modules:
        importlib.import_module(m)

    assert True
