"""
Tool: Report Generator
Produces a scored Markdown report and Rich terminal output.
Handles per-category scores and multiple AI analysis sections.
"""

import os
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich import box
from config import OUTPUT_DIR

console = Console()

SEVERITY_COLORS = {"critical": "bold red", "warning": "bold yellow", "info": "cyan"}
SEVERITY_ICONS = {"critical": "🔴", "warning": "🟡", "info": "🔵"}


def print_terminal_report(repo_url: str, workflows: list[dict], all_findings: list[dict],
                           score: int, category_scores: dict, ai_results: dict):
    """Print full color-coded report to terminal."""
    console.print()
    console.rule("[bold blue]CI/CD Pipeline Health Analyzer[/bold blue]")
    console.print(f"  [dim]Repository:[/dim]  {repo_url}")
    console.print(f"  [dim]Workflows:[/dim]   {', '.join(w['filename'] for w in workflows)}")
    console.print(f"  [dim]Generated:[/dim]   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    console.print()

    # Overall score
    color = "green" if score >= 80 else "yellow" if score >= 50 else "red"
    label = "✅ Healthy" if score >= 80 else "⚠️  Needs Work" if score >= 50 else "❌ Critical"
    console.print(f"  Overall Health Score: [{color}]{score}/100 — {label}[/{color}]", style="bold")
    console.print()

    # Category scores
    cat_table = Table(box=box.SIMPLE, show_header=True, header_style="bold dim")
    cat_table.add_column("Category", style="bold")
    cat_table.add_column("Score", justify="right")
    cat_table.add_column("Bar", width=20)
    for cat, s in category_scores.items():
        c = "green" if s >= 80 else "yellow" if s >= 50 else "red"
        bar = "█" * (s // 5) + "░" * (20 - s // 5)
        cat_table.add_row(cat, f"[{c}]{s}/100[/{c}]", f"[{c}]{bar}[/{c}]")
    console.print(cat_table)
    console.print()

    # Findings table
    if all_findings:
        table = Table(box=box.ROUNDED, show_header=True, header_style="bold white on dark_blue")
        table.add_column("Sev", width=10)
        table.add_column("ID", width=9)
        table.add_column("Finding", width=52)
        table.add_column("Category", width=16)

        for f in sorted(all_findings, key=lambda x: {"critical": 0, "warning": 1, "info": 2}[x["severity"]]):
            icon = SEVERITY_ICONS[f["severity"]]
            color = SEVERITY_COLORS[f["severity"]]
            table.add_row(
                f"[{color}]{icon} {f['severity'].upper()}[/{color}]",
                f["rule_id"],
                f["detail"][:52],
                f["category"],
            )
        console.print(table)
    else:
        console.print("  [bold green]✅ No issues found — pipeline is healthy![/bold green]")

    console.print()

    # AI sections
    if ai_results.get("security"):
        console.rule("[bold red]🔐 AI Security Analysis[/bold red]")
        console.print(ai_results["security"])
        console.print()

    if ai_results.get("action_plan"):
        console.rule("[bold yellow]📋 Prioritized Action Plan[/bold yellow]")
        console.print(ai_results["action_plan"])
        console.print()

    if ai_results.get("rewrite"):
        console.rule("[bold green]✏️  Improved Workflow Snippet[/bold green]")
        console.print(ai_results["rewrite"])
        console.print()


def generate_markdown_report(repo_url: str, workflows: list[dict], all_findings: list[dict],
                              score: int, category_scores: dict, ai_results: dict) -> str:
    """Generate and save a Markdown report. Returns file path."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    repo_slug = repo_url.rstrip("/").split("/")[-1]
    filepath = os.path.join(OUTPUT_DIR, f"{repo_slug}_{timestamp}.md")

    criticals = [f for f in all_findings if f["severity"] == "critical"]
    warnings  = [f for f in all_findings if f["severity"] == "warning"]
    infos     = [f for f in all_findings if f["severity"] == "info"]
    score_label = "✅ Healthy" if score >= 80 else "⚠️ Needs Improvement" if score >= 50 else "❌ Critical Issues"

    lines = [
        "# CI/CD Pipeline Health Report",
        "",
        f"**Repository:** {repo_url}  ",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
        f"**Workflows analyzed:** {', '.join(w['filename'] for w in workflows)}  ",
        "",
        f"## Overall Score: {score}/100 — {score_label}",
        "",
        "## Category Scores",
        "",
        "| Category | Score |",
        "|----------|-------|",
    ]
    for cat, s in category_scores.items():
        emoji = "✅" if s >= 80 else "⚠️" if s >= 50 else "❌"
        lines.append(f"| {cat} | {emoji} {s}/100 |")

    lines += [
        "",
        "## Finding Summary",
        "",
        "| Severity | Count |",
        "|----------|-------|",
        f"| 🔴 Critical | {len(criticals)} |",
        f"| 🟡 Warning  | {len(warnings)} |",
        f"| 🔵 Info     | {len(infos)} |",
        "",
    ]

    for severity, label, items in [
        ("critical", "🔴 Critical Issues", criticals),
        ("warning",  "🟡 Warnings",        warnings),
        ("info",     "🔵 Info",            infos),
    ]:
        if items:
            lines.append(f"## {label}")
            lines.append("")
            for f in items:
                lines.append(f"### {f['rule_id']} — {f['name']}")
                lines.append(f"**Category:** {f['category']}  ")
                lines.append(f"**Finding:** {f['detail']}  ")
                lines.append(f"**Fix:** {f['fix']}")
                lines.append("")

    if ai_results.get("security"):
        lines += ["## 🔐 AI Security Analysis", "", ai_results["security"], ""]

    if ai_results.get("action_plan"):
        lines += ["## 📋 Prioritized Action Plan", "", ai_results["action_plan"], ""]

    if ai_results.get("rewrite"):
        lines += ["## ✏️ Improved Workflow Snippet", "", ai_results["rewrite"], ""]

    lines += ["---", "*Generated by CI/CD Pipeline Health Analyzer*"]

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return filepath
