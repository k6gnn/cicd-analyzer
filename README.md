# CI/CD Pipeline Health Analyzer

An AI-powered command-line tool that analyzes GitHub Actions workflow files for security vulnerabilities, performance issues, and best-practice violations. Produces a scored health report with actionable recommendations.

## What It Does

1. Fetches all `.yml` workflow files from a GitHub repository
2. Parses and analyzes them against 12+ rules across 4 categories
3. Calls Google Gemini AI to generate plain-English recommendations
4. Outputs a color-coded terminal report + saves a Markdown file

## Setup

**Requirements:** Python 3.11+

```bash
# 1. Clone the repository
git clone https://github.com/k6gnn/cicd-analyzer
cd cicd-analyzer

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env
# Edit .env and add your API keys
```

## Configuration

Create a `.env` file in the project root:

```
GEMINI_API_KEY=your_gemini_api_key_here
GITHUB_TOKEN=your_github_token_here
```

- **GEMINI_API_KEY** — Get a free key at [aistudio.google.com](https://aistudio.google.com). Required for AI recommendations.
- **GITHUB_TOKEN** — Optional. Only needed for private repositories. Increases GitHub API rate limits.

## Usage

```bash
# Analyze any public GitHub repository
python main.py https://github.com/owner/repo

# Or run interactively
python main.py
```

## Example Output

```
CI/CD Pipeline Health Analyzer

→ Fetching workflows from https://github.com/owner/repo...
  ✓ Found 2 workflow file(s): ci.yml, deploy.yml
→ Parsing workflow files...
→ Running rule engine...
  ✓ 6 finding(s) detected — score: 54/100
→ Generating AI recommendations...

Health Score: 54/100 ⚠️ Needs Improvement

┌──────────────┬────────┬──────────────────────────────────┬─────────────┐
│ Severity     │ Rule   │ Finding                          │ Category    │
├──────────────┼────────┼──────────────────────────────────┼─────────────┤
│ 🔴 CRITICAL  │ REL001 │ Jobs missing timeout-minutes:... │ Reliability │
│ 🟡 WARNING   │ SEC002 │ Unpinned actions found: ...      │ Security    │
└──────────────┴────────┴──────────────────────────────────┴─────────────┘
```

Reports are saved to the `output/` directory as Markdown files.

## Running Tests

```bash
pytest tests/ -v
```

## Project Structure

```
cicd-analyzer/
├── main.py                  # Entry point
├── agent.py                 # Orchestrator — coordinates all tools
├── config.py                # Configuration and environment variables
├── tools/
│   ├── github_fetcher.py    # GitHub API integration
│   ├── yaml_parser.py       # YAML parsing and normalization
│   ├── rule_engine.py       # Rule evaluation and scoring
│   └── report_generator.py  # Terminal and Markdown output
├── rules/
│   └── pipeline_rules.json  # Rule definitions
├── tests/                   # pytest test suite
├── sample_workflows/        # Sample YAML files for testing
├── output/                  # Generated reports (git-ignored)
├── requirements.txt
└── .env.example
```

## Rule Categories

| Category | Rules |
|----------|-------|
| 🔐 Security | Hardcoded secrets, unpinned actions, missing permissions |
| ⚡ Performance | Missing cache, no parallel jobs |
| 🔁 Reliability | Missing timeouts, no retry logic, no failure notifications |
| 📋 Best Practices | No concurrency control, hardcoded env vars, missing names |

## Data Flow

```
GitHub URL → GitHub API → Raw YAML → Parsed Dict → Rule Findings → Gemini AI → Markdown Report
```
