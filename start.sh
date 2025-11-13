#!/bin/bash
# Minecraft资源包合并器 - 快速启动脚本

echo "================================="
echo "Minecraft 资源包合并器 Web 应用"
echo "================================="
echo ""

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 Python 3"
    echo "请先安装 Python 3"
    exit 1
fi

# 检查依赖是否安装
if ! python3 -c "import flask" 2>/dev/null; then
    echo "📦 正在安装依赖..."
    pip install -r requirements.txt
    echo ""
fi

# 创建必要的目录
mkdir -p uploads outputs templates

# 启动应用
echo "🚀 启动应用..."
echo "访问地址: http://localhost:5001"
echo "按 Ctrl+C 停止服务器"
echo ""
python3 app.py

