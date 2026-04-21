#!/usr/bin/env python3
"""
使用国内源下载 Docling 所需的 HuggingFace 模型
适用于无法直接访问 huggingface.co 的环境
"""

import os
import sys
from pathlib import Path

# 配置 ModelScope 作为 HuggingFace 镜像
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

# 设置缓存目录
cache_dir = Path.home() / ".cache" / "huggingface"
cache_dir.mkdir(parents=True, exist_ok=True)

print("=" * 60)
print("Docling 模型下载工具（国内源）")
print("=" * 60)
print(f"缓存目录: {cache_dir}")
print(f"HF_ENDPOINT: {os.environ.get('HF_ENDPOINT')}")
print()

# 导入 Docling 下载工具
try:
    from docling.utils.model_downloader import download_models
except ImportError as e:
    print(f"错误：无法导入 docling.utils.model_downloader: {e}")
    print("请确保已安装 docling: pip install -e .")
    sys.exit(1)

# 下载基础模型（PDF 转换必需）
print("\n开始下载 Docling 基础模型...")
print("-" * 60)

try:
    output_dir = download_models(
        output_dir=cache_dir / "models",
        force=False,
        progress=True,
        with_layout=True,           # 布局识别模型（必需）
        with_tableformer=True,      # 表格结构识别模型（必需）
        with_code_formula=True,     # 代码/公式识别模型（必需）
        with_picture_classifier=True,  # 图片分类模型（必需）
        with_rapidocr=True,         # OCR 引擎（推荐）
        with_easyocr=False,         # 可选的 OCR 引擎
        with_smolvlm=False,         # 可选的 VLM 模型
        with_granitedocling=False,  # 可选的 VLM 模型
        with_smoldocling=False,     # 可选的 VLM 模型
    )
    
    print("\n" + "=" * 60)
    print(f"✅ 模型下载完成！")
    print(f"模型目录: {output_dir}")
    print("=" * 60)
    print("\n下一步：")
    print("1. 在 .env.local 中设置: DOCLING_ARTIFACTS_PATH=" + str(output_dir))
    print("2. 或使用环境变量启动服务: export DOCLING_ARTIFACTS_PATH=" + str(output_dir))
    print()
    
except Exception as e:
    print(f"\n❌ 下载失败: {e}")
    print("\n故障排查：")
    print("1. 检查网络连接: curl -I https://hf-mirror.com")
    print("2. 尝试使用代理: export https_proxy=http://your-proxy:port")
    print("3. 手动下载模型后放置到缓存目录")
    sys.exit(1)
