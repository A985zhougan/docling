#!/usr/bin/env python3
"""
使用 ModelScope 下载 Docling 所需模型（国内高速镜像）
ModelScope 是阿里云提供的模型托管平台，国内访问速度快
"""

import os
import sys
from pathlib import Path

print("=" * 70)
print("Docling 模型下载工具（ModelScope 国内镜像）")
print("=" * 70)

# 设置缓存目录
cache_dir = Path.home() / ".cache" / "huggingface"
hub_dir = cache_dir / "hub"
hub_dir.mkdir(parents=True, exist_ok=True)

print(f"缓存目录: {cache_dir}")
print()

try:
    from modelscope import snapshot_download
    print("✅ ModelScope 已安装")
except ImportError:
    print("❌ ModelScope 未安装")
    print("安装命令: pip install modelscope -i https://pypi.tuna.tsinghua.edu.cn/simple")
    sys.exit(1)

# Docling 所需的 HuggingFace 模型列表
# 这些模型在 ModelScope 上有镜像
models_to_download = [
    {
        "name": "docling-models (布局+表格+公式识别)",
        "repo_id": "AI-ModelScope/docling-models",  # ModelScope 上的镜像
        "hf_repo": "docling-project/docling-models",
        "local_dir": "models--docling-project--docling-models",
    },
]

print("\n开始下载模型...")
print("-" * 70)

success_count = 0
failed_models = []

for model_info in models_to_download:
    print(f"\n📦 下载: {model_info['name']}")
    print(f"   来源: {model_info['repo_id']}")
    
    local_path = hub_dir / model_info["local_dir"]
    
    try:
        # 使用 ModelScope 下载
        downloaded_path = snapshot_download(
            model_id=model_info["repo_id"],
            cache_dir=str(local_path),
            revision="main",
        )
        
        print(f"   ✅ 下载成功: {downloaded_path}")
        success_count += 1
        
    except Exception as e:
        print(f"   ❌ 下载失败: {e}")
        failed_models.append(model_info["name"])
        
        # 如果 ModelScope 失败，尝试使用 huggingface-cli
        print(f"   ⏳ 尝试备用方案 (huggingface-cli)...")
        
        try:
            import subprocess
            result = subprocess.run(
                [
                    sys.executable, "-m", "huggingface_hub.commands.huggingface_cli",
                    "download",
                    model_info["hf_repo"],
                    "--cache-dir", str(cache_dir),
                    "--resume-download",
                ],
                capture_output=True,
                text=True,
                timeout=600,
            )
            
            if result.returncode == 0:
                print(f"   ✅ 备用方案成功")
                success_count += 1
                failed_models.pop()  # 移除失败记录
            else:
                print(f"   ❌ 备用方案也失败: {result.stderr[:200]}")
                
        except Exception as e2:
            print(f"   ❌ 备用方案异常: {e2}")

print("\n" + "=" * 70)
print(f"下载完成: {success_count}/{len(models_to_download)} 个模型成功")

if failed_models:
    print(f"\n❌ 失败的模型:")
    for name in failed_models:
        print(f"   - {name}")
    print("\n建议:")
    print("1. 检查网络连接")
    print("2. 如果在企业网络，尝试配置代理:")
    print("   export https_proxy=http://your-proxy:port")
    print("3. 如果持续失败，可以从其他机器下载后传输到服务器")
    sys.exit(1)
else:
    print("\n✅ 所有模型下载成功！")
    print(f"\n模型缓存位置: {cache_dir}")
    print("\n下一步:")
    print(f"1. 确认 .env.local 中有: HF_HOME={cache_dir}")
    print("2. 重启服务: pkill -f 'uvicorn api.main:app' && ./scripts/start-docling-api.sh background")
    print()

print("=" * 70)
