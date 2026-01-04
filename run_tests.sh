#!/bin/bash

echo "========================================="
echo "运行AIRP Knowledge Graph API测试"
echo "========================================="

# 检查Python环境
if ! command -v python &> /dev/null; then
    echo "❌ Python未安装"
    exit 1
fi

# 检查pytest是否安装
if ! python -m pytest --version &> /dev/null; then
    echo "⚠️  pytest未安装，正在安装..."
    pip install pytest pytest-asyncio pytest-cov
fi

# 检查环境变量
echo ""
echo "检查环境变量..."
if [ -z "$NEO4J_PASSWORD" ]; then
    echo "⚠️  警告: NEO4J_PASSWORD未设置"
    echo "   测试可能需要Neo4j密码"
    export NEO4J_PASSWORD=testpassword123
else
    echo "✅ NEO4J_PASSWORD已设置"
fi

# 检查Neo4j
echo ""
echo "检查Neo4j状态..."
if docker ps | grep -q neo4j; then
    echo "✅ Neo4j正在运行"
else
    echo "⚠️  Neo4j未运行"
    echo "   测试可能失败，建议先启动Neo4j"
    echo "   docker-compose up -d neo4j"
    read -p "是否继续运行测试？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 运行测试
echo ""
echo "========================================="
echo "运行测试"
echo "========================================="

# 测试选项
echo ""
echo "选择测试类型："
echo "1) 运行所有测试"
echo "2) 只运行单元测试"
echo "3) 只运行API端点测试"
echo "4) 只运行模型测试"
echo "5) 生成测试覆盖率报告"
read -p "请选择 (1-5): " choice

case $choice in
    1)
        echo "运行所有测试..."
        python -m pytest tests/ -v --tb=short
        ;;
    2)
        echo "运行单元测试..."
        python -m pytest tests/test_enhanced_graphiti_service.py -v --tb=short
        ;;
    3)
        echo "运行API端点测试..."
        python -m pytest tests/test_api_endpoints.py -v --tb=short
        ;;
    4)
        echo "运行模型测试..."
        python -m pytest tests/test_models.py -v --tb=short
        ;;
    5)
        echo "生成测试覆盖率报告..."
        python -m pytest tests/ --cov=api_service --cov-report=html --cov-report=term
        echo "✅ 覆盖率报告已生成：htmlcov/index.html"
        ;;
    *)
        echo "无效选择"
        exit 1
        ;;
esac

# 检查测试结果
if [ $? -eq 0 ]; then
    echo ""
    echo "========================================="
    echo "✅ 测试通过！"
    echo "========================================="
else
    echo ""
    echo "========================================="
    echo "❌ 测试失败"
    echo "========================================="
    exit 1
fi
