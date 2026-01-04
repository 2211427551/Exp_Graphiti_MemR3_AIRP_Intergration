#!/bin/bash

echo "========================================="
echo "启动AIRP Knowledge Graph API"
echo "========================================="

# 检查Neo4j是否运行
echo "检查Neo4j状态..."
if ! docker ps | grep -q neo4j; then
    echo "❌ Neo4j未运行，请先启动："
    echo "   docker-compose up -d neo4j"
    exit 1
fi
echo "✅ Neo4j正在运行"

# 检查环境变量
echo ""
echo "检查环境变量..."
if [ -z "$NEO4J_PASSWORD" ]; then
    echo "⚠️  警告: NEO4J_PASSWORD未设置"
    echo "   使用默认密码: password"
    export NEO4J_PASSWORD=password
else
    echo "✅ NEO4J_PASSWORD已设置"
fi

# 启动API
echo ""
echo "启动API服务器..."
cd api_service
python -m api_service.api.main
