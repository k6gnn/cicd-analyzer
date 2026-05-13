# Practical Task — Journal
## Step 3 Submission | Due: 15 May 2025
**Project: CI/CD Pipeline Health Analyzer**

---

## 1. Testing Process Description

Testing was performed in parallel with implementation — each tool was tested as soon as it was written, not after the full system was complete. This approach caught issues early, particularly around YAML edge cases and GitHub API error handling.

The testing strategy has three layers:

**Unit tests** — each tool is tested in complete isolation. External dependencies (GitHub API, Gemini API) are replaced with mocks so tests run offline, instantly, and deterministically. There are 20 unit tests across 3 test files using `pytest` and `unittest.mock`.

**Sample workflow testing** — two real YAML files (`good_pipeline.yml` and `bad_pipeline.yml`) are included in `sample_workflows/` and used as fixtures in the rule engine tests. This ensures rules fire correctly on realistic input, not just minimal synthetic data.

**Manual end-to-end testing** — the full pipeline was run against a real GitHub repository (`k6gnn/grade-management`) to verify the complete flow from URL input to Markdown report output, including all three Gemini AI passes.

Tests are run with:
```bash
pytest tests/ -v
```

All 20 tests pass in under 1 second.

---

## 2. Test Scenarios

### `tests/test_github_fetcher.py` — 6 tests

| Test | What It Checks | Expected Result |
|------|---------------|-----------------|
| `test_parse_valid_url` | URL parser extracts owner and repo correctly | `owner=octocat`, `repo=Hello-World` |
| `test_parse_url_with_trailing_slash` | Trailing slash in URL is handled | Same result as without slash |
| `test_parse_invalid_url_raises` | URL with no repo name raises an error | `ValueError` raised |
| `test_fetch_workflows_success` | Successful API response returns workflow list | List with 1 item, correct filename |
| `test_fetch_workflows_404_raises` | Repository not found raises correct error | `FileNotFoundError` raised |
| `test_fetch_workflows_rate_limit_raises` | GitHub 403 response raises correct error | `PermissionError` raised |

### `tests/test_yaml_parser.py` — 6 tests

| Test | What It Checks | Expected Result |
|------|---------------|-----------------|
| `test_parse_valid_workflow` | Full workflow parses correctly | Name, job count, timeout extracted |
| `test_parse_extracts_steps` | Steps are extracted with correct fields | 2 steps, correct `uses` value |
| `test_parse_minimal_workflow` | Workflow with minimal fields parses without error | 1 job, `timeout=None` |
| `test_parse_triggers` | Trigger events are correctly extracted | `push` in triggers list |
| `test_parse_invalid_yaml_raises` | Malformed YAML raises error | `ValueError` raised |
| `test_parse_empty_raises` | YAML that parses to null raises error | `ValueError` raised |

### `tests/test_rule_engine.py` — 8 tests

| Test | What It Checks | Expected Result |
|------|---------------|-----------------|
| `test_detects_unpinned_actions` | SEC002 fires on `@main`/`@master` refs | `SEC002` in findings |
| `test_detects_missing_timeout` | REL001 fires when no `timeout-minutes` set | `REL001` in findings |
| `test_detects_missing_permissions` | SEC003 fires when no `permissions` block | `SEC003` in findings |
| `test_detects_missing_cache` | PERF001 fires when no cache step present | `PERF001` in findings |
| `test_good_pipeline_scores_higher` | Good pipeline scores better than bad pipeline | `good_score > bad_score` |
| `test_score_between_0_and_100` | Score is always within valid range | `0 <= score <= 100` |
| `test_good_pipeline_no_critical` | Good pipeline has zero critical findings | `len(criticals) == 0` |
| `test_findings_have_required_keys` | Every finding has all required fields | `rule_id`, `severity`, `fix`, `detail` present |

---

## 3. Deployment Preparation

The system is designed to run locally as a command-line tool with minimal setup. Any developer with Python 3.11+ can run it in under 2 minutes.

### Requirements
- Python 3.11 or higher
- A free Gemini API key from [aistudio.google.com](https://aistudio.google.com)
- A GitHub Personal Access Token (optional — only needed for private repos or to avoid rate limits)

### Installation Steps

```bash
# 1. Clone the repository
git clone https://github.com/k6gnn/cicd-analyzer
cd cicd-analyzer

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment variables
cp .env.example .env
# Open .env and add your API keys
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes (for AI features) | Free key from aistudio.google.com — enables all 3 AI analysis passes |
| `GITHUB_TOKEN` | No | GitHub Personal Access Token — needed for private repos, increases API rate limits |

If `GEMINI_API_KEY` is not set, the tool still runs and produces a full rule-based report — only the AI sections are skipped.

### Running the Tool

```bash
# Analyze any public GitHub repository
python main.py https://github.com/owner/repo

# Run interactively (prompts for URL)
python main.py

# Run tests
pytest tests/ -v
```

### Dependencies (`requirements.txt`)

```
google-generativeai==0.8.3
PyYAML==6.0.2
requests==2.32.3
python-dotenv==1.0.1
rich==13.9.4
pytest==8.3.4
```

---

## 4. Data Conversion and Porting

The system transforms data through 6 distinct format changes as it passes between components. Each stage changes the structure, type, or level of abstraction of the data.

### Stage 1 — URL string → GitHub API JSON
**Input:** Plain string `"https://github.com/owner/repo"`  
**Tool:** `github_fetcher.py`  
**Process:** URL is parsed to extract owner and repo name. An HTTP GET request is made to the GitHub REST API, which returns a JSON array of file objects.  
**Output:** Python list of dicts `[{name, download_url, size, ...}]`

### Stage 2 — GitHub API JSON → Raw YAML strings
**Input:** List of file objects with `download_url` fields  
**Tool:** `github_fetcher.py`  
**Process:** Each file's `download_url` is fetched, returning the raw text content of the YAML file.  
**Output:** List of dicts `[{filename, content (raw YAML string), size}]`

### Stage 3 — Raw YAML string → Structured Python dict
**Input:** Raw YAML string (unstructured text)  
**Tool:** `yaml_parser.py`  
**Process:** `PyYAML.safe_load()` parses the YAML into a Python object. The parser then normalizes it — extracting jobs, steps, triggers, timeouts, env vars — into a consistent structure regardless of the original YAML formatting.  
**Output:** Normalized workflow dict `{name, triggers, jobs: [{id, steps, timeout, ...}], raw_content}`

**Why this matters:** The raw YAML format varies significantly between repositories (different indentation, missing optional fields, different trigger formats). Normalization ensures the rule engine always receives a consistent structure.

### Stage 4 — Structured dict → Findings list + scores
**Input:** Normalized workflow dict  
**Tool:** `rule_engine.py`  
**Process:** 32 rules are evaluated using regex, keyword matching, and structural checks. Each violation produces a finding dict. Scores are calculated per category then averaged into an overall score.  
**Output:** `list[dict]` of findings `[{rule_id, severity, category, detail, fix}]` + `dict` of category scores + `int` overall score

### Stage 5 — Findings + raw YAML → AI text sections
**Input:** Findings list + raw YAML content + scores  
**Tool:** Gemini API calls in `agent.py`  
**Process:** Three structured prompts are built from the findings and YAML, sent to `gemini-2.5-flash`, and plain-text responses are returned. Each prompt uses a different expert role (security analyst, DevOps engineer, GitHub Actions expert).  
**Output:** Three plain-English strings: security analysis, action plan, corrected YAML snippet

### Stage 6 — All results → Markdown report + terminal output
**Input:** Findings, scores, AI sections, repo metadata  
**Tool:** `report_generator.py`  
**Process:** Data is formatted into two outputs simultaneously — a Rich terminal display with color-coded tables and score bars, and a structured Markdown file written to the `output/` directory.  
**Output:** Markdown file saved to disk + formatted terminal display

### Full Data Flow Summary

```
"https://github.com/owner/repo"   # plain string
        ↓ github_fetcher
[{filename, raw YAML content}]     # list of file dicts
        ↓ yaml_parser
{name, jobs, triggers, steps}      # normalized workflow dict
        ↓ rule_engine
[{rule_id, severity, fix}] + scores  # findings + category scores
        ↓ agent (Gemini API x3)
{security, action_plan, rewrite}   # AI text sections
        ↓ report_generator
report.md + terminal output        # final deliverables
```

---

*Step 3 of 4 — Next: Final Submission (22 May 2025)*
