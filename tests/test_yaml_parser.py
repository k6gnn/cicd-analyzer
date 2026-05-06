import pytest
from tools.yaml_parser import parse_workflow


VALID_WORKFLOW = """
name: CI
on: [push]
jobs:
  build:
    name: Build
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - run: echo hello
"""

MINIMAL_WORKFLOW = """
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: pytest
"""

INVALID_YAML = "this: is: not: valid: yaml: ]["


def test_parse_valid_workflow():
    result = parse_workflow("ci.yml", VALID_WORKFLOW)
    assert result["name"] == "CI"
    assert len(result["jobs"]) == 1
    assert result["jobs"][0]["id"] == "build"
    assert result["jobs"][0]["timeout"] == 15


def test_parse_extracts_steps():
    result = parse_workflow("ci.yml", VALID_WORKFLOW)
    steps = result["jobs"][0]["steps"]
    assert len(steps) == 2
    assert steps[0]["uses"] == "actions/checkout@v4"


def test_parse_minimal_workflow():
    result = parse_workflow("minimal.yml", MINIMAL_WORKFLOW)
    assert len(result["jobs"]) == 1
    assert result["jobs"][0]["timeout"] is None


def test_parse_triggers():
    result = parse_workflow("ci.yml", VALID_WORKFLOW)
    assert "push" in result["triggers"]


def test_parse_invalid_yaml_raises():
    with pytest.raises(ValueError):
        parse_workflow("bad.yml", INVALID_YAML)


def test_parse_empty_raises():
    with pytest.raises(ValueError):
        parse_workflow("empty.yml", "null")
