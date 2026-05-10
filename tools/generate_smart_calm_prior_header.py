#!/usr/bin/env python3
"""Generate the ESP32 Smart-CALM prior header from the trained JSON prior."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "results" / "smart_calm_prior.json"
DEFAULT_OUTPUT = ROOT / "firmware" / "esp32_smart_calm" / "include" / "smart_calm_prior.hpp"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Smart-CALM prior header")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    entries = payload.get("q_values", [])
    lines = [
        "#pragma once",
        "",
        "#include <array>",
        "",
        "#include \"smart_calm_types.hpp\"",
        "",
        "namespace smart_calm {",
        "",
        f"inline constexpr std::array<PriorEntry, {len(entries)}> kSmartCalmPrior = {{",
        "    {{",
    ]
    for item in entries:
        state = int(item["state"])
        action = int(item["action"])
        value = float(item["value"])
        lines.append(f"        {{{state}, {action}, {value:.7f}f}},")
    lines.extend([
        "    }}",
        "};",
        "",
        "}  // namespace smart_calm",
        "",
    ])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()

