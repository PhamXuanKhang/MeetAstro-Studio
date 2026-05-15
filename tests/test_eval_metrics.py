"""
Evaluation metrics: Recall, Precision, Field Completeness.
Chạy sau mỗi lần sửa prompt hoặc thay đổi analyzer.

Usage:
    pytest tests/test_eval_metrics.py -v
    pytest tests/test_eval_metrics.py -v -k "recall"
    pytest tests/test_eval_metrics.py -v -k "validation" -s
"""
import json
import re
from pathlib import Path
from typing import Any

import pytest

from src.services.analysis_service import analyze_async
from src.services.extraction_service import rule_based_extraction
from src.services.validation_service import validate_action_items
from src.schema import MeetingAnalysis

# ─── Paths ────────────────────────────────────────────────────────────────────

SAMPLES_DIR = Path(__file__).parent.parent / "data" / "eval" / "samples"

VALIDATION_THRESHOLDS = {
    "recall": 0.85,
    "precision": 0.75,
    "schema_validity": 0.95,
    "field_completeness": 0.60,
    "overall_confidence": 0.70,
}


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def eval_samples():
    """Load tất cả eval samples (transcript + ground truth)."""
    samples = []
    if not SAMPLES_DIR.exists():
        pytest.skip(f"Dataset not found at {SAMPLES_DIR}. Run Part 2 of test-procedure.md first.")
    for folder in sorted(SAMPLES_DIR.iterdir()):
        if not folder.is_dir():
            continue
        transcript_file = folder / "transcript.txt"
        gt_file = folder / "ground_truth.json"
        if not transcript_file.exists() or not gt_file.exists():
            continue
        transcript = transcript_file.read_text(encoding="utf-8")
        gt = json.loads(gt_file.read_text(encoding="utf-8"))
        samples.append({
            "id": folder.name,
            "folder": folder,
            "transcript": transcript,
            "ground_truth": gt,
        })
    if not samples:
        pytest.skip(f"No samples found in {SAMPLES_DIR}")
    return samples


# ─── Helper Functions ─────────────────────────────────────────────────────────

def _jaccard_similarity(a: str, b: str) -> float:
    """Tính Jaccard similarity word-level giữa 2 chuỗi."""
    words_a = set(re.findall(r"\w+", a.lower()))
    words_b = set(re.findall(r"\w+", b.lower()))
    if not words_a and not words_b:
        return 1.0
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)


def _task_match(ai_task: dict, gt_task: dict, threshold: float = 0.6) -> bool:
    """So khớp 1 AI task với 1 ground truth task.

    Điều kiện khớp:
    - Jaccard similarity trên summary >= threshold
    - Assignee giống nhau (case-insensitive)
    """
    summary_sim = _jaccard_similarity(
        ai_task.get("summary", ""),
        gt_task.get("summary", "")
    )
    assignee_ai = (ai_task.get("assignee") or "").strip().lower()
    assignee_gt = (gt_task.get("assignee") or "").strip().lower()
    assignee_match = (
        assignee_ai == assignee_gt
        or (assignee_ai and assignee_gt and (assignee_ai in assignee_gt or assignee_gt in assignee_ai))
    )
    return summary_sim >= threshold and assignee_match


def _extract_ai_tasks(analysis: MeetingAnalysis) -> list[dict]:
    """Trích xuất flat list của all tasks từ MeetingAnalysis."""
    tasks = []
    for epic in analysis.epics:
        for task in epic.tasks:
            tasks.append({
                "summary": task.summary,
                "assignee": task.assignee or "",
                "deadline": task.deadline or "",
                "priority": task.priority,
                "context": task.context,
            })
    return tasks


def _ai_tasks_to_dict(tasks: list[dict]) -> list[dict[str, Any]]:
    """Convert internal task dict format to format expected by validate_action_items."""
    return [
        {
            "title": t["summary"],
            "description": t.get("context", ""),
            "assignee": t.get("assignee") or "Unassigned",
        }
        for t in tasks
    ]


# ─── Core Metrics ─────────────────────────────────────────────────────────────

def compute_recall(analysis: MeetingAnalysis, gt: dict) -> float:
    """Tính Recall: % GT tasks được AI extract đúng."""
    ai_tasks = _extract_ai_tasks(analysis)
    gt_tasks = [
        {"summary": t.get("summary", ""), "assignee": t.get("assignee", "")}
        for e in gt.get("epics", [])
        for t in e.get("tasks", [])
    ]
    if not gt_tasks:
        return 1.0
    matched = sum(
        1 for gt_task in gt_tasks
        if any(_task_match(ai_task, gt_task) for ai_task in ai_tasks)
    )
    return matched / len(gt_tasks)


def compute_precision(analysis: MeetingAnalysis, gt: dict) -> float:
    """Tính Precision: % AI tasks khớp với GT."""
    ai_tasks = _extract_ai_tasks(analysis)
    gt_tasks = [
        {"summary": t.get("summary", ""), "assignee": t.get("assignee", "")}
        for e in gt.get("epics", [])
        for t in e.get("tasks", [])
    ]
    if not ai_tasks:
        return 1.0 if not gt_tasks else 0.0
    matched = sum(
        1 for ai_task in ai_tasks
        if any(_task_match(ai_task, gt_task) for gt_task in gt_tasks)
    )
    return matched / len(ai_tasks)


def compute_field_completeness(analysis: MeetingAnalysis) -> float:
    """Tính % tasks có cả assignee + deadline (không null)."""
    all_tasks = _extract_ai_tasks(analysis)
    if not all_tasks:
        return 1.0
    complete = sum(1 for t in all_tasks if t.get("assignee") and t.get("deadline"))
    return complete / len(all_tasks)


# ─── Test Classes ─────────────────────────────────────────────────────────────

class TestEvalRecall:
    """Metric #1: Action Item Recall >= 85%."""

    def test_recall_meets_threshold(self, eval_samples):
        """Recall phải >= 85% trên tất cả samples."""
        failures = []
        for sample in eval_samples:
            analysis = analyze_async(sample["transcript"])
            recall = compute_recall(analysis, sample["ground_truth"])
            if recall < VALIDATION_THRESHOLDS["recall"]:
                failures.append(
                    f"  - {sample['id']}: recall={recall:.3f} "
                    f"< {VALIDATION_THRESHOLDS['recall']}"
                )
        assert not failures, (
            "Recall below threshold:\n" + "\n".join(failures)
        )

    def test_recall_per_sample(self, eval_samples):
        """Log recall cho từng sample (không fail, chỉ log)."""
        for sample in eval_samples:
            analysis = analyze_async(sample["transcript"])
            recall = compute_recall(analysis, sample["ground_truth"])
            status = "PASS" if recall >= VALIDATION_THRESHOLDS["recall"] else "FAIL"
            print(f"\n[{status}] {sample['id']}: recall={recall:.3f}")


class TestEvalPrecision:
    """Metric #2: Action Item Precision >= 75%."""

    def test_precision_meets_threshold(self, eval_samples):
        """Precision phải >= 75% trên tất cả samples."""
        failures = []
        for sample in eval_samples:
            analysis = analyze_async(sample["transcript"])
            precision = compute_precision(analysis, sample["ground_truth"])
            if precision < VALIDATION_THRESHOLDS["precision"]:
                failures.append(
                    f"  - {sample['id']}: precision={precision:.3f} "
                    f"< {VALIDATION_THRESHOLDS['precision']}"
                )
        assert not failures, (
            "Precision below threshold:\n" + "\n".join(failures)
        )

    def test_precision_per_sample(self, eval_samples):
        """Log precision cho từng sample."""
        for sample in eval_samples:
            analysis = analyze_async(sample["transcript"])
            precision = compute_precision(analysis, sample["ground_truth"])
            status = "PASS" if precision >= VALIDATION_THRESHOLDS["precision"] else "FAIL"
            print(f"\n[{status}] {sample['id']}: precision={precision:.3f}")


class TestEvalSchemaValidity:
    """Metric #4: Schema Validity >= 95%."""

    def test_schema_validity_all_samples(self, eval_samples):
        """100% response parse được thành MeetingAnalysis."""
        failures = []
        for sample in eval_samples:
            try:
                result = analyze_async(sample["transcript"])
                assert isinstance(result, MeetingAnalysis), (
                    f"{sample['id']}: result is not MeetingAnalysis"
                )
            except Exception as exc:
                failures.append(f"  - {sample['id']}: {exc}")
        assert not failures, "Schema parse failures:\n" + "\n".join(failures)


class TestEvalFieldCompleteness:
    """Metric #5: Field Completeness >= 60%."""

    def test_field_completeness(self, eval_samples):
        """% tasks có đủ assignee + deadline >= 60%."""
        failures = []
        for sample in eval_samples:
            analysis = analyze_async(sample["transcript"])
            fc = compute_field_completeness(analysis)
            if fc < VALIDATION_THRESHOLDS["field_completeness"]:
                failures.append(
                    f"  - {sample['id']}: field_completeness={fc:.3f} "
                    f"< {VALIDATION_THRESHOLDS['field_completeness']}"
                )
        assert not failures, (
            "Field completeness below threshold:\n" + "\n".join(failures)
        )


class TestEvalValidationMetrics:
    """Metric #9: Validation service metrics (cross-validation, context coherence, structural)."""

    def test_validation_scores_in_range(self, eval_samples):
        """Tất cả validation scores luôn trong [0, 1]."""
        for sample in eval_samples:
            ai_tasks = _extract_ai_tasks(analyze_async(sample["transcript"]))
            rule_tasks = rule_based_extraction(sample["transcript"])
            _, metrics = validate_action_items(
                _ai_tasks_to_dict(ai_tasks),
                rule_tasks,
                sample["transcript"]
            )
            for key in [
                "cross_validation_score",
                "context_coherence_score",
                "structural_validation_score",
                "overall_confidence",
            ]:
                val = metrics[key]
                assert 0.0 <= val <= 1.0, (
                    f"{sample['id']}: {key}={val} out of range [0,1]"
                )

    def test_overall_confidence_threshold(self, eval_samples):
        """Overall confidence >= 0.7 trên tất cả samples."""
        failures = []
        for sample in eval_samples:
            ai_tasks = _extract_ai_tasks(analyze_async(sample["transcript"]))
            rule_tasks = rule_based_extraction(sample["transcript"])
            _, metrics = validate_action_items(
                _ai_tasks_to_dict(ai_tasks),
                rule_tasks,
                sample["transcript"]
            )
            if metrics["overall_confidence"] < VALIDATION_THRESHOLDS["overall_confidence"]:
                failures.append(
                    f"  - {sample['id']}: overall_confidence={metrics['overall_confidence']:.3f} "
                    f"< {VALIDATION_THRESHOLDS['overall_confidence']}"
                )
        assert not failures, (
            "Overall confidence below threshold:\n" + "\n".join(failures)
        )

    def test_validation_metrics_per_sample(self, eval_samples):
        """Log validation metrics cho từng sample."""
        for sample in eval_samples:
            ai_tasks = _extract_ai_tasks(analyze_async(sample["transcript"]))
            rule_tasks = rule_based_extraction(sample["transcript"])
            _, metrics = validate_action_items(
                _ai_tasks_to_dict(ai_tasks),
                rule_tasks,
                sample["transcript"]
            )
            print(f"\n[VALIDATION] {sample['id']}:")
            print(f"  cross_validation_score:      {metrics['cross_validation_score']:.3f}")
            print(f"  context_coherence_score:     {metrics['context_coherence_score']:.3f}")
            print(f"  structural_validation_score: {metrics['structural_validation_score']:.3f}")
            print(f"  overall_confidence:          {metrics['overall_confidence']:.3f}")
            print(f"  ai_items_count:              {metrics['ai_items_count']}")
            print(f"  rule_items_count:            {metrics['rule_items_count']}")


class TestEvalEdgeCases:
    """Edge cases: no-action meetings, short meetings, mixed language."""

    def test_no_action_meeting_does_not_crash(self, eval_samples):
        """Cuộc họp không có action item không crash và trả về summary."""
        no_action_samples = [
            s for s in eval_samples
            if not s["ground_truth"].get("epics")
        ]
        if not no_action_samples:
            pytest.skip("No no-action samples in dataset")
        for sample in no_action_samples:
            result = analyze_async(sample["transcript"])
            assert isinstance(result, MeetingAnalysis)
            assert result.summary, f"{sample['id']}: summary should not be empty"

    def test_short_transcript(self, eval_samples):
        """Transcript ngắn vẫn phân tích được."""
        for sample in eval_samples:
            if len(sample["transcript"].split()) < 50:
                result = analyze_async(sample["transcript"])
                assert isinstance(result, MeetingAnalysis)
