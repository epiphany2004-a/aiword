FROM python:3.9-slim

# 避免生成.pyc并减少输出
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 安装 mysql 客户端工具（用于执行 SQL 文件）
RUN apt-get update && \
    apt-get install -y --no-install-recommends default-mysql-client && \
    rm -rf /var/lib/apt/lists/*

# 先单独复制依赖文件以利用缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 再复制项目源代码（包括 SQL 文件）
COPY . .

# 创建必要的目录并设置权限
RUN mkdir -p temp_images && \
    chmod 755 temp_images && \
    chmod +x start.sh

EXPOSE 8000

# 使用启动脚本，先初始化数据库再启动应用
CMD ["./start.sh"]
