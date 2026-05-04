@echo off
chcp 65001 >nul
title DataChart 启动中...

echo ========================================
echo   多公司财务指标可视化系统
echo ========================================
echo.

:: Kill any process using port 3000
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000.*LISTENING') do (
    echo [*] 发现端口 3000 被占用，正在终止进程 %%a...
    taskkill /F /PID %%a >nul 2>&1
)

:: Start backend server
echo [1/2] 启动后端服务...
start "DataChart-Server" cmd /c "cd /d %~dp0server && node index.js"

:: Wait for server to start
echo [*] 等待后端启动...
timeout /t 3 /nobreak >nul

:: Start frontend
echo [2/2] 启动前端服务...
start "DataChart-Client" cmd /c "cd /d %~dp0client && npx vite --host"

:: Wait for frontend to start
echo [*] 等待前端启动...
timeout /t 5 /nobreak >nul

:: Open browser
echo [*] 打开浏览器...
start http://localhost:5173

echo.
echo ========================================
echo   启动完成！
echo   前台展示: http://localhost:5173
echo   后台登录: http://localhost:5173/login
echo   默认账号: admin / admin123
echo ========================================
echo.
echo 关闭此窗口不会影响服务运行。
echo 要停止服务，请关闭两个命令行窗口。
echo.
pause
