"""
LLM Robustness Evaluation Framework
Main entry point.

Usage:
    python main.py                          # Use default config
    python main.py --config configs/custom.yaml
    python main.py --strategy crescendo     # Run single strategy
    python main.py --dry-run                # Validate config only
"""

import argparse
import sys
import yaml
from pathlib import Path

from utils.rich_compat import Console

from core.orchestrator import Orchestrator
from utils.report import ReportGenerator

console = Console()


def load_config(path: str) -> dict:
    """Load and validate YAML config."""
    config_path = Path(path)
    if not config_path.exists():
        console.print(f"[red]Config file not found: {path}[/red]")
        sys.exit(1)

    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Validate required fields
    required = ["target", "attacker", "judge", "strategies", "test_categories", "scoring"]
    missing = [k for k in required if k not in config]
    if missing:
        console.print(f"[red]Missing config fields: {', '.join(missing)}[/red]")
        sys.exit(1)

    return config


def check_ollama(config: dict) -> bool:
    """Check Ollama connectivity and model availability."""
    import requests

    base_url = config["target"].get("base_url", "http://localhost:11434")
    console.print(f"Checking Ollama at {base_url}...")

    # Check connectivity
    try:
        resp = requests.get(f"{base_url}/api/tags", timeout=5)
        resp.raise_for_status()
    except Exception as e:
        console.print(f"[red]Cannot connect to Ollama: {e}[/red]")
        console.print("Make sure Ollama is running: ollama serve")
        return False

    available = [m["name"] for m in resp.json().get("models", [])]
    console.print(f"Available models: {available}")

    # Check each required model
    all_ok = True
    for role in ["target", "attacker", "judge"]:
        model = config[role]["model"]
        # Ollama model names may or may not have :latest suffix
        found = any(model in m or m.startswith(model.split(":")[0]) for m in available)
        status = "[green]OK[/green]" if found else "[red]MISSING[/red]"
        console.print(f"  {role}: {model} — {status}")
        if not found:
            console.print(f"    → Run: ollama pull {model}")
            all_ok = False

    return all_ok


def main():
    parser = argparse.ArgumentParser(
        description="LLM Robustness Evaluation Framework"
    )
    parser.add_argument(
        "--config",
        default="configs/default.yaml",
        help="Path to experiment config (default: configs/default.yaml)",
    )
    parser.add_argument(
        "--strategy",
        choices=["crescendo", "many_shot", "art_prompt", "iterative_crescendo", "hybrid"],
        help="Run only a specific strategy",
    )
    parser.add_argument(
        "--category",
        help="Run only a specific test category (by ID)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate config and print plan without executing",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check Ollama connectivity and model availability",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Override output directory",
    )
    args = parser.parse_args()

    # Load config
    config = load_config(args.config)

    # Apply CLI filters
    if args.strategy:
        # Filter to the requested strategy and force-enable it
        config["strategies"] = [
            s for s in config["strategies"] if s["name"] == args.strategy
        ]
        if not config["strategies"]:
            console.print(f"[red]Strategy '{args.strategy}' not found in config.[/red]")
            sys.exit(1)
        # Force-enable the selected strategy (even if disabled in config)
        for s in config["strategies"]:
            s["enabled"] = True

    if args.category:
        config["test_categories"] = [
            c for c in config["test_categories"] if c["id"] == args.category
        ]
        if not config["test_categories"]:
            console.print(f"[red]Category '{args.category}' not found in config.[/red]")
            sys.exit(1)

    if args.output_dir:
        config.setdefault("output", {})["results_dir"] = args.output_dir

    # Health check
    if args.check:
        check_ollama(config)
        return

    # Dry run: just print plan
    if args.dry_run:
        strategies = [s["name"] for s in config["strategies"] if s.get("enabled", True)]
        categories = [c["id"] for c in config["test_categories"]]
        console.print("[bold]Dry run — execution plan:[/bold]")
        console.print(f"  Target: {config['target']['model']}")
        console.print(f"  Strategies: {strategies}")
        console.print(f"  Categories: {categories}")
        console.print(f"  Total tasks: {len(strategies) * len(categories)}")
        return

    # Run evaluation
    orchestrator = Orchestrator(config)
    results = orchestrator.run()

    # Generate report
    output_dir = config.get("output", {}).get("results_dir", "results")
    reporter = ReportGenerator(output_dir)
    report_path = reporter.generate(
        results=results,
        config=config,
        target_model=config["target"]["model"],
    )

    console.print(f"\n[bold green]Report saved to: {report_path}[/bold green]")


if __name__ == "__main__":
    main()
