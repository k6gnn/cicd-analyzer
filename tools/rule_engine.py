"""
Tool: Rule Engine
Evaluates parsed workflow data against 32 defined best-practice rules across
5 categories: Security, Performance, Reliability, Best Practices, Maintainability.
"""

import json
import re
import os

RULES_PATH = os.path.join(os.path.dirname(__file__), "..", "rules", "pipeline_rules.json")

# Secret detection patterns
SECRET_PATTERNS = [
    r'(?i)(password|passwd|pwd)\s*[:=]\s*["\']?[A-Za-z0-9+/=_\-]{8,}',
    r'(?i)(secret|token|api_key|apikey|auth_key)\s*[:=]\s*["\']?[A-Za-z0-9+/=_\-!@#$%]{8,}',
    r'(?i)(AWS_SECRET|PRIVATE_KEY|ACCESS_KEY|CLIENT_SECRET)\s*[:=]\s*["\']?[A-Za-z0-9+/=_\-]{8,}',
    r'(?i)bearer\s+[A-Za-z0-9+/=_\-]{20,}',
    r'-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----',
]

# GitHub context injection patterns (dangerous interpolation in run: steps)
INJECTION_PATTERNS = [
    r'\$\{\{.*github\.event\.(issue|pull_request|comment|review|head_commit)\.(title|body|name|message|description)',
    r'\$\{\{.*github\.event\.inputs\.',
    r'\$\{\{.*github\.head_ref',
]

CACHE_KEYWORDS = [
    "actions/cache", "cache: pip", "cache: npm", "cache: maven",
    "cache: gradle", "cache: yarn", "cache: pnpm", "cache: nuget",
]
RETRY_KEYWORDS = ["nick-fields/retry", "max-attempts", "retry-on"]
NOTIFY_KEYWORDS = ["slack", "discord", "teams", "sendgrid", "notify", "notification", "email", "pagerduty", "opsgenie"]
DEPLOY_KEYWORDS = ["deploy", "release", "publish", "push to", "helm upgrade", "kubectl apply", "terraform apply", "serverless deploy"]
HEALTH_CHECK_KEYWORDS = ["health", "smoke", "ping", "curl", "wget", "verify", "validate"]
ROLLBACK_KEYWORDS = ["rollback", "revert", "restore", "undo", "previous version"]
OLD_ACTION_VERSIONS = ["@v1", "@v2"]
THIRD_PARTY_NAMESPACES = ["actions/", "github/", "docker/"]


def load_rules() -> list[dict]:
    with open(RULES_PATH, "r") as f:
        return json.load(f)


def evaluate(parsed_workflow: dict) -> list[dict]:
    """
    Evaluate a parsed workflow against all 32 rules.

    Args:
        parsed_workflow: Output from yaml_parser.parse_workflow()

    Returns:
        List of finding dicts: {rule_id, name, severity, category, detail, fix}
    """
    rules = load_rules()
    rule_map = {r["id"]: r for r in rules}
    findings = []

    content = parsed_workflow["raw_content"]
    jobs = parsed_workflow["jobs"]
    raw = parsed_workflow["raw"]
    triggers = parsed_workflow["triggers"]

    content_lower = content.lower()
    all_steps = [step for job in jobs for step in job["steps"]]
    all_uses = [s["uses"] for s in all_steps if s["uses"]]
    all_run = [s["run"] for s in all_steps if s["run"]]

    # ── SECURITY ────────────────────────────────────────────────────────────

    # SEC001 — Hardcoded secrets
    for pattern in SECRET_PATTERNS:
        match = re.search(pattern, content)
        if match:
            findings.append(_finding(rule_map["SEC001"],
                f"Potential secret detected matching pattern: '{match.group(0)[:60]}...'"))
            break

    # SEC002 — Unpinned actions (@main/@master/@HEAD)
    unpinned = [u for u in all_uses if any(u.endswith(b) for b in ["@main", "@master", "@HEAD", "@latest"])]
    if unpinned:
        findings.append(_finding(rule_map["SEC002"],
            f"Actions pinned to mutable branch refs: {', '.join(set(unpinned))}"))

    # SEC003 — No permissions block
    if "permissions" not in raw:
        findings.append(_finding(rule_map["SEC003"],
            "No 'permissions:' block found at workflow level — defaults to write-all"))

    # SEC004 — pull_request_target trigger
    if "pull_request_target" in triggers:
        findings.append(_finding(rule_map["SEC004"],
            "Workflow is triggered by pull_request_target — high risk of secret exposure from forked PRs"))

    # SEC005 — Script injection via GitHub context
    for run_script in all_run:
        for pattern in INJECTION_PATTERNS:
            if re.search(pattern, run_script):
                findings.append(_finding(rule_map["SEC005"],
                    "GitHub event context value interpolated directly into run: step — injection risk"))
                break

    # SEC006 — Write permissions on PR workflow
    if "pull_request" in triggers:
        perms = raw.get("permissions", {})
        if isinstance(perms, dict):
            if perms.get("contents") == "write" or perms.get("pull-requests") == "write":
                findings.append(_finding(rule_map["SEC006"],
                    "Write permissions granted on a pull_request-triggered workflow"))

    # SEC007 — Third-party actions not SHA-pinned
    third_party_not_sha = []
    for u in all_uses:
        is_first_party = any(u.startswith(ns) for ns in THIRD_PARTY_NAMESPACES)
        if not is_first_party and u and "@" in u:
            ref = u.split("@")[1]
            # SHA is 40 hex chars; version tags are not
            if not re.match(r'^[0-9a-f]{40}$', ref, re.IGNORECASE):
                third_party_not_sha.append(u)
    if third_party_not_sha:
        findings.append(_finding(rule_map["SEC007"],
            f"Third-party actions not SHA-pinned: {', '.join(set(third_party_not_sha[:3]))}"))

    # SEC008 — Secrets in job-level env
    for job in jobs:
        job_env = job.get("env", {}) or {}
        for val in job_env.values():
            if isinstance(val, str) and "secrets." in val:
                findings.append(_finding(rule_map["SEC008"],
                    f"Secret passed at job level in '{job['id']}' — accessible to all steps in the job"))
                break

    # ── PERFORMANCE ─────────────────────────────────────────────────────────

    # PERF001 — No caching
    has_cache = any(kw.lower() in content_lower for kw in CACHE_KEYWORDS)
    if not has_cache:
        findings.append(_finding(rule_map["PERF001"],
            "No dependency caching detected — installs run from scratch on every pipeline run"))

    # PERF002 — No parallel jobs
    if len(jobs) > 1:
        jobs_with_needs = [j for j in jobs if j["needs"]]
        if len(jobs_with_needs) == len(jobs):
            findings.append(_finding(rule_map["PERF002"],
                "All jobs have 'needs' dependencies — no parallel execution possible"))

    # PERF003 — Redundant checkouts
    for job in jobs:
        checkout_count = sum(1 for s in job["steps"] if "actions/checkout" in s["uses"])
        if checkout_count > 1:
            findings.append(_finding(rule_map["PERF003"],
                f"Job '{job['id']}' checks out the repository {checkout_count} times"))
            break

    # PERF004 — No matrix strategy
    has_matrix = any(job.get("strategy", {}) for job in jobs)
    test_jobs = [j for j in jobs if "test" in j["id"].lower() or "test" in j["name"].lower()]
    if test_jobs and not has_matrix:
        findings.append(_finding(rule_map["PERF004"],
            "Test jobs detected but no matrix strategy used — missing multi-version or cross-platform coverage"))

    # PERF005 — Artifact upload without compression
    for step in all_steps:
        if "upload-artifact" in step["uses"]:
            with_config = step.get("with", {}) or {}
            if "compression-level" not in with_config:
                findings.append(_finding(rule_map["PERF005"],
                    "actions/upload-artifact used without compression-level setting"))
                break

    # PERF006 — No shallow clone
    for step in all_steps:
        if "actions/checkout" in step["uses"]:
            with_config = step.get("with", {}) or {}
            if "fetch-depth" not in with_config:
                findings.append(_finding(rule_map["PERF006"],
                    "actions/checkout without fetch-depth: 1 — full git history fetched unnecessarily"))
                break

    # ── RELIABILITY ─────────────────────────────────────────────────────────

    # REL001 — Missing timeouts
    no_timeout = [j["id"] for j in jobs if j["timeout"] is None]
    if no_timeout:
        findings.append(_finding(rule_map["REL001"],
            f"Jobs missing timeout-minutes: {', '.join(no_timeout)} — can run indefinitely"))

    # REL002 — No retry logic
    has_retry = any(kw.lower() in content_lower for kw in RETRY_KEYWORDS)
    if not has_retry:
        findings.append(_finding(rule_map["REL002"],
            "No retry logic found — transient failures will immediately fail the pipeline"))

    # REL003 — No failure notification
    has_notify = any(kw.lower() in content_lower for kw in NOTIFY_KEYWORDS)
    if not has_notify:
        findings.append(_finding(rule_map["REL003"],
            "No failure notification step detected — team won't be alerted on pipeline failures"))

    # REL004 — Deploy without health check
    has_deploy = any(kw.lower() in content_lower for kw in DEPLOY_KEYWORDS)
    has_health = any(kw.lower() in content_lower for kw in HEALTH_CHECK_KEYWORDS)
    if has_deploy and not has_health:
        findings.append(_finding(rule_map["REL004"],
            "Deployment steps detected but no post-deploy health check or smoke test found"))

    # REL005 — continue-on-error on critical steps
    critical_step_keywords = ["test", "build", "deploy", "publish", "release"]
    for step in all_steps:
        if step.get("continue_on_error") is True:
            name_lower = step["name"].lower()
            run_lower = step["run"].lower()
            if any(kw in name_lower or kw in run_lower for kw in critical_step_keywords):
                findings.append(_finding(rule_map["REL005"],
                    f"continue-on-error: true set on critical step: '{step['name']}'"))
                break

    # REL006 — Deploy job without branch condition
    for job in jobs:
        job_content = str(job.get("raw", "")).lower()
        if any(kw in job_content for kw in DEPLOY_KEYWORDS):
            if_condition = job["raw"].get("if", "")
            if not if_condition:
                findings.append(_finding(rule_map["REL006"],
                    f"Deploy job '{job['id']}' has no branch/environment condition — may deploy from any branch"))
                break

    # REL007 — No rollback
    has_rollback = any(kw.lower() in content_lower for kw in ROLLBACK_KEYWORDS)
    if has_deploy and not has_rollback:
        findings.append(_finding(rule_map["REL007"],
            "Deployment detected but no rollback mechanism found — no recovery path on failed deploy"))

    # ── BEST PRACTICES ───────────────────────────────────────────────────────

    # BP001 — No concurrency control
    if "concurrency" not in raw:
        findings.append(_finding(rule_map["BP001"],
            "No 'concurrency:' block — multiple simultaneous runs can conflict or waste resources"))

    # BP002 — Hardcoded env values
    hardcoded_patterns = [
        r'https?://[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}',  # URLs
        r'(?i)(region|zone|cluster|namespace)\s*[:=]\s*["\']?[a-z][a-z0-9\-]+',
    ]
    for pattern in hardcoded_patterns:
        if re.search(pattern, content):
            findings.append(_finding(rule_map["BP002"],
                "Hardcoded URLs or environment-specific values detected in workflow"))
            break

    # BP003 — Missing workflow name
    if not parsed_workflow["name"] or parsed_workflow["name"] == "Unnamed workflow":
        findings.append(_finding(rule_map["BP003"],
            "Workflow has no 'name:' field — shows as filename in GitHub UI"))

    # BP004 — Missing job names
    unnamed = [j["id"] for j in jobs if j["name"] == j["id"]]
    if unnamed:
        findings.append(_finding(rule_map["BP004"],
            f"Jobs without descriptive names: {', '.join(unnamed)}"))

    # BP005 — No GitHub environment on deploy jobs
    for job in jobs:
        job_content = str(job.get("raw", "")).lower()
        if any(kw in job_content for kw in DEPLOY_KEYWORDS):
            if not job["raw"].get("environment"):
                findings.append(_finding(rule_map["BP005"],
                    f"Deploy job '{job['id']}' has no 'environment:' field — missing approval gates and audit trail"))
                break

    # BP006 — Trigger on all branches
    raw_on = raw.get("on", raw.get(True, {}))
    if isinstance(raw_on, dict):
        push_config = raw_on.get("push", {})
        if isinstance(push_config, dict) and not push_config.get("branches"):
            findings.append(_finding(rule_map["BP006"],
                "Push trigger has no branch filter — workflow runs on every branch push"))
        elif push_config is None or push_config == {}:
            findings.append(_finding(rule_map["BP006"],
                "Push trigger has no branch filter — workflow runs on every branch push"))

    # BP007 — Steps without names
    unnamed_steps = sum(1 for s in all_steps if s["name"] == "unnamed step" or not s["name"])
    if unnamed_steps >= 3:
        findings.append(_finding(rule_map["BP007"],
            f"{unnamed_steps} steps have no descriptive name — makes pipeline logs hard to read"))

    # BP008 — Old action versions
    old_actions = [u for u in all_uses if any(u.endswith(v) for v in OLD_ACTION_VERSIONS)]
    if old_actions:
        findings.append(_finding(rule_map["BP008"],
            f"Actions using old major versions: {', '.join(set(old_actions))}"))

    # ── MAINTAINABILITY ──────────────────────────────────────────────────────

    # MAINT001 — Duplicated runner configs
    runners = [j["runs_on"] for j in jobs if j["runs_on"]]
    if len(jobs) > 2 and len(set(runners)) == 1:
        findings.append(_finding(rule_map["MAINT001"],
            f"All {len(jobs)} jobs use identical runner '{runners[0]}' — consider a reusable workflow"))

    # MAINT002 — Long inline scripts
    for step in all_steps:
        if step["run"] and step["run"].count("\n") > 10:
            findings.append(_finding(rule_map["MAINT002"],
                f"Step '{step['name']}' has a {step['run'].count(chr(10))+1}-line inline script — extract to a script file"))
            break

    # MAINT003 — No comments in workflow
    if "#" not in content:
        findings.append(_finding(rule_map["MAINT003"],
            "No YAML comments found — workflow has no inline documentation"))

    # MAINT004 — Mixed runner types
    runner_types = set(j["runs_on"] for j in jobs if j["runs_on"])
    if len(runner_types) > 2:
        findings.append(_finding(rule_map["MAINT004"],
            f"Jobs use {len(runner_types)} different runner types: {', '.join(runner_types)} — intentional?"))

    return findings


def calculate_score(findings: list[dict]) -> int:
    """Calculate a 0-100 health score. Criticals are heavily penalized."""
    deductions = {"critical": 20, "warning": 7, "info": 2}
    total = sum(deductions.get(f["severity"], 0) for f in findings)
    return max(0, 100 - total)


def get_category_scores(findings: list[dict]) -> dict:
    """Return per-category scores for detailed reporting."""
    categories = ["Security", "Performance", "Reliability", "Best Practices", "Maintainability"]
    category_deductions = {"critical": 20, "warning": 7, "info": 2}
    scores = {}
    for cat in categories:
        cat_findings = [f for f in findings if f["category"] == cat]
        deducted = sum(category_deductions.get(f["severity"], 0) for f in cat_findings)
        scores[cat] = max(0, 100 - deducted)
    return scores


def _finding(rule: dict, detail: str) -> dict:
    return {
        "rule_id": rule["id"],
        "name": rule["name"],
        "severity": rule["severity"],
        "category": rule["category"],
        "detail": detail,
        "fix": rule["fix"],
    }
