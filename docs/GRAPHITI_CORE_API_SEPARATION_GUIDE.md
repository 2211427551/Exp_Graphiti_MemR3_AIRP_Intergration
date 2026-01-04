# graphiti_core API分离配置指南

## 需求说明

- **Embedding服务**：使用硅基流动
- **LLM服务**：使用DeepSeek官方API

## 技术限制

`graphiti_core` 库目前使用OpenAI兼容的API接口，通常配置方式为：
- 单个API密钥
- 单个基础URL

这意味着**graphiti_core可能不支持在同一实例中分离配置embedding和LLM的API提供商**。

## 解决方案

### 方案1：使用同一个API提供商（推荐）

选择一个同时提供embedding和LLM服务的API提供商：

#### 选项1.1：完全使用DeepSeek官方API
```bash
# .env配置
OPENAI_API_KEY=sk-251d88fbcbd84a3da35b20cdf62799d4
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-chat
OPENAI_EMBEDDING_MODEL=deepseek-embeddings
```

**优点**：
- 单一API密钥管理简单
- DeepSeek提供embedding和LLM服务
- 成本统一在DeepSeek平台

**缺点**：
- 不能使用硅基流动的embedding服务

#### 选项1.2：完全使用硅基流动API
```bash
# .env配置
OPENAI_API_KEY=sk-rwugpsjvrpahsmotpswtspbagrvrxiikmrduoxlhmryhpfgv
OPENAI_BASE_URL=https://api.siliconflow.cn/v1
OPENAI_MODEL=deepseek-ai/DeepSeek-V3  # 或其他硅基流动支持的模型
