# Docling API 服务

基于 FastAPI 的文档转换 REST API 服务，支持将 PDF、DOCX、PPTX 等多种格式转换为结构化 JSON。

## 功能特性

- 支持多种输入格式：PDF、DOCX、PPTX、XLSX、HTML、Markdown、CSV、图片等
- 输出格式：JSON（结构化文档）、Markdown
- 提供 Web 界面，支持拖拽上传
- RESTful API，方便与前端集成
- 自动生成 API 文档（Swagger UI）

## 快速开始

### 1. 安装依赖

```bash
# 在 docling 项目根目录下执行（即与 api 文件夹同级）
cd /path/to/docling

# 安装 API 服务依赖
pip install fastapi uvicorn python-multipart

# 若未安装 docling，需先安装（开发时可直接用当前项目）
pip install -e .
```

### 2. 启动服务

**重要：必须在 docling 项目根目录下启动**（不要进入 api 目录再启动），否则可能无法加载 docling 和静态页面。

```bash
# 在 docling 项目根目录执行
cd /path/to/docling

# 方式一：uvicorn（推荐，支持热重载）
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# 方式二：直接运行
python -m api.main
```

### 3. 访问服务

- **Web 界面**：http://localhost:8000
- **API 文档**：http://localhost:8000/docs
- **健康检查**：http://localhost:8000/api/health

## API 接口

### 文档转换为 JSON

```bash
POST /api/convert
```

**参数：**
- `file`：上传的文档文件（必填）
- `export_markdown`：是否同时返回 Markdown（可选，默认 false）

**示例：**

```bash
# 转换 PDF 为 JSON
curl -X POST "http://localhost:8000/api/convert" \
  -F "file=@document.pdf"

# 同时获取 Markdown
curl -X POST "http://localhost:8000/api/convert?export_markdown=true" \
  -F "file=@document.pdf"
```

### 文档转换为 Markdown

```bash
POST /api/convert/markdown
```

**示例：**

```bash
curl -X POST "http://localhost:8000/api/convert/markdown" \
  -F "file=@document.docx"
```

### 获取支持的格式

```bash
GET /api/formats
```

### 健康检查

```bash
GET /api/health
```

## 支持的文件格式

| 格式 | 扩展名 |
|------|--------|
| PDF | .pdf |
| Word | .docx, .doc |
| PowerPoint | .pptx |
| Excel | .xlsx |
| HTML | .html, .htm |
| Markdown | .md |
| CSV | .csv |
| 图片 | .png, .jpg, .jpeg, .tiff, .bmp, .webp |

## 部署建议

### 生产环境

```bash
# 使用 gunicorn + uvicorn workers
pip install gunicorn

gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

### Docker 部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir docling

# 复制应用代码
COPY api/ .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 前端集成示例

### JavaScript Fetch

```javascript
async function convertDocument(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch('http://localhost:8000/api/convert', {
    method: 'POST',
    body: formData
  });

  const result = await response.json();
  return result.document;
}
```

### Python Requests

```python
import requests

def convert_document(file_path):
    with open(file_path, 'rb') as f:
        response = requests.post(
            'http://localhost:8000/api/convert',
            files={'file': f}
        )
    return response.json()['document']
```

## 注意事项

1. 大文件转换可能需要较长时间，建议设置合适的超时时间
2. PDF 转换需要较多内存，建议服务器至少 4GB RAM
3. 首次运行会下载 Docling 模型，需要网络连接
