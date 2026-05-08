# Practical Task — Journal
## Step 2 Submission | Due: 08 May 2025
**Project: CI/CD Pipeline Health Analyzer**

---

## 1. Updated System Description

The CI/CD Pipeline Health Analyzer is a fully implemented command-line tool. The system accepts a GitHub repository URL, fetches all GitHub Actions workflow YAML files via the GitHub REST API, parses and evaluates them against 32 defined rules across 5 categories, and produces a scored health report with three specialized AI-powered analysis sections.

The architecture follows an agent-orchestrator pattern: `agent.py` coordinates five tools in a fixed sequence, passing structured data between each stage. The system runs end-to-end with a single command:

```bash
python main.py https://github.com/owner/repo
```

The overall health score is calculated as the average of five per-category scores (Security, Performance, Reliability, Best Practices, Maintainability), giving a consistent and meaningful result. All modules are implemented, tested, and documented. 20 unit tests pass across 3 test files.

---

## 2. Programming Concepts Actually Used

| Concept | Where Applied |
|---------|--------------|
| Modular project structure | `tools/`, `rules/`, `tests/` as separate Python packages |
| Functions with typed parameters | Every tool function has defined input/output types |
| Dictionaries and lists | Core data structures throughout — parsed workflows, findings, scores |
| Exception handling | `FileNotFoundError`, `PermissionError`, `ValueError` raised per tool, caught in `main.py` |
| Environment variables | `python-dotenv` loads `GEMINI_API_KEY` and `GITHUB_TOKEN` from `.env` |
| HTTP requests | `requests.get()` calls GitHub REST API and fetches raw YAML content |
| YAML parsing | `PyYAML.safe_load()` converts raw workflow strings into Python dicts |
| Regex pattern matching | `re.search()` / `re.findall()` for secret detection and injection pattern scanning |
| JSON data files | 32 rules defined in `pipeline_rules.json`, loaded at runtime — no hardcoded rules |
| LLM API integration | `google-generativeai` SDK sends three specialized prompts to Gemini 2.5 Flash |
| Multi-pass AI prompting | Three separate Gemini calls with different system roles and output formats |
| Unit testing with mocks | `unittest.mock.patch` mocks GitHub API calls to test without network access |
| Terminal formatting | `Rich` library renders color-coded tables, progress lines, and category score bars |
| Score aggregation | Per-category scores averaged into a single consistent overall score |

---

## 3. How Concepts Are Applied

**Agent-orchestrator pattern:** `agent.py` is the central coordinator. It imports each tool, calls them in sequence, and passes the output of one as input to the next. No tool knows about the others — all coordination and data flow logic lives in the agent.

**Rule engine as data, not code:** Rules are not hardcoded as Python logic. All 32 rules are defined in `rules/pipeline_rules.json` as structured objects containing `id`, `severity`, `category`, `description`, and `fix` fields. The engine loads them at runtime and maps findings back to rule objects. Adding a new rule requires only a new JSON entry — no code change needed.

**Data transformation pipeline:** Data enters the system as a plain URL and is progressively transformed at each stage:
```
GitHub URL
  → GitHub API (JSON directory listing)
  → Raw YAML strings
  → Parsed workflow dicts (structured Python objects)
  → Findings list (rule violations with severity and fix)
  → Category scores (dict of 5 scores)
  → AI analysis sections (3 plain-English outputs)
  → Markdown report file + terminal output
```

**Multi-pass Gemini AI:** Instead of one generic prompt, the agent runs three specialized Gemini calls with different expert roles:
- **Pass 1 — Security analyst:** Reads the raw YAML and identifies supply chain risks, secret exposure, privilege escalation, and injection vulnerabilities specific to the actual workflow
- **Pass 2 — DevOps engineer:** Receives all findings and produces a 5-item prioritized action plan with effort estimates
- **Pass 3 — GitHub Actions expert:** Rewrites the most problematic section of the workflow as corrected YAML with inline fix comments

**Graceful degradation:** If `GEMINI_API_KEY` is missing, all three AI passes are skipped with a warning and the rule-based analysis still runs and produces a full report.

**Exception handling strategy:** Each tool raises specific, typed exceptions. `main.py` catches them at the top level and prints user-friendly messages:
- `FileNotFoundError` — repo or workflows directory not found
- `PermissionError` — GitHub API rate limit hit (needs token)
- `ValueError` — malformed YAML in workflow file
- `ConnectionError` — GitHub API returned unexpected status

---

## 4. Tool Integration

### Tool 1 — `github_fetcher.py`
- **Input:** GitHub repository URL string
- **Process:** Parses owner/repo from URL, calls `GET /repos/{owner}/{repo}/contents/.github/workflows` via GitHub REST API, fetches raw content of each `.yml` file
- **Output:** `list[dict]` — `[{filename, content, download_url, size}]`
- **Error handling:** `FileNotFoundError` (404), `PermissionError` (403), `ConnectionError` (other)

### Tool 2 — `yaml_parser.py`
- **Input:** Filename string + raw YAML string
- **Process:** `yaml.safe_load()` parses YAML, normalizes structure — extracts jobs, steps, triggers, timeouts, environment variables, concurrency config, and raw content for regex scanning
- **Output:** Parsed workflow dict with normalized fields and original raw content preserved
- **Error handling:** `ValueError` on invalid YAML or non-dict root

### Tool 3 — `rule_engine.py`
- **Input:** Parsed workflow dict from Tool 2
- **Process:** Loads 32 rules from JSON, evaluates each check using regex, structural analysis, keyword matching, and YAML field inspection. Calculates per-category scores (100 minus deductions per severity). Overall score = average of 5 category scores.
- **Output:** `list[dict]` of findings + `int` overall score + `dict` of category scores

### Tool 4 — Gemini AI (3 passes in `agent.py`)
- **Input:** Raw YAML content + findings list + scores
- **Process:** Three sequential calls to `gemini-2.5-flash`, each with a different expert role and structured prompt
- **Output:** Three plain-English strings: security analysis, action plan, corrected YAML snippet
- **Graceful degradation:** Entire block skipped if `GEMINI_API_KEY` not set

### Tool 5 — `report_generator.py`
- **Input:** All findings, overall score, category scores, AI results, repo metadata
- **Process:** Renders Rich terminal output with color-coded severity table and category score bars; writes structured Markdown file to `output/` directory
- **Output:** Markdown report file path + terminal display

---

*Step 2 of 4 — Next: Step 3 (15 May 2025)*
