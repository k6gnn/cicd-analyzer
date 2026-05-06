import pytest
from tools.yaml_parser import parse_workflow
from tools.rule_engine import evaluate, calculate_score


BAD_WORKFLOW = open("sample_workflows/bad_pipeline.yml").read()
GOOD_WORKFLOW = open("sample_workflows/good_pipeline.yml").read()


def test_detects_unpinned_actions():
    parsed = parse_workflow("bad.yml", BAD_WORKFLOW)
    findings = evaluate(parsed)
    rule_ids = [f["rule_id"] for f in findings]
    assert "SEC002" in rule_ids


def test_detects_missing_timeout():
    parsed = parse_workflow("bad.yml", BAD_WORKFLOW)
    findings = evaluate(parsed)
    rule_ids = [f["rule_id"] for f in findings]
    assert "REL001" in rule_ids


def test_detects_missing_permissions():
    parsed = parse_workflow("bad.yml", BAD_WORKFLOW)
    findings = evaluate(parsed)
    rule_ids = [f["rule_id"] for f in findings]
    assert "SEC003" in rule_ids


def test_detects_missing_cache():
    parsed = parse_workflow("bad.yml", BAD_WORKFLOW)
    findings = evaluate(parsed)
    rule_ids = [f["rule_id"] for f in findings]
    assert "PERF001" in rule_ids


def test_good_pipeline_scores_higher():
    bad_parsed = parse_workflow("bad.yml", BAD_WORKFLOW)
    good_parsed = parse_workflow("good.yml", GOOD_WORKFLOW)
    bad_score = calculate_score(evaluate(bad_parsed))
    good_score = calculate_score(evaluate(good_parsed))
    assert good_score > bad_score


def test_score_between_0_and_100():
    parsed = parse_workflow("bad.yml", BAD_WORKFLOW)
    score = calculate_score(evaluate(parsed))
    assert 0 <= score <= 100


def test_good_pipeline_no_critical():
    parsed = parse_workflow("good.yml", GOOD_WORKFLOW)
    findings = evaluate(parsed)
    criticals = [f for f in findings if f["severity"] == "critical"]
    assert len(criticals) == 0


def test_findings_have_required_keys():
    parsed = parse_workflow("bad.yml", BAD_WORKFLOW)
    findings = evaluate(parsed)
    for f in findings:
        assert "rule_id" in f
        assert "severity" in f
        assert "fix" in f
        assert "detail" in f
