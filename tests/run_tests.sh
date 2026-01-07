#!/bin/bash

# ========================================
# 测试运行脚本
# ========================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示帮助信息
show_help() {
    echo "使用方法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help              显示此帮助信息"
    echo "  -l, --local            在本地运行测试（不使用Docker）"
    echo "  -d, --docker           使用Docker运行测试（默认）"
    echo "  -u, --unit             只运行单元测试"
    echo "  -i, --integration      只运行集成测试"
    echo "  -c, --coverage         生成代码覆盖率报告"
    echo "  -v, --verbose          详细输出模式"
    echo "  --clean                清理测试数据和容器"
    echo ""
    echo "示例:"
    echo "  $0                     使用Docker运行所有测试"
    echo "  $0 -l                  在本地运行所有测试"
    echo "  $0 -u -c               在本地运行单元测试并生成覆盖率报告"
    echo "  $0 -d -i -v            使用Docker运行集成测试（详细模式）"
}

# 默认选项
USE_DOCKER=true
RUN_UNIT=true
RUN_INTEGRATION=true
GENERATE_COVERAGE=false
VERBOSE=false
CLEAN=false

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -l|--local)
            USE_DOCKER=false
            shift
            ;;
        -d|--docker)
            USE_DOCKER=true
            shift
            ;;
        -u|--unit)
            RUN_UNIT=true
            RUN_INTEGRATION=false
            shift
            ;;
        -i|--integration)
            RUN_UNIT=false
            RUN_INTEGRATION=true
            shift
            ;;
        -c|--coverage)
            GENERATE_COVERAGE=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --clean)
            CLEAN=true
            shift
            ;;
        *)
            print_error "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
done

# 清理函数
clean_test_data() {
    print_info "清理测试数据..."
    
    if [ "$USE_DOCKER" = true ]; then
        # 停止并删除测试容器
        docker-compose -f tests/docker-compose.test.yml down -v
        
        # 删除测试数据卷
        docker volume rm airp-neo4j-test-data 2>/dev/null || true
        docker volume rm airp-neo4j-test-logs 2>/dev/null || true
        docker volume rm airp-redis-test-data 2>/dev/null || true
    fi
    
    # 删除本地测试结果
    rm -rf tests/test-results
    rm -rf tests/test-coverage
    
    print_success "清理完成"
    exit 0
}

# 如果指定了清理选项
if [ "$CLEAN" = true ]; then
    clean_test_data
fi

# 获取项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

print_info "项目根目录: $PROJECT_ROOT"
print_info "测试模式: $([ "$USE_DOCKER" = true ] && echo "Docker" || echo "本地")"
print_info "测试类型: $([ "$RUN_UNIT" = true ] && echo "单元测试 " || echo "")$([ "$RUN_INTEGRATION" = true ] && echo "集成测试" || echo "")"

# ========================================
# 本地测试运行
# ========================================

run_local_tests() {
    print_info "在本地运行测试..."
    
    # 设置Python路径
    export PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/api-service"
    
    # 安装测试依赖
    print_info "检查测试依赖..."
    pip list | grep pytest > /dev/null || {
        print_warning "pytest未安装，正在安装..."
        pip install -q pytest pytest-asyncio pytest-cov pytest-mock pytest-xdist
    }
    
    # 构建pytest命令
    PYTEST_CMD="pytest"
    
    # 添加测试路径
    if [ "$RUN_UNIT" = true ]; then
        PYTEST_CMD="$PYTEST_CMD tests/unit/"
    fi
    
    if [ "$RUN_INTEGRATION" = true ]; then
        PYTEST_CMD="$PYTEST_CMD tests/integration/"
    fi
    
    # 添加选项
    if [ "$VERBOSE" = true ]; then
        PYTEST_CMD="$PYTEST_CMD -v -s"
    else
        PYTEST_CMD="$PYTEST_CMD -v"
    fi
    
    # 添加覆盖率
    if [ "$GENERATE_COVERAGE" = true ]; then
        PYTEST_CMD="$PYTEST_CMD --cov=api-service --cov-report=html --cov-report=term --cov-report=json"
    fi
    
    # 添加并行执行
    PYTEST_CMD="$PYTEST_CMD -n auto"
    
    # 运行测试
    print_info "执行命令: $PYTEST_CMD"
    eval $PYTEST_CMD
    
    # 显示覆盖率报告
    if [ "$GENERATE_COVERAGE" = true ]; then
        print_success "覆盖率报告已生成在 htmlcov/ 目录"
    fi
}

# ========================================
# Docker测试运行
# ========================================

run_docker_tests() {
    print_info "使用Docker运行测试..."
    
    # 检查Docker是否运行
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker未运行，请先启动Docker"
        exit 1
    fi
    
    # 检查docker-compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "docker-compose未安装"
        exit 1
    fi
    
    # 确定使用docker-compose还是docker compose
    DOCKER_COMPOSE_CMD="docker-compose"
    if docker compose version &> /dev/null; then
        DOCKER_COMPOSE_CMD="docker compose"
    fi
    
    # 构建测试环境
    print_info "构建测试环境..."
    $DOCKER_COMPOSE_CMD -f tests/docker-compose.test.yml build
    
    # 运行测试
    print_info "启动测试容器并运行测试..."
    
    # 设置环境变量
    export PYTEST_VERBOSE=$([ "$VERBOSE" = true ] && echo "true" || echo "false")
    
    # 构建pytest命令
    PYTEST_ARGS=""
    
    if [ "$RUN_UNIT" = true ] && [ "$RUN_INTEGRATION" = false ]; then
        PYTEST_ARGS="tests/unit/"
    elif [ "$RUN_UNIT" = false ] && [ "$RUN_INTEGRATION" = true ]; then
        PYTEST_ARGS="tests/integration/"
    fi
    
    # 修改docker-compose命令以支持pytest参数
    if [ -n "$PYTEST_ARGS" ]; then
        # 需要修改docker-compose.test.yml中的command
        print_info "运行指定测试: $PYTEST_ARGS"
        $DOCKER_COMPOSE_CMD -f tests/docker-compose.test.yml run --rm test-runner pytest /app/$PYTEST_ARGS -v $([ "$VERBOSE" = true ] && echo "-s" || echo "") $([ "$GENERATE_COVERAGE" = true ] && echo "--cov=/app/api-service --cov-report=html --cov-report=term" || echo "")
    else
        # 运行所有测试
        $DOCKER_COMPOSE_CMD -f tests/docker-compose.test.yml up --abort-on-container-exit
    fi
    
    # 检查测试结果
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -eq 0 ]; then
        print_success "所有测试通过！"
    else
        print_error "测试失败，退出码: $EXIT_CODE"
    fi
    
    # 复制测试结果到本地
    print_info "复制测试结果..."
    mkdir -p tests/test-results tests/test-coverage
    docker cp airp-test-runner:/app/test-results/. tests/test-results/ 2>/dev/null || true
    docker cp airp-test-runner:/app/coverage/. tests/test-coverage/ 2>/dev/null || true
    
    # 显示覆盖率信息
    if [ "$GENERATE_COVERAGE" = true ] && [ -f "tests/test-coverage/coverage.json" ]; then
        print_success "覆盖率报告已生成在 tests/test-coverage/ 目录"
    fi
    
    # 停止容器
    print_info "停止测试容器..."
    $DOCKER_COMPOSE_CMD -f tests/docker-compose.test.yml down
    
    exit $EXIT_CODE
}

# ========================================
# 主逻辑
# ========================================

# 创建测试结果目录
mkdir -p tests/test-results
mkdir -p tests/test-coverage

# 运行测试
if [ "$USE_DOCKER" = true ]; then
    run_docker_tests
else
    run_local_tests
fi
