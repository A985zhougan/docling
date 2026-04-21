from __future__ import annotations

import html
from typing import Dict, List, Tuple

from api.pet_report.schemas import PetReportPayload


def _e(s: str | None) -> str:
    return html.escape(s or "", quote=True)


def _split_details(details: Dict[str, str]) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
    abnormal: List[Tuple[str, str]] = []
    normal: List[Tuple[str, str]] = []
    for k, v in sorted(details.items(), key=lambda x: x[0].upper()):
        if (v or "").strip() == "正常":
            normal.append((k, v))
        else:
            abnormal.append((k, v))
    return abnormal, normal


def build_report_html(
    payload: PetReportPayload,
    *,
    ai_extra_html: str | None = None,
) -> str:
    """由结构化数据生成版式 HTML（规则层）；ai_extra_html 为可选的 AI 补充块（已转义外层由调用方保证）。"""
    p = payload.pet_info
    abnormal, normal = _split_details(payload.details)

    parts: List[str] = []
    parts.append("<!DOCTYPE html>")
    parts.append('<html lang="zh-CN"><head><meta charset="utf-8"/>')
    parts.append(
        "<title>"
        + _e(p.name or "宠物")
        + " - 基因检测报告</title>"
        "<style>"
        "body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;"
        "margin:24px;color:#222;background:#fafafa;}"
        ".wrap{max-width:880px;margin:0 auto;background:#fff;padding:28px 32px;border-radius:12px;"
        "box-shadow:0 1px 3px rgba(0,0,0,.08);}"
        "h1{font-size:22px;margin:0 0 8px;}"
        "h2{font-size:17px;margin:28px 0 12px;border-left:4px solid #2e7d32;padding-left:10px;}"
        ".meta{display:grid;grid-template-columns:140px 1fr;gap:6px 16px;font-size:14px;}"
        ".meta dt{color:#666;margin:0;}"
        ".meta dd{margin:0;}"
        "table{width:100%;border-collapse:collapse;font-size:13px;margin:10px 0;}"
        "th,td{border:1px solid #e0e0e0;padding:8px 10px;text-align:left;vertical-align:top;}"
        "th{background:#f5f5f5;}"
        "tr.abnormal td:last-child{color:#b71c1c;font-weight:600;}"
        ".card{background:#f1f8e9;border:1px solid #c5e1a5;border-radius:8px;padding:12px 14px;margin:12px 0;}"
        ".muted{color:#666;font-size:13px;}"
        ".ai-box{background:#e8f5e9;border:1px solid #a5d6a7;border-radius:8px;padding:12px 14px;margin:12px 0;}"
        "ul{margin:8px 0 0 18px;padding:0;}"
        "li{margin:4px 0;}"
        "</style></head><body><div class='wrap'>"
    )

    title = "宠物基因检测报告"
    if payload.pet_type:
        title = ("猫" if payload.pet_type == "cat" else "犬" if payload.pet_type == "dog" else "宠物") + "基因检测报告"
    parts.append(f"<h1>{_e(title)}</h1>")
    parts.append(f"<p class='muted'>本页由规则引擎从 JSON 渲染；文案类段落可叠加 AI 补充。</p>")

    parts.append("<h2>基本信息</h2><dl class='meta'>")
    for label, val in [
        ("姓名", p.name),
        ("品种", p.breed),
        ("性别", p.gender),
        ("年龄", p.age),
        ("样本编号", p.sample_id),
        ("样本类型", p.sample_type),
        ("检测套餐", p.test_package),
        ("收样日期", p.receipt_date),
        ("报告日期", p.report_date),
        ("检测类型", p.test_type),
        ("主人", p.owner),
    ]:
        if val:
            parts.append(f"<dt>{_e(label)}</dt><dd>{_e(val)}</dd>")
    parts.append("</dl>")

    if ai_extra_html:
        parts.append("<div class='ai-box'><strong>AI 补充说明</strong>" + ai_extra_html + "</div>")

    if payload.key_findings:
        parts.append("<h2>关键发现</h2>")
        for kf in payload.key_findings:
            parts.append("<div class='card'>")
            line = " · ".join(
                x
                for x in [
                    kf.condition,
                    kf.gene and f"基因 {kf.gene}",
                    kf.risk_level,
                    kf.inheritance,
                ]
                if x
            )
            if line:
                parts.append(f"<div><strong>{_e(line)}</strong></div>")
            if kf.description:
                parts.append(f"<p style='margin:8px 0 0;font-size:14px;line-height:1.6'>{_e(kf.description)}</p>")
            parts.append("</div>")

    if payload.AI_overview:
        parts.append("<h2>分项概览</h2>")
        for it in payload.AI_overview:
            parts.append("<div class='card'>")
            head = " · ".join(x for x in [it.icon, it.title, it.label] if x and x != "[表情]")
            if head:
                parts.append(f"<div><strong>{_e(head)}</strong></div>")
            if it.evidence:
                parts.append(f"<p class='muted' style='margin:8px 0 4px'>依据：{_e(it.evidence)}</p>")
            if it.analysis:
                parts.append(f"<p style='margin:4px 0;font-size:14px;line-height:1.6'>{_e(it.analysis)}</p>")
            if it.suggestions:
                parts.append("<ul>")
                for s in it.suggestions:
                    parts.append(f"<li>{_e(s)}</li>")
                parts.append("</ul>")
            if it.note:
                parts.append(f"<p class='muted' style='margin:8px 0 0'>{_e(it.note)}</p>")
            parts.append("</div>")

    if payload.AI_letter:
        al = payload.AI_letter
        parts.append("<h2>致家长的一封信</h2>")
        if al.important_things:
            parts.append("<h3 style='font-size:15px;margin:16px 0 8px'>重点事项</h3>")
            for t in al.important_things:
                if t.title:
                    parts.append(f"<p><strong>{_e(t.title)}</strong></p>")
                if t.description:
                    parts.append(f"<p style='font-size:14px;line-height:1.6'>{_e(t.description)}</p>")
        if al.actions:
            parts.append("<h3 style='font-size:15px;margin:16px 0 8px'>行动建议</h3><ul>")
            for a in al.actions:
                parts.append(f"<li>{_e(a)}</li>")
            parts.append("</ul>")
        if al.days_30:
            parts.append("<h3 style='font-size:15px;margin:16px 0 8px'>30 天计划</h3><ul>")
            for a in al.days_30:
                parts.append(f"<li>{_e(a)}</li>")
            parts.append("</ul>")
        if al.days_90:
            parts.append("<h3 style='font-size:15px;margin:16px 0 8px'>90 天观察</h3><ul>")
            for a in al.days_90:
                parts.append(f"<li>{_e(a)}</li>")
            parts.append("</ul>")
        if al.tips:
            parts.append(f"<p class='muted' style='margin-top:16px;line-height:1.6'>{_e(al.tips)}</p>")

    parts.append("<h2>位点明细</h2>")
    parts.append("<p class='muted'>以下为规则层全量列出；非「正常」项优先展示。</p>")
    if abnormal:
        parts.append("<table><thead><tr><th>基因/位点</th><th>结果</th></tr></thead><tbody>")
        for gene, status in abnormal:
            parts.append(f"<tr class='abnormal'><td>{_e(gene)}</td><td>{_e(status)}</td></tr>")
        parts.append("</tbody></table>")
    show_normal = normal[:40]
    if show_normal:
        parts.append("<table><thead><tr><th>基因/位点</th><th>结果</th></tr></thead><tbody>")
        for gene, status in show_normal:
            parts.append(f"<tr><td>{_e(gene)}</td><td>{_e(status)}</td></tr>")
        parts.append("</tbody></table>")
    if len(normal) > len(show_normal):
        parts.append(f"<p class='muted'>… 另有 {len(normal) - len(show_normal)} 项为「正常」，略。</p>")

    if payload.certification_number:
        parts.append(f"<p class='muted' style='margin-top:24px'>证书编号：{_e(payload.certification_number)}</p>")

    parts.append("</div></body></html>")
    return "\n".join(parts)
