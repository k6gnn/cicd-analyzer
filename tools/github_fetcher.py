"""
Tool: GitHub Fetcher
Fetches all workflow YAML files from a GitHub repository's .github/workflows/ directory.
"""

import requests
import re
from config import GITHUB_TOKEN


def parse_repo_url(url: str) -> tuple[str, str]:
    """Extract owner and repo name from a GitHub URL."""
    url = url.rstrip("/").replace("https://github.com/", "")
    parts = url.split("/")
    if len(parts) < 2:
        raise ValueError(f"Invalid GitHub URL: {url}")
    return parts[0], parts[1]


def fetch_workflows(repo_url: str) -> list[dict]:
    """
    Fetch all .yml workflow files from a GitHub repository.

    Args:
        repo_url: Full GitHub repository URL

    Returns:
        List of dicts with keys: filename, content, download_url
    """
    owner, repo = parse_repo_url(repo_url)

    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    # List files in .github/workflows/
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/.github/workflows"
    response = requests.get(api_url, headers=headers, timeout=10)

    if response.status_code == 404:
        raise FileNotFoundError(f"No .github/workflows/ directory found in {repo_url}")
    if response.status_code == 403:
        raise PermissionError("GitHub API rate limit reached. Set GITHUB_TOKEN in .env to increase limits.")
    if response.status_code != 200:
        raise ConnectionError(f"GitHub API error {response.status_code}: {response.text}")

    files = response.json()
    workflows = []

    for f in files:
        if not f["name"].endswith((".yml", ".yaml")):
            continue

        # Fetch raw file content
        raw = requests.get(f["download_url"], headers=headers, timeout=10)
        if raw.status_code == 200:
            workflows.append({
                "filename": f["name"],
                "content": raw.text,
                "download_url": f["download_url"],
                "size": f.get("size", 0),
            })

    if not workflows:
        raise FileNotFoundError(f"No .yml workflow files found in {repo_url}/.github/workflows/")

    return workflows
