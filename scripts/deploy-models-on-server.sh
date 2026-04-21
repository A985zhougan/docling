#!/usr/bin/env bash
# ===================================================================
# 在服务器上运行此脚本
# 用于接收并部署从本地机器传输过来的模型文件
# ===================================================================

set -euo pipefail

MODEL_FILE="/tmp/docling-models.tar.gz"
TARGET_DIR="$HOME"

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║   Docling 模型部署脚本（在服务器上运行）                  ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# 检查模型文件是否存在
if [ ! -f "$MODEL_FILE" ]; then
    echo "❌ 错误: 未找到模型文件 $MODEL_FILE"
    echo ""
    echo "请先从本地机器传输模型文件:"
    echo ""
    echo "  在本地机器上执行:"
    echo "  scp ~/docling-models-download/docling-models.tar.gz root@120.24.112.113:/tmp/"
    echo ""
    exit 1
fi

# 显示文件大小
FILE_SIZE=$(du -h "$MODEL_FILE" | cut -f1)
echo "✅ 找到模型文件: $MODEL_FILE"
echo "   大小: $FILE_SIZE"
echo ""

# 解压
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 步骤 1/3: 解压模型文件..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd "$TARGET_DIR"
tar -xzf "$MODEL_FILE"

if [ $? -eq 0 ]; then
    echo "✅ 解压成功"
    echo "   目标目录: $TARGET_DIR/.cache/huggingface"
else
    echo "❌ 解压失败"
    exit 1
fi

# 验证
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 步骤 2/3: 验证模型文件..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

HF_CACHE="$HOME/.cache/huggingface"
if [ -d "$HF_CACHE/hub" ]; then
    MODEL_DIRS=$(find "$HF_CACHE/hub" -maxdepth 1 -type d -name "models--docling*" 2>/dev/null | wc -l)
    
    if [ "$MODEL_DIRS" -gt 0 ]; then
        echo "✅ 模型文件已就绪"
        echo ""
        echo "   模型目录:"
        find "$HF_CACHE/hub" -maxdepth 1 -type d -name "models--*" 2>/dev/null | while read dir; do
            SIZE=$(du -sh "$dir" 2>/dev/null | cut -f1)
            echo "   - $(basename "$dir") ($SIZE)"
        done
    else
        echo "⚠️  警告: 未找到模型目录"
    fi
else
    echo "❌ 缓存目录不存在"
    exit 1
fi

# 清理临时文件
echo ""
echo "🧹 清理临时文件..."
rm -f "$MODEL_FILE"
echo "✅ 清理完成"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 步骤 3/3: 重启 Docling 服务..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd /home/zhuazi-wordjson/docling

# 停止现有服务
echo "⏹️  停止现有服务..."
pkill -f "uvicorn api.main:app" 2>/dev/null || true
sleep 2

# 启动服务
echo "▶️  启动服务..."
./scripts/start-docling-api.sh background

sleep 5

# 验证服务
echo ""
echo "🔍 验证服务状态..."
if curl -sS http://127.0.0.1:8001/api/health &>/dev/null; then
    echo "✅ 服务启动成功"
    curl -sS http://127.0.0.1:8001/api/health
else
    echo "⚠️  服务可能还在启动中，请稍后检查"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 部署完成！"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🌐 访问地址: http://120.24.112.113:8001/"
echo ""
echo "📝 验证模型是否正常加载:"
echo ""
echo "   cd /home/zhuazi-wordjson/docling"
echo "   .venv/bin/python -c \"from docling.document_converter import DocumentConverter; DocumentConverter(); print('✅ 模型加载成功')\""
echo ""
echo "📊 查看服务日志:"
echo ""
echo "   tail -f /home/zhuazi-wordjson/docling/.logs/docling-api-8001.log"
echo ""
