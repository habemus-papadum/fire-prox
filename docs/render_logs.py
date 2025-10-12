#!/usr/bin/env python3
"""
Render Claude Code sessions for this repository into docs/sessionslogs.

The script locates Claude Code JSONL archives under ~/.claude/projects that
match the current repository (identified by the nearest pyproject.toml).
Each session is converted into a compact Markdown transcript that highlights
the main user prompt and assistant response while folding ancillary details
into <details> blocks. Generated logs live in docs/sessionslogs and the
mkdocs navigation is kept sorted by session start time.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

CLAUDE_PROJECTS_ROOT = Path.home() / ".claude" / "projects"
DOCS_SUBDIR = Path("docs")
SESSION_LOG_DIR_NAME = "sessionslogs"
SESSION_ID_PATTERN = re.compile(r"Session ID:\s*`?([\w-]+)`?")
TIMESTAMP_SLUG_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})")
SUMMARY_MAX_LENGTH = 100
# Sessions whose short IDs should be ignored when rendering.
IGNORED_SESSION_SUFFIXES = {"251119ea", "392f9b59"}


@dataclass
class SessionRecord:
    """Metadata wrapper for a Claude Code session JSONL file."""

    path: Path
    session_id: str
    start_time: Optional[str]
    end_time: Optional[str]
    project_dir: Optional[str]
    messages: List[dict]
    stats: Dict[str, int]

    @property
    def start_datetime(self) -> datetime:
        timestamp = self.start_time or ""
        parsed = parse_timestamp(timestamp)
        if parsed is None:
            # Fallback to file modification time if metadata is missing.
            mtime = self.path.stat().st_mtime
            return datetime.fromtimestamp(mtime, tz=timezone.utc)
        return parsed


def session_short_id(session: SessionRecord) -> str:
    """Return the canonical short identifier for a session."""
    return session.session_id.replace("-", "")[:8]


def parse_timestamp(value: str) -> Optional[datetime]:
    """Parse ISO8601 timestamps from Claude exports."""
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def find_project_root(start: Path) -> Path:
    """Walk up from start until a pyproject.toml is located."""
    for path in [start, *start.parents]:
        if (path / "pyproject.toml").exists():
            return path
    raise RuntimeError("Unable to locate project root (missing pyproject.toml).")


def claude_project_directory(project_root: Path) -> Path:
    """Map a repository path to Claude's normalized project directory."""
    normalized = str(project_root).replace("\\", "/")
    project_dir_name = normalized.replace("/", "-").replace(".", "-")
    if project_dir_name.startswith("-"):
        project_dir_name = project_dir_name[1:]
    return CLAUDE_PROJECTS_ROOT / f"-{project_dir_name}"


def discover_session_files(project_root: Path) -> Sequence[Path]:
    """List session JSONL files associated with the repository."""
    claude_dir = claude_project_directory(project_root)
    if not claude_dir.exists():
        return []
    return sorted(claude_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)


def parse_jsonl_file(file_path: Path) -> SessionRecord:
    """Parse messages and metadata from a Claude session archive."""
    messages: List[dict] = []
    metadata = {
        "session_id": None,
        "start_time": None,
        "end_time": None,
        "project_dir": None,
        "total_messages": 0,
        "user_messages": 0,
        "assistant_messages": 0,
        "tool_uses": 0,
    }

    with file_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                data = json.loads(line.strip())
            except json.JSONDecodeError:
                continue

            messages.append(data)

            if metadata["session_id"] is None and "sessionId" in data:
                metadata["session_id"] = data["sessionId"]

            if metadata["project_dir"] is None and "cwd" in data:
                metadata["project_dir"] = data["cwd"]

            if "timestamp" in data:
                timestamp = data["timestamp"]
                if metadata["start_time"] is None or timestamp < metadata["start_time"]:
                    metadata["start_time"] = timestamp
                if metadata["end_time"] is None or timestamp > metadata["end_time"]:
                    metadata["end_time"] = timestamp

            if "message" in data and "role" in data["message"]:
                role = data["message"]["role"]
                if role == "user":
                    metadata["user_messages"] += 1
                elif role == "assistant":
                    metadata["assistant_messages"] += 1

            if "message" in data and "content" in data["message"]:
                for content in data["message"]["content"]:
                    if isinstance(content, dict) and content.get("type") == "tool_use":
                        metadata["tool_uses"] += 1

    metadata["total_messages"] = len(messages)

    return SessionRecord(
        path=file_path,
        session_id=metadata["session_id"] or file_path.stem,
        start_time=metadata["start_time"],
        end_time=metadata["end_time"],
        project_dir=metadata["project_dir"],
        messages=messages,
        stats={
            "total_messages": metadata["total_messages"],
            "user_messages": metadata["user_messages"],
            "assistant_messages": metadata["assistant_messages"],
            "tool_uses": metadata["tool_uses"],
        },
    )


def load_existing_session_ids(output_dir: Path) -> Dict[str, Path]:
    """Read already-rendered sessions by scanning for their Session ID lines."""
    recorded: Dict[str, Path] = {}
    if not output_dir.exists():
        return recorded

    for file_path in output_dir.glob("*.md"):
        try:
            with file_path.open("r", encoding="utf-8") as handle:
                for _ in range(20):
                    line = handle.readline()
                    if not line:
                        break
                    match = SESSION_ID_PATTERN.search(line)
                    if match:
                        recorded[match.group(1)] = file_path
                        break
        except OSError:
            continue

    return recorded


def normalise_title(text: str) -> str:
    """Collapse whitespace for display strings."""
    return re.sub(r"\s+", " ", text.strip())


def condense_value(value, max_len: int = 32) -> str:
    """Return a short, human readable representation of a value."""
    if isinstance(value, (list, tuple)):
        rendered = ", ".join(condense_value(v, max_len=12) for v in value[:2])
        if len(value) > 2:
            rendered += ", …"
    elif isinstance(value, dict):
        keys = list(value.keys())
        rendered = "{"
        if keys:
            rendered += f"{keys[0]}=…"
            if len(keys) > 1:
                rendered += ", …"
        rendered += "}"
    else:
        rendered = str(value)

    rendered = re.sub(r"\s+", " ", rendered.strip())
    if len(rendered) > max_len:
        rendered = rendered[: max_len - 1] + "…"
    return rendered


def truncate_summary(summary: str, max_len: int = SUMMARY_MAX_LENGTH) -> str:
    """Trim summary text to a safe length."""
    summary = re.sub(r"\s+", " ", summary.strip())
    if len(summary) > max_len:
        return summary[: max_len - 1] + "…"
    return summary


def condensed_timestamp(timestamp: Optional[datetime]) -> str:
    """Return HH:MM timestamp or placeholder."""
    if not timestamp:
        return "--:--"
    return timestamp.strftime("%H:%M")


def condensed_model_name(model: Optional[str]) -> str:
    """Produce a short, human-friendly model label."""
    if not model:
        return ""
    token = model.split("/")[-1]
    token = token.replace("claude-", "")
    parts = [p for p in token.split("-") if p]
    if not parts:
        return token.capitalize()
    primary = parts[0].lower()
    lookup = {
        "sonnet": "Sonnet",
        "opus": "Opus",
        "haiku": "Haiku",
        "gpt": "GPT",
    }
    if primary in lookup:
        return lookup[primary]
    return primary.capitalize()


def format_duration_label(start: datetime, end: Optional[datetime]) -> str:
    """Create a compact, human-readable duration string."""
    if end is None or end <= start:
        return "unknown"

    total_seconds = int((end - start).total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts: List[str] = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if not parts and seconds:
        parts.append(f"{seconds}s")
    elif seconds and hours == 0 and minutes < 5:
        parts.append(f"{seconds}s")

    if not parts:
        parts.append("<1s")

    return " ".join(parts)


def summarise_tool_use(part: dict) -> str:
    name = part.get("name", "tool")
    input_payload = part.get("input")
    if isinstance(input_payload, dict) and input_payload:
        key = next(iter(input_payload))
        value = condense_value(input_payload[key])
        return f"{name} {key}={value}"
    return name


def summarise_tool_result(part: dict) -> str:
    identifier = part.get("tool_use_id") or part.get("name") or "result"
    content = part.get("content", "")
    if isinstance(content, str) and content.strip():
        value = condense_value(content.strip(), max_len=40)
        return f"{identifier} → {value}"
    if isinstance(content, list) and content:
        value = condense_value(content[0], max_len=40)
        return f"{identifier} → {value}"
    return f"{identifier} (no content)"


def summarise_usage(usage: dict) -> Optional[str]:
    if not usage:
        return None
    in_tok = usage.get("input_tokens")
    out_tok = usage.get("output_tokens")
    if in_tok is None and out_tok is None:
        return None
    if in_tok is not None and out_tok is not None:
        return f"tok {in_tok}/{out_tok}"
    if in_tok is not None:
        return f"in {in_tok}"
    return f"out {out_tok}"


def summarise_tool_metadata(tool_meta: dict) -> Optional[str]:
    if not isinstance(tool_meta, dict):
        return None
    duration = tool_meta.get("durationMs")
    if duration is None:
        return None
    seconds = duration / 1000
    if seconds >= 1:
        return f"{seconds:.1f}s"
    return f"{seconds*1000:.0f}ms"


def summarise_message(message: dict) -> str:
    """Create a condensed single-line summary for messages without primary text."""
    msg = message.get("message", {})
    content = msg.get("content")
    summaries: List[str] = []

    if isinstance(content, list):
        for part in content:
            if not isinstance(part, dict):
                continue
            kind = part.get("type")
            if kind == "tool_use":
                summaries.append(f"tool {summarise_tool_use(part)}")
            elif kind == "tool_result":
                summaries.append(f"result {summarise_tool_result(part)}")
            elif kind == "thinking":
                summaries.append("internal reasoning")
            elif kind == "text":
                text = part.get("text", "").strip()
                if text:
                    summaries.append(condense_value(text, max_len=40))
    elif isinstance(content, str) and content.strip():
        summaries.append(condense_value(content.strip(), max_len=60))

    usage_summary = summarise_usage(msg.get("usage", {}))
    if usage_summary:
        summaries.append(usage_summary)

    metadata_summary = summarise_tool_metadata(message.get("toolUseResult", {}))
    if metadata_summary:
        summaries.append(metadata_summary)

    if not summaries:
        event_type = message.get("type") or msg.get("role") or "event"
        summaries.append(f"{event_type} (no content)")

    return truncate_summary("; ".join(summaries))


def build_compact_line(
    timestamp: Optional[datetime], role: str, icon: str, model: Optional[str], summary: str
) -> str:
    """Assemble compact single-line representation for non-detailed messages."""
    ts = condensed_timestamp(timestamp)
    if role == "assistant":
        descriptor = condensed_model_name(model) or "Assistant"
    elif role == "user":
        descriptor = "User"
    else:
        descriptor = role.capitalize()
    components = [ts, icon, descriptor, "—", summary]
    return " ".join(part for part in components if part)


def format_primary_and_details(message: dict) -> Tuple[str, List[Tuple[str, str, str]]]:
    """
    Return the primary text along with detail sections.

    Detail tuples are (title, body, block_type) where block_type is one of
    "text", "code", or "json".
    """
    if "message" not in message:
        return "", []

    msg = message["message"]
    content = msg.get("content", "")
    role = msg.get("role", "assistant")

    if isinstance(content, str):
        return content.strip(), []

    if not isinstance(content, list):
        return "", []

    primary_fragments: List[str] = []
    details: List[Tuple[str, str, str]] = []

    for idx, part in enumerate(content):
        if not isinstance(part, dict):
            continue

        part_type = part.get("type")

        if part_type == "text":
            text_value = part.get("text", "").strip()
            if not text_value:
                continue

            if role == "assistant":
                if not primary_fragments:
                    primary_fragments.append(text_value)
                else:
                    details.append(("Additional Text", text_value, "text"))
            else:
                # User prompts include all text as part of the primary body.
                primary_fragments.append(text_value)

        elif part_type == "thinking":
            details.append(
                (
                    "Internal Reasoning",
                    part.get("thinking", "").strip(),
                    "code",
                )
            )

        elif part_type == "tool_use":
            tool_name = part.get("name", "unknown tool")
            tool_id = part.get("id", "")
            payload = json.dumps(part.get("input", {}), indent=2)
            title = f"Tool Use — {tool_name}"
            if tool_id:
                title += f" ({tool_id})"
            details.append((title, payload, "json"))

        elif part_type == "tool_result":
            title = "Tool Result"
            if "tool_use_id" in part:
                title += f" ({part['tool_use_id']})"
            result_content = part.get("content", "")
            if isinstance(result_content, str):
                body = result_content.strip()
                block_type = "code"
            else:
                body = json.dumps(result_content, indent=2)
                block_type = "json"
            details.append((title, body, block_type))

    primary_text = "\n\n".join(primary_fragments).strip()
    return primary_text, details


def format_message_markdown(message: dict) -> str:
    """Generate compact markdown for a single Claude message."""
    if "message" not in message:
        return ""

    msg = message["message"]
    timestamp = parse_timestamp(message.get("timestamp", ""))
    ts_label = timestamp.strftime("%Y-%m-%d %H:%M:%S %Z") if timestamp else "Unknown time"

    role = msg.get("role", "unknown")
    icon = "👤" if role == "user" else "🤖"
    model = ""
    if role == "assistant" and msg.get("model"):
        model = f" ({msg['model']})"

    header = f"### [{ts_label}] {icon} {role.capitalize()}{model}"
    primary_text, detail_sections = format_primary_and_details(message)

    if primary_text:
        lines: List[str] = [header]
        lines.extend(["", primary_text, ""])
        extra_details = gather_message_metadata_details(message, detail_sections)
        if extra_details:
            lines.extend(render_details_block(extra_details))
        return "\n".join(line for line in lines if line is not None).strip()

    summary_line = summarise_message(message)
    return build_compact_line(timestamp, role, icon, msg.get("model"), summary_line)


def gather_message_metadata_details(
    message: dict, detail_sections: List[Tuple[str, str, str]]
) -> List[Tuple[str, str, str]]:
    """Attach usage metadata to the detail view."""
    combined = list(detail_sections)

    msg = message.get("message", {})
    usage = msg.get("usage")
    if isinstance(usage, dict):
        payload = json.dumps(usage, indent=2)
        combined.append(("Token Usage", payload, "json"))

    tool_result_meta = message.get("toolUseResult")
    if isinstance(tool_result_meta, dict):
        payload = json.dumps(tool_result_meta, indent=2)
        combined.append(("Tool Execution Metadata", payload, "json"))

    return combined


def render_details_block(sections: Iterable[Tuple[str, str, str]]) -> List[str]:
    """Render a <details> block from detail section tuples."""
    details = list(sections)
    if not details:
        return []

    lines = ["<details>", "<summary>Details</summary>", ""]
    for title, body, block_type in details:
        title = normalise_title(title)
        lines.append(f"#### {title}")
        if block_type == "json":
            lines.append("```json")
            lines.append(body)
            lines.append("```")
        elif block_type == "code":
            lines.append("```")
            lines.append(body)
            lines.append("```")
        else:
            lines.append(body)
        lines.append("")
    lines.append("</details>")
    lines.append("")
    return lines


def build_markdown(session: SessionRecord) -> str:
    """Assemble the Markdown transcript for a session."""
    start_dt = session.start_datetime
    end_dt = parse_timestamp(session.end_time or "")

    header_lines = [
        f"# Claude Code Session — {start_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}",
        "",
        f"- Session ID: `{session.session_id}`",
        f"- Project: `{session.project_dir or ''}`",
        f"- Started: {start_dt.isoformat()}",
    ]

    if end_dt:
        header_lines.append(f"- Ended: {end_dt.isoformat()}")
    header_lines.extend(
        [
            f"- Total Messages: {session.stats['total_messages']} "
            f"(user: {session.stats['user_messages']}, assistant: {session.stats['assistant_messages']})",
            f"- Tool Uses: {session.stats['tool_uses']}",
            "",
            "---",
            "",
            "## Conversation",
            "",
        ]
    )

    body_blocks: List[str] = []
    for message in session.messages:
        rendered = format_message_markdown(message)
        if rendered:
            body_blocks.append(rendered)
            body_blocks.append("")  # Spacer between messages.

    return "\n".join(header_lines + body_blocks).rstrip() + "\n"


def derive_output_filename(session: SessionRecord) -> str:
    """Generate a tidy filename for the session markdown."""
    start_slug = session.start_datetime.strftime("%Y-%m-%d_%H-%M-%S")
    short_id = session_short_id(session)
    return f"{start_slug}_{short_id}.md"


def write_markdown(output_dir: Path, session: SessionRecord, overwrite: bool = False) -> Path:
    """Persist the rendered markdown to disk."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / derive_output_filename(session)

    if output_path.exists() and not overwrite:
        return output_path

    markdown = build_markdown(session)
    output_path.write_text(markdown, encoding="utf-8")
    return output_path


def format_nav_label(session: SessionRecord) -> str:
    """Build the navigation label with timestamp and duration."""
    start_dt = session.start_datetime
    end_dt = parse_timestamp(session.end_time or "")
    duration = format_duration_label(start_dt, end_dt)
    return f"{start_dt.strftime('%Y-%m-%d %H:%M')} ({duration})"


def update_mkdocs_nav(project_root: Path, rendered_files: Sequence[Tuple[SessionRecord, Path]]) -> None:
    """Add rendered sessions to the mkdocs navigation sorted by timestamp."""
    if not rendered_files:
        return

    mkdocs_path = project_root / "mkdocs.yml"
    if not mkdocs_path.exists():
        raise RuntimeError("mkdocs.yml not found; cannot update navigation.")

    lines = mkdocs_path.read_text().splitlines()
    section_label = "- Claude Code Sessions"
    section_index = next((i for i, line in enumerate(lines) if section_label in line), None)

    if section_index is None:
        raise RuntimeError("Claude Code Sessions nav section not found in mkdocs.yml.")

    start_line = lines[section_index]
    base_indent = re.match(r"^\s*", start_line).group(0)
    child_indent = base_indent + "  "

    # Find the extent of the section (up to the next top-level nav item).
    end_index = section_index + 1
    while end_index < len(lines):
        line = lines[end_index]
        if re.match(rf"^{base_indent}-\s+\S", line) and not line.startswith(child_indent):
            break
        end_index += 1

    section_body = lines[section_index + 1 : end_index]

    managed_entries: Dict[str, str] = {}
    preserved_lines: List[str] = []

    for line in section_body:
        if line.startswith(f"{child_indent}- "):
            entry = line.strip()[2:]  # drop leading "- "
            if ":" in entry:
                label_part, path_part = entry.rsplit(":", 1)
                path = path_part.strip()
                label = label_part.strip()
                if path.startswith(f"{SESSION_LOG_DIR_NAME}/"):
                    managed_entries[path] = label
                    continue
        preserved_lines.append(line)

    for session, output_path in rendered_files:
        rel_path = f"{SESSION_LOG_DIR_NAME}/{output_path.name}"
        label = format_nav_label(session)
        managed_entries[rel_path] = label

    sortable_entries: List[Tuple[datetime, str, str]] = []
    for rel_path, label in managed_entries.items():
        match = TIMESTAMP_SLUG_PATTERN.match(Path(rel_path).name)
        if match:
            dt = datetime.strptime(match.group(1), "%Y-%m-%d_%H-%M-%S").replace(tzinfo=timezone.utc)
        else:
            dt = datetime.min.replace(tzinfo=timezone.utc)
        sortable_entries.append((dt, label, rel_path))

    sortable_entries.sort(key=lambda item: item[0], reverse=True)

    new_section_body = [start_line]
    for _, label, rel_path in sortable_entries:
        new_section_body.append(f"{child_indent}- {label}: {rel_path}")

    for line in preserved_lines:
        if line.strip() or line == "":
            new_section_body.append(line)

    lines[section_index : end_index] = new_section_body
    mkdocs_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def session_matches_project(session: SessionRecord, project_root: Path) -> bool:
    """Ensure the session belongs to this repository."""
    if not session.project_dir:
        return False
    try:
        recorded = Path(session.project_dir).resolve()
    except OSError:
        return False
    return recorded == project_root.resolve()


def render_sessions(
    project_root: Path,
    overwrite: bool = False,
    session_filter: Optional[str] = None,
    dry_run: bool = False,
) -> List[Tuple[SessionRecord, Path]]:
    """Render matching sessions and return list of (session, output_path)."""
    docs_dir = project_root / DOCS_SUBDIR
    output_dir = docs_dir / SESSION_LOG_DIR_NAME

    existing_sessions = load_existing_session_ids(output_dir)
    rendered: List[Tuple[SessionRecord, Path]] = []

    session_files = discover_session_files(project_root)
    for file_path in session_files:
        session = parse_jsonl_file(file_path)

        if session_short_id(session) in IGNORED_SESSION_SUFFIXES:
            continue

        if session_filter and session.session_id != session_filter:
            continue

        if not session_matches_project(session, project_root):
            continue

        if not overwrite and session.session_id in existing_sessions:
            continue

        if dry_run:
            rendered.append((session, output_dir / derive_output_filename(session)))
            continue

        output_path = write_markdown(output_dir, session, overwrite=overwrite)
        rendered.append((session, output_path))

    return rendered


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Render Claude Code session logs into docs/sessionslogs.")
    parser.add_argument("--session-id", help="Render only the specified session ID.")
    parser.add_argument("--overwrite", action="store_true", help="Re-render markdown even if it already exists.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be rendered without writing files.")

    args = parser.parse_args(argv)

    project_root = find_project_root(Path.cwd())
    rendered = render_sessions(
        project_root=project_root,
        overwrite=args.overwrite,
        session_filter=args.session_id,
        dry_run=args.dry_run,
    )

    if not rendered:
        print("No new sessions rendered.")
        return 0

    if args.dry_run:
        print("Sessions that would be rendered:")
        for session, path in rendered:
            print(f"  - {session.session_id} -> {path}")
        return 0

    update_mkdocs_nav(project_root, rendered)

    print("Rendered session logs:")
    for session, path in rendered:
        print(f"  - {session.session_id} -> {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
