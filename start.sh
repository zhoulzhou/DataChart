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
    pkill -9 node 2>/dev/null || true
    echo -e "${GREEN}[*] 再见！${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

echo -e "${CYAN}========================================${NC}"
echo -e "${YELLOW}   DataChart - 财务指标可视化系统${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

echo -e "${YELLOW}[*] 清理旧进程...${NC}"
pkill -9 node 2>/dev/null || true
lsof -ti:3001 | xargs kill -9 2>/dev/null || true
sleep 1

echo -e "${YELLOW}[1/4] 安装 Python 依赖...${NC}"
pip3 install pandas yfinance akshare -q 2>/dev/null || true
echo -e "${GREEN}      Python 依赖 OK${NC}"

echo -e "${YELLOW}[2/4] 安装后端依赖...${NC}"
cd "$SCRIPT_DIR/server"
npm install --silent --force
echo -e "${GREEN}      后端依赖 OK${NC}"

echo -e "${YELLOW}[3/4] 安装前端依赖 + 构建...${NC}"
cd "$SCRIPT_DIR/client"
npm install --silent --force
npx vite build
echo -e "${GREEN}      前端构建完成${NC}"

echo -e "${YELLOW}[4/4] 启动服务 (127.0.0.1:3001)...${NC}"
cd "$SCRIPT_DIR/server"
node index.js &
SERVER_PID=$!
sleep 2

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${GREEN}  启动完成！${NC}"
echo -e "${CYAN}========================================${NC}"
echo -e "  外网地址:   ${GREEN}https://data.kaiamu.top${NC}"
echo -e "  本地地址:   ${GREEN}http://127.0.0.1:3001${NC}"
echo -e "  默认账号:   ${YELLOW}admin / admin123${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
echo -e "${YELLOW}按 Ctrl+C 停止服务${NC}"
echo ""

wait
