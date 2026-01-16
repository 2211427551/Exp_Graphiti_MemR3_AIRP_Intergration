# API Documentation

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

当前版本不需要认证。在生产环境中，建议添加API密钥认证。

## Endpoints

### 1. Health Check

检查API服务健康状态。

**Endpoint:** `GET /health`

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T12:00:00Z",
  "version": "1.0.0"
}
```

### 2. Chat Completion

创建聊天完成请求，支持Tool Calling和Strict模式。

**Endpoint:** `POST /chat/completions`

#### Request Body

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `model` | string | 是 | `deepseek-chat` 或 `deepseek-reasoner` |
| `messages` | array | 是 | 对话消息列表 |
| `tools` | array | 否 | Tool定义列表 |
| `temperature` | number | 否 | 采样温度 (0-2) |
| `max_tokens` | integer | 否 | 最大生成token数 |
| `stream` | boolean | 否 | 是否流式响应（暂不支持） |

#### Message Object

```json
{
  "role": "system|user|assistant|tool",
  "content": "string",
  "tool_call_id": "string (optional)",
  "name": "string (optional)"
}
```

#### Tool Object

```json
{
  "type": "function",
  "function": {
    "name": "function_name",
    "description": "Function description",
    "strict": true,
    "parameters": {
      "type": "object",
      "properties": {...},
      "required": [...],
      "additionalProperties": false
    }
  }
}
```

#### Response

```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "deepseek-chat",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Response text",
        "tool_calls": [
          {
            "id": "call_xxx",
            "type": "function",
            "function": {
              "name": "function_name",
              "arguments": "{\"key\":\"value\"}"
            }
          }
        ]
      },
      "finish_reason": "stop|tool_calls|length"
    }
  ],
  "usage": {
    "prompt_tokens": 100,
    "completion_tokens": 50,
    "total_tokens": 150
  }
}
```

## Examples

### Example 1: Simple Chat

```bash
curl -X POST http://localhost:8000/api/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "deepseek-chat",
    "messages": [
      {"role": "user", "content": "Explain quantum computing"}
    ],
    "temperature": 0.7,
    "max_tokens": 500
  }'
```

### Example 2: Tool Calling

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
        "description": "Get current weather for a location",
        "strict": true,
        "parameters": {
          "type": "object",
          "properties": {
            "location": {
              "type": "string",
              "description": "City name, e.g. Beijing, China"
            }
          },
          "required": ["location"],
          "additionalProperties": false
        }
      }
    }]
  }'
```

### Example 3: Multi-turn Conversation

```bash
curl -X POST http://localhost:8000/api/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "deepseek-chat",
    "messages": [
      {"role": "user", "content": "Get AAPL stock price"},
      {
        "role": "assistant",
        "content": null,
        "tool_calls": [{
          "id": "call_abc",
          "type": "function",
          "function": {
            "name": "get_stock_price",
            "arguments": "{\"symbol\":\"AAPL\"}"
          }
        }]
      },
      {
        "role": "tool",
        "tool_call_id": "call_abc",
        "content": "$178.52"
      }
    ],
    "tools": [...]
  }'
```

## Error Responses

### 422 Unprocessable Entity

Schema验证失败：

```json
{
  "detail": {
    "error": "Invalid JSON Schema for DeepSeek Strict mode",
    "tool": "function_name",
    "validation_errors": [
      "root: All properties must be required. Missing in 'required': ['name']"
    ]
  }
}
```

### 502 Bad Gateway

DeepSeek API错误：

```json
{
  "detail": {
    "error": "deepseek_api_error",
    "message": "Rate limit exceeded"
  }
}
```

### 500 Internal Server Error

内部服务器错误：

```json
{
  "detail": {
    "error": "internal_error",
    "message": "Internal server error"
  }
}
```

## JSON Schema Validation Rules

### Object Type

✅ **Valid:**
```json
{
  "type": "object",
  "properties": {
    "name": {"type": "string"},
    "age": {"type": "integer"}
  },
  "required": ["name", "age"],
  "additionalProperties": false
}
```

❌ **Invalid - Missing Required:**
```json
{
  "type": "object",
  "properties": {
    "name": {"type": "string"}
  },
  "additionalProperties": false
}
```

### String Type

✅ **Valid:**
```json
{
  "type": "string",
  "format": "email",
  "pattern": "^[a-z]+@[a-z]+\\\\.[a-z]+$"
}
```

❌ **Invalid - Unsupported Attributes:**
```json
{
  "type": "string",
  "minLength": 10,
  "maxLength": 100
}
```

### Array Type

✅ **Valid:**
```json
{
  "type": "array",
  "items": {"type": "string"}
}
```

❌ **Invalid - Unsupported Attributes:**
```json
{
  "type": "array",
  "items": {"type": "string"},
  "minItems": 1,
  "maxItems": 10
}
```

## Auto-Transformation

API会自动转换不符合要求的Schema：

- 自动添加所有properties到required
- 强制设置additionalProperties为false
- 移除不支持的属性（minLength, maxLength, minItems, maxItems）

这确保您的Schema始终与DeepSeek Strict模式兼容。
