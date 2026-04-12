"""
Export MeetingAnalysis sang Markdown, JSON, CSV.
"""
import csv
import io
import json

from src.schema import MeetingAnalysis


def export_markdown(analysis: MeetingAnalysis) -> str:
    """Xuất MeetingAnalysis thành Markdown có cấu trúc."""
    lines: list[str] = []
    lines.append("# Kết quả phân tích cuộc họp\n")
    lines.append(f"**Tóm tắt:** {analysis.summary}\n")

    for i, epic in enumerate(analysis.epics, 1):
        lines.append(f"\n## Epic {i}: {epic.summary}")
        if epic.description:
            lines.append(f"\n{epic.description}\n")

        for j, task in enumerate(epic.tasks, 1):
            lines.append(f"\n### Task {i}.{j}: {task.summary}")
            lines.append(f"- **Assignee:** {task.assignee or 'Chưa phân công'}")
            lines.append(f"- **Deadline:** {task.deadline or 'Chưa xác định'}")
            lines.append(f"- **Priority:** {task.priority.value}")
            if task.context:
                lines.append(f"- **Context:** _{task.context}_")

            for k, subtask in enumerate(task.subtasks, 1):
                lines.append(f"\n#### Subtask {i}.{j}.{k}: {subtask.summary}")
                lines.append(f"  - Assignee: {subtask.assignee or 'Chưa phân công'}")
                lines.append(f"  - Deadline: {subtask.deadline or 'Chưa xác định'}")
                lines.append(f"  - Priority: {subtask.priority.value}")
                if subtask.context:
                    lines.append(f"  - Context: _{subtask.context}_")

    return "\n".join(lines)


def export_json(analysis: MeetingAnalysis) -> str:
    """Xuất MeetingAnalysis thành JSON string."""
    return json.dumps(analysis.to_dict(), ensure_ascii=False, indent=2)


def export_csv(analysis: MeetingAnalysis) -> str:
    """Xuất MeetingAnalysis thành CSV — mỗi task/subtask là một row."""
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["type", "epic", "task", "summary", "assignee", "deadline", "priority", "context"],
        lineterminator="\n",
    )
    writer.writeheader()

    for epic in analysis.epics:
        for task in epic.tasks:
            writer.writerow({
                "type": "Task",
                "epic": epic.summary,
                "task": task.summary,
                "summary": task.summary,
                "assignee": task.assignee or "",
                "deadline": task.deadline or "",
                "priority": task.priority.value,
                "context": task.context,
            })
            for subtask in task.subtasks:
                writer.writerow({
                    "type": "Subtask",
                    "epic": epic.summary,
                    "task": task.summary,
                    "summary": subtask.summary,
                    "assignee": subtask.assignee or "",
                    "deadline": subtask.deadline or "",
                    "priority": subtask.priority.value,
                    "context": subtask.context,
                })

    return output.getvalue()
