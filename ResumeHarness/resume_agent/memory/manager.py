"""记忆加载/写入/容量控制。"""

from __future__ import annotations

import logging
from pathlib import Path
from re import sub

from resume_agent.config.settings import get_settings
from resume_agent.memory.paths import get_user_memory_dir, ensure_user_dirs

log = logging.getLogger(__name__)

# 允许 LLM 通过 memory_write 写入的文件名
WRITABLE_MEMORY_FILES = {"职业偏好.md", "技能标签.md", "优化历史.md", "custom_instructions.md"}

# 简历原文不允许 LLM 修改
PROTECTED_MEMORY_FILES = {"简历原文.md"}


def list_memory_files(user_id: str) -> list[Path]:
    """列出用户记忆目录中的 markdown 文件。"""
    memory_dir = get_user_memory_dir(user_id)
    return sorted(path for path in memory_dir.glob("*.md"))


def load_memory_prompt(user_id: str, *, max_files: int = 5) -> str | None:
    """加载用户记忆内容，组装为提示词片段。"""
    memory_dir = get_user_memory_dir(user_id)
    settings = get_settings()

    lines: list[str] = [
        "# Resume Agent Memory",
        f"- 用户记忆目录: {memory_dir}",
        "- 此记忆包含用户的稳定偏好和持久上下文。",
    ]

    files = list_memory_files(user_id)[:max_files]
    if not files:
        return None

    for path in files:
        try:
            content = path.read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            continue
        if not content:
            continue
        max_bytes = (
            settings.memory_resume_max_bytes
            if path.name == "简历原文.md"
            else settings.memory_other_max_bytes
        )
        # 简单截断
        if len(content.encode("utf-8")) > max_bytes:
            content = content[:max_bytes]
        lines.extend(["", f"## {path.name}", "```md", content, "```"])

    return "\n".join(lines)


def add_memory_entry(user_id: str, title: str, content: str) -> Path:
    """创建一个记忆文件。"""
    memory_dir = get_user_memory_dir(user_id)
    memory_dir.mkdir(parents=True, exist_ok=True)
    slug = sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "_", title.strip().lower()).strip("_") or "memory"
    path = memory_dir / f"{slug}.md"
    path.write_text(content.strip() + "\n", encoding="utf-8")
    return path


def write_memory_file(
    user_id: str,
    doc_name: str,
    content: str,
    mode: str = "append",
) -> Path:
    """写入记忆文件（供 memory_write 工具调用）。

    Args:
        user_id: 用户 ID
        doc_name: 目标文件名（必须是 WRITABLE_MEMORY_FILES 之一）
        content: 要写入的内容
        mode: "append" 追加或 "replace" 替换
    """
    if doc_name in PROTECTED_MEMORY_FILES:
        raise ValueError(f"不允许通过 memory_write 修改 {doc_name}，请使用上传 API")
    if doc_name not in WRITABLE_MEMORY_FILES:
        raise ValueError(f"不支持的记忆文件名: {doc_name}，允许的文件: {WRITABLE_MEMORY_FILES}")

    ensure_user_dirs(user_id)
    memory_dir = get_user_memory_dir(user_id)
    path = memory_dir / doc_name

    settings = get_settings()
    max_bytes = settings.memory_other_max_bytes

    if mode == "replace":
        # 替换模式：直接写入
        final_content = content.strip()
    else:
        # 追加模式：读取现有内容并追加
        existing = ""
        if path.exists():
            existing = path.read_text(encoding="utf-8", errors="replace").strip()

        if existing:
            final_content = existing + "\n\n" + content.strip()
        else:
            final_content = content.strip()

    # 容量控制：超出限制时，保留新内容，截断旧内容
    if len(final_content.encode("utf-8")) > max_bytes:
        if mode == "append" and existing:
            # 保留最新追加的内容，截断旧内容
            keep_new = content.strip()
            available = max_bytes - len(keep_new.encode("utf-8")) - 4  # 留分隔符空间
            if available > 0:
                final_content = existing[:available] + "\n\n" + keep_new
            else:
                final_content = keep_new[:max_bytes]
        else:
            final_content = final_content[:max_bytes]

    path.write_text(final_content.strip() + "\n", encoding="utf-8")
    log.info("写入记忆文件: user=%s doc=%s mode=%s", user_id, doc_name, mode)
    return path


def read_memory_file(user_id: str, doc_name: str) -> str | None:
    """读取记忆文件内容。"""
    memory_dir = get_user_memory_dir(user_id)
    path = memory_dir / doc_name
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
