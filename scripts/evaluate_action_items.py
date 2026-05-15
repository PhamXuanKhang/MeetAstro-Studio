"""
Evaluate action items extracted from a meeting transcript against ground-truth
action items annotated in the AMI corpus XML.

Ground truth:
    <actions> block in ES2002a.abssumm.xml

Extracted:
    output_action_items.txt

Expected extracted format:
    Action plan
    HIGH
    1. Phát triển thiết kế chức năng cho điều khiển từ xa [@David]
    Topic: Thiết kế điều khiển từ xa mới
    Action: David, với vai trò là Nhà thiết kế công nghiệp, sẽ làm việc trên thiết kế chức năng...

Evaluation method:
    1. Parse gold action items.
    2. Parse extracted action items.
    3. Score every extracted item against every gold item using GPT.
    4. Match extracted items to gold items one-to-one.
    5. Compute:
        - hard precision / recall / F1
        - soft precision / recall / F1

Why pairwise matching?
    If your system extracts 4 action items and the gold has 3 action items,
    where 3 extracted items correctly match the 3 gold items and 1 is extra:

        precision = 3 / 4 = 0.75
        recall    = 3 / 3 = 1.00
        F1        = 0.857

    The extra item should reduce precision, not recall.

Usage:
    python scripts/evaluate_action_items.py \
        --xml data/eval/real/amicorpus/ES2002a/action_items/ES2002a.abssumm.xml \
        --txt data/eval/real/amicorpus/ES2002a/action_items/output_action_items.txt

With output JSON:
    python scripts/evaluate_action_items.py \
        --xml ... \
        --txt ... \
        --output results/action_item_eval.json

Dry run:
    python scripts/evaluate_action_items.py \
        --xml ... \
        --txt ... \
        --dry-run
"""

import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from openai import OpenAI


# ---------------------------------------------------------------------------
# 0 · Environment
# ---------------------------------------------------------------------------

load_dotenv()


# ---------------------------------------------------------------------------
# 1 · Parse ground-truth action items from AMI *.abssumm.xml
# ---------------------------------------------------------------------------

def parse_gt_action_items(xml_path: Path) -> list[str]:
    """
    Extract ground-truth action items from the <actions> block of an
    AMI *.abssumm.xml file.

    Returns:
        list[str]: One action item per <sentence>.
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    actions: list[str] = []

    for elem in root.iter():
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

        if tag == "actions":
            for child in elem:
                child_tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag

                if child_tag == "sentence":
                    text = (child.text or "").strip()
                    if text:
                        actions.append(text)

            break

    return actions


# ---------------------------------------------------------------------------
# 2 · Parse extracted action items from output_action_items.txt
# ---------------------------------------------------------------------------

def parse_extracted_action_items(txt_path: Path) -> list[dict[str, str]]:
    """
    Parse extracted action items into structured dictionaries.

    Expected format:
        Action plan
        HIGH
        1. Some title [@David]
        Topic: ...
        Action: ...

    Returns:
        [
            {
                "priority": "HIGH",
                "title": "...",
                "topic": "...",
                "action": "...",
                "assignee": "David"
            }
        ]
    """
    raw = txt_path.read_text(encoding="utf-8").strip()
    lines = raw.splitlines()

    items: list[dict[str, str]] = []

    current_priority = ""
    current_title = ""
    current_topic = ""
    current_action = ""
    current_assignee = ""

    def flush_current_item() -> None:
        nonlocal current_title, current_topic, current_action, current_assignee

        if current_title or current_action:
            items.append(
                {
                    "priority": current_priority,
                    "title": current_title.strip(),
                    "topic": current_topic.strip(),
                    "action": current_action.strip(),
                    "assignee": current_assignee.strip(),
                }
            )

        current_title = ""
        current_topic = ""
        current_action = ""
        current_assignee = ""

    for line in lines:
        line = line.strip()

        if not line:
            continue

        if line.lower() == "action plan":
            continue

        if line.upper() in {"HIGH", "MEDIUM", "LOW"}:
            current_priority = line.upper()
            continue

        # Example:
        # 1. Phát triển thiết kế chức năng cho điều khiển từ xa [@David]
        if re.match(r"^\d+\.", line):
            flush_current_item()

            match = re.match(r"^\d+\.\s*(.+?)\s*(?:\[@([^\]]+)\])?$", line)
            if match:
                current_title = match.group(1).strip()
                current_assignee = match.group(2).strip() if match.group(2) else ""
            else:
                current_title = line
                current_assignee = ""

            continue

        if line.startswith("Topic:"):
            current_topic = line[len("Topic:"):].strip()
            continue

        if line.startswith("Action:"):
            current_action = line[len("Action:"):].strip()
            continue

        # Continuation line for action text.
        if current_action:
            current_action += " " + line
        elif current_title:
            # If model output has free text after title but no Action: prefix.
            current_action = line

    flush_current_item()

    return items


# ---------------------------------------------------------------------------
# 3 · GPT scoring
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """
You are an expert evaluator for meeting action item extraction.

You compare one extracted action item against one ground-truth action item.

Evaluation rules:
- Focus primarily on the intended task: what needs to be done.
- Treat paraphrases, translations, and more detailed wording as acceptable
  if the core task is the same.
- Assignee names, roles, topics, and priority are secondary:
  they are not required for a match, but they may support the match
  if consistent with the task.
- Do not penalize an extracted item merely because it is more detailed than
  the gold item.
- Penalize when the extracted item changes the task, assigns a clearly
  different responsibility, or adds an unrelated task.
- Score:
  1.0 = same action/task
  0.8-0.95 = same core task with minor wording/detail differences
  0.5-0.75 = partially overlapping task
  0.1-0.4 = weak topical overlap but not the same action
  0.0 = unrelated

Return ONLY a JSON object with this exact schema:
{
  "score": <float between 0.0 and 1.0>,
  "reason": "<one sentence explaining the score>"
}
""".strip()


def _get_client() -> OpenAI:
    """
    Lazily initialize OpenAI client.

    Make sure OPENAI_API_KEY exists in your environment or .env file.
    """
    return OpenAI()


def _safe_json_loads(raw: str) -> dict[str, Any]:
    """
    Parse JSON safely.

    GPT response_format=json_object should already return valid JSON,
    but this function avoids crashing on occasional formatting issues.
    """
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "score": 0.0,
            "reason": f"Failed to parse model JSON response: {raw[:200]}",
        }


def _normalize_score(value: Any) -> float:
    """
    Convert score to float and clamp it to [0, 1].
    """
    try:
        score = float(value)
    except (TypeError, ValueError):
        score = 0.0

    return max(0.0, min(1.0, score))


def score_pair(
    extracted: dict[str, str],
    gold_item: str,
    client: Optional[OpenAI] = None,
    model: str = "gpt-4o",
) -> dict[str, Any]:
    """
    Score one extracted action item against one gold action item.

    Returns:
        {
            "score": float,
            "reason": str
        }
    """
    if client is None:
        client = _get_client()

    extracted_action = extracted.get("action") or extracted.get("title", "")

    user_prompt = f"""
Ground-truth action item:
{gold_item}

Extracted action item:
Title: {extracted.get("title", "")}
Topic: {extracted.get("topic", "")}
Action: {extracted_action}
Assignee: {extracted.get("assignee", "")}
Priority: {extracted.get("priority", "")}

How well does the extracted action item match the ground-truth action item?

Return JSON only.
""".strip()

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content or "{}"
    result = _safe_json_loads(raw)

    return {
        "score": _normalize_score(result.get("score", 0.0)),
        "reason": str(result.get("reason", "")),
    }


def score_pairwise_matrix(
    extracted: list[dict[str, str]],
    gold: list[str],
    client: Optional[OpenAI] = None,
    model: str = "gpt-4o",
) -> list[list[dict[str, Any]]]:
    """
    Score every extracted item against every gold item.

    matrix[i][j] = score of extracted[i] against gold[j].
    """
    if client is None:
        client = _get_client()

    matrix: list[list[dict[str, Any]]] = []

    total = len(extracted) * len(gold)
    done = 0

    for i, ext in enumerate(extracted):
        row: list[dict[str, Any]] = []

        for j, gold_item in enumerate(gold):
            done += 1
            print(
                f"  [{done}/{total}] Scoring extracted {i + 1} "
                f"against gold {j + 1}..."
            )

            result = score_pair(
                extracted=ext,
                gold_item=gold_item,
                client=client,
                model=model,
            )

            row.append(
                {
                    "extracted_index": i,
                    "gold_index": j,
                    "score": result["score"],
                    "reason": result["reason"],
                    "extracted_item": ext,
                    "gold_item": gold_item,
                }
            )

        matrix.append(row)

    return matrix


# ---------------------------------------------------------------------------
# 4 · Matching and aggregation
# ---------------------------------------------------------------------------

def greedy_match(
    matrix: list[list[dict[str, Any]]],
    threshold: float = 0.5,
) -> list[dict[str, Any]]:
    """
    Greedy one-to-one matching.

    Each extracted item can match at most one gold item.
    Each gold item can match at most one extracted item.

    This is usually enough for small action-item lists.
    """
    candidates: list[dict[str, Any]] = []

    for row in matrix:
        for cell in row:
            candidates.append(cell)

    candidates.sort(key=lambda x: float(x["score"]), reverse=True)

    used_extracted: set[int] = set()
    used_gold: set[int] = set()
    matches: list[dict[str, Any]] = []

    for cand in candidates:
        score = float(cand["score"])

        if score < threshold:
            continue

        extracted_index = int(cand["extracted_index"])
        gold_index = int(cand["gold_index"])

        if extracted_index in used_extracted:
            continue

        if gold_index in used_gold:
            continue

        matches.append(cand)
        used_extracted.add(extracted_index)
        used_gold.add(gold_index)

    return matches


def compute_prf(
    matches: list[dict[str, Any]],
    extracted_count: int,
    gold_count: int,
) -> dict[str, Any]:
    """
    Compute hard and soft precision / recall / F1.

    Hard metrics:
        Match count is treated as TP.

    Soft metrics:
        Sum of matched scores is treated as soft TP.
    """
    matched_extracted = {int(m["extracted_index"]) for m in matches}
    matched_gold = {int(m["gold_index"]) for m in matches}

    false_positives = [
        i for i in range(extracted_count)
        if i not in matched_extracted
    ]

    false_negatives = [
        j for j in range(gold_count)
        if j not in matched_gold
    ]

    hard_tp = len(matches)

    precision = hard_tp / extracted_count if extracted_count > 0 else 0.0
    recall = hard_tp / gold_count if gold_count > 0 else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall > 0
        else 0.0
    )

    soft_tp = sum(float(m["score"]) for m in matches)

    soft_precision = soft_tp / extracted_count if extracted_count > 0 else 0.0
    soft_recall = soft_tp / gold_count if gold_count > 0 else 0.0
    soft_f1 = (
        2 * soft_precision * soft_recall / (soft_precision + soft_recall)
        if soft_precision + soft_recall > 0
        else 0.0
    )

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "soft_precision": round(soft_precision, 4),
        "soft_recall": round(soft_recall, 4),
        "soft_f1": round(soft_f1, 4),
        "hits": hard_tp,
        "extracted_count": extracted_count,
        "gold_count": gold_count,
        "false_positive_count": len(false_positives),
        "false_negative_count": len(false_negatives),
        "false_positives": false_positives,
        "false_negatives": false_negatives,
    }


def aggregate_pairwise_scores(
    matrix: list[list[dict[str, Any]]],
    extracted: list[dict[str, str]],
    gold: list[str],
    threshold: float = 0.5,
) -> dict[str, Any]:
    """
    Aggregate pairwise scores into final metrics.
    """
    extracted_count = len(extracted)
    gold_count = len(gold)

    if extracted_count == 0 and gold_count == 0:
        return {
            "precision": 1.0,
            "recall": 1.0,
            "f1": 1.0,
            "soft_precision": 1.0,
            "soft_recall": 1.0,
            "soft_f1": 1.0,
            "hits": 0,
            "extracted_count": 0,
            "gold_count": 0,
            "false_positive_count": 0,
            "false_negative_count": 0,
            "false_positives": [],
            "false_negatives": [],
            "matches": [],
        }

    if extracted_count == 0:
        return {
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "soft_precision": 0.0,
            "soft_recall": 0.0,
            "soft_f1": 0.0,
            "hits": 0,
            "extracted_count": 0,
            "gold_count": gold_count,
            "false_positive_count": 0,
            "false_negative_count": gold_count,
            "false_positives": [],
            "false_negatives": list(range(gold_count)),
            "matches": [],
        }

    if gold_count == 0:
        return {
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "soft_precision": 0.0,
            "soft_recall": 0.0,
            "soft_f1": 0.0,
            "hits": 0,
            "extracted_count": extracted_count,
            "gold_count": 0,
            "false_positive_count": extracted_count,
            "false_negative_count": 0,
            "false_positives": list(range(extracted_count)),
            "false_negatives": [],
            "matches": [],
        }

    matches = greedy_match(matrix=matrix, threshold=threshold)
    metrics = compute_prf(
        matches=matches,
        extracted_count=extracted_count,
        gold_count=gold_count,
    )

    metrics["matches"] = matches
    return metrics


# ---------------------------------------------------------------------------
# 5 · Public evaluation API
# ---------------------------------------------------------------------------

def evaluate_meeting(
    xml_path: Path | str,
    txt_path: Path | str,
    model: str = "gpt-4o",
    threshold: float = 0.5,
) -> dict[str, Any]:
    """
    End-to-end evaluation.

    Returns:
        {
            "meeting_id": str,
            "gold_items": list[str],
            "extracted_items": list[dict],
            "score_matrix": list[list[dict]],
            "summary": dict,
            "overall_score": float,
            "soft_overall_score": float
        }
    """
    xml_path = Path(xml_path)
    txt_path = Path(txt_path)

    print(f"Loading ground truth from: {xml_path}")
    gold = parse_gt_action_items(xml_path)
    print(f"  Found {len(gold)} gold action items")

    print(f"Loading extracted items from: {txt_path}")
    extracted = parse_extracted_action_items(txt_path)
    print(f"  Found {len(extracted)} extracted action items")

    print("\nScoring pairwise with GPT...")
    matrix = score_pairwise_matrix(
        extracted=extracted,
        gold=gold,
        model=model,
    )

    summary = aggregate_pairwise_scores(
        matrix=matrix,
        extracted=extracted,
        gold=gold,
        threshold=threshold,
    )

    return {
        "meeting_id": xml_path.stem.replace(".abssumm", ""),
        "gold_items": gold,
        "extracted_items": extracted,
        "score_matrix": matrix,
        "summary": summary,
        "overall_score": summary["f1"],
        "soft_overall_score": summary["soft_f1"],
    }


# ---------------------------------------------------------------------------
# 6 · Human-readable report
# ---------------------------------------------------------------------------

def _short(text: str, limit: int = 90) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def build_report(result: dict[str, Any]) -> str:
    """
    Build a readable report.
    """
    lines: list[str] = []

    summary = result["summary"]

    lines.append("")
    lines.append("=" * 80)
    lines.append("ACTION ITEM EVALUATION REPORT")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"Meeting:          {result['meeting_id']}")
    lines.append(f"Gold items:       {len(result['gold_items'])}")
    lines.append(f"Extracted items:  {len(result['extracted_items'])}")
    lines.append("")

    lines.append("Gold action items:")
    for i, item in enumerate(result["gold_items"]):
        lines.append(f"  G{i + 1}. {_short(item)}")
    lines.append("")

    lines.append("Extracted action items:")
    for i, item in enumerate(result["extracted_items"]):
        title = item.get("title", "")
        assignee = item.get("assignee", "")
        action = item.get("action", "")

        assignee_text = f" [@{assignee}]" if assignee else ""
        lines.append(f"  E{i + 1}. {_short(title)}{assignee_text}")
        if action:
            lines.append(f"      Action: {_short(action)}")
    lines.append("")

    lines.append("Matched pairs:")
    matches = summary.get("matches", [])

    if not matches:
        lines.append("  No matched pairs.")
    else:
        for m in matches:
            e_idx = int(m["extracted_index"])
            g_idx = int(m["gold_index"])
            score = float(m["score"])
            reason = m.get("reason", "")

            extracted_title = result["extracted_items"][e_idx].get("title", "")
            gold_item = result["gold_items"][g_idx]

            lines.append(
                f"  E{e_idx + 1} -> G{g_idx + 1} | score={score:.2f}"
            )
            lines.append(f"      Extracted: {_short(extracted_title)}")
            lines.append(f"      Gold:      {_short(gold_item)}")
            lines.append(f"      Reason:    {_short(reason, 120)}")
    lines.append("")

    false_positives = summary.get("false_positives", [])
    false_negatives = summary.get("false_negatives", [])

    lines.append("False positives:")
    if not false_positives:
        lines.append("  None")
    else:
        for idx in false_positives:
            item = result["extracted_items"][idx]
            lines.append(f"  E{idx + 1}. {_short(item.get('title', ''))}")
    lines.append("")

    lines.append("False negatives:")
    if not false_negatives:
        lines.append("  None")
    else:
        for idx in false_negatives:
            lines.append(f"  G{idx + 1}. {_short(result['gold_items'][idx])}")
    lines.append("")

    lines.append("Metrics:")
    lines.append(
        f"  Hard Precision:  {summary['precision']:.4f} "
        f"({summary['precision'] * 100:.1f}%)"
    )
    lines.append(
        f"  Hard Recall:     {summary['recall']:.4f} "
        f"({summary['recall'] * 100:.1f}%)"
    )
    lines.append(
        f"  Hard F1:         {summary['f1']:.4f} "
        f"({summary['f1'] * 100:.1f}%)"
    )
    lines.append("")
    lines.append(
        f"  Soft Precision:  {summary['soft_precision']:.4f} "
        f"({summary['soft_precision'] * 100:.1f}%)"
    )
    lines.append(
        f"  Soft Recall:     {summary['soft_recall']:.4f} "
        f"({summary['soft_recall'] * 100:.1f}%)"
    )
    lines.append(
        f"  Soft F1:         {summary['soft_f1']:.4f} "
        f"({summary['soft_f1'] * 100:.1f}%)"
    )
    lines.append("")
    lines.append(f"Hits:             {summary['hits']}/{summary['gold_count']}")
    lines.append(f"False positives:  {summary['false_positive_count']}")
    lines.append(f"False negatives:  {summary['false_negative_count']}")
    lines.append("")
    lines.append(f"Overall Score:       {result['overall_score']:.4f}")
    lines.append(f"Soft Overall Score:  {result['soft_overall_score']:.4f}")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 7 · CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate extracted meeting action items against AMI gold standard "
            "using pairwise GPT-based semantic matching."
        )
    )

    parser.add_argument(
        "--xml",
        required=True,
        help="Path to AMI *.abssumm.xml ground-truth file.",
    )

    parser.add_argument(
        "--txt",
        required=True,
        help="Path to extracted output_action_items.txt file.",
    )

    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Optional path to write JSON evaluation result.",
    )

    parser.add_argument(
        "--meeting-id",
        default=None,
        help="Override meeting ID in output.",
    )

    parser.add_argument(
        "--model",
        default="gpt-4o",
        help="OpenAI model used for scoring. Default: gpt-4o.",
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Minimum score for a pair to count as a hard match. Default: 0.5.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only parse and print gold/extracted items without calling GPT.",
    )

    args = parser.parse_args()

    xml_path = Path(args.xml)
    txt_path = Path(args.txt)

    print(f"Loading ground truth from: {xml_path}")
    gold = parse_gt_action_items(xml_path)
    print(f"  Found {len(gold)} gold action items")
    for i, item in enumerate(gold):
        print(f"    G{i + 1}. {item}")

    print(f"\nLoading extracted items from: {txt_path}")
    extracted = parse_extracted_action_items(txt_path)
    print(f"  Found {len(extracted)} extracted action items")
    for i, item in enumerate(extracted):
        assignee = item.get("assignee", "")
        assignee_text = f" [@{assignee}]" if assignee else ""
        print(f"    E{i + 1}. {item.get('title', '')}{assignee_text}")

    if args.dry_run:
        print("\n--dry-run: skipping GPT scoring.")
        return

    result = evaluate_meeting(
        xml_path=xml_path,
        txt_path=txt_path,
        model=args.model,
        threshold=args.threshold,
    )

    if args.meeting_id:
        result["meeting_id"] = args.meeting_id

    report = build_report(result)
    print(report)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"Written JSON result to: {out_path}")
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()