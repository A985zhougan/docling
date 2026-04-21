"""
Docling API 服务
提供 PDF/DOCX 等文档转换为 JSON 的 REST API
"""

import json
import tempfile
import shutil
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import quote

from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Body, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, Response


def _load_local_env_files() -> None:
    """自动加载项目内 .env / .env.local，避免每次手工 export。"""
    import os
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("env_loader")
    
    # 🔥 优先设置 HuggingFace 镜像，必须在任何 import docling/transformers 之前
    os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
    os.environ.setdefault("TRANSFORMERS_CACHE", str(Path.home() / ".cache/huggingface/transformers"))
    os.environ.setdefault("HF_HOME", str(Path.home() / ".cache/huggingface"))
    logger.info(f"🌍 HuggingFace endpoint: {os.environ.get('HF_ENDPOINT')}")
    
    try:
        from dotenv import load_dotenv
    except Exception as e:
        logger.error(f"❌ dotenv import failed: {e}")
        return
    
    root = Path(__file__).resolve().parents[1]
    logger.info(f"📁 Project root: {root}")
    
    for name in (".env", ".env.local"):
        env_path = root / name
        logger.info(f"🔍 Checking {env_path} ... exists={env_path.exists()}")
        if env_path.exists():
            load_dotenv(env_path, override=True)
            logger.info(f"✅ Loaded {name}")
    
    # 代理商可能使用 ANTHROPIC_AUTH_TOKEN 而非标准的 ANTHROPIC_API_KEY
    key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN") or ""
    if key:
        logger.info(f"🔑 API key loaded: {key[:15]}... (source: {'ANTHROPIC_API_KEY' if os.environ.get('ANTHROPIC_API_KEY') else 'ANTHROPIC_AUTH_TOKEN'})")
    else:
        logger.warning("⚠️ No ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN found!")


_load_local_env_files()

# ⚠️ 必须在设置 HF_ENDPOINT 之后再 import docling
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat, ConversionStatus

from api.health_report.runner import run_health_report_from_pdf
from api.pet_report.pipeline import render_pet_report

app = FastAPI(
    title="Docling API",
    description="文档转换服务 - 支持 PDF、DOCX、PPTX、HTML、图片等格式转换为 JSON",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 使用 resolve() 确保静态目录为绝对路径，避免工作目录影响
STATIC_DIR = (Path(__file__).resolve().parent / "static")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

SUPPORTED_EXTENSIONS = {
    ".pdf": InputFormat.PDF,
    ".docx": InputFormat.DOCX,
    ".doc": InputFormat.DOCX,
    ".pptx": InputFormat.PPTX,
    ".xlsx": InputFormat.XLSX,
    ".html": InputFormat.HTML,
    ".htm": InputFormat.HTML,
    ".md": InputFormat.MD,
    ".csv": InputFormat.CSV,
    ".png": InputFormat.IMAGE,
    ".jpg": InputFormat.IMAGE,
    ".jpeg": InputFormat.IMAGE,
    ".tiff": InputFormat.IMAGE,
    ".tif": InputFormat.IMAGE,
    ".bmp": InputFormat.IMAGE,
    ".webp": InputFormat.IMAGE,
}

converter = DocumentConverter()


@app.get("/", response_class=HTMLResponse)
async def index():
    """返回前端页面"""
    html_path = STATIC_DIR / "index.html"
    if html_path.exists():
        return FileResponse(html_path, media_type="text/html; charset=utf-8")
    return HTMLResponse(
        content="<h1>Docling API</h1><p>请访问 <a href='/docs'>/docs</a> 查看 API 文档</p>"
    )


@app.get("/api/formats")
async def get_supported_formats():
    """获取支持的文件格式列表"""
    return {
        "supported_extensions": list(SUPPORTED_EXTENSIONS.keys()),
        "description": {
            "pdf": "PDF 文档",
            "docx/doc": "Word 文档",
            "pptx": "PowerPoint 演示文稿",
            "xlsx": "Excel 表格",
            "html/htm": "HTML 网页",
            "md": "Markdown 文档",
            "csv": "CSV 表格",
            "png/jpg/jpeg/tiff/bmp/webp": "图片文件",
        },
    }


@app.post("/api/convert")
async def convert_document(
    file: UploadFile = File(..., description="要转换的文档文件"),
    export_markdown: bool = Query(False, description="是否同时返回 Markdown 格式"),
    download: bool = Query(False, description="是否以文件形式下载（默认返回 JSON 响应）"),
):
    """
    上传文档并转换为 JSON 格式

    - **file**: 上传的文档文件（支持 PDF、DOCX、PPTX、HTML、图片等）
    - **export_markdown**: 是否同时返回 Markdown 格式（默认 False）
    - **download**: 是否以文件形式下载（默认 False，返回 JSON 响应）

    返回转换后的 JSON 结构化数据，或直接下载 JSON 文件
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {file_ext}。支持的格式: {list(SUPPORTED_EXTENSIONS.keys())}",
        )

    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp()
        temp_file_path = Path(temp_dir) / file.filename

        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        result = converter.convert(str(temp_file_path))

        if result.status != ConversionStatus.SUCCESS:
            error_msgs = [str(e) for e in result.errors] if result.errors else ["转换失败"]
            raise HTTPException(status_code=500, detail=f"文档转换失败: {'; '.join(error_msgs)}")

        doc_dict = result.document.export_to_dict()

        if download:
            json_filename = Path(file.filename).stem + ".json"
            json_content = json.dumps(doc_dict, ensure_ascii=False, indent=2)
            encoded_filename = quote(json_filename)
            return Response(
                content=json_content,
                media_type="application/json",
                headers={
                    "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
                },
            )

        response_data = {
            "success": True,
            "filename": file.filename,
            "document": doc_dict,
        }

        if export_markdown:
            response_data["markdown"] = result.document.export_to_markdown()

        return JSONResponse(content=response_data)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理文档时发生错误: {str(e)}")
    finally:
        if temp_dir and Path(temp_dir).exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


@app.post("/api/convert/markdown")
async def convert_to_markdown(file: UploadFile = File(...)):
    """
    上传文档并转换为 Markdown 格式

    返回纯 Markdown 文本
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {file_ext}",
        )

    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp()
        temp_file_path = Path(temp_dir) / file.filename

        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        result = converter.convert(str(temp_file_path))

        if result.status != ConversionStatus.SUCCESS:
            raise HTTPException(status_code=500, detail="文档转换失败")

        return {
            "success": True,
            "filename": file.filename,
            "markdown": result.document.export_to_markdown(),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理文档时发生错误: {str(e)}")
    finally:
        if temp_dir and Path(temp_dir).exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


@app.get("/api/health")
async def health_check():
    """健康检查接口"""
    return {"status": "ok", "service": "docling-api"}


@app.post("/api/pet-report/render")
async def pet_report_render(
    use_ai: bool = Query(False, description="是否调用 Anthropic 生成「AI 补充说明」"),
    x_anthropic_api_key: Optional[str] = Header(None, alias="X-Anthropic-Api-Key"),
    x_anthropic_base_url: Optional[str] = Header(None, alias="X-Anthropic-Base-URL"),
    anthropic_api_key: Optional[str] = Query(None, description="可选；默认读取环境变量 ANTHROPIC_API_KEY"),
    anthropic_base_url: Optional[str] = Query(None, description="可选；默认读取环境变量 ANTHROPIC_BASE_URL"),
    anthropic_model: Optional[str] = Query(None, description="可选；覆盖 PET_REPORT_ANTHROPIC_MODEL"),
    payload: Dict[str, Any] = Body(..., description="与 cankao.json 结构一致的报告 JSON 对象"),
):
    """规则层渲染完整 HTML；可选叠加 Claude 短文案。"""
    import json as _json
    try:
        raw = _json.dumps(payload, ensure_ascii=False)
        key = x_anthropic_api_key or anthropic_api_key
        base_url = x_anthropic_base_url or anthropic_base_url
        result = render_pet_report(
            raw,
            use_ai=use_ai,
            api_key=key,
            base_url=base_url,
            model=anthropic_model,
        )
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/pet-report/render-file")
async def pet_report_render_file(
    file: UploadFile = File(..., description="原始 .json 文件（可含 // 或 /**/ 注释）"),
    use_ai: bool = Query(False),
    x_anthropic_api_key: Optional[str] = Header(None, alias="X-Anthropic-Api-Key"),
    x_anthropic_base_url: Optional[str] = Header(None, alias="X-Anthropic-Base-URL"),
    anthropic_api_key: Optional[str] = Query(None),
    anthropic_base_url: Optional[str] = Query(None),
    anthropic_model: Optional[str] = Query(None),
):
    """上传 JSON 文件（支持带注释），渲染报告 HTML。"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    try:
        raw_bytes = await file.read()
        raw = raw_bytes.decode("utf-8")
        key = x_anthropic_api_key or anthropic_api_key
        base_url = x_anthropic_base_url or anthropic_base_url
        result = render_pet_report(
            raw,
            use_ai=use_ai,
            api_key=key,
            base_url=base_url,
            model=anthropic_model,
        )
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/health-report/from-pdf")
async def health_report_from_pdf(
    file: UploadFile = File(..., description="PDF 文件"),
    ai_provider: Optional[str] = Query(
        None,
        description="AI 提供方：anthropic 或 openai；不传则使用服务端 HEALTH_REPORT_AI_PROVIDER",
    ),
    ai_model: Optional[str] = Query(None, description="模型名，未传时使用环境变量默认值"),
    ai_api_key: Optional[str] = Query(None, description="可选；也可通过 Header X-AI-Api-Key 传入"),
    ai_base_url: Optional[str] = Query(None, description="可选；订阅链接 / 网关地址"),
    anthropic_api_key: Optional[str] = Query(None, description="兼容旧参数，等价于 ai_api_key"),
    anthropic_base_url: Optional[str] = Query(None, description="兼容旧参数，等价于 ai_base_url"),
    x_ai_api_key: Optional[str] = Header(None, alias="X-AI-Api-Key"),
    x_ai_base_url: Optional[str] = Header(None, alias="X-AI-Base-URL"),
    x_anthropic_api_key: Optional[str] = Header(None, alias="X-Anthropic-Api-Key"),
):
    """上传 PDF → Docling 转 Markdown → AI 结构化 → 渲染 HTML 报告。"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")
    ext = Path(file.filename).suffix.lower()
    if ext != ".pdf":
        raise HTTPException(status_code=400, detail="仅支持 .pdf 文件")
    try:
        data = await file.read()
        key = x_ai_api_key or ai_api_key or x_anthropic_api_key or anthropic_api_key
        base_url = x_ai_base_url or ai_base_url or anthropic_base_url
        out = run_health_report_from_pdf(
            data,
            file.filename,
            api_key=key,
            provider=ai_provider,
            base_url=base_url,
            model=ai_model,
        )
        return {"success": True, **out}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
