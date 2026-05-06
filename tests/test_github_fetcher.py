import pytest
from unittest.mock import patch, MagicMock
from tools.github_fetcher import parse_repo_url, fetch_workflows


def test_parse_valid_url():
    owner, repo = parse_repo_url("https://github.com/octocat/Hello-World")
    assert owner == "octocat"
    assert repo == "Hello-World"


def test_parse_url_with_trailing_slash():
    owner, repo = parse_repo_url("https://github.com/octocat/Hello-World/")
    assert owner == "octocat"
    assert repo == "Hello-World"


def test_parse_invalid_url_raises():
    with pytest.raises(ValueError):
        parse_repo_url("https://github.com/onlyone")


@patch("tools.github_fetcher.requests.get")
def test_fetch_workflows_success(mock_get):
    # Mock directory listing
    mock_list = MagicMock()
    mock_list.status_code = 200
    mock_list.json.return_value = [
        {"name": "ci.yml", "download_url": "https://raw.github.com/ci.yml", "size": 500}
    ]

    # Mock file content
    mock_content = MagicMock()
    mock_content.status_code = 200
    mock_content.text = "on: push\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo hi"

    mock_get.side_effect = [mock_list, mock_content]

    result = fetch_workflows("https://github.com/octocat/Hello-World")
    assert len(result) == 1
    assert result[0]["filename"] == "ci.yml"


@patch("tools.github_fetcher.requests.get")
def test_fetch_workflows_404_raises(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_get.return_value = mock_resp

    with pytest.raises(FileNotFoundError):
        fetch_workflows("https://github.com/nobody/norepo")


@patch("tools.github_fetcher.requests.get")
def test_fetch_workflows_rate_limit_raises(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_get.return_value = mock_resp

    with pytest.raises(PermissionError):
        fetch_workflows("https://github.com/octocat/Hello-World")
