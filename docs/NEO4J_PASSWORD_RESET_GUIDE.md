# Neo4j密码重置指南

## 问题说明

Neo4j数据库在首次启动时会使用环境变量中的密码进行初始化，之后密码会被加密存储在数据目录中。**后续修改环境变量不会改变已加密的密码**。

当前状态：
- Neo4j已用某个未知密码初始化
- `.env`文件中设置的密码无法生效
- 测试失败：`Neo.ClientError.Security.Unauthorized`

## 解决方案

### 方案1：重置Neo4j数据目录（推荐）

使用提供的脚本重置Neo4j：

```bash
# 运行重置脚本
bash reset_neo4j.sh

# 按照提示确认：输入 "yes"
# 等待Neo4j重新启动（约30秒）
```

**注意**：此操作会删除所有Neo4j数据，请确保已备份重要数据。

### 方案2：手动重置

如果脚本执行失败，可以手动执行：

```bash
# 1. 停止所有容器
docker-compose down

# 2. 删除Neo4j数据目录（需要sudo权限）
sudo rm -rf neo4j/data/*

# 3. 重新启动Neo4j容器
docker-compose up -d neo4j

# 4. 等待Neo4j启动完成（约30秒）
sleep 30

# 5. 验证连接
python3 -c "from neo4j import GraphDatabase; driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'neo4j')); driver.verify_connectivity(); print('✅ 连接成功'); driver.close()"
```

## 重置后的配置

重置后，Neo4j将使用`.env`文件中配置的密码：

```bash
# .env文件中的配置
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=neo4j  # 这个密码将在重置后生效
```

## 验证连接

### 1. 使用Python测试

```bash
export NEO4J_PASSWORD=neo4j
python3 -c "from neo4j import GraphDatabase; driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'neo4j')); driver.verify_connectivity(); print('✅ Neo4j连接成功'); driver.close()"
```

### 2. 使用Neo4j浏览器

打开浏览器访问：http://localhost:7474

- 用户名：`neo4j`
- 密码：`neo4j`

### 3. 运行测试

```bash
export NEO4J_PASSWORD=neo4j
python -m pytest tests/test_enhanced_graphiti_service.py::test_graphiti_core_enabled tests/test_enhanced_graphiti_service.py::test_get_graphiti_core_info tests/test_enhanced_graphiti_service.py::test_add_episode_text -v --tb=short
```

## 完整配置说明

### .env文件（当前配置）

```bash
# Neo4j配置
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=neo4j  # 重置后使用此密码

# OpenAI兼容API配置（用于graphiti_core）
OPENAI_API_KEY=sk-251d88fbcbd84a3da35b20cdf62799d4
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-chat  # DeepSeek官方API模型
OPENAI_EMBEDDING_MODEL=deepseek-embeddings  # DeepSeek embedding模型

# Graphiti Core配置
GRAPHITI_CORE_ENABLED=True
```

### 配置说明

1. **OPENAI_MODEL**: 用于graphiti_core的知识提取和推理
   - `deepseek-chat`: DeepSeek官方API的聊天模型
   - graphiti_core使用此模型来理解文本、提取实体、建立关系

2. **OPENAI_EMBEDDING_MODEL**: 用于文本向量化
   - `deepseek-embeddings`: DeepSeek官方API的embedding模型
   - 用于语义搜索和相似度计算

3. **NEO4J_PASSWORD**: Neo4j数据库密码
   - 重置后为：`neo4j`
   - 测试时需要设置环境变量：`export NEO4J_PASSWORD=neo4j`

## 故障排除

### 问题1：重置后仍无法连接

**检查点**：
- Neo4j容器是否正在运行：`docker ps | grep neo4j`
- Neo4j是否完全启动：`docker logs airp-neo4j --tail 50`
- 等待足够时间（至少30秒）让Neo4j完全启动

### 问题2：权限错误

如果删除数据目录时遇到权限错误：

```bash
# 使用sudo权限
sudo rm -rf neo4j/data/*

# 或修改数据目录所有者
sudo chown -R $USER:$USER neo4j/data
```

### 问题3：端口冲突

如果7474或7687端口被占用：

```bash
# 查看端口占用
lsof -i :7474
lsof -i :7687

# 停止占用端口的进程或修改docker-compose.yaml中的端口映射
```

## 预期结果

重置并验证成功后，测试应显示：

```
tests/test_enhanced_graphiti_service.py::test_graphiti_core_enabled PASSED
tests/test_enhanced_graphiti_service.py::test_get_graphiti_core_info PASSED
tests/test_enhanced_graphiti_service.py::test_add_episode_text PASSED
```

## 相关文档

- [graphiti_core集成测试总结](./GRAPHITI_CORE_INTEGRATION_SUMMARY.md)
- [OpenAI兼容API配置指南](./OPENAI_COMPATIBLE_API_GUIDE.md)
- [配置文档](./CONFIGURATION.md)

## 快速参考

```bash
# 重置Neo4j（推荐方式）
bash reset_neo4j.sh

# 验证连接
export NEO4J_PASSWORD=neo4j
python -m pytest tests/test_enhanced_graphiti_service.py -v

# Neo4j浏览器
http://localhost:7474
