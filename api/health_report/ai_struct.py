from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Optional, Tuple

from api.health_report.schemas import AIHealthReportPayload


STRUCT_SYSTEM = """你是兽医检验与宠物健康报告结构化助手。用户给出来自 PDF 经工具转换的 Markdown 正文，可能含乱序、分页重复或 OCR 噪声。
你的任务：只依据可见文字与表格内容，抽取并整理为一份「AI健康报告」用的 JSON。禁止编造文档中未出现的数值、单位与参考范围；无法识别时对应字段用 null、空字符串或空数组。
必须只输出一个 JSON 对象，不要使用 Markdown 代码围栏，不要添加任何解释性文字。

JSON 字段约定（均为简体中文为主）：
- report_title: 字符串，默认 "AI健康报告"
- pet_name: 宠物名或 null
- report_date: 日期字符串或 null
- overall_score: 0-100 的数字或 null（文档无明确总分时填 null）
- overall_status: 简短状态，如 "正常"/"注意"/"警告"/"未知"
- ai_summary: 2-5 句综合健康评估（勿诊断性下结论，可写「建议复查」类表述）
- categories: 数组，每项含 name, status_label, interpretation, recommendations（按文档中的大项拆分，如肝、肾、血糖等；无则 [])
- data_tables: 数组，每项含 section_title（表标题）, columns（字符串数组）, rows（二维字符串数组，每行列数与 columns 对齐）
- disclaimer: 一句免责说明

若文档并非检验报告，仍尽量抽取标题、列表与表格为 data_tables，overall_status 可用 "未知"，ai_summary 说明文档性质。"""


def _extract_json_object(text: str) -> Dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        raise ValueError("模型未返回可解析的 JSON")
    return json.loads(m.group(0))


def _normalize_base_url(base_url: Optional[str]) -> Optional[str]:
    if not base_url:
        return None
    u = base_url.strip().rstrip("/")
    return u or None


def _openai_chat_completions_url(base_url: str) -> str:
    """兼容用户传 /v1 或根地址两种写法。"""
    if base_url.endswith("/v1"):
        return base_url + "/chat/completions"
    return base_url + "/v1/chat/completions"


def call_anthropic_structure(
    markdown: str,
    *,
    api_key: str,
    model: str,
    base_url: Optional[str] = None,
) -> Tuple[Optional[AIHealthReportPayload], Optional[Dict[str, Any]], Optional[str]]:
    """返回 (payload, usage, error)。"""
    try:
        import anthropic
    except ImportError as e:
        return None, None, f"未安装 anthropic：{e}"

    kwargs: Dict[str, Any] = {"api_key": api_key}
    norm_base = _normalize_base_url(base_url)
    if norm_base:
        kwargs["base_url"] = norm_base
    
    # 某些代理商要求伪装成 Claude Code 客户端
    # 模拟 Cursor IDE 的请求 headers
    kwargs["default_headers"] = {
        "anthropic-client": "cursor-code"
    }

    client = anthropic.Anthropic(**kwargs)
    msg = client.messages.create(
        model=model,
        max_tokens=8192,
        system=STRUCT_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": "以下为 PDF 转换得到的 Markdown，请输出约定 JSON：\n\n" + markdown,
            }
        ],
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
    try:
        raw = _extract_json_object(text)
        payload = AIHealthReportPayload.model_validate(raw)
        return payload, usage, None
    except Exception as e:
        return None, usage, f"JSON 解析或校验失败: {e}"


def call_openai_compatible_structure(
    markdown: str,
    *,
    api_key: str,
    model: str,
    base_url: str,
) -> Tuple[Optional[AIHealthReportPayload], Optional[Dict[str, Any]], Optional[str]]:
    """调用 OpenAI 兼容的 Chat Completions 接口，返回 (payload, usage, error)。"""
    try:
        import requests
    except ImportError as e:
        return None, None, f"未安装 requests：{e}"

    base = _normalize_base_url(base_url)
    if not base:
        return None, None, "openai provider 需要 ai_base_url（订阅链接）"

    endpoint = _openai_chat_completions_url(base)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": STRUCT_SYSTEM},
            {
                "role": "user",
                "content": "以下为 PDF 转换得到的 Markdown，请输出约定 JSON：\n\n"
                + markdown,
            },
        ],
    }
    try:
        resp = requests.post(endpoint, headers=headers, json=body, timeout=180)
    except Exception as e:
        return None, None, f"请求 OpenAI 兼容接口失败: {e}"

    if resp.status_code >= 400:
        raw = resp.text[:500]
        return None, None, f"OpenAI 兼容接口调用失败({resp.status_code}): {raw}"

    try:
        data = resp.json()
    except Exception as e:
        return None, None, f"OpenAI 兼容接口返回非 JSON: {e}"

    usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
    usage = {
        "input_tokens": usage.get("prompt_tokens"),
        "output_tokens": usage.get("completion_tokens"),
    }

    content = ""
    try:
        choices = data.get("choices") or []
        message = choices[0].get("message", {}) if choices else {}
        content = message.get("content") or ""
    except Exception:
        content = ""
    if not isinstance(content, str) or not content.strip():
        return None, usage, "OpenAI 兼容接口未返回有效内容"

    try:
        raw = _extract_json_object(content)
        payload = AIHealthReportPayload.model_validate(raw)
        return payload, usage, None
    except Exception as e:
        return None, usage, f"JSON 解析或校验失败: {e}"


def resolve_provider(provider: Optional[str]) -> str:
    raw = (provider or os.environ.get("HEALTH_REPORT_AI_PROVIDER") or "openai").strip()
    low = raw.lower()
    if low in ("anthropic", "claude"):
        return "anthropic"
    if low in ("openai", "openai_compatible", "compat", "compatible"):
        return "openai"
    return "openai"


def call_structure(
    markdown: str,
    *,
    api_key: str,
    model: str,
    provider: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Tuple[Optional[AIHealthReportPayload], Optional[Dict[str, Any]], Optional[str]]:
    p = resolve_provider(provider)
    if p == "openai":
        return call_openai_compatible_structure(
            markdown, api_key=api_key, model=model, base_url=base_url or ""
        )
    return call_anthropic_structure(
        markdown, api_key=api_key, model=model, base_url=base_url
    )


def default_model(provider: Optional[str] = None) -> str:
    p = resolve_provider(provider)
    if p == "openai":
        return os.environ.get("PET_REPORT_OPENAI_MODEL", "deepseek-chat")
    return os.environ.get("PET_REPORT_ANTHROPIC_MODEL", "claude-sonnet-4-5")


def default_base_url(provider: Optional[str] = None) -> Optional[str]:
    p = resolve_provider(provider)
    if p == "openai":
        return _normalize_base_url(os.environ.get("OPENAI_BASE_URL", "https://api.deepseek.com"))
    return _normalize_base_url(os.environ.get("ANTHROPIC_BASE_URL"))
