#!/bin/bash
# 开发模式启动脚本（不使用热重载）
# 适用于开发 agent 等不需要频繁重启的模块

export CORS_ALLOW_ORIGIN="http://localhost:5173;http://localhost:5555"
PORT="${PORT:-6000}"

echo "启动后端服务（无热重载模式）..."
echo "端口: $PORT"
echo "提示: 修改代码后需要手动重启服务"

uvicorn open_webui.main:app --port $PORT --host 0.0.0.0 --forwarded-allow-ips '*'

