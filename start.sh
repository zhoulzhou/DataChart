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

if ! command -v node &>/dev/null; then
    echo -e "${YELLOW}[0/3] Node.js 未安装，正在安装...${NC}"
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
    echo -e "${GREEN}      Node.js $(node -v) 安装完成${NC}"
else
    echo -e "${GREEN}[0/3] Node.js $(node -v) 已就绪${NC}"
fi

if ! command -v npm &>/dev/null; then
    echo -e "${RED}[!] npm 未找到，请检查 Node.js 安装${NC}"
    exit 1
fi

echo -e "${YELLOW}[1/3] 安装后端依赖...${NC}"
cd "$SCRIPT_DIR/server"
npm install --silent
echo -e "${GREEN}      后端依赖安装完成${NC}"

echo -e "${YELLOW}[2/3] 安装前端依赖...${NC}"
cd "$SCRIPT_DIR/client"
npm install --silent
echo -e "${GREEN}      前端依赖安装完成${NC}"

for port in 3000 5173; do
    PID=$(lsof -ti :$port 2>/dev/null || true)
    if [ -n "$PID" ]; then
        echo -e "${YELLOW}[*] 端口 $port 被占用 (PID: $PID)，正在释放...${NC}"
        kill -9 "$PID" 2>/dev/null || true
        sleep 1
    fi
done

echo -e "${YELLOW}[3/3] 启动服务...${NC}"

cd "$SCRIPT_DIR/server"
node index.js &
SERVER_PID=$!
echo -e "${GREEN}      后端已启动 (PID: $SERVER_PID)${NC}"
sleep 2

cd "$SCRIPT_DIR/client"
npx vite --host &
CLIENT_PID=$!
echo -e "${GREEN}      前端已启动 (PID: $CLIENT_PID)${NC}"
sleep 3

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${GREEN}  启动完成！${NC}"
echo -e "${CYAN}========================================${NC}"
echo -e "  前台展示:   ${GREEN}http://localhost:5173${NC}"
echo -e "  后台登录:   ${GREEN}http://localhost:5173/login${NC}"
echo -e "  默认账号:   ${YELLOW}admin / admin123${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
echo -e "${YELLOW}按 Ctrl+C 停止所有服务${NC}"
echo ""

wait
