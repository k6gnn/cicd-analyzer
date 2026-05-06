"""
Tool: YAML Parser
Parses raw GitHub Actions workflow YAML into structured Python data.
"""

import yaml


def parse_workflow(filename: str, content: str) -> dict:
    """
    Parse a raw YAML workflow string into a structured dict.

    Args:
        filename: Name of the workflow file
        content: Raw YAML string

    Returns:
        Structured dict with normalized workflow data
    """
    try:
        raw = yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise ValueError(f"Failed to parse {filename}: {e}")

    if not isinstance(raw, dict):
        raise ValueError(f"{filename} does not contain a valid workflow definition")

    jobs = raw.get("jobs", {}) or {}

    parsed = {
        "filename": filename,
        "name": raw.get("name", "Unnamed workflow"),
        "triggers": _extract_triggers(raw),
        "jobs": _extract_jobs(jobs),
        "env": raw.get("env", {}),
        "raw": raw,
        "raw_content": content,
    }

    return parsed


def _extract_triggers(raw: dict) -> list[str]:
    """Extract trigger event names from 'on' key."""
    on = raw.get("on", raw.get(True, {}))  # PyYAML parses 'on' as True
    if isinstance(on, str):
        return [on]
    if isinstance(on, list):
        return on
    if isinstance(on, dict):
        return list(on.keys())
    return []


def _extract_jobs(jobs: dict) -> list[dict]:
    """Extract normalized job data."""
    result = []
    for job_id, job in jobs.items():
        if not isinstance(job, dict):
            continue

        steps = job.get("steps", []) or []
        result.append({
            "id": job_id,
            "name": job.get("name", job_id),
            "runs_on": job.get("runs-on", ""),
            "timeout": job.get("timeout-minutes"),
            "needs": job.get("needs", []),
            "env": job.get("env", {}),
            "steps": _extract_steps(steps),
            "strategy": job.get("strategy", {}),
            "concurrency": job.get("concurrency"),
            "raw": job,
        })
    return result


def _extract_steps(steps: list) -> list[dict]:
    """Extract normalized step data."""
    result = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        result.append({
            "name": step.get("name", "unnamed step"),
            "uses": step.get("uses", ""),
            "run": step.get("run", ""),
            "env": step.get("env", {}),
            "with": step.get("with", {}),
            "continue_on_error": step.get("continue-on-error", False),
            "raw": step,
        })
    return result
