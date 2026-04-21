#!/usr/bin/env python3
"""
使用 wget/curl 从备用地址下载预打包的 Docling 模型
适用于无法访问 HuggingFace 的服务器环境
"""

import os
import sys
import subprocess
from pathlib import Path

print("=" * 70)
print("Docling 模型下载工具（备用方案）")
print("=" * 70)
print()

# 模型文件信息（需要提供一个可访问的下载地址）
MODEL_URLS = [
    {
        "name": "Docling Models Package",
        "url": "https://您的CDN或OSS地址/docling-models.tar.gz",  # 需要替换
        "size": "~2.5GB",
        "md5": "待计算",
    }
]

cache_dir = Path.home() / ".cache" / "huggingface"
cache_dir.mkdir(parents=True, exist_ok=True)

print("🎯 备用下载方案说明:")
print()
print("由于您的服务器无法直接访问 HuggingFace，您有以下选择:")
print()
print("方案 1: 使用方案 A（推荐）")
print("   - 在本地电脑下载模型")
print("   - 使用 scp 传输到服务器")
print("   - 详见: 方案A执行指南.md")
print()
print("方案 2: 使用云存储中转")
print("   - 将模型上传到阿里云 OSS/腾讯云 COS")
print("   - 从云存储下载到服务器")
print("   - 服务器可以访问国内云存储")
print()
print("方案 3: 联系运维开通网络权限")
print("   - 需要访问: huggingface.co")
print("   - 或配置 HTTP 代理")
print()
print("=" * 70)
print()

# 检查网络连通性
print("🔍 网络诊断:")
print()

def test_connectivity(url, name):
    try:
        result = subprocess.run(
            ["curl", "-I", "-m", "5", url],
            capture_output=True,
            text=True,
            timeout=6
        )
        if result.returncode == 0:
            print(f"  ✅ {name}: 可访问")
            return True
        else:
            print(f"  ❌ {name}: 不可访问")
            return False
    except:
        print(f"  ❌ {name}: 测试失败")
        return False

test_connectivity("https://huggingface.co", "HuggingFace")
test_connectivity("https://hf-mirror.com", "HF Mirror")
test_connectivity("https://www.aliyun.com", "阿里云")

print()
print("=" * 70)
print()
print("📝 推荐操作:")
print()
print("1. 使用方案 A - 从本地下载并传输")
print("   bash /home/zhuazi-wordjson/docling/scripts/download-on-local-machine.sh")
print()
print("2. 查看详细指南:")
print("   cat /home/zhuazi-wordjson/docling/方案A执行指南.md")
print()
print("=" * 70)
