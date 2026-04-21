from __future__ import annotations

import html
from typing import List

from api.health_report.schemas import AIHealthReportPayload


def _e(s: str | None) -> str:
    return html.escape(s or "", quote=True)


def _status_class(status: str | None) -> str:
    s = (status or "").strip()
    if any(x in s for x in ("警告", "异常", "高", "低", "危")):
        return "st-warn"
    if any(x in s for x in ("注意", "临界", "复查")):
        return "st-caution"
    if "正常" in s or s in ("", "-", "—"):
        return "st-ok"
    return "st-muted"


def build_health_report_html(payload: AIHealthReportPayload) -> str:
    parts: List[str] = []
    parts.append("<!DOCTYPE html>")
    parts.append('<html lang="zh-CN"><head><meta charset="utf-8"/>')
    parts.append("<title>" + _e(payload.report_title) + "</title>")
    parts.append(
        "<style>"
        "*{box-sizing:border-box;}"
        "body{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;"
        "color:#222;background:linear-gradient(180deg,#fff5f7 0%,#f1f8f4 40%,#fafafa 100%);min-height:100vh;}"
        ".shell{max-width:920px;margin:0 auto;padding:28px 20px 48px;}"
        "header.hero{background:linear-gradient(135deg,#ffe4ec 0%,#e8f5e9 100%);border-radius:16px;"
        "padding:28px 24px 24px;margin-bottom:20px;box-shadow:0 2px 12px rgba(0,0,0,.06);"
        "display:flex;align-items:center;gap:16px;}"
        "header.hero .mark{font-size:42px;line-height:1;}"
        "header.hero h1{margin:0 0 6px;font-size:24px;font-weight:700;}"
        "header.hero .sub{margin:0;color:#555;font-size:14px;}"
        ".score-row{display:flex;flex-wrap:wrap;gap:16px;align-items:center;margin-top:12px;}"
        ".score{font-size:36px;font-weight:800;color:#2e7d32;}"
        ".pill{display:inline-block;padding:4px 12px;border-radius:999px;font-size:13px;font-weight:600;}"
        ".pill.ok{background:#e8f5e9;color:#1b5e20;}"
        ".pill.ca{background:#fff8e1;color:#f57f17;}"
        ".pill.wa{background:#ffebee;color:#c62828;}"
        ".pill.unk{background:#eceff1;color:#455a64;}"
        "section{margin:22px 0;background:#fff;border-radius:12px;padding:18px 20px;"
        "box-shadow:0 1px 4px rgba(0,0,0,.06);}"
        "section h2{margin:0 0 12px;font-size:17px;border-left:4px solid #ec407a;padding-left:10px;}"
        ".sum{line-height:1.75;font-size:15px;color:#333;}"
        ".cat{margin:14px 0;padding:14px;border:1px solid #eee;border-radius:10px;background:#fafafa;}"
        ".cat h3{margin:0 0 8px;font-size:15px;}"
        ".cat .meta{font-size:13px;color:#666;margin-bottom:8px;}"
        ".cat p{margin:6px 0;font-size:14px;line-height:1.65;}"
        "table{width:100%;border-collapse:collapse;font-size:13px;margin:10px 0;}"
        "th,td{border:1px solid #e8e8e8;padding:8px 10px;text-align:left;}"
        "th{background:#f5f5f5;font-weight:600;}"
        "tr:nth-child(even) td{background:#fcfcfc;}"
        ".st-ok{color:#2e7d32;font-weight:600;}"
        ".st-caution{color:#f57f17;font-weight:600;}"
        ".st-warn{color:#c62828;font-weight:600;}"
        ".st-muted{color:#757575;}"
        ".disc{margin-top:20px;font-size:12px;color:#888;line-height:1.6;}"
        "caption{caption-side:top;text-align:left;font-weight:700;padding:8px 0;font-size:14px;}"
        "</style></head><body><div class='shell'>"
    )

    parts.append("<header class='hero'>")
    parts.append("<div class='mark' aria-hidden='true'>🐾</div>")
    parts.append("<div>")
    parts.append(f"<h1>{_e(payload.report_title)}</h1>")
    sub_bits = []
    if payload.pet_name:
        sub_bits.append("宠物：" + _e(payload.pet_name))
    if payload.report_date:
        sub_bits.append("日期：" + _e(payload.report_date))
    parts.append("<p class='sub'>" + " · ".join(sub_bits) + "</p>" if sub_bits else "<p class='sub'> </p>")

    parts.append("<div class='score-row'>")
    if payload.overall_score is not None:
        parts.append(f"<div class='score'>{payload.overall_score:g}<span style='font-size:16px;font-weight:600;color:#666'>/100</span></div>")
    st = (payload.overall_status or "未知").strip()
    pcl = "unk"
    if "正常" in st:
        pcl = "ok"
    elif any(x in st for x in ("注意", "临界")):
        pcl = "ca"
    elif any(x in st for x in ("警告", "异常")):
        pcl = "wa"
    parts.append(f"<span class='pill {pcl}'>{_e(st)}</span>")
    parts.append("</div></div></header>")

    parts.append("<section><h2>综合健康评估</h2>")
    parts.append(f"<div class='sum'>{_e(payload.ai_summary) or '（文档中未提供可归纳的综述）'}</div></section>")

    if payload.categories:
        parts.append("<section><h2>详细健康分析</h2>")
        for c in payload.categories:
            parts.append("<div class='cat'>")
            parts.append(f"<h3>{_e(c.name)}</h3>")
            if c.status_label:
                parts.append(
                    f"<div class='meta'>状态：<span class='{_status_class(c.status_label)}'>{_e(c.status_label)}</span></div>"
                )
            if c.interpretation:
                parts.append(f"<p><strong>解读</strong>：{_e(c.interpretation)}</p>")
            if c.recommendations:
                parts.append(f"<p><strong>建议</strong>：{_e(c.recommendations)}</p>")
            parts.append("</div>")
        parts.append("</section>")

    if payload.data_tables:
        parts.append("<section><h2>检测结果数据</h2>")
        for tb in payload.data_tables:
            parts.append("<table>")
            parts.append(f"<caption>{_e(tb.section_title or '检测表')}</caption>")
            cols = tb.columns or ["项目", "结果", "单位", "参考范围", "状态"]
            parts.append("<thead><tr>")
            for col in cols:
                parts.append(f"<th>{_e(col)}</th>")
            parts.append("</tr></thead><tbody>")
            for row in tb.rows:
                parts.append("<tr>")
                for i, cell in enumerate(row):
                    cls = ""
                    if i == len(row) - 1 and cols and cols[-1] in ("状态", "提示"):
                        cls = f" class='{_status_class(cell)}'"
                    parts.append(f"<td{cls}>{_e(str(cell))}</td>")
                for _ in range(len(row), len(cols)):
                    parts.append("<td></td>")
                parts.append("</tr>")
            parts.append("</tbody></table>")
        parts.append("</section>")

    parts.append(f"<p class='disc'>{_e(payload.disclaimer)}</p>")
    parts.append("</div></body></html>")
    return "\n".join(parts)
