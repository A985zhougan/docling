from __future__ import annotations

import os
from typing import Any, Dict, Optional

from api.pet_report.ai_client import call_anthropic_supplement, default_model, supplement_to_html_fragment
from api.pet_report.jsonutil import loads_json_flexible
from api.pet_report.rules_html import build_report_html
from api.pet_report.schemas import coerce_payload


def render_pet_report(
    raw_json: str,
    *,
    use_ai: bool = False,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    规则层生成完整 HTML；use_ai=True 且提供 api_key 时追加「AI 补充说明」块。
    返回 dict：html, meta
    """
    data = loads_json_flexible(raw_json)
    payload = coerce_payload(data)

    ai_html: Optional[str] = None
    ai_err: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None
    ai_model: Optional[str] = None

    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    anth_base_url = (base_url or "").strip() or os.environ.get("ANTHROPIC_BASE_URL")
    mdl = (model or "").strip() or default_model()

    if use_ai and key:
        sup, usage, ai_err = call_anthropic_supplement(
            payload,
            api_key=key,
            model=mdl,
            base_url=anth_base_url,
        )
        ai_model = mdl
        if sup and not ai_err:
            frag = supplement_to_html_fragment(sup)
            if frag:
                ai_html = frag
        elif ai_err:
            ai_html = None
    elif use_ai and not key:
        ai_err = "未设置 ANTHROPIC_API_KEY 或未传入 api_key"

    html_out = build_report_html(payload, ai_extra_html=ai_html)

    return {
        "html": html_out,
        "meta": {
            "use_ai_requested": use_ai,
            "ai_succeeded": bool(ai_html),
            "ai_error": ai_err,
            "model": ai_model if use_ai else None,
            "usage": usage,
        },
    }
