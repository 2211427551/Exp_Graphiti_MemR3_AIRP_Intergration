# AIRP记忆系统测试报告

**生成时间**: 2026-01-06 17:34:00

---

## 测试概览

本报告包含第一阶段（Week 1-6）功能的完整测试结果。

## 测试范围

### 单元测试

- **SillyTavern解析器服务** (`test_parser_service.py`)
  - 标签检测（正则表达式）
  - 内容分类（指令性/叙事性）
  - World Info解析
  - Chat History解析
  - 对话模式识别

- **变化检测** (`test_change_detection.py`)
  - World Info变化检测
  - Chat History变化检测
  - 状态更新
  - 哈希计算

### 集成测试

- **API端点** (`test_api_endpoints.py`)
  - 健康检查端点
  - OpenAI兼容的Chat Completions端点
  - 完整请求处理流程
  - 响应格式验证

## 测试环境

- **Python版本**: 3.11+
- **测试框架**: pytest 7.4.3
- **容器化**: Docker (neo4j, redis, test-runner)

## 运行测试

### 使用Docker（推荐）

```bash
# 运行所有测试
./tests/run_tests.sh

# 只运行单元测试
./tests/run_tests.sh -u

# 只运行集成测试
./tests/run_tests.sh -i

# 生成覆盖率报告
./tests/run_tests.sh -c

# 详细输出
./tests/run_tests.sh -v
```

### 在本地运行

```bash
# 运行所有测试
./tests/run_tests.sh -l

# 使用Python脚本
python tests/run_tests.py -l -c
```

## 测试说明

### 标记说明

- `@pytest.mark.unit`: 单元测试
- `@pytest.mark.integration`: 集成测试
- `@pytest.mark.parser`: 解析器相关测试
- `@pytest.mark.change_detection`: 变化检测相关测试
- `@pytest.mark.api`: API端点测试

### 运行特定标记的测试

```bash
pytest -m unit

pytest -m parser

pytest -m api
```

## 报告文件

- **HTML覆盖率报告**: `tests/test-coverage/html/index.html`
- **JSON覆盖率数据**: `tests/test-coverage/coverage.json`
- **Markdown报告**: `tests/test-results/TEST_REPORT.md` (本文件)

## 下一步

1. 查看HTML覆盖率报告了解详细覆盖情况
2. 针对低覆盖率的模块补充测试用例
3. 确保所有测试通过后再部署到生产环境

---

*报告生成于 2026-01-06 17:34:00*