import json
import re


def strip_json_comments(raw: str) -> str:
    """剥离常见 JSONC 风格注释（/**/ 与 //），便于解析 cankao.json 这类带注释文件。"""
    s = re.sub(r"/\*[\s\S]*?\*/", "", raw)
    s = re.sub(r"//[^\n]*", "", s)
    return s


def loads_json_flexible(raw: str) -> dict:
    """解析 JSON；失败时尝试去注释后再解析。"""
    raw = raw.strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = json.loads(strip_json_comments(raw))
    if not isinstance(data, dict):
        raise ValueError("根节点必须是 JSON 对象")
    return data
