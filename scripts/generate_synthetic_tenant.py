import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic inventory imports without real tenant data")
    parser.add_argument("--output", type=Path, default=Path("synthetic_inventory"))
    parser.add_argument("--count", type=int, default=25)
    args = parser.parse_args()
    if not 1 <= args.count <= 10000:
        parser.error("count must be between 1 and 10000")
    args.output.mkdir(parents=True, exist_ok=True)
    kinds = ["connector", "app", "plugin", "extension", "agent", "custom_gpt", "skill"]
    for platform in ["claude", "chatgpt", "copilot"]:
        rows = [{"external_id": f"synthetic-{platform}-{index:04}", "name": f"Synthetic {kinds[index % 7]} {index:04}", "kind": kinds[index % 7], "owner": f"owner-{index % 5}@example.test", "version": "1.0"} for index in range(args.count)]
        (args.output / f"inventory_{platform}.json").write_text(json.dumps(rows, indent=2))
    print(f"Generated three synthetic inventory files in {args.output}")


if __name__ == "__main__":
    main()