# OpenAI兼容API配置指南

## 概述

`graphiti_core`库需要OpenAI兼容的API来提供embedding和LLM功能。本项目支持使用任何OpenAI兼容的API服务提供商。

## 支持的API提供商

1. **OpenAI** (官方)
2. **硅基流动** (推荐，支持qwen3embedding)
3. **DeepSeek** (用于LLM功能，非embedding)
4. **任何其他OpenAI兼容API**

## 硅基流动 qwen3embedding 配置

### 步骤1：获取API密钥

1. 访问 [硅基流动官网](https://siliconflow.cn)
2. 注册账号并登录
3. 创建API密钥

### 步骤2：配置环境变量

#### 方法A：使用.env文件（推荐）

在项目根目录创建或编辑`.env`文件：

```bash
# 硅基流动配置
OPENAI_API_KEY=你的硅基流动API密钥
OPENAI_BASE_URL=https://api.siliconflow.cn/v1

# 使用qwen3embedding模型（可选）
OPENAI_EMBEDDING_MODEL=qwen3embedding

# Neo4j配置（必需）
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=你的neo4j密码
```

#### 方法B：使用命令行环境变量

```bash
# Linux/Mac
export OPENAI_API_KEY="你的硅基流动API密钥"
export OPENAI_BASE_URL="https://api.siliconflow.cn/v1"
export OPENAI_EMBEDDING_MODEL="qwen3embedding"

# Windows PowerShell
$env:OPENAI_API_KEY="你的硅基流动API密钥"
$env:OPENAI_BASE_URL="https://api.siliconflow.cn/v1"
$env:OPENAI_EMBEDDING_MODEL="qwen3embedding"
```

#### 方法C：使用docker-compose.yaml

在`docker-compose.yaml`中添加环境变量：

```yaml
services:
  api:
    environment:
      - OPENAI_API_KEY=你的硅基流动API密钥
      - OPENAI_BASE_URL=https://api.siliconflow.cn/v1
      - OPENAI_EMBEDDING_MODEL=qwen3embedding
```

## 配置参数说明

### OPENAI_API_KEY
- **必需**: 是
- **说明**: API密钥
- **获取方式**: 从选择的API提供商获取
- **示例**: `sk-xxxxxxxxxxxxxxxx`

### OPENAI_BASE_URL
- **必需**: 否（可选）
- **说明**: 自定义API基础URL
- **默认值**: 留空则使用OpenAI官方API
- **常用值**:
  - OpenAI: 留空
  - 硅基流动: `https://api.siliconflow.cn/v1`
  - 其他: 根据提供商文档设置

### OPENAI_EMBEDDING_MODEL
- **必需**: 否（可选）
- **说明**: 指定使用的embedding模型
- **默认值**: `text-embedding-3-small`
- **硅基流动推荐**: `qwen3embedding`
- **其他可选值**:
  - `text-embedding-3-small` (OpenAI)
  - `text-embedding-3-large` (OpenAI)
  - `qwen3embedding` (硅基流动)

## 测试配置

配置完成后，运行测试验证：

```bash
# 运行所有测试
export NEO4J_PASSWORD=你的neo4j密码
export OPENAI_API_KEY=你的硅基流动API密钥
export OPENAI_BASE_URL=https://api.siliconflow.cn/v1
export OPENAI_EMBEDDING_MODEL=qwen3embedding

python -m pytest tests/ -v
```

预期结果：
- 12个之前失败的graphiti_core测试现在应该通过
- 总测试通过率应从75%提升到约96%

## graphiti_core中的API密钥使用

`graphiti_core`库在以下场景使用OpenAI API密钥：

1. **文本Embedding**: 将episode内容转换为向量，用于语义搜索
2. **实体提取**: 使用LLM从文本中识别实体和关系
3. **关系推理**: 推断实体之间的潜在关系
4. **语义搜索**: 基于向量相似度进行混合搜索

### API调用示例

```python
# graphiti_core内部使用（简化示例）
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    base_url=os.environ.get("OPENAI_BASE_URL")
)

# Embedding调用
embedding = client.embeddings.create(
    model=os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
    input="用户Alice今天访问了网站"
)

# LLM调用
response = client.chat.completions.create(
    model="gpt-3.5-turbo",  # 或使用其他模型
    messages=[{"role": "user", "content": "分析这段文本"}]
)
```

## 常见问题

### Q1: 我可以同时使用DeepSeek和硅基流动吗？

**A**: 可以！
- `DEEPSEEK_API_KEY`: 用于项目LLMService中的功能（文本分析、心理分析等）
- `OPENAI_API_KEY`: 用于graphiti_core的embedding和LLM功能

两者可以独立配置。

### Q2: 硅基流动的embedding模型支持吗？

**A**: 支持！硅基流动提供OpenAI兼容的API，`qwen3embedding`模型可以正常工作。

### Q3: 如何确认配置成功？

**A**: 运行健康检查端点：

```bash
curl http://localhost:8000/health
```

响应中应该包含：
```json
{
  "graphiti_core_enabled": true
}
```

### Q4: embedding模型可以更换吗？

**A**: 可以随时更换，只需修改`OPENAI_EMBEDDING_MODEL`环境变量并重启服务。

### Q5: API密钥会保存在哪里？

**A**: 
- 环境变量中（运行时）
- .env文件中（如果使用）
- 不会保存在代码或数据库中

**安全建议**:
- 不要将.env文件提交到git
- 使用不同的API密钥用于开发和生产环境
- 定期轮换API密钥

## 其他OpenAI兼容API提供商

除了硅基流动，您还可以使用：

### 1. 阿里云DashScope
```bash
export OPENAI_API_KEY=你的DashScope密钥
export OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
export OPENAI_EMBEDDING_MODEL=text-embedding-v2
```

### 2. 智谱AI (ZhipuAI)
```bash
export OPENAI_API_KEY=你的智谱密钥
export OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4
export OPENAI_EMBEDDING_MODEL=embedding-v2
```

### 3. 月之暗面 (Moonshot AI)
```bash
export OPENAI_API_KEY=你的月之暗面密钥
export OPENAI_BASE_URL=https://api.moonshot.cn/v1
export OPENAI_EMBEDDING_MODEL=moonshot-v1-8k
```

## 技术支持

如果遇到问题：

1. 检查API密钥是否正确
2. 检查网络连接
3. 查看API提供商文档
4. 查看项目日志：`docker-compose logs api`
5. 查看测试结果：`python -m pytest tests/ -v`

## 相关文档

- [项目配置文档](./CONFIGURATION.md)
- [测试总结](./TEST_SUMMARY.md)
- [集成文档](./TASK_2_1_2_4_SUMMARY.md)
