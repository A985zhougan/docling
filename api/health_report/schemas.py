from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CategoryBlock(BaseModel):
    name: str = ""
    status_label: Optional[str] = None
    interpretation: str = ""
    recommendations: str = ""


class DataTableBlock(BaseModel):
    section_title: str = ""
    columns: List[str] = Field(
        default_factory=lambda: ["项目", "结果", "单位", "参考范围", "状态"]
    )
    rows: List[List[str]] = Field(default_factory=list)


class AIHealthReportPayload(BaseModel):
    """由 LLM 从 PDF/Markdown 抽取并映射；用于规则层渲染。"""

    model_config = ConfigDict(extra="ignore")

    report_title: str = "AI健康报告"
    pet_name: Optional[str] = None
    report_date: Optional[str] = None
    overall_score: Optional[float] = None
    overall_status: Optional[str] = None
    ai_summary: str = ""
    categories: List[CategoryBlock] = Field(default_factory=list)
    data_tables: List[DataTableBlock] = Field(default_factory=list)
    disclaimer: str = (
        "本报告由 AI 根据上传文档内容整理生成，仅供健康管理参考，不能替代执业兽医的诊断与治疗。"
    )
