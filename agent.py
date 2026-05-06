"""
Agent: CI/CD Pipeline Health Analyzer
Orchestrates all tools and runs multiple specialized Gemini AI passes:
  1. Security deep-dive
  2. Prioritized action plan
  3. Rewritten workflow snippet for the top issue
"""

import google.generativeai as genai
from rich.console import Console

from config import GEMINI_API_KEY, GEMINI_MODEL
from tools.github_fetcher import fetch_workflows
from tools.yaml_parser import parse_workflow
from tools.rule_engine import evaluate, calculate_score, get_category_scores
from tools.report_generator import print_terminal_report, generate_markdown_report

console = Console()


def run(repo_url: str) -> str:
    """
    Run the full analysis pipeline on a GitHub repository.

    Returns:
        Path to the generated Markdown report file
    """

    # Step 1 — Fetch workflow files
    console.print(f"\n[dim]→ Fetching workflows from[/dim] {repo_url}...")
    workflows_raw = fetch_workflows(repo_url)
    console.print(f"  [green]✓[/green] Found {len(workflows_raw)} workflow file(s): "
                  f"{', '.join(w['filename'] for w in workflows_raw)}")

    # Step 2 — Parse YAML
    console.print("[dim]→ Parsing workflow files...[/dim]")
    parsed_workflows = []
    for w in workflows_raw:
        parsed = parse_workflow(w["filename"], w["content"])
        parsed_workflows.append(parsed)
    console.print(f"  [green]✓[/green] Parsed {len(parsed_workflows)} workflow(s)")

    # Step 3 — Run rule engine
    console.print("[dim]→ Running rule engine (32 checks)...[/dim]")
    all_findings = []
    for pw in parsed_workflows:
        findings = evaluate(pw)
        all_findings.extend(findings)
    score = calculate_score(all_findings)
    category_scores = get_category_scores(all_findings)
    console.print(f"  [green]✓[/green] {len(all_findings)} finding(s) — overall score: {score}/100")

    # Step 4 — Multiple Gemini AI passes
    ai_results = {}
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(GEMINI_MODEL)

        # Combine all raw YAML for context
        combined_yaml = "\n\n---\n\n".join(
            f"# File: {w['filename']}\n{w['content']}" for w in workflows_raw
        )
        findings_text = _format_findings(all_findings)

        # Pass 1 — Security analysis
        console.print("[dim]→ AI Pass 1: Security deep-dive...[/dim]")
        ai_results["security"] = _ai_security_analysis(model, combined_yaml, all_findings)
        console.print("  [green]✓[/green] Security analysis complete")

        # Pass 2 — Prioritized action plan
        console.print("[dim]→ AI Pass 2: Prioritized action plan...[/dim]")
        ai_results["action_plan"] = _ai_action_plan(model, findings_text, score, category_scores)
        console.print("  [green]✓[/green] Action plan generated")

        # Pass 3 — Rewrite worst section
        console.print("[dim]→ AI Pass 3: Generating improved workflow snippet...[/dim]")
        ai_results["rewrite"] = _ai_rewrite_snippet(model, combined_yaml, all_findings)
        console.print("  [green]✓[/green] Improved snippet generated")

    else:
        console.print("  [yellow]⚠ GEMINI_API_KEY not set — skipping AI analysis[/yellow]")

    # Step 5 — Generate report
    console.print("[dim]→ Generating report...[/dim]")
    print_terminal_report(repo_url, workflows_raw, all_findings, score, category_scores, ai_results)
    report_path = generate_markdown_report(repo_url, workflows_raw, all_findings, score, category_scores, ai_results)
    console.print(f"  [green]✓[/green] Report saved: [bold]{report_path}[/bold]\n")

    return report_path


# ── Gemini AI Passes ─────────────────────────────────────────────────────────

def _ai_security_analysis(model, yaml_content: str, findings: list[dict]) -> str:
    """Deep security analysis of the raw workflow YAML."""
    security_findings = [f for f in findings if f["category"] == "Security"]
    findings_text = _format_findings(security_findings) or "No rule-based security issues found."

    prompt = f"""You are a DevSecOps security expert specializing in GitHub Actions supply chain security.

Analyze this CI/CD workflow YAML for security vulnerabilities:

{yaml_content[:3000]}

Rule-based findings already detected:
{findings_text}

Provide a security analysis covering:
1. **Supply chain risks** — action pinning, third-party dependencies
2. **Secret exposure risks** — how secrets are handled and scoped
3. **Privilege escalation risks** — permissions and token usage
4. **Injection vulnerabilities** — any user-controlled input in run: steps

Be specific to THIS workflow. Point to actual lines or steps where relevant.
Keep it under 250 words. Use markdown formatting."""

    try:
        return model.generate_content(prompt).text
    except Exception as e:
        return f"(Security analysis unavailable: {e})"


def _ai_action_plan(model, findings_text: str, score: int, category_scores: dict) -> str:
    """Generate a concrete, prioritized action plan."""
    scores_text = "\n".join(f"- {cat}: {s}/100" for cat, s in category_scores.items())

    prompt = f"""You are a senior DevOps engineer reviewing a pipeline health report.

Overall score: {score}/100

Category scores:
{scores_text}

All findings:
{findings_text}

Generate a concrete action plan with exactly 5 prioritized items.
Format each item as:
**[Priority N] Fix title** (effort: Low/Medium/High)
One sentence on what to do and why it matters most.

Order by: critical severity first, then highest impact, then easiest wins.
Be specific — name the actual job/step/file where relevant.
No fluff. Total response under 300 words."""

    try:
        return model.generate_content(prompt).text
    except Exception as e:
        return f"(Action plan unavailable: {e})"


def _ai_rewrite_snippet(model, yaml_content: str, findings: list[dict]) -> str:
    """Rewrite the worst part of the workflow to fix the top critical issues."""
    criticals = [f for f in findings if f["severity"] == "critical"]
    if not criticals:
        criticals = [f for f in findings if f["severity"] == "warning"]
    if not criticals:
        return "No critical issues to rewrite — your pipeline looks solid!"

    top_issues = criticals[:3]
    issues_text = "\n".join(f"- {f['rule_id']}: {f['detail']}" for f in top_issues)

    prompt = f"""You are a GitHub Actions expert. Below is a CI/CD workflow with issues.

Workflow:
{yaml_content[:2000]}

Top issues to fix:
{issues_text}

Provide a corrected YAML snippet that fixes these specific issues.
- Show only the relevant section (job or steps block), not the entire file
- Add inline comments explaining each fix
- Keep it concise and production-ready

Format your response as:
**What was changed and why** (2-3 sentences)

```yaml
# corrected snippet here
```"""

    try:
        return model.generate_content(prompt).text
    except Exception as e:
        return f"(Rewrite unavailable: {e})"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _format_findings(findings: list[dict]) -> str:
    if not findings:
        return "No issues found."
    return "\n".join(
        f"[{f['severity'].upper()}] {f['rule_id']} — {f['name']}: {f['detail']}"
        for f in findings
    )
