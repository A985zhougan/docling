from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from docling.document_converter import DocumentConverter

from api.health_report.ai_struct import (
    call_structure,
    default_base_url,
    default_model,
    resolve_provider,
)
from api.health_report.pdf_pipeline import convert_pdf_to_markdown, truncate_text
from api.health_report.render_html import build_health_report_html


# 控制送入模型的正文长度（中英混合，保守截断）
DEFAULT_MAX_MARKDOWN_CHARS = 100_000


def run_health_report_from_pdf(
    file_bytes: bytes,
    filename: str,
    *,
    api_key: Optional[str] = None,
    provider: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    max_markdown_chars: int = DEFAULT_MAX_MARKDOWN_CHARS,
) -> Dict[str, Any]:
    """PDF → Markdown → AI 结构化 → HTML。支持 anthropic / openai(兼容 chat completions)。"""
    import logging
    logger = logging.getLogger("health_report")
    
    p = resolve_provider(provider)
    logger.info(f"🔧 Provider: {p}")
    
    if p == "openai":
        key = (
            api_key
            or os.environ.get("OPENAI_API_KEY")
            or os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("ANTHROPIC_AUTH_TOKEN")
            or ""
        ).strip()
    else:
        # 代理商可能使用 ANTHROPIC_AUTH_TOKEN 而非标准的 ANTHROPIC_API_KEY
        key = (
            api_key
            or os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("ANTHROPIC_AUTH_TOKEN")
            or ""
        ).strip()
    
    logger.info(f"🔑 api_key param: {bool(api_key)}")
    logger.info(f"🔑 ANTHROPIC_API_KEY env: {bool(os.environ.get('ANTHROPIC_API_KEY'))}")
    logger.info(f"🔑 ANTHROPIC_AUTH_TOKEN env: {bool(os.environ.get('ANTHROPIC_AUTH_TOKEN'))}")
    logger.info(f"🔑 Final key available: {bool(key)} (len={len(key)})")

    if not key:
        hint = "OPENAI_API_KEY" if p == "openai" else "ANTHROPIC_API_KEY 或 ANTHROPIC_AUTH_TOKEN"
        logger.error(f"❌ No API key found! Looking for {hint}")
        raise ValueError(
            f"需要 AI API Key：请在服务端 .env.local 中设置 {hint}，或请求时传 ai_api_key / X-AI-Api-Key"
        )

    mdl = (model or "").strip() or default_model(p)
    base = (base_url or "").strip() or (default_base_url(p) or "")
    suffix = Path(filename).suffix.lower()
    if suffix != ".pdf":
        raise ValueError("仅支持 .pdf 文件")

    tmpdir = tempfile.mkdtemp()
    path = Path(tmpdir) / Path(filename).name
    try:
        path.write_bytes(file_bytes)
        conv = DocumentConverter()
        md, ok = convert_pdf_to_markdown(conv, path)
        if not ok:
            raise RuntimeError("PDF 文档转换失败")
        md_in, truncated = truncate_text(md, max_markdown_chars)

        payload, usage, err = call_structure(
            md_in,
            api_key=key,
            model=mdl,
            provider=p,
            base_url=base or None,
        )
        if err or payload is None:
            raise RuntimeError(err or "AI 结构化失败")

        html_out = build_health_report_html(payload)
        structured = payload.model_dump()
        return {
            "html": html_out,
            "structured": structured,
            "meta": {
                "filename": filename,
                "markdown_chars": len(md),
                "markdown_truncated": truncated,
                "provider": p,
                "base_url": base or None,
                "model": mdl,
                "usage": usage,
            },
        }
    finally:
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)
