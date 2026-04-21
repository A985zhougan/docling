#!/usr/bin/env bash
# 在能访问 HuggingFace 的机器上运行此脚本
# 用于下载 Docling 所需的全部模型

set -euo pipefail

echo "============================================================"
echo "Docling 模型下载脚本（在外网机器上运行）"
echo "============================================================"
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 python3，请先安装 Python 3.8+"
    exit 1
fi

echo "✅ Python: $(python3 --version)"
echo ""

# 创建临时工作目录
WORK_DIR=$(mktemp -d)
echo "📁 工作目录: $WORK_DIR"
cd "$WORK_DIR"

# 安装必要的包
echo "📦 安装依赖..."
python3 -m pip install --quiet huggingface_hub requests tqdm

# 下载模型
echo ""
echo "开始下载模型..."
echo "------------------------------------------------------------"

python3 << 'PYTHON_SCRIPT'
import os
from pathlib import Path
from huggingface_hub import snapshot_download

# 设置缓存目录
cache_dir = Path.home() / ".cache" / "huggingface"
cache_dir.mkdir(parents=True, exist_ok=True)

models = [
    {
        "repo_id": "docling-project/docling-models",
        "name": "Docling Models (布局+表格+公式)",
    },
]

print(f"缓存目录: {cache_dir}\n")

for model in models:
    print(f"📥 下载: {model['name']}")
    print(f"   仓库: {model['repo_id']}")
    
    try:
        path = snapshot_download(
            repo_id=model["repo_id"],
            cache_dir=str(cache_dir),
            resume_download=True,
            local_files_only=False,
        )
        print(f"   ✅ 完成: {path}\n")
    except Exception as e:
        print(f"   ❌ 失败: {e}\n")
        raise

print("=" * 60)
print("✅ 所有模型下载完成！")
print(f"模型位置: {cache_dir}")
print("=" * 60)
PYTHON_SCRIPT

echo ""
echo "============================================================"
echo "✅ 下载完成！"
echo "============================================================"
echo ""
echo "下一步：打包并传输到服务器"
echo ""
echo "1. 打包模型:"
echo "   cd ~/.cache"
echo "   tar -czf /tmp/docling-models.tar.gz huggingface/"
echo ""
echo "2. 传输到服务器:"
echo "   scp /tmp/docling-models.tar.gz root@120.24.112.113:/tmp/"
echo ""
echo "3. 在服务器上解压:"
echo "   ssh root@120.24.112.113"
echo "   cd ~ && tar -xzf /tmp/docling-models.tar.gz"
echo ""
echo "4. 重启服务:"
echo "   cd /home/zhuazi-wordjson/docling"
echo "   pkill -f 'uvicorn api.main:app'"
echo "   ./scripts/start-docling-api.sh background"
echo ""
echo "============================================================"
