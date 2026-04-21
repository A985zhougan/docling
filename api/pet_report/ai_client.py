from __future__ import annotations

import html
import json
import os
from typing import Any, Dict, Optional, Tuple

from api.pet_report.schemas import PetReportPayload


def _slim_facts(payload: PetReportPayload) -> str:
    """仅抽取非「正常」位点与关键发现标题，控制输入 token。"""
    lines: list[str] = []
    pi = payload.pet_info
    if pi.name or pi.breed:
        lines.append(f"宠物：{pi.name or ''} {pi.breed or ''}".strip())
    for kf in payload.key_findings[:12]:
        bits = [x for x in [kf.condition, kf.gene, kf.risk_level] if x]
        if bits:
            lines.append(" · ".join(bits))
    abnormal = [(g, s) for g, s in payload.details.items() if (s or "").strip() != "正常"]
    abnormal.sort(key=lambda x: x[0])
    for g, s in abnormal[:80]:
        lines.append(f"{g}: {s}")
    if len(abnormal) > 80:
        lines.append(f"… 另有 {len(abnormal) - 80} 个非「正常」位点未列出")
    return "\n".join(lines)


SYSTEM_PROMPT = (
    "你是宠物基因检测报告撰写助手。只根据用户给出的检测要点撰写说明，不得编造未出现的基因或诊断。"
    "输出必须是严格 JSON 对象，不要 Markdown 围栏。"
)


def _user_prompt(facts: str) -> str:
    return (
        "根据以下要点，用简体中文写一段给宠物家长的「综合说明」，并给出 3 条简短行动建议。\n"
        'JSON 格式：{"summary":"200字以内","actions":["","",""]}\n\n'
        "要点：\n"
        f"{facts}"
    )


def _normalize_base_url(base_url: Optional[str]) -> Optional[str]:
    if not base_url:
        return None
    u = base_url.strip().rstrip("/")
    return u or None


def call_anthropic_supplement(
    payload: PetReportPayload,
    *,
    api_key: str,
    model: str,
    base_url: Optional[str] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[str]]:
    """
    调用 Anthropic Messages API，返回 (parsed_json, usage_dict, error_message)。
    parsed_json 含 summary 与 actions；失败时 error_message 非空。
    """
    try:
        import anthropic
    except ImportError as e:
        return None, None, f"未安装 anthropic 包：{e}"

    facts = _slim_facts(payload)
    kwargs: Dict[str, Any] = {"api_key": api_key}
    norm_base = _normalize_base_url(base_url)
    if norm_base:
        kwargs["base_url"] = norm_base
    client = anthropic.Anthropic(**kwargs)
    msg = client.messages.create(
        model=model,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _user_prompt(facts)}],
    )
    usage: Dict[str, Any] = {}
    if getattr(msg, "usage", None):
        usage = {
            "input_tokens": getattr(msg.usage, "input_tokens", None),
            "output_tokens": getattr(msg.usage, "output_tokens", None),
        }
    text = ""
    for block in msg.content:
        if getattr(block, "type", None) == "text":
            text += block.text
    text = text.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            data = json.loads(text[start : end + 1])
        else:
            return None, usage, "模型返回非 JSON"
    if not isinstance(data, dict):
        return None, usage, "JSON 根类型错误"
    return data, usage, None


def supplement_to_html_fragment(data: Dict[str, Any]) -> str:
    """将 AI JSON 转为已转义的 HTML 片段（放入规则层容器内）。"""
    summary = data.get("summary") if isinstance(data.get("summary"), str) else ""
    actions = data.get("actions") if isinstance(data.get("actions"), list) else []
    parts: list[str] = []
    if summary:
        parts.append(f"<p style='margin:8px 0;line-height:1.6'>{html.escape(summary, quote=False)}</p>")
    if actions:
        parts.append("<ul style='margin:8px 0 0 18px'>")
        for a in actions[:8]:
            if isinstance(a, str) and a.strip():
                parts.append(f"<li>{html.escape(a.strip(), quote=False)}</li>")
        parts.append("</ul>")
    return "".join(parts) if parts else ""


def default_model() -> str:
    return os.environ.get("PET_REPORT_ANTHROPIC_MODEL", "claude-sonnet-4-5")
