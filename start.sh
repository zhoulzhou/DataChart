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
echo -e "${YELLOW}   DataChart - 财务指标可视化系统${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# ==============================
# 安装依赖（修复 vite 找不到错误）
# ==============================
echo -e "${YELLOW}[1/3] 安装后端依赖...${NC}"
cd "$SCRIPT_DIR/server"
npm install --silent --force

echo -e "${YELLOW}[2/3] 安装前端依赖...${NC}"
cd "$SCRIPT_DIR/client"
npm install --silent --force

# ==============================
# 清理旧端口
# ==============================
echo -e "${YELLOW}[*] 清理端口 3000 ...${NC}"
lsof -ti:3000 | xargs kill -9 2>/dev/null || true
sleep 1

# ==============================
# 启动服务
# ==============================
echo -e "${YELLOW}[3/3] 启动服务...${NC}"

cd "$SCRIPT_DIR/server"
node index.js &
SERVER_PID=$!
echo -e "${GREEN}✅ 后端启动成功 (127.0.0.1:3000)${NC}"
sleep 2

cd "$SCRIPT_DIR/client"
# ✅ 正确：监听本地 3000 端口
npx vite --host 127.0.0.1 --port 3000 &
CLIENT_PID=$!
echo -e "${GREEN}✅ 前端启动成功 (127.0.0.1:3000)${NC}"
sleep 3

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${GREEN}  启动完成！${NC}"
echo -e "${CYAN}========================================${NC}"
echo -e "  访问地址:   ${GREEN}https://data.kaiamu.com${NC}"
echo -e "  默认账号:   ${YELLOW}admin / admin123${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
echo -e "${YELLOW}按 Ctrl+C 停止所有服务${NC}"
echo ""

wait