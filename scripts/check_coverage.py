"""Fail when a module of the integration has 95% test coverage or less.

The Silver rule test-coverage asks for more than 95% in every module, not just
in total. Reads coverage.json written by pytest --cov-report=json.
"""
from __future__ import annotations

import json
import sys

MINIMUM = 95.0

files = json.load(open("coverage.json", encoding="utf-8"))["files"]
failed = False
for path, data in sorted(files.items()):
    percent = data["summary"]["percent_covered"]
    print(f"{percent:6.1f}%  {path}")
    if percent <= MINIMUM:
        print(f"::error file={path}::coverage {percent:.1f}% is not above {MINIMUM:.0f}%")
        failed = True
sys.exit(1 if failed else 0)
