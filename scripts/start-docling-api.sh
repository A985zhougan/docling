#!/usr/bin/env bash
# 在 docling 项目根目录启动文档转换 API（FastAPI + uvicorn）
# 用法：
#   ./scripts/start-docling-api.sh              # 前台运行（Ctrl+C 结束）
#   ./scripts/start-docling-api.sh background   # 后台运行，日志见 LOG_FILE
# 环境变量：HOST（默认 0.0.0.0）、PORT（默认 8001）

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8001}"
MODE="${1:-foreground}"

VENV_PY="${ROOT}/.venv/bin/python"
if [[ ! -x "$VENV_PY" ]]; then
  echo "错误：未找到可执行虚拟环境 ${VENV_PY}" >&2
  echo "请在项目根目录执行：python3 -m venv .venv" >&2
  echo "然后：.venv/bin/python -m pip install -U pip && .venv/bin/python -m pip install -r api/requirements.txt && .venv/bin/python -m pip install -e ." >&2
  exit 1
fi

if "$VENV_PY" -c "import fastapi, uvicorn" 2>/dev/null; then
  :
else
  echo "错误：虚拟环境缺少依赖，请执行：" >&2
  echo "  .venv/bin/python -m pip install -r api/requirements.txt && .venv/bin/python -m pip install -e ." >&2
  exit 1
fi

if command -v ss >/dev/null 2>&1; then
  if ss -ltn 2>/dev/null | grep -qE ":${PORT}[[:space:]]"; then
    echo "错误：端口 ${PORT} 已被占用，请执行：ss -ltnp | grep ${PORT}" >&2
    exit 1
  fi
fi

LOG_DIR="${ROOT}/.logs"
LOG_FILE="${LOG_DIR}/docling-api-${PORT}.log"
PID_FILE="/tmp/docling-api-${PORT}.pid"

run_uvicorn() {
  exec "$VENV_PY" -m uvicorn api.main:app --host "$HOST" --port "$PORT"
}

case "$MODE" in
  background|-d|--daemon)
    mkdir -p "$LOG_DIR"
    if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      echo "已有进程在运行（PID $(cat "$PID_FILE")），如需重启请先：kill \$(cat $PID_FILE)" >&2
      exit 1
    fi
    nohup "$VENV_PY" -m uvicorn api.main:app --host "$HOST" --port "$PORT" \
      >>"$LOG_FILE" 2>&1 &
    echo $! >"$PID_FILE"
    echo "已在后台启动 Docling API（PID $(cat "$PID_FILE")），端口 ${PORT}，日志：${LOG_FILE}"
    echo "健康检查：curl -sS http://127.0.0.1:${PORT}/api/health"
    ;;
  foreground|""|*)
    echo "前台启动 Docling API：http://${HOST}:${PORT}/ （本机可用 127.0.0.1）"
    run_uvicorn
    ;;
esac
