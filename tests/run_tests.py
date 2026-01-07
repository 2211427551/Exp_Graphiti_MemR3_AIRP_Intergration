#!/usr/bin/env python3
"""
测试运行脚本（Python版本）

支持本地和Docker测试运行
"""

import os
import sys
import argparse
import subprocess
import shutil
from pathlib import Path

# 颜色代码
class Colors:
    BLUE = '\033[0;34m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    NC = '\033[0m'  # No Color

def print_info(message):
    print(f"{Colors.BLUE}[INFO]{Colors.NC} {message}")

def print_success(message):
    print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {message}")

def print_warning(message):
    print(f"{Colors.YELLOW}[WARNING]{Colors.NC} {message}")

def print_error(message):
    print(f"{Colors.RED}[ERROR]{Colors.NC} {message}")

def run_command(cmd, cwd=None, check=True):
    """运行命令并返回结果"""
    print_info(f"执行命令: {cmd}")
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=cwd,
        check=check,
        capture_output=not check
    )
    return result

def clean_test_data(use_docker=True):
    """清理测试数据"""
    print_info("清理测试数据...")
    
    if use_docker:
        # 停止Docker容器
        print_info("停止测试容器...")
        run_command("docker-compose -f tests/docker-compose.test.yml down -v", check=False)
        
        # 删除数据卷
        print_info("删除数据卷...")
        run_command("docker volume rm airp-neo4j-test-data", check=False)
        run_command("docker volume rm airp-neo4j-test-logs", check=False)
        run_command("docker volume rm airp-redis-test-data", check=False)
    
    # 删除本地测试结果
    print_info("删除本地测试结果...")
    test_results_path = Path("tests/test-results")
    test_coverage_path = Path("tests/test-coverage")
    
    if test_results_path.exists():
        shutil.rmtree(test_results_path)
    
    if test_coverage_path.exists():
        shutil.rmtree(test_coverage_path)
    
    print_success("清理完成")

def run_local_tests(args):
    """在本地运行测试"""
    print_info("在本地运行测试...")
    
    # 设置Python路径
    project_root = Path(__file__).parent.parent
    os.environ["PYTHONPATH"] = str(project_root) + ":" + str(project_root / "api-service")
    
    # 检查测试依赖
    print_info("检查测试依赖...")
    try:
        import pytest
        print_success("pytest已安装")
    except ImportError:
        print_warning("pytest未安装，正在安装...")
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-q",
            "pytest", "pytest-asyncio", "pytest-cov", 
            "pytest-mock", "pytest-xdist"
        ], check=True)
    
    # 构建pytest命令
    pytest_cmd = [sys.executable, "-m", "pytest"]
    
    # 添加测试路径
    test_paths = []
    if args.unit:
        test_paths.append("tests/unit/")
    if args.integration:
        test_paths.append("tests/integration/")
    
    if test_paths:
        pytest_cmd.extend(test_paths)
    else:
        pytest_cmd.append("tests/")
    
    # 添加选项
    if args.verbose:
        pytest_cmd.extend(["-v", "-s"])
    else:
        pytest_cmd.append("-v")
    
    # 添加覆盖率
    if args.coverage:
        pytest_cmd.extend([
            "--cov=api-service",
            "--cov-report=html",
            "--cov-report=term",
            "--cov-report=json"
        ])
    
    # 添加并行执行
    pytest_cmd.extend(["-n", "auto"])
    
    # 运行测试
    print_info("执行命令: " + " ".join(pytest_cmd))
    result = subprocess.run(pytest_cmd, check=False)
    
    # 显示覆盖率报告
    if args.coverage:
        print_success("覆盖率报告已生成在 htmlcov/ 目录")
    
    return result.returncode

def run_docker_tests(args):
    """使用Docker运行测试"""
    print_info("使用Docker运行测试...")
    
    # 检查Docker
    print_info("检查Docker环境...")
    try:
        result = run_command("docker info", check=False)
        if result.returncode != 0:
            print_error("Docker未运行，请先启动Docker")
            return 1
    except Exception as e:
        print_error(f"Docker检查失败: {e}")
        return 1
    
    # 检查docker-compose
    docker_compose_cmd = "docker-compose"
    if shutil.which("docker compose"):
        docker_compose_cmd = "docker compose"
    elif not shutil.which("docker-compose"):
        print_error("docker-compose未安装")
        return 1
    
    print_info(f"使用命令: {docker_compose_cmd}")
    
    # 构建测试环境
    print_info("构建测试环境...")
    run_command(f"{docker_compose_cmd} -f tests/docker-compose.test.yml build")
    
    # 准备环境变量
    env = os.environ.copy()
    env["PYTEST_VERBOSE"] = "true" if args.verbose else "false"
    
    # 构建pytest命令
    pytest_args = ""
    
    if args.unit and not args.integration:
        pytest_args = "tests/unit/"
    elif not args.unit and args.integration:
        pytest_args = "tests/integration/"
    
    # 运行测试
    if pytest_args:
        print_info(f"运行指定测试: {pytest_args}")
        cmd = (
            f"{docker_compose_cmd} -f tests/docker-compose.test.yml run --rm test-runner "
            f"pytest /app/{pytest_args} -v "
            f"{'-s ' if args.verbose else ''}"
            f"--cov=/app/api-service --cov-report=html --cov-report=term"
        )
        result = run_command(cmd, check=False)
    else:
        print_info("运行所有测试...")
        cmd = f"{docker_compose_cmd} -f tests/docker-compose.test.yml up --abort-on-container-exit"
        result = run_command(cmd, check=False)
    
    # 检查结果
    if result.returncode == 0:
        print_success("所有测试通过！")
    else:
        print_error(f"测试失败，退出码: {result.returncode}")
    
    # 复制测试结果
    print_info("复制测试结果...")
    Path("tests/test-results").mkdir(parents=True, exist_ok=True)
    Path("tests/test-coverage").mkdir(parents=True, exist_ok=True)
    
    run_command("docker cp airp-test-runner:/app/test-results/. tests/test-results/", check=False)
    run_command("docker cp airp-test-runner:/app/coverage/. tests/test-coverage/", check=False)
    
    # 停止容器
    print_info("停止测试容器...")
    run_command(f"{docker_compose_cmd} -f tests/docker-compose.test.yml down", check=False)
    
    return result.returncode

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="AIRP记忆系统测试运行脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                     使用Docker运行所有测试
  %(prog)s -l                  在本地运行所有测试
  %(prog)s -u -c               在本地运行单元测试并生成覆盖率报告
  %(prog)s -d -i -v            使用Docker运行集成测试（详细模式）
  %(prog)s --clean             清理测试数据和容器
        """
    )
    
    parser.add_argument(
        "-l", "--local",
        action="store_true",
        help="在本地运行测试（不使用Docker）"
    )
    
    parser.add_argument(
        "-d", "--docker",
        action="store_true",
        help="使用Docker运行测试（默认）"
    )
    
    parser.add_argument(
        "-u", "--unit",
        action="store_true",
        default=True,
        help="运行单元测试（默认：True）"
    )
    
    parser.add_argument(
        "-i", "--integration",
        action="store_true",
        default=True,
        help="运行集成测试（默认：True）"
    )
    
    parser.add_argument(
        "-c", "--coverage",
        action="store_true",
        help="生成代码覆盖率报告"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="详细输出模式"
    )
    
    parser.add_argument(
        "--clean",
        action="store_true",
        help="清理测试数据和容器"
    )
    
    args = parser.parse_args()
    
    # 如果指定了清理
    if args.clean:
        clean_test_data(use_docker=not args.local)
        return 0
    
    # 设置默认值
    use_docker = True
    if args.local:
        use_docker = False
    elif args.docker:
        use_docker = True
    
    # 如果没有指定测试类型，默认运行所有测试
    if not args.unit and not args.integration:
        args.unit = True
        args.integration = True
    
    # 切换到项目根目录
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    print_info(f"项目根目录: {project_root}")
    print_info(f"测试模式: {'Docker' if use_docker else '本地'}")
    test_types = []
    if args.unit:
        test_types.append("单元测试")
    if args.integration:
        test_types.append("集成测试")
    print_info(f"测试类型: {' '.join(test_types)}")
    
    # 创建测试结果目录
    Path("tests/test-results").mkdir(parents=True, exist_ok=True)
    Path("tests/test-coverage").mkdir(parents=True, exist_ok=True)
    
    # 运行测试
    try:
        if use_docker:
            exit_code = run_docker_tests(args)
        else:
            exit_code = run_local_tests(args)
        
        return exit_code
    except KeyboardInterrupt:
        print_warning("\n测试被用户中断")
        return 130
    except Exception as e:
        print_error(f"测试运行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
