# Usage Examples

本目录包含DeepSeek JSON Schema API的使用示例。

## 目录

1. [基础聊天](#1-基础聊天)
2. [Tool Calling](#2-tool-calling)
3. [多轮对话](#3-多轮对话)
4. [Python客户端示例](#4-python客户端示例)
5. [JavaScript客户端示例](#5-javascript客户端示例)

## 1. 基础聊天

### 示例：简单问答

```bash
curl -X POST http://localhost:8000/api/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "deepseek-chat",
    "messages": [
      {"role": "user", "content": "请解释什么是量子计算"}
    ],
    "temperature": 0.7,
    "max_tokens": 500
  }'
```

**响应示例：**
```json
{
  "id": "chatcmpl-1234567890",
  "object": "chat.completion",
  "created": 1736947200,
  "model": "deepseek-chat",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "量子计算是一种利用量子力学原理进行计算的新型计算方式...",
        "tool_calls": null
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 20,
    "completion_tokens": 150,
    "total_tokens": 170
  }
}
```

### 示例：带系统提示

```bash
curl -X POST http://localhost:8000/api/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "deepseek-chat",
    "messages": [
      {
        "role": "system",
        "content": "你是一个专业的Python编程助手，专注于提供清晰准确的代码示例。"
      },
      {
        "role": "user",
        "content": "如何使用列表推导式过滤偶数？"
      }
    ]
  }'
```

## 2. Tool Calling

### 示例：获取天气信息

```bash
curl -X POST http://localhost:8000/api/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "deepseek-chat",
    "messages": [
      {"role": "user", "content": "北京现在的天气怎么样？"}
    ],
    "tools": [{
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "获取指定城市的当前天气信息",
        "strict": true,
        "parameters": {
          "type": "object",
          "properties": {
            "location": {
              "type": "string",
              "description": "城市名称，例如：北京、上海"
            }
          },
          "required": ["location"],
          "additionalProperties": false
        }
      }
    }]
  }'
```

**响应示例（包含Tool Call）：**
```json
{
  "id": "chatcmpl-9876543210",
  "object": "chat.completion",
  "created": 1736947300,
  "model": "deepseek-chat",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": null,
        "tool_calls": [
          {
            "id": "call_abc123",
            "type": "function",
            "function": {
              "name": "get_weather",
              "arguments": "{\"location\":\"北京\"}"
            }
          }
        ]
      },
      "finish_reason": "tool_calls"
    }
  ],
  "usage": {
    "prompt_tokens": 80,
    "completion_tokens": 20,
    "total_tokens": 100
  }
}
```

### 示例：股票查询

```bash
curl -X POST http://localhost:8000/api/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "deepseek-chat",
    "messages": [
      {"role": "user", "content": "查询苹果公司(AAPL)的当前股价"}
    ],
    "tools": [{
      "type": "function",
      "function": {
        "name": "get_stock_price",
        "description": "获取指定股票代码的当前价格",
        "strict": true,
        "parameters": {
          "type": "object",
          "properties": {
            "symbol": {
              "type": "string",
              "description": "股票代码，例如：AAPL, GOOGL, TSLA"
            }
          },
          "required": ["symbol"],
          "additionalProperties": false
        }
      }
    }]
  }'
```

### 示例：复杂Schema（嵌套对象）

```bash
curl -X POST http://localhost:8000/api/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "deepseek-chat",
    "messages": [
      {"role": "user", "content": "帮我创建一个用户"}
    ],
    "tools": [{
      "type": "function",
      "function": {
        "name": "create_user",
        "description": "创建新用户",
        "strict": true,
        "parameters": {
          "type": "object",
          "properties": {
            "user": {
              "type": "object",
              "description": "用户信息",
              "properties": {
                "name": {
                  "type": "string",
                  "description": "用户姓名"
                },
                "email": {
                  "type": "string",
                  "format": "email",
                  "description": "电子邮件地址"
                },
                "age": {
                  "type": "integer",
                  "minimum": 0,
                  "maximum": 150,
                  "description": "年龄"
                }
              }
            }
          },
          "required": ["user"],
          "additionalProperties": false
        }
      }
    }]
  }'
```

## 3. 多轮对话

### 示例：完整的多轮Tool Calling流程

**第一步：发起请求**

```bash
curl -X POST http://localhost:8000/api/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "deepseek-chat",
    "messages": [
      {"role": "user", "content": "杭州现在的气温是多少？"}
    ],
    "tools": [{
      "type": "function",
      "function": {
        "name": "get_temperature",
        "description": "获取城市当前温度",
        "strict": true,
        "parameters": {
          "type": "object",
          "properties": {
            "city": {
              "type": "string",
              "description": "城市名称"
            }
          },
          "required": ["city"],
          "additionalProperties": false
        }
      }
    }]
  }'
```

**响应：**
```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "tool_calls": [{
        "id": "call_xyz",
        "type": "function",
        "function": {
          "name": "get_temperature",
          "arguments": "{\"city\":\"杭州\"}"
        }
      }]
    }
  }]
}
```

**第二步：执行Tool并返回结果**

```bash
curl -X POST http://localhost:8000/api/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "deepseek-chat",
    "messages": [
      {"role": "user", "content": "杭州现在的气温是多少？"},
      {
        "role": "assistant",
        "content": null,
        "tool_calls": [{
          "id": "call_xyz",
          "type": "function",
          "function": {
            "name": "get_temperature",
            "arguments": "{\"city\":\"杭州\"}"
          }
        }]
      },
      {
        "role": "tool",
        "tool_call_id": "call_xyz",
        "content": "24°C"
      }
    ],
    "tools": [{
      "type": "function",
      "function": {
        "name": "get_temperature",
        "description": "获取城市当前温度",
        "strict": true,
        "parameters": {
          "type": "object",
          "properties": {
            "city": {"type": "string"}
          },
          "required": ["city"],
          "additionalProperties": false
        }
      }
    }]
  }'
```

**最终响应：**
```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "杭州现在的气温是24°C。"
    }
  }]
}
```

## 4. Python客户端示例

### 基础使用

```python
import requests
import json

API_URL = "http://localhost:8000/api/v1/chat/completions"

def chat_completion(messages, tools=None):
    """调用聊天完成API"""
    payload = {
        "model": "deepseek-chat",
        "messages": messages
    }

    if tools:
        payload["tools"] = tools

    response = requests.post(API_URL, json=payload)
    return response.json()

# 示例：基础聊天
result = chat_completion([
    {"role": "user", "content": "你好！"}
])
print(result["choices"][0]["message"]["content"])
```

### Tool Calling示例

```python
import requests
import json

API_URL = "http://localhost:8000/api/v1/chat/completions"

# 定义Tool
tools = [{
    "type": "function",
    "function": {
        "name": "calculate",
        "description": "执行数学计算",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "数学表达式，例如：2+2"
                }
            },
            "required": ["expression"],
            "additionalProperties": False
        }
    }
}]

# 发起请求
response = requests.post(API_URL, json={
    "model": "deepseek-chat",
    "messages": [
        {"role": "user", "content": "2加2等于多少？"}
    ],
    "tools": tools
})

result = response.json()

# 检查是否有Tool Call
tool_calls = result["choices"][0]["message"].get("tool_calls")
if tool_calls:
    for tool_call in tool_calls:
        function_name = tool_call["function"]["name"]
        arguments = json.loads(tool_call["function"]["arguments"])
        print(f"调用函数: {function_name}")
        print(f"参数: {arguments}")

        # 执行实际函数
        if function_name == "calculate":
            expr = arguments["expression"]
            result = eval(expr)
            print(f"计算结果: {result}")
```

### 完整的多轮对话示例

```python
import requests
import json

class DeepSeekClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api/v1/chat/completions"

    def chat(self, messages, tools=None):
        """发送聊天请求"""
        payload = {
            "model": "deepseek-chat",
            "messages": messages
        }
        if tools:
            payload["tools"] = tools

        response = requests.post(self.api_url, json=payload)
        return response.json()

    def chat_with_tools(self, user_message, tools, tool_functions):
        """
        完整的Tool Calling流程

        Args:
            user_message: 用户消息
            tools: Tool定义
            tool_functions: Tool执行函数映射
        """
        messages = [{"role": "user", "content": user_message}]

        # 第一轮：获取Tool Call
        response = self.chat(messages, tools)
        tool_calls = response["choices"][0]["message"].get("tool_calls")

        if not tool_calls:
            # 没有Tool Call，直接返回
            return response["choices"][0]["message"]["content"]

        # 添加助手消息（包含Tool Call）
        messages.append(response["choices"][0]["message"])

        # 执行所有Tool Calls
        for tool_call in tool_calls:
            function_name = tool_call["function"]["name"]
            arguments = json.loads(tool_call["function"]["arguments"])

            # 执行Tool函数
            if function_name in tool_functions:
                result = tool_functions[function_name](**arguments)
            else:
                result = f"Error: Unknown function {function_name}"

            # 添加Tool结果消息
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": str(result)
            })

        # 第二轮：获取最终回复
        final_response = self.chat(messages, tools)
        return final_response["choices"][0]["message"]["content"]

# 使用示例
client = DeepSeekClient()

# 定义Tool函数
def get_weather(location):
    # 这里应该调用实际的天气API
    return f"{location}现在是晴天，温度25°C"

# 定义Tool
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "获取天气信息",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string"}
            },
            "required": ["location"],
            "additionalProperties": False
        }
    }
}]

# 调用
result = client.chat_with_tools(
    "北京今天的天气怎么样？",
    tools,
    {"get_weather": get_weather}
)
print(result)
```

## 5. JavaScript客户端示例

### 使用fetch API

```javascript
const API_URL = 'http://localhost:8000/api/v1/chat/completions';

async function chatCompletion(messages, tools = null) {
  const payload = {
    model: 'deepseek-chat',
    messages: messages
  };

  if (tools) {
    payload.tools = tools;
  }

  const response = await fetch(API_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  });

  return await response.json();
}

// 基础使用
async function main() {
  const result = await chatCompletion([
    { role: 'user', content: '你好！' }
  ]);

  console.log(result.choices[0].message.content);
}

main();
```

### Tool Calling示例

```javascript
const API_URL = 'http://localhost:8000/api/v1/chat/completions';

const tools = [{
  type: 'function',
  function: {
    name: 'get_current_time',
    description: '获取当前时间',
    strict: true,
    parameters: {
      type: 'object',
      properties: {
        timezone: {
          type: 'string',
          description: '时区，例如：Asia/Shanghai'
        }
      },
      required: ['timezone'],
      additionalProperties: false
    }
  }
}];

async function chatWithTool(userMessage) {
  let messages = [
    { role: 'user', content: userMessage }
  ];

  // 第一轮：获取Tool Call
  let response = await chatCompletion(messages, tools);
  const toolCalls = response.choices[0].message.tool_calls;

  if (!toolCalls) {
    return response.choices[0].message.content;
  }

  // 添加助手消息
  messages.push(response.choices[0].message);

  // 执行Tool Calls
  for (const toolCall of toolCalls) {
    const functionName = toolCall.function.name;
    const args = JSON.parse(toolCall.function.arguments);

    // 执行函数
    let result;
    if (functionName === 'get_current_time') {
      result = new Date().toLocaleString('zh-CN', { timeZone: args.timezone });
    }

    // 添加Tool结果
    messages.push({
      role: 'tool',
      tool_call_id: toolCall.id,
      content: result
    });
  }

  // 第二轮：获取最终回复
  response = await chatCompletion(messages, tools);
  return response.choices[0].message.content;
}

// 使用
chatWithTool('现在北京时间是多少？')
  .then(result => console.log(result))
  .catch(error => console.error('Error:', error));
```

## 常见使用场景

### 场景1：代码生成

```bash
curl -X POST http://localhost:8000/api/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "deepseek-chat",
    "messages": [
      {
        "role": "system",
        "content": "你是一个专业的程序员，擅长Python开发。"
      },
      {
        "role": "user",
        "content": "写一个Python函数计算斐波那契数列"
      }
    ]
  }'
```

### 场景2：数据提取

```bash
curl -X POST http://localhost:8000/api/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "deepseek-chat",
    "messages": [
      {
        "role": "user",
        "content": "从以下文本中提取人名和地点：张三昨天去了北京出差。"
      }
    ],
    "tools": [{
      "type": "function",
      "function": {
        "name": "extract_entities",
        "description": "提取文本中的实体",
        "strict": true,
        "parameters": {
          "type": "object",
          "properties": {
            "names": {
              "type": "array",
              "items": {"type": "string"},
              "description": "人名列表"
            },
            "places": {
              "type": "array",
              "items": {"type": "string"},
              "description": "地点列表"
            }
          },
          "required": ["names", "places"],
          "additionalProperties": false
        }
      }
    }]
  }'
```

### 场景3：API调用代理

```bash
curl -X POST http://localhost:8000/api/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "deepseek-chat",
    "messages": [
      {"role": "user", "content": "发送邮件给admin@example.com，主题是测试"}
    ],
    "tools": [{
      "type": "function",
      "function": {
        "name": "send_email",
        "description": "发送电子邮件",
        "strict": true,
        "parameters": {
          "type": "object",
          "properties": {
            "to": {
              "type": "string",
              "format": "email",
              "description": "收件人邮箱"
            },
            "subject": {
              "type": "string",
              "description": "邮件主题"
            },
            "body": {
              "type": "string",
              "description": "邮件正文"
            }
          },
          "required": ["to", "subject", "body"],
          "additionalProperties": false
        }
      }
    }]
  }'
```

## 错误处理示例

### Python错误处理

```python
import requests
from requests.exceptions import RequestException

API_URL = "http://localhost:8000/api/v1/chat/completions"

def chat_completion_safe(messages, tools=None):
    """带错误处理的聊天完成"""
    try:
        payload = {
            "model": "deepseek-chat",
            "messages": messages
        }
        if tools:
            payload["tools"] = tools

        response = requests.post(API_URL, json=payload)
        response.raise_for_status()

        return response.json()

    except requests.exceptions.HTTPError as e:
        print(f"HTTP错误: {e}")
        print(f"响应内容: {e.response.text}")
        return None

    except RequestException as e:
        print(f"请求错误: {e}")
        return None

    except Exception as e:
        print(f"未知错误: {e}")
        return None

# 使用
result = chat_completion_safe([
    {"role": "user", "content": "你好"}
])

if result:
    print(result["choices"][0]["message"]["content"])
```

## 最佳实践

1. **重试逻辑**：对于网络错误，实现指数退避重试
2. **超时设置**：为请求设置合理的超时时间
3. **错误日志**：记录所有错误以便调试
4. **Schema验证**：在客户端也验证Tool的Schema
5. **速率限制**：避免发送过多请求导致被限流

更多示例和详细信息，请参考：
- [API文档](API.md)
- [部署指南](DEPLOYMENT.md)
- [项目README](../README.md)
