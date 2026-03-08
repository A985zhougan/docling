# Docling API 服务 Docker 镜像
# 构建时请在 docling 项目根目录执行: docker build -f api/Dockerfile -t docling-api:latest .

FROM python:3.11-slim

WORKDIR /app

# 系统依赖（Docling/OCR 等可能用到）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 复制整个项目（构建上下文为 docling 根目录）
COPY . .

# 安装 Docling 及 API 依赖
RUN pip install --no-cache-dir -e . \
    && pip install --no-cache-dir fastapi uvicorn python-multipart

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
