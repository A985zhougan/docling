"""
Docling API 服务
提供 PDF/DOCX 等文档转换为 JSON 的 REST API
"""

import json
import tempfile
import shutil
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, Response

from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat, ConversionStatus

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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
