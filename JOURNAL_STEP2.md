# Practical Task — Journal
## Step 2 Submission | Due: 08 May 2025
**Project: CI/CD Pipeline Health Analyzer**

---

## 1. Updated System Description

The CI/CD Pipeline Health Analyzer has been implemented as a fully working command-line tool. The system accepts a GitHub repository URL, fetches all GitHub Actions workflow files via the GitHub REST API, parses and evaluates them against 12 defined rules, and generates a scored health report with AI-powered recommendations.

The core architecture follows an agent-orchestrator pattern: `agent.py` calls four tools in sequence, passing structured data between them. The system runs end-to-end with a single command: `python main.py <repo_url>`.

All modules are implemented, tested, and documented. 20 unit tests pass across 3 test files.

---

## 2. Programming Concepts Actually Used

| Concept | Where Applied |
|---------|--------------|
| Modular project structure | `tools/`, `rules/`, `tests/` as separate packages |
| Functions with typed parameters | Every tool function has defined inputs/outputs |
| Dictionaries and lists | Core data structures for parsed workflows and findings |
| Exception handling | `FileNotFoundError`, `PermissionError`, `ValueError` in all tools |
| Environment variables | `python-dotenv` loads `GEMINI_API_KEY` and `GITHUB_TOKEN` from `.env` |
| HTTP requests | `requests.get()` calls GitHub REST API and downloads raw YAML |
| YAML parsing | `PyYAML.safe_load()` converts raw workflow strings to Python dicts |
| Regex pattern matching | `re.findall()` in rule engine for secret detection |
| JSON data files | Rules defined in `pipeline_rules.json`, loaded at runtime |
| LLM API integration | `google-generativeai` SDK sends structured prompts to Gemini 2.5 Flash |
| Unit testing with mocks | `unittest.mock.patch` mocks GitHub API calls in tests |
| Terminal formatting | `Rich` library renders color-coded tables and progress messages |

---

## 3. How Concepts Are Applied

**Agent-orchestrator pattern:** `agent.py` acts as the central coordinator. It imports each tool, calls them in order, and passes output from one as input to the next. No tool knows about the others — all coordination happens in the agent.

**Rule engine as data:** Rules are not hardcoded in Python logic. They are defined in `rules/pipeline_rules.json` as structured objects with `id`, `severity`, `description`, and `fix` fields. The engine loads them at runtime and maps findings to rule objects. This makes adding new rules trivial — no code change needed, only a new JSON entry.

**Data transformation pipeline:** Raw text enters the system and is progressively transformed:
```
GitHub URL → API response (JSON) → raw YAML (string) → parsed dict → findings list → Markdown report
```
Each transformation is handled by a dedicated tool with a single responsibility.

**Exception handling strategy:** Each tool raises a specific, meaningful exception (`FileNotFoundError` for missing repos, `PermissionError` for rate limits, `ValueError` for malformed YAML). `main.py` catches these at the top level and prints user-friendly messages without crashing.

---

## 4. Tool Integration

### Tool 1 — `github_fetcher.py`
- **Input:** GitHub repository URL string
- **Process:** Calls `GET /repos/{owner}/{repo}/contents/.github/workflows` via GitHub REST API, then fetches each `.yml` file's raw content
- **Output:** List of dicts `[{filename, content, download_url, size}]`
- **Error handling:** Raises `FileNotFoundError` (404), `PermissionError` (403 rate limit), `ConnectionError` (other HTTP errors)

### Tool 2 — `yaml_parser.py`
- **Input:** Filename string + raw YAML string
- **Process:** `yaml.safe_load()` parses YAML, then normalizes into structured format extracting jobs, steps, triggers, timeouts, and environment variables
- **Output:** Parsed workflow dict with normalized fields
- **Error handling:** Raises `ValueError` on invalid YAML or non-dict content

### Tool 3 — `rule_engine.py`
- **Input:** Parsed workflow dict from Tool 2
- **Process:** Loads rules from JSON, evaluates 12 checks using string matching, regex, and structural analysis of the parsed data. Calculates score by deducting points per severity (critical: -20, warning: -8, info: -3)
- **Output:** List of finding dicts + integer score (0–100)

### Tool 4 (AI) — Gemini API call in `agent.py`
- **Input:** Repo URL + findings list + score
- **Process:** Builds a structured prompt, sends to `gemini-2.5-flash`, parses text response
- **Output:** Plain-English summary string (max 200 words)
- **Graceful degradation:** If `GEMINI_API_KEY` is not set, this step is skipped with a warning — the rest of the pipeline still works

### Tool 5 — `report_generator.py`
- **Input:** All findings, score, AI summary, repo metadata
- **Process:** Renders color-coded Rich table to terminal; writes structured Markdown to `output/` directory
- **Output:** Markdown file path + terminal display

---

*Step 2 of 4 — Next: Step 3 (15 May 2025)*
