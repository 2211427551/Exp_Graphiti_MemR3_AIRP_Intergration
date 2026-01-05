# AIRP记忆系统 - Graphiti + DeepSeek V3.2 集成项目

基于Graphiti时序知识图谱的记忆增强系统，为SillyTavern提供强大的记忆管理和角色理解能力。

## 项目特点

- ✅ **完整的Docker部署方案** - 一键启动所有服务
- ✅ **DeepSeek V3.2兼容** - 支持Strict JSON Schema模式
- ✅ **OpenAI兼容API** - 无缝集成SillyTavern
- ✅ **智能格式解析** - 自动识别和处理SillyTavern特殊格式
- ✅ **记忆增强** - 基于知识图谱的动态记忆管理
- ✅ **生产就绪** - 包含完整的监控、日志和故障排除方案

## 快速开始

### 1. 前置要求

- Docker 20.10+
- Docker Compose v2.0+
- 至少8GB可用内存
- DeepSeek API密钥

### 2. 配置环境变量

```bash
# 编辑.env文件
nano .env

# 修改以下关键配置：
# - DEEPSEEK_API_KEY: 你的DeepSeek API密钥
# - SILICONFLOW_API_KEY: 你的硅基流动API密钥（从 https://siliconflow.cn 获取）
# - NEO4J_PASSWORD: 设置强密码
# - REDIS_PASSWORD: 设置强密码
# - APP_SECRET_KEY: 生成随机密钥（python -c "import secrets; print(secrets.token_urlsafe(32))"）
```

**API密钥获取**:
- DeepSeek API: https://platform.deepseek.com
- 硅基流动API: https://siliconflow.cn

### 3. 启动服务

```bash
# 创建必要的目录
mkdir -p neo4j/{data,logs,import,plugins}
mkdir -p redis/data
mkdir -p logs/api
mkdir -p api-service

# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps
```

### 4. 验证部署

```bash
# 检查API健康状态
curl http://localhost:8000/health

# 访问Neo4j Browser（可选）
# http://localhost:7474
# 用户名：neo4j
# 密码：你在.env中设置的密码
```

### 5. 配置SillyTavern

1. 打开SillyTavern设置
2. 连接设置：
   - 后端提供商：OpenAI
   - API URL：`http://your-server-ip:8000/v1/chat/completions`
   - API Key：任意值（系统不验证）
   - 模型：`deepseek-chat`

## 文档说明

### 开发部署指南.md
完整的开发部署文档，包含：
- 详细的系统架构设计
- Docker配置说明
- Graphiti配置与兼容层设计
- API服务实现逻辑
- DeepSeek集成方案（两种方案）
- SillyTavern连接配置
- 测试验证流程
- 故障排除指南

### docker-compose.yaml
Docker Compose配置文件，定义了：
- Neo4j 5.26图数据库
- Redis缓存服务
- FastAPI服务容器

### .env
环境变量配置文件，包含：
- Neo4j连接配置
- Redis配置
- DeepSeek API配置
- Graphiti配置
- API服务配置

## 技术栈

- **数据库**: Neo4j 5.26
- **记忆框架**: Graphiti-core
- **LLM推理**: DeepSeek V3.2
- **向量化和重排序**: 硅基流动 (SiliconFlow)
- **API框架**: FastAPI
- **缓存**: Redis 7
- **容器化**: Docker + Docker Compose

## 关键特性

### DeepSeek + 硅基流动集成方案

**LLM推理**: 使用DeepSeek官方API
- 模型：DeepSeek V3.2 (deepseek-chat)
- 支持Beta端点 + Strict模式（推荐）
- 备选方案：标准端点 + 兼容层

**Embedding**: 使用硅基流动API
- 推荐模型：BAAI/bge-m3
- 多语言支持
- 开源BGE系列模型

**Reranker**: 使用硅基流动API
- 推荐模型：BAAI/bge-reranker-v2-m3
- 搜索结果重排序
- 提升检索准确性

### DeepSeek兼容方案

**方案A（推荐）**: 使用Beta端点 + Strict模式
- 端点：`https://api.deepseek.com/beta`
- 完全支持JSON Schema
- 服务器端验证
- 最佳质量和稳定性

**方案B（备选）**: 标准端点 + 兼容层
- 端点：`https://api.deepseek.com`
- 自定义兼容层
- 提示词增强 + 后处理验证
- 降级保障

### SillyTavern格式解析

自动识别和处理：
- `<核心指导>` - 指令性内容（不入图谱）
- `<相关资料>` - 世界书信息
- `<互动历史>` - 对话历史
- 特殊标签格式
- User/Assistant交替模式

### 记忆管理

- 自动实体关系提取
- 去重和合并
- 时序跟踪
- 混合检索（向量+图）
- 上下文优化

## 项目结构

```
.
├── docker-compose.yaml          # Docker编排配置
├── .env                        # 环境变量
├── README.md                   # 本文件
├── 开发部署指南.md            # 完整部署文档
├── api-service/               # API服务代码（需自行实现）
│   ├── main.py
│   ├── config/
│   ├── services/
│   ├── models/
│   └── utils/
├── neo4j/                     # Neo4j数据目录
├── redis/                     # Redis数据目录
└── logs/                      # 日志目录
```

## 下一步

1. 阅读`开发部署指南.md`了解详细实现方案
2. 在`api-service/`目录实现API服务代码
3. 根据指南配置Graphiti和兼容层
4. 测试与SillyTavern的集成

## 故障排除

### 常见问题

1. **Neo4j启动失败**
   - 检查内存配置
   - 降低`NEO4J_dbms_memory_*`值
   - 参考`开发部署指南.md`第9节

2. **API无法连接**
   - 检查端口是否开放
   - 检查防火墙设置
   - 查看容器日志：`docker-compose logs api-service`

3. **DeepSeek API错误**
   - 验证API密钥
   - 检查端点URL
   - 降低并发限制：`GRAPHITI_SEMAPHORE_LIMIT`

4. **记忆功能不生效**
   - 启用调试日志
   - 检查Graphiti配置
   - 验证Neo4j数据

详细的故障排除步骤请参考`开发部署指南.md`第9节。

## 安全建议

生产环境部署前请务必：

1. ✅ 修改所有默认密码
2. ✅ 使用强密码（至少16位）
3. ✅ 启用HTTPS（配置反向代理）
4. ✅ 限制Neo4j Browser访问
5. ✅ 实施API速率限制
6. ✅ 定期备份数据库
7. ✅ 监控系统资源使用

## 许可证

本项目基于开源项目构建，遵循相应许可证。

## 联系方式

如有问题，请参考`开发部署指南.md`或提交Issue。

---

**重要提示**: 本项目目前处于初级开发阶段，API服务代码需要根据`开发部署指南.md`中的设计自行实现。配置文件已经准备就绪，可以直接用于Docker部署。
