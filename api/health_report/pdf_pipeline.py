from __future__ import annotations

from pathlib import Path

from docling.datamodel.base_models import ConversionStatus
from docling.document_converter import DocumentConverter


def convert_pdf_to_markdown(converter: DocumentConverter, file_path: Path) -> tuple[str, bool]:
    """
    将 PDF 转为 Markdown 正文。返回 (markdown, success)。
    """
    result = converter.convert(str(file_path))
    if result.status != ConversionStatus.SUCCESS:
        return "", False
    md = result.document.export_to_markdown()
    return md or "", True


def truncate_text(text: str, max_chars: int) -> tuple[str, bool]:
    if len(text) <= max_chars:
        return text, False
    return (
        text[:max_chars]
        + "\n\n[文档过长已截断；请仅根据以上可见内容抽取，不得臆测截断后内容。]",
        True,
    )
