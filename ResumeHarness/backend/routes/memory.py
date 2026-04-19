"""用户记忆 CRUD API。"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request, UploadFile, File

from resume_agent.config.settings import get_settings
from resume_agent.exceptions import MemoryNotFoundError
from resume_agent.memory.manager import (
    WRITABLE_MEMORY_FILES,
    list_memory_files,
    read_memory_file,
    write_memory_file,
)
from resume_agent.memory.paths import ensure_user_dirs, get_user_memory_dir

logger = logging.getLogger(__name__)

router = APIRouter(tags=["memory"])


def _get_user_id(request: Request) -> str:
    """获取当前用户 ID（P1 开发模式使用默认值）。"""
    settings = get_settings()
    return settings.effective_default_user_id


@router.get("/memory")
async def list_memory(request: Request) -> dict[str, Any]:
    """获取当前用户记忆文档列表。"""
    user_id = _get_user_id(request)
    ensure_user_dirs(user_id)

    files = list_memory_files(user_id)
    documents = []
    for path in files:
        try:
            stat = path.stat()
            documents.append({
                "name": path.name,
                "size_bytes": stat.st_size,
                "modified_at": stat.st_mtime,
                "writable": path.name in WRITABLE_MEMORY_FILES,
            })
        except OSError:
            continue

    return {"documents": documents}


@router.get("/memory/{doc_name}")
async def get_memory(doc_name: str, request: Request) -> dict[str, Any]:
    """获取指定记忆文档内容。"""
    user_id = _get_user_id(request)
    content = read_memory_file(user_id, doc_name)
    if content is None:
        raise HTTPException(status_code=404, detail=f"记忆文档不存在: {doc_name}")
    return {"name": doc_name, "content": content}


@router.put("/memory/{doc_name}")
async def update_memory(
    doc_name: str,
    request: Request,
    body: dict[str, Any],
) -> dict[str, Any]:
    """更新记忆文档内容。

    Body:
        content: 文档内容（Markdown 格式）
        mode: 写入模式 - "append" 追加或 "replace" 替换，默认 "replace"
    """
    user_id = _get_user_id(request)
    content = body.get("content", "")
    mode = body.get("mode", "replace")

    if not content.strip():
        raise HTTPException(status_code=400, detail="内容不能为空")

    if mode not in ("append", "replace"):
        raise HTTPException(status_code=400, detail="mode 必须为 'append' 或 'replace'")

    # 简历原文通过上传 API 更新，不允许直接编辑
    if doc_name == "简历原文.md":
        raise HTTPException(status_code=400, detail="简历原文请通过上传 API 更新")

    try:
        path = write_memory_file(user_id, doc_name, content, mode=mode)
        return {"name": doc_name, "path": str(path), "mode": mode}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/memory/{doc_name}")
async def delete_memory(doc_name: str, request: Request) -> dict[str, Any]:
    """删除记忆文档。"""
    user_id = _get_user_id(request)
    settings = get_settings()
    memory_dir = settings.get_user_memory_dir(user_id)
    path = memory_dir / doc_name

    if not path.exists():
        raise HTTPException(status_code=404, detail=f"记忆文档不存在: {doc_name}")

    # 保护简历原文不允许通过此接口删除
    if doc_name == "简历原文.md":
        raise HTTPException(status_code=400, detail="不允许删除简历原文")

    try:
        path.unlink()
        logger.info("删除记忆文档: user=%s doc=%s", user_id, doc_name)
        return {"deleted": True, "name": doc_name}
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"删除失败: {exc}")


@router.post("/memory/upload")
async def upload_resume(
    request: Request,
    file: UploadFile = File(...),
) -> dict[str, Any]:
    """上传简历原文。

    支持上传 .md / .txt / .pdf 文件，内容将存为 memory/简历原文.md。
    PDF 文件暂不支持自动解析，仅存储原始文件。
    """
    user_id = _get_user_id(request)
    ensure_user_dirs(user_id)

    # 读取上传文件内容
    try:
        raw_bytes = await file.read()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"读取上传文件失败: {exc}")

    filename = file.filename or "resume.txt"

    if filename.endswith(".pdf"):
        # PDF 文件暂不支持自动解析，返回提示
        raise HTTPException(
            status_code=400,
            detail="暂不支持 PDF 文件自动解析，请上传 Markdown 或纯文本格式的简历",
        )

    # 将上传内容存为简历原文
    content = raw_bytes.decode("utf-8", errors="replace").strip()
    if not content:
        raise HTTPException(status_code=400, detail="上传文件内容为空")

    settings = get_settings()
    memory_dir = settings.get_user_memory_dir(user_id)
    resume_path = memory_dir / "简历原文.md"

    # 容量控制
    max_bytes = settings.memory_resume_max_bytes
    if len(content.encode("utf-8")) > max_bytes:
        content = content[:max_bytes]

    resume_path.write_text(content + "\n", encoding="utf-8")
    logger.info("上传简历原文: user=%s filename=%s size=%d", user_id, filename, len(raw_bytes))

    return {
        "name": "简历原文.md",
        "path": str(resume_path),
        "size_bytes": len(content.encode("utf-8")),
        "source_filename": filename,
    }
