#!/usr/bin/env python3
"""
直接使用 Docling 内置的下载工具，配合超时和重试设置
"""

import os
import sys
from pathlib import Path

# 设置环境变量
os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = "300"  # 5分钟超时
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"  # 启用高速传输
os.environ["TRANSFORMERS_CACHE"] = str(Path.home() / ".cache" / "huggingface" / "transformers")
os.environ["HF_HOME"] = str(Path.home() / ".cache" / "huggingface")

# 不使用镜像，直接连官方（因为镜像也超时）
if "HF_ENDPOINT" in os.environ:
    del os.environ["HF_ENDPOINT"]

print("=" * 70)
print("Docling 模型下载工具")
print("=" * 70)
print(f"HF_HOME: {os.environ['HF_HOME']}")
print(f"下载超时: {os.environ['HF_HUB_DOWNLOAD_TIMEOUT']}秒")
print("=" * 70)
print()

try:
    from docling.utils.model_downloader import download_models
    from docling.datamodel.settings import settings
    
    print(f"默认模型缓存目录: {settings.cache_dir}")
    print()
    
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    sys.exit(1)

# 只下载必需的基础模型
print("开始下载 Docling 必需模型...")
print("注意：首次下载可能需要较长时间（模型文件较大）")
print("-" * 70)

try:
    output_dir = download_models(
        output_dir=None,  # 使用默认目录
        force=False,
        progress=True,
        with_layout=True,
        with_tableformer=True,
        with_code_formula=True,
        with_picture_classifier=True,
        with_rapidocr=True,
        with_easyocr=False,
    )
    
    print("\n" + "=" * 70)
    print("✅ 模型下载完成！")
    print(f"模型位置: {output_dir}")
    print("=" * 70)
    
except KeyboardInterrupt:
    print("\n\n⚠️  下载被用户中断")
    sys.exit(130)
    
except Exception as e:
    print(f"\n\n❌ 下载失败: {e}")
    print("\n原因分析：")
    print("你的服务器无法访问 huggingface.co 和 hf-mirror.com")
    print("\n解决方案：")
    print("1. 配置 HTTP 代理（如果有）:")
    print("   export https_proxy=http://proxy-server:port")
    print("   export http_proxy=http://proxy-server:port")
    print()
    print("2. 或从其他能访问的机器下载后传输:")
    print("   在可访问机器上:")
    print("   $ python scripts/download-models-modelscope.py")
    print("   $ tar -czf docling-models.tar.gz ~/.cache/huggingface")
    print("   ")
    print("   传输到服务器:")
    print("   $ scp docling-models.tar.gz user@your-server:/tmp/")
    print("   $ ssh user@your-server")
    print("   $ cd ~ && tar -xzf /tmp/docling-models.tar.gz")
    print()
    print("3. 联系网络管理员开放 huggingface.co 访问权限")
    print()
    sys.exit(1)
