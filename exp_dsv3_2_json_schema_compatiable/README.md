# DeepSeek V3.2 JSON Schema Compatible API

基于官方DeepSeek V3.2 API的生产级FastAPI服务，提供支持Strict模式的JSON Schema Tool Calling功能。

## 特性

- ✅ 支持DeepSeek V3.2 Tool Calling的Strict模式
- ✅ 自动JSON Schema验证和转换
- ✅ 完整的错误处理和日志记录
- ✅ 异步高性能架构
- ✅ 自动生成OpenAPI文档（Swagger UI）
- ✅ 生产级部署配置（Docker）
- ✅ 全面的测试覆盖

## 快速开始

### 1. 克隆项目

```bash
cd /home/user/exp_dsv3_2_json_schema_compatiable
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，添加您的DeepSeek API密钥：

```bash
DEEPSEEK_API_KEY=your_api_key_here
```

### 3. 安装依赖

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 4. 启动服务

```bash
# 使用启动脚本
bash scripts/start.sh

# 或直接使用uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. 访问文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Docker部署

### 使用Docker Compose（推荐）

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 使用Docker

```bash
# 构建镜像
docker build -t deepseek-api:latest .

# 运行容器
docker run -d \\
  -p 8000:8000 \\
  -e DEEPSEEK_API_KEY=your_api_key \\
  deepseek-api:latest
```

## API使用示例

### 基础聊天（无Tools）

```bash
curl -X POST http://localhost:8000/api/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "deepseek-chat",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'
```

### 带Tool Calling的请求

```bash
curl -X POST http://localhost:8000/api/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "deepseek-chat",
    "messages": [
      {"role": "user", "content": "What'\''s the weather in Beijing?"}
    ],
    "tools": [{
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "Get weather information",
        "strict": true,
        "parameters": {
          "type": "object",
          "properties": {
            "location": {
              "type": "string",
              "description": "City name"
            }
          },
          "required": ["location"],
          "additionalProperties": false
        }
      }
    }]
  }'
```

## 测试

运行测试套件：

```bash
# 使用测试脚本
bash scripts/test.sh

# 或直接使用pytest
pytest tests/ -v --cov=app --cov-report=html
```

查看覆盖率报告：

```bash
open htmlcov/index.html
```

## 项目结构

```
.
├── app/
│   ├── api/routes/          # API端点
│   ├── core/                # 核心配置（日志、配置）
│   ├── models/              # Pydantic模型
│   ├── services/            # 业务逻辑（验证器、转换器、客户端）
│   ├── utils/               # 工具函数
│   ├── middleware/          # 中间件
│   └── main.py              # 应用入口
├── tests/                   # 测试套件
├── scripts/                 # 启动和测试脚本
├── docs/                    # 文档
├── Dockerfile               # Docker配置
├── docker-compose.yml       # Docker Compose配置
└── requirements.txt         # Python依赖
```

## JSON Schema要求

DeepSeek Strict模式对JSON Schema有以下限制：

### Object类型
- ✅ 所有properties必须在`required`数组中
- ✅ `additionalProperties`必须为`false`

### String类型
- ✅ 支持: `pattern`, `format` (email, hostname, ipv4, ipv6, uuid)
- ❌ 不支持: `minLength`, `maxLength`

### Array类型
- ❌ 不支持: `minItems`, `maxItems`

本服务会自动验证并转换Schema以满足这些要求。

## 配置选项

主要环境变量：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DEEPSEEK_API_KEY` | DeepSeek API密钥 | 必填 |
| `DEEPSEEK_BASE_URL` | API基础URL | `https://api.deepseek.com/beta` |
| `DEEPSEEK_TIMEOUT` | 请求超时（秒） | `30` |
| `DEEPSEEK_MAX_RETRIES` | 最大重试次数 | `3` |
| `DEBUG` | 调试模式 | `false` |
| `LOG_LEVEL` | 日志级别 | `INFO` |
| `HOST` | 监听地址 | `0.0.0.0` |
| `PORT` | 监听端口 | `8000` |
| `WORKERS` | 工作进程数 | `1` |

## API端点

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/` | API信息 |
| POST | `/api/v1/chat/completions` | 聊天完成 |

## 技术栈

- **Python 3.13+**
- **FastAPI** - 现代化的Web框架
- **Pydantic v2** - 数据验证
- **OpenAI SDK** - DeepSeek兼容的API客户端
- **Structlog** - 结构化日志
- **Pytest** - 测试框架
- **Docker** - 容器化部署

## 参考资料

- [DeepSeek Tool Calls文档](https://api-docs.deepseek.com/guides/tool_calls)
- [DeepSeek Chat Completion API](https://api-docs.deepseek.com/api/create-chat-completion)
- [FastAPI官方文档](https://fastapi.tiangolo.com/)

## License

MIT

## 贡献

欢迎提交Issue和Pull Request！
