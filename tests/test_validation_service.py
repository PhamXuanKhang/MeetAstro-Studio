"""Tests cho validation_service.py."""
import pytest

from src.services.validation_service import validate_action_items


def make_item(title: str, description: str = "", assignee: str = "Alice") -> dict:
    return {"title": title, "description": description, "assignee": assignee}


class TestValidateActionItems:
    def test_returns_tuple_of_items_and_metrics(self):
        ai = [make_item("Implement login")]
        rule = [make_item("Implement login")]
        items, metrics = validate_action_items(ai, rule, "implement login feature")
        assert isinstance(items, list)
        assert isinstance(metrics, dict)

    def test_confidence_in_range(self):
        ai = [make_item("Implement login")]
        rule = [make_item("Implement login")]
        items, _ = validate_action_items(ai, rule, "implement login")
        assert 0.0 <= items[0]["confidence"] <= 1.0

    def test_overlap_gives_higher_confidence(self):
        ai = [make_item("Implement login feature")]
        rule = [make_item("Implement login feature")]
        transcript = "implement login feature"
        items_high, metrics_high = validate_action_items(ai, rule, transcript)

        ai2 = [make_item("Implement login feature")]
        rule2 = [make_item("Deploy to production")]
        items_low, metrics_low = validate_action_items(ai2, rule2, "different text")

        assert metrics_high["overall_confidence"] > metrics_low["overall_confidence"]

    def test_short_title_adds_note(self):
        ai = [make_item("Do")]
        items, _ = validate_action_items(ai, [], "do something")
        assert "Title too short" in items[0]["validation_notes"]

    def test_no_assignee_adds_note(self):
        ai = [{"title": "Implement feature", "description": "some desc", "assignee": ""}]
        items, _ = validate_action_items(ai, [], "implement feature")
        assert "No assignee detected" in items[0]["validation_notes"]

    def test_question_title_adds_note(self):
        ai = [make_item("Should we implement this?")]
        items, _ = validate_action_items(ai, [], "should we implement this")
        assert "Possible question, not an action" in items[0]["validation_notes"]

    def test_empty_ai_items(self):
        items, metrics = validate_action_items([], [], "transcript")
        assert items == []
        assert metrics["ai_items_count"] == 0

    def test_metrics_keys(self):
        _, metrics = validate_action_items([], [], "")
        expected = {
            "cross_validation_score", "context_coherence_score",
            "structural_validation_score", "overall_confidence",
            "ai_items_count", "rule_items_count",
        }
        assert expected.issubset(metrics.keys())
