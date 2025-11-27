#!/bin/bash
# 开发模式启动脚本（默认使用热重载）
# 如需禁用热重载，设置环境变量: ENABLE_RELOAD=false

export CORS_ALLOW_ORIGIN="http://localhost:5174;http://localhost:5556"
PORT="${PORT:-6001}"

uvicorn open_webui.main:app --port $PORT --host 0.0.0.0 --forwarded-allow-ips '*' --reload
