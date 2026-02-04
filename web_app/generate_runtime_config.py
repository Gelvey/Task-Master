from __future__ import annotations

import argparse
from pathlib import Path

from config_loader import write_runtime_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate runtime config JSON for the Task-Master web app."
    )
    parser.add_argument(
        "--output",
        default="public/runtime-config.json",
        help="Output path for the generated JSON file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base_dir = Path(__file__).resolve().parent
    output_path = base_dir / args.output
    write_runtime_config(base_dir, output_path)


if __name__ == "__main__":
    main()
