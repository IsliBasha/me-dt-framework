#!/usr/bin/env python3
"""
CLI injector — triggers attack scenarios via the running FastAPI server.

Usage:
  python attacks/inject_attack.py --scenario water_hammer --delay 0
  python attacks/inject_attack.py --scenario cross_domain_cascade --delay 5
"""

import argparse
import sys
import urllib.request
import json

import config
from models.attack_scenarios import SCENARIO_DEFINITIONS


def main():
    parser = argparse.ArgumentParser(description="ME-DT Attack Injector CLI")
    parser.add_argument("--scenario", required=True, choices=list(SCENARIO_DEFINITIONS.keys()))
    parser.add_argument("--delay", type=int, default=0, help="Ticks before attack starts")
    parser.add_argument(
        "--host",
        default=f"http://localhost:{config.SERVER_PORT}",
        help=f"Server URL (default: http://localhost:{config.SERVER_PORT})",
    )
    args = parser.parse_args()

    scenario = SCENARIO_DEFINITIONS[args.scenario]
    print(f"[Injector] Injecting '{scenario.display_name}' with delay={args.delay} ticks")
    print(f"[Injector] Severity: {scenario.severity}  |  Simulator: {scenario.simulator}")

    payload = json.dumps({"scenario": args.scenario, "delay": args.delay}).encode()
    req = urllib.request.Request(
        f"{args.host}/api/inject-attack",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read().decode()
            print(f"[Injector] Response: {body}")
    except Exception as e:
        print(f"[Injector] ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
