# graphiti_core分离配置验证指南

## 概述

本文档说明如何验证graphiti_core的分离配置（DeepSeek LLM + SiliconFlow Embedding）是否正常工作。

## 配置总结

### 当前配置

```bash
# LLM配置（DeepSeek官方API）
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-

# Embedding配置（SiliconFlow）
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.siliconflow.cn/v1
OPENAI_EMBEDDING_MODEL=Qwen/Qwen3-Embedding-4B
```

### 配置说明

- **LLM提供商**：DeepSeek官方API
  - 用于：知识提取、实体识别、关系建立、问答推理
  - 模型：deepseek-chat

- **Embedding提供商**：SiliconFlow
  - 用于：文本向量化、语义搜索、相似度计算
  - 模型：Qwen/Qwen3-Embedding-4B

## 验证步骤

### 步骤1：重置Neo4j密码（必需）

由于Neo4j已用未知密码初始化，需要重置：

```bash
# 运行重置脚本
bash reset_neo4j.sh

# 按照提示确认（输入 "yes"）
# 等待Neo4j重新启动（约30秒）
```

### 步骤2：验证Neo4j连接

```bash
export NEO4J_PASSWORD=neo4j
python3 -c "from neo4j import GraphDatabase; driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'neo4j')); driver.verify_connectivity(); print('✅ Neo4j连接成功'); driver.close()"
```

**预期输出**：
```
✅ Neo4j连接成功
```

### 步骤3：验证graphiti_core初始化

```bash
export NEO4J_PASSWORD=neo4j
python3 << 'EOF'
from api_service.services.enhanced_graphiti_service import EnhancedGraphitiService

print("=== 初始化EnhancedGraphitiService ===")
service = EnhancedGraphitiService()
print("\n=== 检查graphiti_core状态 ===")
info = service.get_graphiti_core_info()
print(f"✅ graphiti_core启用: {info['enabled']}")
print(f"📦 版本: {info['version']}")
print(f"🔧 功能: {', '.join(info['features'])}")
print("\n=== 验证完成 ===")
EOF
```

**预期输出**：
```
=== 初始化EnhancedGraphitiService ===
🔗 连接Neo4j: bolt://localhost:7687
🤖 LLM提供商: DeepSeek官方API
🔗 LLM端点: https://api.deepseek.com
📦 LLM模型: deepseek-chat
🔢 Embedding提供商: SiliconFlow
🔗 Embedding端点: https://api.siliconflow.cn/v1
📦 Embedding模型: Qwen/Qwen3-Embedding-4B
✅ graphiti_core初始化成功（分离配置：DeepSeek LLM + SiliconFlow Embedding）

=== 检查graphiti_core状态 ===
✅ graphiti_core启用: True
📦 版本: 0.25.0
🔧 功能: add_episode, search_episodes, search_nodes_hybrid, search_with_center_node, time_based_query, bitemporal_model, hybrid_search

=== 验证完成 ===
```

### 步骤4：运行单元测试

```bash
export NEO4J_PASSWORD=neo4j
python -m pytest tests/test_enhanced_graphiti_service.py::test_graphiti_core_enabled tests/test_enhanced_graphiti_service.py::test_get_graphiti_core_info tests/test_enhanced_graphiti_service.py::test_add_episode_text -v --tb=short
```

**预期输出**：
```
tests/test_enhanced_graphiti_service.py::test_graphiti_core_enabled PASSED                                    [ 33%]
tests/test_enhanced_graphiti_service.py::test_get_graphiti_core_info PASSED                                   [ 66%]
tests/test_enhanced_graphiti_service.py::test_add_episode_text PASSED                                         [100%]

============================================== 3 passed in 5.23s ==============================================
```

### 步骤5：验证API端点

启动API服务：

```bash
export NEO4J_PASSWORD=neo4j
bash start_api.sh
```

在另一个终端测试API：

```bash
# 测试健康检查
curl http://localhost:8000/health

# 预期输出：
# {"status":"healthy","timestamp":"2024-01-04T...","services":{"neo4j":"healthy","redis":"healthy","graphiti_core":"enabled"}}

# 测试graphiti_core信息
curl http://localhost:8000/graphiti/info

# 预期输出：
# {"enabled":true,"version":"0.25.0","features":[...]}
```

## 验证检查清单

- [ ] Neo4j容器正在运行：`docker ps | grep neo4j`
- [ ] Neo4j密码已重置：运行`bash reset_neo4j.sh`
- [ ] 环境变量已设置：`export NEO4J_PASSWORD=neo4j`
- [ ] Neo4j连接成功：步骤2验证通过
- [ ] graphiti_core初始化成功：显示分离配置日志
- [ ] 单元测试全部通过：3个测试PASSED
- [ ] API健康检查通过：访问`/health`端点

## 常见问题

### Q1：Neo4j认证失败

**症状**：
```
Neo.ClientError.Security.Unauthorized: The client is unauthorized due to authentication failure.
```

**解决方案**：
```bash
bash reset_neo4j.sh
```

### Q2：graphiti_core初始化失败

**症状**：
```
❌ 初始化graphiti_core失败
```

**检查项**：
1. Neo4j是否正在运行：`docker ps`
2. API密钥是否正确：检查`.env`文件
3. 网络连接是否正常：`ping api.deepseek.com`

### Q3：API密钥无效

**症状**：
```
401 Unauthorized
```

**解决方案**：
1. 验证`DEEPSEEK_API_KEY`是否有效
2. 验证`OPENAI_API_KEY`是否有效
3. 检查API余额是否充足

### Q4：模型不存在

**症状**：
```
Model not found
```

**解决方案**：
1. 确认模型名称拼写正确
2. 检查模型是否在提供商中可用
3. 尝试使用其他推荐的模型

## 配置验证脚本

```bash
python3 << 'EOF'
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

print("=== graphiti_core分离配置验证 ===\n")

# LLM配置
print("🤖 LLM配置（DeepSeek）")
print(f"  API密钥: {'已配置' if os.getenv('DEEPSEEK_API_KEY') else '❌ 未配置'}")
print(f"  API端点: {os.getenv('DEEPSEEK_BASE_URL', '使用默认值')}")
print(f"  模型: {os.getenv('OPENAI_MODEL', '使用默认值')}")

# Embedding配置
print("\n🔢 Embedding配置（SiliconFlow）")
print(f"  API密钥: {'已配置' if os.getenv('OPENAI_API_KEY') else '❌ 未配置'}")
print(f"  API端点: {os.getenv('OPENAI_BASE_URL', '使用默认值')}")
print(f"  模型: {os.getenv('OPENAI_EMBEDDING_MODEL', '使用默认值')}")

# Neo4j配置
print("\n🗄️  Neo4j配置")
print(f"  URI: {os.getenv('NEO4J_URI', '使用默认值')}")
print(f"  用户: {os.getenv('NEO4J_USER', '使用默认值')}")
print(f"  密码: {'已配置' if os.getenv('NEO4J_PASSWORD') != 'your_neo4j_password_here' else '⚠️  需要配置'}")

# 验证结果
print("\n=== 验证结果 ===")
required = [
    ('DEEPSEEK_API_KEY', os.getenv('DEEPSEEK_API_KEY')),
    ('OPENAI_API_KEY', os.getenv('OPENAI_API_KEY')),
    ('NEO4J_PASSWORD', os.getenv('NEO4J_PASSWORD') != 'your_neo4j_password_here'),
]

all_ok = True
for name, value in required:
    status = "✅" if value else "❌"
    print(f"{status} {name}")
    if not value:
        all_ok = False

if all_ok:
    print("\n✅ 所有必需配置已就绪！")
else:
    print("\n❌ 请检查缺失的配置")
EOF
```

## 性能和成本优化

### 分离配置的优势

1. **成本优化**：
   - SiliconFlow的Embedding服务通常比OpenAI便宜
   - 可以利用不同提供商的免费额度

2. **性能优化**：
   - DeepSeek的LLM质量高，适合知识提取
   - SiliconFlow的Embedding针对中文优化

3. **灵活性**：
   - 可以根据需求调整配置
   - 支持A/B测试不同模型

### 监控建议

```bash
# 查看graphiti_core的缓存统计
python3 << 'EOF'
from api_service.services.enhanced_graphiti_service import EnhancedGraphitiService

service = EnhancedGraphitiService()
stats = service.get_cache_stats()
print(f"缓存命中率: {stats['hit_rate']:.2%}")
print(f"总查询数: {stats['total_queries']}")
print(f"缓存大小: {stats['cache_size']}")
EOF
```

## 相关文档

- [配置指南](./CONFIGURATION.md)
- [Neo4j密码重置指南](./NEO4J_PASSWORD_RESET_GUIDE.md)
- [graphiti_core集成总结](./GRAPHITI_CORE_INTEGRATION_SUMMARY.md)

## 总结

通过分离配置LLM和Embedding，AIRP项目实现了：

✅ **成本优化**：使用不同提供商的优惠定价
✅ **性能优化**：选择最适合的服务
✅ **灵活性**：根据需求调整配置
✅ **可扩展性**：支持添加更多API提供商

按照本文档的验证步骤，可以确保graphiti_core正确使用DeepSeek LLM和SiliconFlow Embedding服务。
