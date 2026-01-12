#!/bin/bash
set -e

echo "=========================================="
echo "AIWord 应用启动脚本"
echo "=========================================="

# 检查必要的目录
echo "检查目录结构..."
mkdir -p temp_images
chmod 755 temp_images
echo "✓ temp_images 目录已准备"

# 初始化数据库
echo ""
echo "开始初始化数据库..."
python init_db.py

# 启动应用
echo ""
echo "启动应用..."
echo "应用将在 http://0.0.0.0:8000 上运行"
echo "=========================================="
uvicorn main:app --host 0.0.0.0 --port 8000 --log-level info
