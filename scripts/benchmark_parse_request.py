"""Benchmark `parse_request()` with and without validation.

Usage: run from repo root with the repo `.venv` active, e.g.:

    & .\.venv\Scripts\python.exe scripts\benchmark_parse_request.py

This script runs a baseline (no validator), then runs with a simple in-Python
validator enabled, for 1k iterations and then increases to ~10k in steps.
"""
from __future__ import annotations
import time
from typing import Any, Dict

from OmniFlowCentral.shared.request_contract import parse_request


class FakeReq:
    def __init__(self, params: Dict[str, Any] | None = None, body: Dict[str, Any] | None = None):
        self.params = params or {}
        self._body = body or {}

    def get_json(self):
        return self._body


def simple_validator(contract: Dict[str, Any]) -> bool:
    """A CPU-only validator that performs a few deterministic checks.

    Keep this intentionally small but realistic: check `tool` shape and
    iterate some payload keys to simulate validation work.
    """
    tool = contract.get("tool")
    if not isinstance(tool, str):
        return False
    if len(tool) == 0:
        return False

    payload = contract.get("payload", {}) or {}
    # iterate and do small ops to simulate cost
    s = 0
    for k, v in payload.items():
        s += len(str(k)) + (0 if v is None else 1)
    return s >= 0


def bench(iterations: int, validate: bool, req_factory) -> float:
    # warmup
    for _ in range(5):
        contract = parse_request(req_factory())
        if validate:
            simple_validator(contract)

    t0 = time.perf_counter()
    for _ in range(iterations):
        contract = parse_request(req_factory())
        if validate:
            simple_validator(contract)
    t1 = time.perf_counter()
    total_ms = (t1 - t0) * 1000.0
    avg_ms = total_ms / iterations
    return avg_ms


def run_all():
    print("Benchmark parse_request() — baseline and validator-enabled runs")

    # request factory that simulates typical small JSON body
    def req_factory():
        return FakeReq(params={}, body={"tool": "echo", "a": 1, "b": "x", "c": True})

    steps = []
    # baseline: no validator, 1k
    steps.append((1000, False))
    # with validator: 1k
    steps.append((1000, True))
    # ramp up with validator enabled
    for n in (2000, 5000, 10000):
        steps.append((n, True))

    results = []
    for iterations, validate in steps:
        avg = bench(iterations, validate, req_factory)
        results.append((iterations, validate, avg))
        mode = "validator ON" if validate else "validator OFF"
        print(f"{iterations:6d} iters — {mode:12s} — avg = {avg:.4f} ms")

    print("\nSummary:")
    for iters, validate, avg in results:
        print(f"{iters:6d} | {'ON' if validate else 'OFF':3s} | {avg:.4f} ms")


if __name__ == "__main__":
    run_all()
