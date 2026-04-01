"""
Report generator.
Aggregates results from all strategies and produces a summary report
with visualizations.
"""

import json
import os
from datetime import datetime
from dataclasses import asdict
from typing import Optional

from strategies.base import StrategyResult


class ReportGenerator:
    """Generate evaluation reports from strategy results."""

    def __init__(self, output_dir: str = "results"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate(
        self,
        results: list[StrategyResult],
        config: dict,
        target_model: str,
    ) -> str:
        """
        Generate a complete evaluation report.

        Args:
            results: List of StrategyResult from all strategies.
            config: The experiment config dict.
            target_model: Name of the target model evaluated.

        Returns:
            Path to the generated report file.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_dir = os.path.join(self.output_dir, f"eval_{timestamp}")
        os.makedirs(report_dir, exist_ok=True)

        # Save raw results as JSON
        raw_path = os.path.join(report_dir, "raw_results.json")
        self._save_raw(results, raw_path)

        # Generate summary statistics
        summary = self._compute_summary(results)

        # Generate markdown report
        report_path = os.path.join(report_dir, "report.md")
        self._write_markdown_report(
            report_path, summary, results, target_model, timestamp
        )

        # Generate charts
        self._generate_charts(report_dir, summary, results)

        # Save conversation logs
        logs_path = os.path.join(report_dir, "conversations.json")
        self._save_conversations(results, logs_path)

        return report_path

    def _compute_summary(self, results: list[StrategyResult]) -> dict:
        """Compute aggregate statistics."""
        by_strategy = {}
        by_category = {}

        for r in results:
            # Per strategy
            if r.strategy_name not in by_strategy:
                by_strategy[r.strategy_name] = {"total": 0, "success": 0, "scores": [], "rounds": []}
            s = by_strategy[r.strategy_name]
            s["total"] += 1
            s["success"] += int(r.success)
            s["scores"].append(r.final_score)
            s["rounds"].append(r.rounds_taken)

            # Per category
            if r.category_id not in by_category:
                by_category[r.category_id] = {"total": 0, "success": 0, "scores": []}
            c = by_category[r.category_id]
            c["total"] += 1
            c["success"] += int(r.success)
            c["scores"].append(r.final_score)

        # Compute rates
        for key in by_strategy:
            s = by_strategy[key]
            s["asr"] = s["success"] / max(s["total"], 1)
            s["avg_score"] = sum(s["scores"]) / max(len(s["scores"]), 1)
            s["avg_rounds"] = sum(s["rounds"]) / max(len(s["rounds"]), 1)

        for key in by_category:
            c = by_category[key]
            c["asr"] = c["success"] / max(c["total"], 1)
            c["avg_score"] = sum(c["scores"]) / max(len(c["scores"]), 1)

        overall_asr = sum(r.success for r in results) / max(len(results), 1)

        return {
            "overall_asr": overall_asr,
            "total_tests": len(results),
            "total_success": sum(r.success for r in results),
            "by_strategy": by_strategy,
            "by_category": by_category,
        }

    def _write_markdown_report(
        self,
        path: str,
        summary: dict,
        results: list[StrategyResult],
        target_model: str,
        timestamp: str,
    ):
        """Write a human-readable markdown report."""
        lines = [
            f"# LLM Robustness Evaluation Report",
            f"",
            f"- **Target model**: {target_model}",
            f"- **Date**: {timestamp}",
            f"- **Total test cases**: {summary['total_tests']}",
            f"- **Overall ASR**: {summary['overall_asr']:.1%}",
            f"",
            f"## Results by strategy",
            f"",
            f"| Strategy | Tests | ASR | Avg Score | Avg Rounds |",
            f"|----------|-------|-----|-----------|------------|",
        ]

        for name, s in summary["by_strategy"].items():
            lines.append(
                f"| {name} | {s['total']} | {s['asr']:.1%} | "
                f"{s['avg_score']:.1f} | {s['avg_rounds']:.1f} |"
            )

        lines += [
            f"",
            f"## Results by category",
            f"",
            f"| Category | Tests | ASR | Avg Score |",
            f"|----------|-------|-----|-----------|",
        ]

        for name, c in summary["by_category"].items():
            lines.append(
                f"| {name} | {c['total']} | {c['asr']:.1%} | {c['avg_score']:.1f} |"
            )

        lines += [
            f"",
            f"## Detailed results",
            f"",
        ]

        for r in results:
            status = "SUCCESS" if r.success else "FAILED"
            extra = ""
            if r.metadata.get("iterations_used"):
                extra = f", iterations={r.metadata['iterations_used']}"
                if r.metadata.get("lessons_accumulated"):
                    extra += f", lessons={r.metadata['lessons_accumulated']}"
            lines.append(
                f"- **{r.strategy_name}** × {r.category_id}: "
                f"{status} (score={r.final_score}, rounds={r.rounds_taken}{extra})"
            )

            # Include post-mortem summaries for iterative strategies
            if r.metadata.get("post_mortems"):
                for pm in r.metadata["post_mortems"]:
                    lines.append(
                        f"  - Iteration {pm['iteration']} post-mortem: "
                        f"{pm.get('failure_reason', 'N/A')[:100]}"
                    )
                    if pm.get("lessons"):
                        for lesson in pm["lessons"][:3]:
                            lines.append(f"    - Lesson: {lesson[:80]}")
                    if pm.get("suggested_angle"):
                        lines.append(f"    - Next angle: {pm['suggested_angle'][:80]}")

        with open(path, "w") as f:
            f.write("\n".join(lines))

    def _generate_charts(
        self, report_dir: str, summary: dict, results: list[StrategyResult]
    ):
        """Generate matplotlib charts."""
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            return  # Skip if matplotlib not available

        # Chart 1: ASR by strategy
        strategies = list(summary["by_strategy"].keys())
        asr_values = [summary["by_strategy"][s]["asr"] * 100 for s in strategies]

        fig, ax = plt.subplots(figsize=(8, 5))
        bars = ax.bar(strategies, asr_values, color=["#D85A30", "#1D9E75", "#534AB7"])
        ax.set_ylabel("Attack Success Rate (%)")
        ax.set_title("ASR by Strategy")
        ax.set_ylim(0, 100)
        for bar, val in zip(bars, asr_values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 2,
                f"{val:.0f}%",
                ha="center",
                fontsize=11,
            )
        plt.tight_layout()
        plt.savefig(os.path.join(report_dir, "asr_by_strategy.png"), dpi=150)
        plt.close()

        # Chart 2: Score distribution
        fig, ax = plt.subplots(figsize=(8, 5))
        for name in strategies:
            scores = summary["by_strategy"][name]["scores"]
            ax.hist(scores, bins=range(1, 12), alpha=0.6, label=name)
        ax.set_xlabel("Judge Score")
        ax.set_ylabel("Count")
        ax.set_title("Score Distribution by Strategy")
        ax.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(report_dir, "score_distribution.png"), dpi=150)
        plt.close()

    def _save_raw(self, results: list[StrategyResult], path: str):
        """Save raw results as JSON."""
        data = []
        for r in results:
            d = {
                "strategy": r.strategy_name,
                "category": r.category_id,
                "success": r.success,
                "final_score": r.final_score,
                "rounds_taken": r.rounds_taken,
                "max_rounds": r.max_rounds,
                "metadata": r.metadata,
            }
            data.append(d)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def _save_conversations(self, results: list[StrategyResult], path: str):
        """Save full conversation logs."""
        logs = []
        for r in results:
            entry = {
                "strategy": r.strategy_name,
                "category": r.category_id,
                "success": r.success,
                "rounds": [
                    {
                        "round": rd.round_num,
                        "phase": getattr(rd, 'phase', ''),
                        "prompt": rd.prompt_sent,
                        "response": rd.target_response[:500],
                        "score": rd.judge_score,
                        "reasoning": rd.judge_reasoning,
                    }
                    for rd in r.rounds
                ],
            }
            logs.append(entry)
        with open(path, "w") as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)
