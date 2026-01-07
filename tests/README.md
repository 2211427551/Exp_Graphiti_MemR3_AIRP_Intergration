# AIRP记忆系统测试套件

本测试套件为AIRP记忆系统（第一阶段：Week 1-6）提供完整的测试覆盖，包括单元测试和集成测试。

## 📋 目录

- [测试范围](#测试范围)
- [测试结构](#测试结构)
- [快速开始](#快速开始)
- [运行测试](#运行测试)
- [测试环境](#测试环境)
- [测试覆盖率](#测试覆盖率)
- [生成报告](#生成报告)
- [故障排查](#故障排查)

## 🎯 测试范围

### 第一阶段功能（Week 1-6）

#### 单元测试

1. **SillyTavern解析器服务** (`test_parser_service.py`)
   - ✅ 标签检测（正则表达式）
   - ✅ 内容分类（指令性/叙事性）
   - ✅ World Info解析
   - ✅ Chat History解析
   - ✅ 对话模式识别
   - ✅ 边界情况处理
   - ✅ 性能测试

2. **变化检测** (`test_change_detection.py`)
   - ✅ World Info变化检测
   - ✅ Chat History变化检测
   - ✅ 状态更新
   - ✅ 哈希计算
   - ✅ 条目ID计算

#### 集成测试

1. **API端点** (`test_api_endpoints.py`)
   - ✅ 健康检查端点
   - ✅ OpenAI兼容的Chat Completions端点
   - ✅ 完整请求处理流程
   - ✅ 响应格式验证
   - ✅ 错误处理
   - ✅ CORS支持
   - ✅ 多会话管理

## 📁 测试结构

```
tests/
├── __init__.py                 # 测试包初始化
├── conftest.py                 # pytest配置和fixtures
├── pytest.ini                  # pytest配置文件
├── run_tests.sh                # Bash测试运行脚本
├── run_tests.py                # Python测试运行脚本
├── generate_test_report.py     # 测试报告生成器
├── README.md                   # 本文件
├── docker-compose.test.yml      # Docker测试环境配置
├── Dockerfile.test             # Docker测试镜像
├── unit/                      # 单元测试目录
│   ├── __init__.py
│   ├── test_parser_service.py   # 解析器服务测试
│   └── test_change_detection.py # 变化检测测试
├── integration/                # 集成测试目录
│   ├── __init__.py
│   └── test_api_endpoints.py   # API端点测试
├── test-results/              # 测试结果输出
│   └── TEST_REPORT.md        # 测试报告
└── test-coverage/            # 覆盖率报告
    ├── html/
    │   └── index.html        # HTML覆盖率报告
    └── coverage.json        # JSON覆盖率数据
```

## 🚀 快速开始

### 前置要求

- Python 3.11+
- Docker（用于Docker模式）
- docker-compose（用于Docker模式）

### 安装依赖

```bash
# 进入项目根目录
cd /home/user/Exp_Graphiti_MemR3_AIRP_Intergration

# 安装Python依赖
pip install -r api-service/requirements.txt

# 安装测试依赖
pip install pytest pytest-asyncio pytest-cov pytest-mock pytest-xdist pytest-html
```

## 🏃 运行测试

### 方式1：使用Bash脚本（推荐）

```bash
# 运行所有测试（Docker模式，默认）
./tests/run_tests.sh

# 运行所有测试（本地模式）
./tests/run_tests.sh -l

# 只运行单元测试
./tests/run_tests.sh -u

# 只运行集成测试
./tests/run_tests.sh -i

# 生成覆盖率报告
./tests/run_tests.sh -c

# 详细输出模式
./tests/run_tests.sh -v

# 组合选项：本地运行单元测试，生成覆盖率，详细输出
./tests/run_tests.sh -l -u -c -v

# 清理测试数据和容器
./tests/run_tests.sh --clean
```

### 方式2：使用Python脚本

```bash
# 运行所有测试
python tests/run_tests.py

# 本地运行所有测试
python tests/run_tests.py -l

# 只运行单元测试，生成覆盖率
python tests/run_tests.py -u -c

# 只运行集成测试
python tests/run_tests.py -i

# 查看帮助
python tests/run_tests.py --help
```

### 方式3：直接使用pytest

```bash
# 运行所有测试
pytest tests/

# 运行单元测试
pytest tests/unit/

# 运行集成测试
pytest tests/integration/

# 运行特定测试文件
pytest tests/unit/test_parser_service.py

# 运行特定测试函数
pytest tests/unit/test_parser_service.py::TestSillyTavernParser::test_parse_empty_content

# 生成覆盖率报告
pytest tests/ --cov=api-service --cov-report=html --cov-report=term

# 并行运行测试
pytest tests/ -n auto

# 使用标记运行
pytest -m unit          # 只运行单元测试
pytest -m integration   # 只运行集成测试
pytest -m parser        # 只运行解析器测试
pytest -m api           # 只运行API测试
```

## 🐳 测试环境

### Docker模式（推荐）

Docker模式提供隔离的测试环境，包含：

- **Neo4j 5.15.0-community**: 图数据库
  - 端口: 7688 (Bolt), 7475 (HTTP)
  - 认证: neo4j/test_password_123
  - 插件: APOC

- **Redis 7-alpine**: 缓存和状态存储
  - 端口: 6380

- **测试运行器**: Python测试环境
  - Python 3.11-slim
  - 包含所有测试依赖

**优势：**
- ✅ 完全隔离的环境
- ✅ 一致的测试结果
- ✅ 易于清理和重建
- ✅ 支持CI/CD

### 本地模式

本地模式在主机上运行测试，需要：

- 已安装Neo4j（可选，用于真实数据库测试）
- 已安装Redis（可选，用于真实缓存测试）
- Python环境配置正确

**优势：**
- ✅ 更快的迭代速度
- ✅ 更容易调试
- ✅ 无需Docker

## 📊 测试覆盖率

### 查看覆盖率报告

运行测试后，覆盖率报告将生成在：

- **HTML报告**: `tests/test-coverage/html/index.html`
- **JSON数据**: `tests/test-coverage/coverage.json`
- **终端摘要**: 运行测试时自动显示

### 覆盖率目标

- **总体目标**: ≥ 80%
- **核心模块**: ≥ 90%
- **辅助模块**: ≥ 70%

### 提高覆盖率

1. 识别低覆盖率模块
2. 分析未覆盖的代码路径
3. 添加相应的测试用例
4. 重新运行测试验证

## 📝 生成报告

### 自动生成报告

测试运行脚本会自动生成报告：

```bash
# 运行测试并生成报告
./tests/run_tests.sh -c
```

### 手动生成报告

```bash
# 生成测试报告
python tests/generate_test_report.py

# 指定结果目录
python tests/generate_test_report.py --results-dir tests/test-results
```

### 报告内容

生成的报告包括：

- ✅ 测试概览
- ✅ 代码覆盖率统计
- ✅ 模块覆盖率详情
- ✅ 测试范围说明
- ✅ 测试环境信息
- ✅ 运行说明
- ✅ 下一步建议

报告格式：
- Markdown: `tests/test-results/TEST_REPORT.md`
- HTML: `tests/test-results/TEST_REPORT.html`

## 🔧 故障排查

### 问题1：Docker未运行

**错误信息**: `Docker未运行，请先启动Docker`

**解决方案**:
```bash
# 启动Docker Desktop（Windows/Mac）
# 或启动Docker服务（Linux）
sudo systemctl start docker
```

### 问题2：端口已被占用

**错误信息**: `bind: address already in use`

**解决方案**:
```bash
# 修改docker-compose.test.yml中的端口映射
# 或停止占用端口的进程
sudo lsof -i :7688
sudo kill -9 <PID>
```

### 问题3：测试依赖缺失

**错误信息**: `ModuleNotFoundError: No module named 'pytest'`

**解决方案**:
```bash
pip install pytest pytest-asyncio pytest-cov pytest-mock pytest-xdist pytest-html
```

### 问题4：Neo4j连接失败

**错误信息**: `Failed to establish connection to Neo4j`

**解决方案**:
1. 检查Neo4j容器是否运行: `docker ps`
2. 检查Neo4j日志: `docker logs airp-neo4j-test`
3. 验证连接配置: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
4. 确保Neo4j已启动并准备就绪

### 问题5：测试超时

**错误信息**: `TimeoutError: Condition not met within X seconds`

**解决方案**:
1. 增加超时时间（在conftest.py的`wait_for_condition`函数中）
2. 检查系统资源使用情况
3. 优化测试用例，减少等待时间

### 问题6：Mock测试失败

**错误信息**: `AssertionError: Expected X but got Y`

**解决方案**:
1. 检查mock配置是否正确
2. 验证mock返回值设置
3. 使用`--pdb`选项进入调试模式
4. 添加详细的日志输出

## 📚 测试最佳实践

### 1. 编写清晰的测试名称

```python
# ✅ 好的命名
def test_parse_world_info_location():
    """测试解析地点条目"""

# ❌ 不好的命名
def test_1():
```

### 2. 使用描述性的断言

```python
# ✅ 好的断言
assert len(result.instructions) == 1, "应该只包含一个指令块"
assert result.instructions[0].tag == "核心指导", "指令块标签应该正确"

# ❌ 不好的断言
assert len(result.instructions) == 1
```

### 3. 测试独立性和可重复性

```python
# 每个测试应该独立运行，不依赖其他测试的执行顺序
# 每个测试应该可以重复运行，产生相同的结果
```

### 4. 使用fixtures共享测试数据

```python
# 在conftest.py中定义fixtures
@pytest.fixture
def sample_parsed_content():
    return ParsedContent(...)
```

### 5. 测试边界情况

```python
# ✅ 测试空输入
def test_parse_empty_content(self, parser):
    result = parser.parse("")
    assert len(result.instructions) == 0

# ✅ 测试无效输入
def test_parse_malformed_tag(self, parser):
    result = parser.parse("<核心指导>未闭合")
    assert isinstance(result, ParsedContent)
```

## 🤝 贡献指南

添加新测试时：

1. 确定测试类型（单元/集成）
2. 选择合适的测试文件或创建新文件
3. 添加测试函数和必要的fixtures
4. 运行测试确保通过
5. 更新覆盖率
6. 更新文档

## 📞 获取帮助

遇到问题时：

1. 查看本文档的[故障排查](#故障排查)部分
2. 查看pytest文档: https://docs.pytest.org/
3. 查看项目文档: `AIRP记忆系统完整实施指南.md`
4. 提交Issue或联系开发团队

## 📄 许可证

本测试套件遵循项目的主许可证。

---

*最后更新: 2026-01-06*
