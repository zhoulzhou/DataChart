#!/usr/bin/env bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

cleanup() {
    echo ""
    echo -e "${YELLOW}[*] 正在停止服务...${NC}"
    if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
        kill "$SERVER_PID" 2>/dev/null
        echo -e "${GREEN}    后端已停止 (PID: $SERVER_PID)${NC}"
    fi
    if [ -n "$CLIENT_PID" ] && kill -0 "$CLIENT_PID" 2>/dev/null; then
        kill "$CLIENT_PID" 2>/dev/null
        echo -e "${GREEN}    前端已停止 (PID: $CLIENT_PID)${NC}"
    fi
    echo -e "${GREEN}[*] 所有服务已停止，再见！${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

echo -e "${CYAN}========================================${NC}"
echo -e "${YELLOW}   DataChart - 多公司财务指标可视化系统${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

cd "$SCRIPT_DIR/server"
node index.js &
SERVER_PID=$!
echo -e "${GREEN}      后端已启动 127.0.0.1:3000${NC}"
sleep 2

cd "$SCRIPT_DIR/client"
# ✅ 线上服务器固定 3000 端口，不使用 5173
npx vite --host 127.0.0.1 --port 3000 &
CLIENT_PID=$!
echo -e "${GREEN}      前端已启动 127.0.0.1:3000${NC}"
sleep 3

echo ""
echo -e "  访问地址: ${GREEN}https://data.kaiamu.com${NC}"
echo -e "  默认账号: ${YELLOW}admin / admin123${NC}"
echo ""
echo -e "${YELLOW}按 Ctrl+C 停止所有服务${NC}"
echo ""

wait