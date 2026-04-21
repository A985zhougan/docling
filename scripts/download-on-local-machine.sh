#!/usr/bin/env bash
# ===================================================================
# 在你的本地电脑（Mac/Windows/Linux）上运行此脚本
# 用于下载 Docling 模型并打包传输到服务器
# ===================================================================

set -euo pipefail

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║   Docling 模型下载脚本（在本地电脑上运行）                ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# 检查操作系统
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macOS"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="Linux"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    OS="Windows"
else
    OS="Unknown"
fi

echo "📍 检测到操作系统: $OS"
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 python3"
    echo ""
    echo "请先安装 Python 3.8 或更高版本:"
    if [[ "$OS" == "macOS" ]]; then
        echo "  brew install python3"
    elif [[ "$OS" == "Linux" ]]; then
        echo "  sudo apt install python3 python3-pip  # Debian/Ubuntu"
        echo "  sudo yum install python3 python3-pip  # CentOS/RHEL"
    fi
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✅ Python 版本: $PYTHON_VERSION"
echo ""

# 创建工作目录
WORK_DIR="$HOME/docling-models-download"
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

echo "📁 工作目录: $WORK_DIR"
echo ""

# 安装依赖
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 步骤 1/4: 安装必要的 Python 包..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 -m pip install --quiet --upgrade pip
python3 -m pip install --quiet huggingface_hub requests tqdm
echo "✅ 依赖安装完成"
echo ""

# 下载模型
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📥 步骤 2/4: 下载 Docling 模型（约 2-3GB）..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⏳ 这可能需要 10-30 分钟，取决于你的网络速度..."
echo ""

python3 << 'PYTHON_DOWNLOAD'
import os
import sys
from pathlib import Path
from huggingface_hub import snapshot_download

# 设置缓存目录
cache_dir = Path.home() / ".cache" / "huggingface"
cache_dir.mkdir(parents=True, exist_ok=True)

print(f"📂 缓存目录: {cache_dir}\n")

# 要下载的模型
model_repo = "docling-project/docling-models"

print(f"🔄 正在下载: {model_repo}")
print("   (下载过程中会显示进度条)\n")

try:
    downloaded_path = snapshot_download(
        repo_id=model_repo,
        cache_dir=str(cache_dir),
        resume_download=True,
        local_files_only=False,
    )
    
    print(f"\n✅ 模型下载成功！")
    print(f"   位置: {downloaded_path}\n")
    
    # 检查下载的文件
    hub_dir = cache_dir / "hub"
    model_dirs = list(hub_dir.glob("models--docling-project--*"))
    
    if model_dirs:
        import subprocess
        result = subprocess.run(
            ["du", "-sh", str(model_dirs[0])],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            size = result.stdout.split()[0]
            print(f"   大小: {size}")
    
except KeyboardInterrupt:
    print("\n\n⚠️  下载被用户中断")
    sys.exit(130)
    
except Exception as e:
    print(f"\n❌ 下载失败: {e}")
    print("\n可能的原因:")
    print("  1. 网络连接问题")
    print("  2. HuggingFace 服务暂时不可用")
    print("  3. 磁盘空间不足（需要约 3GB）")
    print("\n请检查后重新运行此脚本")
    sys.exit(1)

PYTHON_DOWNLOAD

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ 模型下载失败，请检查错误信息后重试"
    exit 1
fi

echo ""

# 打包模型
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 步骤 3/4: 打包模型文件..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

CACHE_DIR="$HOME/.cache/huggingface"
OUTPUT_FILE="$WORK_DIR/docling-models.tar.gz"

echo "正在压缩 $CACHE_DIR ..."
cd "$HOME/.cache"
tar -czf "$OUTPUT_FILE" huggingface/

if [ -f "$OUTPUT_FILE" ]; then
    FILE_SIZE=$(du -h "$OUTPUT_FILE" | cut -f1)
    echo "✅ 打包完成"
    echo "   文件: $OUTPUT_FILE"
    echo "   大小: $FILE_SIZE"
else
    echo "❌ 打包失败"
    exit 1
fi

echo ""

# 传输说明
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 步骤 4/4: 传输到服务器"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "现在请执行以下命令将模型传输到服务器:"
echo ""
echo "1️⃣  传输文件 (请在新终端窗口中执行):"
echo ""
echo "   scp $OUTPUT_FILE root@120.24.112.113:/tmp/"
echo ""
echo "2️⃣  登录服务器并解压:"
echo ""
echo "   ssh root@120.24.112.113"
echo "   cd ~"
echo "   tar -xzf /tmp/docling-models.tar.gz"
echo "   rm /tmp/docling-models.tar.gz"
echo ""
echo "3️⃣  重启 Docling 服务:"
echo ""
echo "   cd /home/zhuazi-wordjson/docling"
echo "   pkill -f 'uvicorn api.main:app'"
echo "   ./scripts/start-docling-api.sh background"
echo ""
echo "4️⃣  验证模型是否加载成功:"
echo ""
echo "   .venv/bin/python -c \"from docling.document_converter import DocumentConverter; DocumentConverter(); print('✅ 模型加载成功')\""
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ 本地准备工作完成！请按照上面的步骤传输到服务器。"
echo ""
