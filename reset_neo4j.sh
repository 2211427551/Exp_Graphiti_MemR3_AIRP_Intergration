#!/bin/bash
# Neo4j数据目录重置脚本
# 使用方法: bash reset_neo4j.sh

echo "⚠️  警告：此脚本将删除所有Neo4j数据！"
echo "请确保已备份重要数据"
read -p "继续吗？(yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "操作已取消"
    exit 0
fi

echo "🛑 停止Neo4j容器..."
docker-compose down

echo "🗑️  删除Neo4j数据目录..."
sudo rm -rf neo4j/data/*

echo "✅ Neo4j数据目录已清空"
echo "🚀 重新启动Neo4j容器..."
docker-compose up -d neo4j

echo "⏳ 等待Neo4j启动（约30秒）..."
sleep 30

echo "✅ Neo4j已重新初始化"
echo "📝 新密码是: neo4j"
echo "🔗 Neo4j浏览器: http://localhost:7474"
