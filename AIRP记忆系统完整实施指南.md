# AIRP记忆系统完整实施指南

## 文档概述

本文档整合了"项目分析.md"、"API服务实现计划.md"、"开发部署指南.md"和"项目实现情况检查报告.md"四个文档，提供一个完整、详细的AIRP（AI Role Play）记忆系统实施指南。本文档以项目实现情况检查报告中的10周实施路线图为框架，整合所有技术细节、架构设计和实现逻辑。

**文档目标**：
- 提供从基础架构到高级功能的完整实施路径
- 详细展现每个功能的实现逻辑和技术方案
- 确保不同角色卡需求的通用性和可扩展性
- 平衡专用实体类型与通用属性容器的使用
- 实现心理连贯性建模和世界观逻辑推演

**当前状态**：
- 基础设施：100% 完成
- 核心功能：60% 完成（缺少高级特性）
- 高级特性：0% 完成（心理建模、因果推演、变化检测等）
- **总体完成度：53%**

**实施周期**：预计10周（详见本指南实施路线图）

---

## 目录

1. [项目概述与架构设计](#1-项目概述与架构设计)
2. [当前实现状态分析](#2-当前实现状态分析)
3. [实施路线图详解](#3-实施路线图详解)
4. [基础设施与部署配置](#4-基础设施与部署配置)
5. [核心功能实现](#5-核心功能实现)
6. [第一阶段：变化检测与同步机制](#6-第一阶段变化检测与同步机制)
7. [第二阶段：心理连贯性建模](#7-第二阶段心理连贯性建模)
8. [第三阶段：因果逻辑链建模](#8-第三阶段因果逻辑链建模)
9. [第四阶段：并发处理与去重](#9-第四阶段并发处理与去重)
10. [第五阶段：高级上下文优化](#10-第五阶段高级上下文优化)
11. [可选增强功能](#11-可选增强功能)
12. [测试与验证](#12-测试与验证)
13. [监控与运维](#13-监控与运维)

---

## 1. 项目概述与架构设计

### 1.1 项目目标

构建一个基于Graphiti时序知识图谱的记忆增强系统，为SillyTavern提供：
- **实时角色心理状态建模**：跟踪角色的情绪、特质、信念演化
- **世界观逻辑推演支持**：支持因果链、事件推演、反事实推理
- **动态记忆检索与整合**：智能检索相关记忆并整合到上下文
- **OpenAI兼容API接口**：无需修改SillyTavern即可使用

### 1.2 核心技术栈

| 层级 | 技术选型 | 版本 | 说明 |
|------|---------|------|------|
| **数据存储** | Neo4j | 5.26+ | 时序知识图谱后端 |
| **记忆框架** | Graphiti | 最新版 | Zep AI的开源时序知识图谱框架 |
| **LLM服务** | DeepSeek V3.2 | 最新 | 通过OpenAI兼容API调用（支持Strict模式） |
| **Embedding** | 硅基流动API | - | BAAI/bge-m3（1024维） |
| **Reranker** | 硅基流动API | - | BAAI/bge-reranker-v2-m3 |
| **API框架** | FastAPI | 0.104+ | 高性能异步Web框架 |
| **部署** | Docker Compose | v2.0+ | 容器化部署 |

### 1.3 系统架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SillyTavern客户端                          │
│              (通过OpenAI兼容API /v1/chat/completions)              │
└────────────────────────────────────┬────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        OpenAI兼容API服务层                           │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  请求处理流程                                                │  │
│  │  1. 接收SillyTavern请求（包含复杂格式内容）                  │  │
│  │  2. 提取session_id（header/参数/系统消息）                  │  │
│  │  3. 解析最后一个user消息（完整提示词）                       │  │
│  │  4. 解析SillyTavern格式（标签检测、内容分类）               │  │
│  │  5. 记忆处理（Graphiti）                                     │  │
│  │  6. 记忆检索（混合检索）                                     │  │
│  │  7. 上下文优化（指令保留+记忆替换+Token管理）                 │  │
│  │  8. LLM调用（DeepSeek）                                      │  │
│  │  9. 响应后处理（异步存储AI响应）                             │  │
│  │  10. 返回OpenAI兼容响应                                      │  │
│  └─────────────────────────────────────────────────────────────┘  │
└───────────────────┬─────────────────────────────────────────────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
        ▼           ▼           ▼
┌───────────┐ ┌─────────┐ ┌──────────┐
│ 解析服务  │ │记忆服务 │ │ LLM服务  │
│ (parser)  │ │(Graphiti)│ │ (DeepSeek)│
└─────┬─────┘ └────┬────┘ └────┬─────┘
      │            │           │
      └────────────┼───────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Graphiti记忆引擎（Neo4j）                        │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  核心功能                                                    │  │
│  │  • 时序知识图谱存储                                          │  │
│  │  • 实体关系提取（LLM驱动）                                    │  │
│  │  • 混合检索（向量+图遍历+Reranker）                          │  │
│  │  • 心理状态建模（新增功能）                                   │  │
│  │  • 因果逻辑链建模（新增功能）                                 │  │
│  │  • 变化检测与同步（新增功能）                                 │  │
│  └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.4 Graphiti三层架构设计

为解决"不同角色卡之间差别很大"的问题，采用三层架构：

```
┌─────────────────────────────────────────┐
│         动态扩展层 (Dynamic Layer)      │
│  • 角色卡特定实体/关系                  │
│  • 运行时通过LLM分析创建                │
│  • 可持久化复用                        │
│  • 示例：PsychologicalState, CausalChain │
└────────────────────┬────────────────────┘
                     │
┌────────────────────▼────────────────────┐
│         通用适配层 (Adaptive Layer)     │
│  • 通用属性容器（垃圾桶属性）            │
│  • 灵活的关系映射                       │
│  • 临时实体存储                         │
│  • 示例：UniversalPropertyContainer      │
└────────────────────┬────────────────────┘
                     │
┌────────────────────▼────────────────────┐
│         核心基础层 (Core Layer)         │
│  • 跨角色卡通用实体类型                 │
│  • 基础关系类型                         │
│  • 系统元数据                           │
│  • 示例：Character, Location, Event      │
└─────────────────────────────────────────┘
```

#### 1.4.1 核心基础层：通用实体类型

**实体类型设计原则**：
- 跨所有角色卡通用的基础实体
- 提供最小必要的核心属性
- 支持通过属性扩展适应特定需求

**核心实体类型**：

| 实体类型 | 核心属性 | 描述性属性 | 关系属性 | 时间属性 |
|---------|---------|-----------|---------|---------|
| **Character** | entity_id, name, entity_type | age, gender, appearance, background | relationships, affiliations | created_at, validity_period |
| **Location** | entity_id, name, entity_type | geography_type, description | contained_entities, connections | created_at, valid_from, valid_until |
| **Event** | entity_id, name, event_type | participants, significance, description | causes, effects, sub_events | start_time, end_time |
| **Object/Item** | entity_id, name, object_type | properties, description | owner, location, related_objects | created_at, modified_at |
| **WorldConcept** | entity_id, name, concept_type | definition, scope, exceptions | related_concepts, examples | established_date |

#### 1.4.2 通用适配层：属性化关系模型

**关系类型设计改进**（基于问题1的优化建议）：

采用**基础关系类型 + 属性标签**的设计，而非定义大量具体关系类型：

```text
基础关系类型（仅5种）：
1. HAS_RELATION_WITH        # 社交关系基类
2. HAS_ASSOCIATION_WITH    # 关联关系基类  
3. HAS_TEMPORAL_ORDER      # 时序关系基类
4. HAS_CAUSAL_LINK         # 因果关系基类
5. HAS_SPATIAL_RELATION    # 空间关系基类

关系属性标签（可动态扩展）：
- relation_subtype: "love", "friend", "enemy", "mentor"等
- intensity: 0.0-1.0（关系强度）
- confidence: 0.0-1.0（置信度）
- context_tags: ["work", "personal", "secret"]等
- temporal: valid_from, valid_until
- causal_strength: 0.0-1.0（因果关系强度）

示例：
关系：HAS_RELATION_WITH
属性：
  - relation_subtype: "love"        # 爱恋关系
  - intensity: 0.95                 # 强度
  - reciprocity: 0.8                # 互惠性
  - started_at: "2024-01-15"        # 开始时间
  - context: ["romantic", "secret"] # 上下文标签
```

**优势**：
1. **扩展性极佳**：无需修改图模式即可支持新关系
2. **查询灵活性**：既可按基础关系查询，也可按属性过滤
3. **维护简单**：关系逻辑集中在属性处理，而非图结构
4. **LLM友好**：LLM自然输出属性字典，易于转换

#### 1.4.3 动态扩展层：LLM驱动的模式演化

**问题**：如何在不为每个角色卡预定义所有实体类型的情况下，支持任意角色卡需求？

**解决方案**：在第一次遇到新类型时，通过LLM判断是否需要创建新的Pydantic实体模型。

**模式扩展决策流程**：

```
开始新实体识别
    │
    ▼
分析数据特征
    ├── 是否有明确的结构化模式？ ──是──→ 创建专用实体类型
    │       (如：consistent fields, clear relationships)
    │
    ├── 是否高频出现？ ──────────是──→ 考虑创建专用类型
    │       (出现次数 > 阈值)
    │
    ├── 是否与其他实体有复杂关系？ ─是──→ 优先创建专用类型
    │       (multiple relation types)
    │
    ├── 是否具有时间序列特性？ ────是──→ 考虑专用类型
    │       (values change over time)
    │
    └── 否 ──────────────────────────→ 使用通用属性容器
        (UniversalPropertyContainer)
    
创建专用类型前检查（使用LLM）：
    输入：文本数据 + 当前所有Pydantic实体模型定义 + 当前所有关系类型定义
    任务：
        1. 识别数据中的概念、实体、关系
        2. 与现有模型匹配度评估
        3. 判断是否需要新模型/关系
        4. 提供模型定义建议
    输出：
        {
            "entities": [...],
            "relations": [...],
            "recommendations": {
                "new_entity_types_needed": ["类型1", "类型2"],
                "existing_extensions_needed": ["类型1: 添加字段X"],
                "new_relation_types_needed": ["关系1", "关系2"]
            }
        }
    
决策：
    如果LLM建议创建新类型 AND 通过验证 → 创建新Pydantic模型
    如果LLM建议扩展现有类型 → 生成模型扩展补丁
    否则 → 使用通用属性容器
```

**LLM分析提示词模板**：

```
你是一个知识图谱模式设计专家。请分析以下文本数据，判断是否需要扩展现有的实体模型或关系类型。

## 当前系统状态
### 已有实体类型：
{existing_entity_types}

### 已有关系类型：
{existing_relation_types}

### 最近扩展记录：
{recent_expansions}

## 待分析文本：
{text_to_analyze}

## 分析任务：
1. **实体识别**：找出文本中提到的所有实体（人物、地点、事件、概念等）
2. **关系识别**：找出实体之间的所有关系
3. **模式匹配**：对于每个实体/关系，判断是否：
   a) 完全匹配现有类型（提供匹配的实体类型名）
   b) 部分匹配但需要扩展现有类型（说明如何扩展）
   c) 全新类型，需要创建新模型（建议模型定义）
4. **置信度评估**：给出每个判断的置信度（0.0-1.0）
5. **复用潜力评估**：新类型在其他角色卡中复用的可能性（高/中/低）

## 输出格式要求（JSON）：
{
  "entities": [
    {
      "text_mention": "文本中提及的内容",
      "entity_category": "人物/地点/事件/概念/物品/心理特质",
      "existing_match": {
        "type": "完全匹配/部分匹配/无匹配",
        "entity_type": "匹配的实体类型名或null",
        "confidence": 0.95
      },
      "recommendation": {
        "action": "使用现有/扩展现有/创建新类型/使用通用属性容器",
        "new_type_name": "建议的新类型名或null",
        "field_definitions": ["字段1: 类型", "字段2: 类型"],
        "reuse_potential": "高/中/低",
        "reasoning": "判断理由"
      }
    }
  ],
  "relations": [
    {
      "source_entity": "源实体",
      "target_entity": "目标实体",
      "relation_description": "关系描述",
      "existing_match": {
        "type": "完全匹配/部分匹配/无匹配",
        "relation_type": "匹配的关系类型名或null",
        "confidence": 0.85
      },
      "recommendation": {
        "action": "使用现有/创建新类型",
        "new_relation_type": "建议的新关系类型名",
        "properties": ["属性1: 类型", "属性2: 类型"],
        "base_relation": "使用哪个基础关系类型"
      }
    }
  ],
  "summary": {
    "new_entity_types_needed": ["类型1", "类型2"],
    "existing_extensions_needed": ["类型1: 添加字段X"],
    "new_relation_types_needed": ["关系1", "关系2"],
    "use_generic_container": true/false,
    "overall_confidence": 0.90
  }
}
```

**通用属性容器设计**（UniversalPropertyContainer）：

```text
通用属性容器 - 用于存储未预定义或角色卡特定的数据

设计原则：保持查询能力的同时提供最大灵活性

结构定义：
property_type: str              # 属性分类（如"appearance", "behavior", "background"）
data_type: str                 # 数据类型：string, number, boolean, list, object
value: Any                      # 实际值
unit: Optional[str]             # 单位（如cm, kg等）
qualifiers: List[str]           # 修饰词（如"approximately", "at least"等）

来源与置信度：
source: SourceRef               # 来源引用
confidence: float              # 置信度
conflicting_values: List[Dict]  # 冲突值记录

上下文信息：
context: Dict[str, Any]        # 出现上下文
constraints: List[str]         # 约束条件
exceptions: List[str]          # 例外情况

时间属性：
valid_from: Optional[datetime]
valid_until: Optional[datetime]
observed_at: List[datetime]   # 观测时间点

关系信息：
related_properties: List[PropertyRef]  # 相关属性
dependencies: List[Condition]         # 依赖条件
```

**专用实体类型与通用属性的权衡决策树**：

```
开始新实体识别
    │
    ▼
分析数据特征
    │
    ├── 有明确的结构化模式？
    │   │  是 ──────────────────────────→ 考虑创建专用实体类型
    │   │  否
    │   │
    │   ▼
    │   高频出现？（出现次数 > 阈值）
    │   │  是 ──────────────────────────→ 考虑创建专用类型
    │   │  否
    │   │
    │   ▼
    │   与其他实体有复杂关系？
    │   │  是（multiple relation types） → 优先创建专用类型
    │   │  否
    │   │
    │   ▼
    │   具有时间序列特性？
    │   │  是（values change over time） → 考虑专用类型
    │   │  否
    │   │
    │   ▼
    │   使用通用属性容器
    │
    创建专用类型前检查：
    1. 与现有类型的语义重叠度 < 阈值？
    2. 预期使用频率 > 成本？
    3. 查询需求是否复杂？
    4. 是否有多角色卡复用潜力？
    
    全部是 → 创建新Pydantic模型
    有否 → 使用通用属性容器
```

---

## 2. 当前实现状态分析

### 2.1 功能完成度矩阵

| 功能模块 | 要求完整度 | 实现完整度 | 符合度 | 优先级 |
|---------|-----------|-----------|--------|--------|
| **基础设施与部署** | 100% | 100% | ✅ 100% | - |
| **API服务核心架构** | 100% | 95% | ✅ 95% | - |
| **配置管理系统** | 100% | 100% | ✅ 100% | - |
| **服务层实现** | 100% | 60% | ⚠️ 60% | - |
| **数据模型** | 100% | 100% | ✅ 100% | - |
| **SillyTavern解析器** | 100% | 50% | ⚠️ 50% | 中 |
| **高级数据模式** | 100% | 0% | ❌ 0% | 高 |
| **心理连贯性建模** | 100% | 0% | ❌ 0% | 🔴 高 |
| **世界观逻辑推演** | 100% | 0% | ❌ 0% | 🔴 高 |
| **并发处理队列** | 100% | 0% | ❌ 0% | 🟡 中 |
| **多层次去重策略** | 100% | 0% | ❌ 0% | 🟡 中 |
| **变化检测与同步** | 100% | 0% | ❌ 0% | 🔴 高 |
| **高级上下文优化** | 100% | 30% | ⚠️ 30% | 🟡 中 |
| **总体平均** | **100%** | **53%** | **⚠️ 53%** | - |

**图例**：
- ✅ 完成（>90%）
- ⚠️ 部分完成（50-90%）
- ❌ 未实现（<50%）
- 🔴 高优先级
- 🟡 中优先级
- 🟢 低优先级

### 2.2 详细功能对比

#### 2.2.1 已完成功能（90%+）

1. **基础设施与部署** ✅
   - Neo4j Docker Compose v2部署完整配置
   - Redis缓存服务配置
   - API服务容器化部署
   - 网络隔离和资源限制
   - 健康检查机制

2. **配置管理系统** ✅
   - Pydantic Settings配置管理
   - 环境变量加载和验证
   - Neo4j、DeepSeek、SiliconFlow、API配置类完整
   - Graphiti客户端工厂模式实现

3. **数据模型** ✅
   - OpenAI兼容请求/响应模型
   - Message、Usage、ChatCompletion模型
   - 完整的Pydantic验证

4. **LLM服务** ✅
   - AsyncOpenAI客户端封装
   - DeepSeek API集成
   - 完整的generate_completion方法

#### 2.2.2 部分完成功能（50-90%）

1. **API服务核心架构** ⚠️ 95%
   - FastAPI应用、lifespan管理
   - /health和/v1/chat/completions端点
   - session_id提取逻辑
   - 9步处理流程完整
   - **缺失**：响应内容解析与存储的详细实现

2. **Graphiti服务封装** ⚠️ 60%
   - process_content方法：添加Episode
   - search_memories方法：混合检索
   - process_response方法：异步存储响应
   - **缺失**：实体级别去重、变化检测、心理建模、因果链

3. **SillyTavern解析器** ⚠️ 50%
   - 数据模型定义（NarrativeBlock, InstructionBlock, DialogTurn, ParsedContent）
   - 标签映射表
   - parse方法：三级检测
   - _parse_world_info和_parse_dialog_history方法
   - **缺失**：并发处理队列、动态角色名识别、复杂格式解析、LLM辅助消歧

4. **上下文优化** ⚠️ 30%
   - 基础优化逻辑（指令保留+记忆替换+最近5轮对话）
   - **缺失**：Token计算、智能替换策略、摘要生成

#### 2.2.3 未实现功能（<50%）

1. **高级数据模式** ❌ 0%
   - 三层模式架构未实现
   - 通用属性容器未实现
   - LLM驱动的模式演化未实现

2. **心理连贯性建模** ❌ 0%
   - PsychologicalState实体未定义
   - EmotionNode、TraitNode、BeliefNode未实现
   - 心理状态演化跟踪未实现
   - 心理连贯性度量未实现

3. **世界观逻辑推演** ❌ 0%
   - 因果链数据结构未实现
   - 世界观规则表示未实现
   - 事件推演机制未实现

4. **并发处理队列** ❌ 0%
   - 任务队列未实现
   - 工作线程池未实现
   - 动态任务分配未实现

5. **多层次去重策略** ❌ 0%
   - 哈希去重未实现
   - 实体级别去重未实现
   - 关系级别去重未实现

6. **变化检测与同步** ❌ 0%
   - World Info变化检测未实现
   - Chat History变化检测未实现
   - Graphiti同步更新（删除/修改）未实现

---

## 3. 实施路线图详解

基于项目实现情况检查报告，提供详细的10周实施计划。

### 3.1 总体时间线

```
Week 1-2:  变化检测与同步机制（高优先级）
Week 3-4:  心理连贯性建模（高优先级）
Week 5-6:  因果逻辑链建模（高优先级）
Week 7-8:  并发处理与去重（中优先级）
Week 9-10: 高级上下文优化（中优先级）
```

### 3.2 优先级矩阵

| 功能 | 重要性 | 紧急性 | 优先级 | 预计工作量 |
|------|--------|--------|--------|-----------|
| 变化检测与同步 | 高 | 高 | 🔴 P0 | 2-3周 |
| 心理连贯性建模 | 高 | 高 | 🔴 P0 | 3-4周 |
| 因果逻辑链建模 | 高 | 高 | 🔴 P0 | 3-4周 |
| 并发处理队列 | 中 | 中 | 🟡 P1 | 1-2周 |
| 多层次去重策略 | 中 | 中 | 🟡 P1 | 2周 |
| 高级上下文优化 | 中 | 中 | 🟡 P1 | 2周 |
| 动态角色名识别 | 低 | 低 | 🟢 P2 | 1周 |
| 复杂格式解析 | 低 | 低 | 🟢 P2 | 1-2周 |
| 语义哈希去重 | 低 | 低 | 🟢 P2 | 2周 |
| 三层模式架构 | 低 | 低 | 🟢 P2 | 4-5周 |

---

## 4. 基础设施与部署配置

### 4.1 Docker Compose配置

**文件位置**：`docker-compose.yaml`

```yaml
version: '3.8'

services:
  # Neo4j图数据库服务
  neo4j:
    image: neo4j:5.26-community
    container_name: airp-neo4j
    restart: unless-stopped
    ports:
      - "7474:7474"    # HTTP Browser界面
      - "7687:7687"    # Bolt协议端口
    environment:
      # 认证配置
      - NEO4J_AUTH=${NEO4J_USER}/${NEO4J_PASSWORD}
      - NEO4J_ACCEPT_LICENSE_AGREEMENT=yes
      
      # 内存配置（根据服务器内存调整）
      - NEO4J_dbms_memory_pagecache_size=2G
      - NEO4J_dbms_memory_heap_initial__size=4G
      - NEO4J_dbms_memory_heap_max__size=4G
      
      # 插件配置
      - NEO4J_PLUGINS=["apoc"]
      - NEO4J_dbms_security_procedures_unrestricted=apoc.*
      
      # 日志配置
      - NEO4J_dbms_logs_debug_level=INFO
    volumes:
      # 数据持久化
      - ./neo4j/data:/data
      - ./neo4j/logs:/logs
      - ./neo4j/import:/var/lib/neo4j/import
      - ./neo4j/plugins:/plugins
    healthcheck:
      test: ["CMD", "cypher-shell", "-u", "${NEO4J_USER}", "-p", "${NEO4J_PASSWORD}", "RETURN 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - airp-network
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 6G
        reservations:
          cpus: '2'
          memory: 4G

  # Redis缓存服务
  redis:
    image: redis:7-alpine
    container_name: airp-redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - ./redis/data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - airp-network

  # API服务
  api-service:
    build:
      context: ./api-service
      dockerfile: Dockerfile
    container_name: airp-api
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      # Neo4j连接配置
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=${NEO4J_USER}
      - NEO4J_PASSWORD=${NEO4J_PASSWORD}
      
      # Redis配置
      - REDIS_URL=redis://redis:6379
      - REDIS_PASSWORD=${REDIS_PASSWORD}
      
      # DeepSeek API配置
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
      - DEEPSEEK_BASE_URL=${DEEPSEEK_BASE_URL}
      - DEEPSEEK_MODEL=${DEEPSEEK_MODEL}
      
      # Graphiti配置
      - GRAPHITI_SEMAPHORE_LIMIT=${GRAPHITI_SEMAPHORE_LIMIT}
      - GRAPHITI_TELEMETRY_ENABLED=${GRAPHITI_TELEMETRY_ENABLED}
      
      # API服务配置
      - API_HOST=0.0.0.0
      - API_PORT=8000
      - API_WORKERS=${API_WORKERS}
      - API_LOG_LEVEL=${API_LOG_LEVEL}
      
      # 应用配置
      - APP_ENV=${APP_ENV}
      - APP_SECRET_KEY=${APP_SECRET_KEY}
    volumes:
      # 代码热重载（开发环境）
      - ./api-service:/app
      # 日志持久化
      - ./logs/api:/app/logs
    depends_on:
      neo4j:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    networks:
      - airp-network
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 4G
        reservations:
          cpus: '2'
          memory: 2G

networks:
  airp-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16

volumes:
  neo4j_data:
    driver: local
  neo4j_logs:
    driver: local
  redis_data:
    driver: local
```

### 4.2 环境变量配置

**文件位置**：`.env`

```env
# ============================================
# Neo4j数据库配置
# ============================================
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_secure_neo4j_password_change_this

# ============================================
# Redis缓存配置
# ============================================
REDIS_PASSWORD=your_secure_redis_password_change_this

# ============================================
# DeepSeek API配置
# ============================================
# API密钥（从DeepSeek平台获取）
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# API端点
# 标准端点：https://api.deepseek.com
# Beta端点：https://api.deepseek.com/beta（推荐，支持Strict模式）
DEEPSEEK_BASE_URL=https://api.deepseek.com/beta

# 使用的模型
DEEPSEEK_MODEL=deepseek-chat

# ============================================
# 硅基流动API配置
# ============================================
SILICONFLOW_API_KEY=your_siliconflow_api_key_here
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
SILICONFLOW_EMBEDDING_MODEL=BAAI/bge-m3
SILICONFLOW_EMBEDDING_DIM=1024
SILICONFLOW_RERANKER_MODEL=BAAI/bge-reranker-v2-m3

# ============================================
# Graphiti配置
# ============================================
# 并发限制（避免API 429错误）
GRAPHITI_SEMAPHORE_LIMIT=5

# 禁用遥测（可选）
GRAPHITI_TELEMETRY_ENABLED=false

# ============================================
# API服务配置
# ============================================
API_HOST=0.0.0.0
API_PORT=8000

# Worker数量（建议为CPU核心数-1）
API_WORKERS=3

# 日志级别: debug, info, warning, error, critical
API_LOG_LEVEL=info

# ============================================
# 应用配置
# ============================================
# 运行环境: development, production
APP_ENV=development

# 会话密钥（用于会话管理）
APP_SECRET_KEY=your_random_secret_key_at_least_32_characters_long

# ============================================
# 安全警告
# ============================================
# ⚠️ 重要：修改所有密码和密钥！
# ⚠️ 不要将.env文件提交到版本控制系统
# ⚠️ 生产环境请使用强密码
```

### 4.3 项目目录结构

```
airp-memory-system/
├── docker-compose.yaml          # Docker Compose配置
├── .env                        # 环境变量配置
├── requirements.txt             # Python依赖
├── api-service/                # API服务代码目录
│   ├── main.py                 # FastAPI主入口
│   ├── Dockerfile              # API服务Docker镜像
│   ├── config/                 # 配置模块
│   │   ├── __init__.py
│   │   ├── settings.py          # 应用设置
│   │   └── graphiti_config.py  # Graphiti配置
│   ├── models/                 # 数据模型
│   │   ├── __init__.py
│   │   ├── requests.py         # 请求模型
│   │   └── responses.py        # 响应模型
│   ├── services/               # 服务层
│   │   ├── __init__.py
│   │   ├── graphiti_service.py     # Graphiti操作
│   │   ├── llm_service.py           # LLM调用
│   │   └── parser_service.py        # SillyTavern格式解析
│   ├── utils/                  # 工具函数
│   │   ├── __init__.py
│   │   ├── session_manager.py    # 会话管理
│   │   ├── dedup.py              # 去重逻辑
│   │   └── logger.py             # 日志工具
│   └── advanced/               # 高级功能（新增）
│       ├── change_detection.py   # 变化检测
│       ├── psychological_modeling.py  # 心理建模
│       ├── causal_modeling.py   # 因果建模
│       ├── concurrent_processor.py    # 并发处理
│       └── advanced_dedup.py    # 高级去重
├── neo4j/                      # Neo4j数据挂载
│   ├── data/                   # 数据持久化
│   ├── logs/                   # 日志文件
│   └── import/                 # 初始数据导入
└── logs/                       # 应用日志
    └── api/                    # API服务日志
```

---

## 5. 核心功能实现

### 5.1 输入解析与内容分类

#### 5.1.1 问题背景

SillyTavern发送的输入格式不固定，包含：
- Persona Description（用户设定描述）
- World Info（世界书，包含角色设定、世界观、物品设定、地点设定、过往剧情等）
- Char Description（角色描述）
- Chat History（对话上下文，可能包含CoT）
- 核心指导（`<核心指导>`等包裹的内容）

**挑战**：
1. 标签格式多样（`<核心指导>`, `<|User|>`, `<\|User\|>`等）
2. 标签名称不固定（不一定是"补充资料"、"核心指导"等标准名称）
3. 可能完全没有标签，只有自然语言
4. 对话历史中Assistant和User的名字可能动态变化

#### 5.1.2 解决方案：三级渐进式解析

```
第一级：标签检测（正则表达式）
    ↓
第二级：启发式规则识别
    ↓
第三级：LLM辅助分析（可选）
```

**第一级：标签检测**

正则表达式模式库：

```text
1. 标准开标签：<([^/>]+)>
   匹配：<核心指导>、<相关资料>、<互动历史>
   不匹配：HTML标签属性、自闭合标签

2. 标准闭标签：</([^>]+)>
   匹配：</核心指导>、</相关资料>

3. 自闭合标签：<([^>]+)/>
   匹配：<br/>、<format/>

4. 特殊格式标签：
   a) 竖线分隔：<\|([^|]+)\|>
      匹配：<|User|>、<|Assistant|>
   b) 花括号：{{([^}]+)}}
      匹配：{{user}}、{{char}}
   c) 方括号：\[\[([^\]]+)\]\]
      匹配：[[user name]]
```

**检测算法逻辑**：

```python
# 伪代码：标签检测算法

def detect_tags_with_regex(text):
    """
    使用正则表达式检测所有标签
    
    参数:
        text: 原始文本
    
    返回:
        List[TagDetection]: 检测到的标签列表
    """
    detected_tags = []
    
    # 编译正则模式
    patterns = {
        "opening_tag": r"<([^/>]+)>",
        "closing_tag": r"</([^>]+)>",
        "self_closing": r"<([^>]+)/>",
        "pipe_tag": r"<\|([^|]+)\|>",
        "brace_tag": r"\{\{([^}]+)\}\}",
        "bracket_tag": r"\[\[([^\]]+)\]\]"
    }
    
    # 扫描所有模式
    for pattern_name, pattern in patterns.items():
        matches = re.finditer(pattern, text)
        
        for match in matches:
            tag_name = match.group(1).strip()
            
            # 验证是否为有效标签（非HTML/XML技术标签）
            if is_content_tag(tag_name):
                tag_type = determine_tag_type(match.group(), pattern_name)
                
                detected_tags.append({
                    'full_match': match.group(),
                    'tag_name': tag_name,
                    'pattern_type': pattern_name,
                    'tag_type': tag_type,  # opening/closing/self_closing
                    'position': match.start(),
                    'end_position': match.end()
                })
    
    return detected_tags


def is_content_tag(tag_name):
    """
    判断标签是否为内容标签（非技术标签）
    
    排除的标签：html, head, body, div, span, script, style等
    """
    excluded_tags = {
        'html', 'head', 'body', 'div', 'span', 'p', 'br',
        'script', 'style', 'link', 'meta', 'title',
        'a', 'img', 'table', 'tr', 'td', 'th'
    }
    return tag_name.lower() not in excluded_tags


def determine_tag_type(full_match, pattern_type):
    """
    确定标签类型
    """
    if pattern_name == "closing_tag":
        return "closing"
    elif pattern_name == "self_closing":
        return "self_closing"
    elif pattern_name == "pipe_tag":
        # 竖线标签通常是自闭合的
        return "self_closing"
    else:
        return "opening"
```

**第二级：启发式内容识别**

当标签检测不完整或置信度低时，使用启发式规则：

```text
启发式识别规则集：

1. 对话历史识别：
   IF 文本包含交替出现的"User:"和"Assistant:"（或角色名）模式
   AND 相邻行时间相近
   THEN 识别为对话历史
   
   正则模式：
   (User:|Assistant:|[A-Za-z\u4e00-\u9fa5]+:)\s*[^\n]+
   
2. 世界书条目识别：
   IF 文本包含以下任一模式：
      - 地点("地点名")["描述"]
      - 类别("类别名")["描述"]
      - 概念("概念名")["描述"]
      - Character_Profile_of: 角色名
   AND 包含结构化描述（列表、属性对）
   THEN 识别为世界书条目
   
3. 角色描述识别：
   IF 文本包含以下模式：
      - Character_Profile_of: 角色名
      - character: 角色名
      - [角色描述] 标题
   AND 包含详细属性描述（外貌、性格、背景等）
   THEN 识别为角色描述
   
4. 指令内容识别：
   IF 文本包含以下关键词：
      - "必须"、"不得"、"应该"、"禁止"
      - 或包含在<基础风格>、<创作准则>等标签中
   THEN 识别为指令内容
```

**启发式识别算法**：

```python
# 伪代码：启发式内容识别

def heuristic_content_detection(text, detected_tags):
    """
    启发式内容识别
    
    参数:
        text: 原始文本
        detected_tags: 检测到的标签列表
    
    返回:
        Dict[str, List[ContentBlock]]: 按类型分类的内容块
    """
    content_blocks = {
        "dialog_history": [],
        "world_info": [],
        "character_desc": [],
        "instruction": [],
        "general_narrative": []
    }
    
    # 规则1：对话历史检测
    if has_dialog_pattern(text):
        dialog_blocks = parse_dialog_history(text)
        content_blocks["dialog_history"].extend(dialog_blocks)
    
    # 规则2：世界书条目检测
    if has_world_info_pattern(text):
        world_info_blocks = parse_world_info(text)
        content_blocks["world_info"].extend(world_info_blocks)
    
    # 规则3：角色描述检测
    if has_character_desc_pattern(text):
        char_blocks = parse_character_description(text)
        content_blocks["character_desc"].extend(char_blocks)
    
    # 规则4：指令内容检测
    if has_instruction_pattern(text):
        instruction_blocks = parse_instructions(text)
        content_blocks["instruction"].extend(instruction_blocks)
    
    return content_blocks


def has_dialog_pattern(text):
    """
    检测对话历史模式
    
    算法：
    1. 搜索"User:"和"Assistant:"或角色名的出现
    2. 检查是否交替出现
    3. 检查是否有对话内容
    """
    # 匹配User/Assistant或动态角色名
    pattern = r"(User|Assistant|[A-Za-z\u4e00-\u9fa5]+):\s*[^\n]+"
    matches = re.findall(pattern, text)
    
    if len(matches) < 2:
        return False
    
    # 检查是否交替
    for i in range(len(matches) - 1):
        if matches[i] == matches[i + 1]:
            # 连续两个相同的说话者，可能不是对话
            pass
        else:
            # 交替模式
            return True
    
    return False


def parse_dialog_history(text):
    """
    解析对话历史
    
    算法：
    1. 识别所有对话行
    2. 动态识别说话者名字
    3. 提取对话内容
    4. 构建DialogTurn对象
    """
    lines = text.strip().split('\n')
    turns = []
    
    # 动态角色名识别
    speaker_mapping = {}
    
    for line in lines:
        # 匹配对话行
        match = re.match(r"^(User|Assistant|[A-Za-z\u4e00-\u9fa5]+):\s*(.+)$", line.strip())
        
        if match:
            speaker = match.group(1).strip()
            content = match.group(2).strip()
            
            # 动态角色名映射
            if speaker not in speaker_mapping:
                if speaker.lower() == "user":
                    speaker_mapping[speaker] = "User"
                elif speaker.lower() in ["assistant", "ai"]:
                    speaker_mapping[speaker] = "Assistant"
                else:
                    # 新角色名，判断是User还是Assistant
                    speaker_mapping[speaker] = determine_role(speaker, turns)
            
            turns.append(DialogTurn(
                role=speaker_mapping[speaker],
                content=content,
                raw_speaker=speaker,
                turn_number=len(turns) + 1
            ))
    
    return turns


def determine_role(speaker, existing_turns):
    """
    动态判断角色类型
    
    策略：
    1. 如果已有角色映射，使用映射
    2. 如果第一个非User角色，判定为Assistant
    3. 否则根据上下文推断
    """
    if not existing_turns:
        return "User"
    
    # 检查是否已有Assistant
    has_assistant = any(t.role == "Assistant" for t in existing_turns)
    
    if not has_assistant:
        # 第一个非User角色
        return "Assistant"
    else:
        # 已有Assistant，新角色可能是用户别名或NPC
        # 暂时判定为Assistant（用户别名）
        return "Assistant"
```

**第三级：LLM辅助分析（按需使用）**

**使用条件**：
- 正则检测结果置信度低（< 0.7）
- 标签结构复杂或嵌套
- 出现未知格式

**LLM提示词设计**：

```
你是一个文本格式分析专家。请分析以下文本片段，识别其中的内容标签和类型。

## 任务说明
文本中可能包含各种格式的内容标签，如：
- 结构化标签：<核心指导>、<相关资料>
- 对话标签：<|User|>、<|Assistant|>
- 格式标签：<format>、<br/>
- 自定义标签：各种用户定义的标签
- 无标签的自然语言内容

## 输入文本
{text_fragment}

## 分析要求
1. 找出所有可能是内容标签的文本片段
2. 判断每个标签的类型（开标签/闭标签/自闭合）
3. 推测标签的语义用途
4. 识别无标签的内容类型（对话、世界书、指令等）
5. 评估识别置信度

## 输出格式（JSON）：
{
  "detected_tags": [
    {
      "text": "<核心指导>",
      "type": "opening",
      "semantic_guess": "instruction_section",
      "confidence": 0.95
    }
  ],
  "content_blocks": [
    {
      "type": "dialog_history",
      "start_position": 100,
      "end_position": 500,
      "speaker_pattern": "User/Assistant",
      "confidence": 0.90
    }
  ],
  "uncertain_regions": [
    {
      "start": 50,
      "end": 100,
      "reason": "格式不明确",
      "suggestion": "可能是对话或指令"
    }
  ]
}
```

#### 5.1.3 内容分类逻辑

```
开始分类
    │
    ▼
是否有明确标签？
    │  是 → 按标签映射表分类
    │       ├─ <核心指导>、<基础风格>、<创作准则> → instruction（指令性）
    │       ├─ <相关资料> → world_info（叙事性）
    │       ├─ <互动历史> → dialog_history（叙事性）
    │       └─ <补充资料> → supplementary（叙事性）
    │
    └─ 否 → 应用启发式规则
        ├─ 包含"User:"/"Assistant:"交替 → dialog_history（叙事性）
        ├─ 包含"地点("、"角色("、"概念(" → world_info（叙事性）
        ├─ 包含"必须"、"不得"、"禁止" → instruction（指令性）
        ├─ 包含Character_Profile_of: → character_desc（叙事性）
        └─ 默认 → general_narrative（叙事性）
        
    │
    ▼
分类完成，构建ParsedContent对象
```

**内容处理策略矩阵**：

| 内容类型 | Graphiti处理 | 直接传递LLM | Token优化策略 | 示例 |
|---------|------------|-------------|---------------|------|
| **核心指导** | 否 | 是 | 必须完整保留 | `<核心指导>你是非常规的中文创作助手haruki</核心指导>` |
| **基础风格** | 否 | 是 | 必须完整保留 | `<基础风格>- 正文严格使用简体中文</基础风格>` |
| **创作准则** | 否 | 是 | 必须完整保留 | 创作要求列表 |
| **Persona描述** | 是 | 可选 | 替换为图谱召回信息 | {{user}}翊山，夏莱的老师 |
| **World Info** | 是 | 否 | 替换为图谱召回信息 | `<相关资料>翊山设定...</相关资料>` |
| **Char Description** | 是 | 否 | 替换为图谱召回信息 | Character_Profile_of: 圣园未花 |
| **Chat History** | 是 | 部分 | 近期历史保留，远期摘要 | `<互动历史>User: 你好\nAssistant: 你好！</互动历史>` |
| **补充资料** | 是 | 可选 | 根据相关性选择保留 | `<补充资料>序幕 2-1</补充资料>` |

### 5.2 Graphiti集成配置

#### 5.2.1 DeepSeek API集成（支持Strict模式）

**两种模式对比**：

| 模式 | 端点 | 优势 | 劣势 | 适用场景 |
|------|------|------|------|----------|
| **Beta端点** | https://api.deepseek.com/beta | 完全支持JSON Schema strict模式，服务器端验证 | 可能不够稳定 | 生产环境，追求最佳质量 |
| **标准端点** | https://api.deepseek.com | 更稳定 | 不支持strict模式，需要兼容层 | 测试环境，快速部署 |

**配置选择**：

```python
# 配置文件：api-service/config/settings.py

class DeepSeekConfig(BaseSettings):
    """DeepSeek LLM配置类"""
    
    api_key: str = Field(..., description="DeepSeek API密钥（必填）")
    
    base_url: str = Field(
        default="https://api.deepseek.com/beta",
        description="DeepSeek API基础URL"
    )
    
    model: str = Field(default="deepseek-chat", description="DeepSeek模型名称")
    small_model: str = Field(default="deepseek-chat", description="DeepSeek小模型名称")
    
    use_strict_mode: bool = Field(
        default=True,
        description="是否使用Strict JSON Schema模式"
    )
    
    class Config:
        env_prefix = "DEEPSEEK_"
        case_sensitive = False
```

**Strict模式实现**：

```python
# Graphiti客户端工厂：api-service/config/graphiti_config.py

from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
from graphiti_core.llm_client.config import LLMConfig

def create_deepseek_llm_client(config: DeepSeekConfig):
    """
    创建DeepSeek LLM客户端（支持Strict模式）
    
    参数:
        config: DeepSeekConfig配置
    
    返回:
        OpenAIGenericClient: LLM客户端实例
    """
    # 使用OpenAIGenericClient（Graphiti推荐）
    # 它支持自定义base_url和自动处理JSON Schema
    
    llm_config = LLMConfig(
        api_key=config.api_key,
        model=config.model,
        small_model=config.small_model,
        base_url=config.base_url
    )
    
    llm_client = OpenAIGenericClient(config=llm_config)
    
    # 如果使用Beta端点，确保Strict模式启用
    if "/beta" in config.base_url and config.use_strict_mode:
        # OpenAIGenericClient会自动在Function Call中添加strict: true
        pass
    
    return llm_client
```

**Strict模式的要求**：

```text
Strict模式对JSON Schema的要求：
1. 所有object属性必须设置为required
2. additionalProperties必须设置为false
3. 不允许额外字段
4. 类型必须严格匹配

示例：
{
    "type": "object",
    "properties": {
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "type": {"type": "string"}
                },
                "required": ["name", "type"],  # 必须是required
                "additionalProperties": false  # 必须为false
            }
        }
    },
    "required": ["entities"],
    "additionalProperties": false
}
```

#### 5.2.2 硅基流动API集成

**Embedding API配置**：

```python
# 使用OpenAIGenericClient（Graphiti推荐）

from openai import OpenAI

def create_siliconflow_embedder(config: SiliconFlowConfig):
    """
    创建硅基流动Embedding客户端
    
    硅基流动的Embedding API是OpenAI兼容的
    直接使用OpenAI客户端，base_url指向硅基流动
    """
    embedding_client = OpenAI(
        api_key=config.api_key,
        base_url=config.base_url
    )
    
    # Graphiti会自动使用这个客户端进行向量化
    return embedding_client
```

**Reranker API配置**：

```python
# 硅基流动的Reranker API不是标准的OpenAI兼容接口
# 需要自定义客户端封装

import httpx

class SiliconFlowRerankerClient:
    """硅基流动Reranker客户端"""
    
    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {api_key}"}
        )
    
    async def rerank(
        self,
        query: str,
        documents: List[str],
        top_n: int = 5
    ) -> List[Dict]:
        """
        对文档进行重排序
        
        API端点: POST https://api.siliconflow.cn/v1/rerank
        
        参数:
            model: BAAI/bge-reranker-v2-m3
            query: 用户查询
            documents: 文档列表
            top_n: 返回的顶部文档数量
        
        返回:
            按相关性排序的文档列表，带相关性分数
        """
        url = f"{self.base_url}/rerank"
        
        payload = {
            "model": self.model,
            "query": query,
            "documents": documents,
            "top_n": top_n
        }
        
        response = await self.client.post(url, json=payload)
        response.raise_for_status()
        
        result = response.json()
        return result.get("results", [])
    
    async def close(self):
        await self.client.aclose()
```

#### 5.2.3 Graphiti完整初始化

```python
# Graphiti客户端工厂完整实现

class GraphitiClientFactory:
    """Graphiti客户端工厂类"""
    
    @staticmethod
    async def create_graphiti_client(
        neo4j_uri: str,
        neo4j_user: str,
        neo4j_password: str,
        deepseek_config: DeepSeekConfig,
        siliconflow_config: SiliconFlowConfig,
        semaphore_limit: int = 5
    ) -> Graphiti:
        """
        创建Graphiti客户端实例
        
        完整初始化流程：
        1. 创建Neo4j驱动
        2. 验证连接
        3. 创建DeepSeek LLM客户端
        4. 创建硅基流动Embedding客户端
        5. 创建硅基流动Reranker客户端
        6. 初始化Graphiti实例
        7. 构建索引和约束
        8. 返回Graphiti实例
        """
        # 步骤1: 创建Neo4j驱动
        driver = GraphDatabase.driver(
            uri=neo4j_uri,
            auth=(neo4j_user, neo4j_password)
        )
        
        # 步骤2: 验证连接
        driver.verify_connectivity()
        
        # 步骤3: 创建DeepSeek LLM客户端
        llm_client = create_deepseek_llm_client(deepseek_config)
        
        # 步骤4: 创建硅基流动Embedding客户端
        embedding_client = create_siliconflow_embedder(siliconflow_config)
        
        # 步骤5: 创建硅基流动Reranker客户端
        reranker_client = SiliconFlowRerankerClient(
            api_key=siliconflow_config.api_key,
            base_url=siliconflow_config.base_url,
            model=siliconflow_config.reranker_model
        )
        
        # 步骤6: 初始化Graphiti实例
        graphiti = Graphiti(
            uri=neo4j_uri,
            user=neo4j_user,
            password=neo4j_password,
            llm_client=llm_client,
            embedder=embedding_client,
            cross_encoder=reranker_client,
            semaphore_limit=semaphore_limit
        )
        
        # 步骤7: 构建索引和约束
        await graphiti.build_indices_and_constraints()
        
        # 步骤8: 返回Graphiti实例
        return graphiti
```

---

## 6. 第一阶段：变化检测与同步机制

### 6.1 问题分析

**背景**：
- SillyTavern的世界书可能频繁变化（用户添加、删除、修改条目）
- 对话历史是动态增长的，也可能被编辑或删除
- 当前实现每次将所有内容作为新Episode添加，导致重复信息
- 没有利用Graphiti的时序特性

**影响**：
- 知识图谱中存在大量重复信息
- 检索质量下降（召回重复内容）
- 存储空间浪费
- 查询性能下降

**目标**：
1. 检测World Info的新增、删除、修改
2. 检测Chat History的新增、删除、修改
3. 根据变化更新Graphiti（增量处理）
4. 避免使用LLM进行变化检测（使用哈希、规则等）

### 6.2 World Info变化检测

#### 6.2.1 条目状态跟踪

```python
# World Info状态跟踪数据结构

class WorldInfoEntry:
    """世界书条目"""
    
    entry_id: str                      # 唯一标识（基于内容哈希）
    entry_type: str                    # 类型：location, character, concept等
    name: str                         # 条目名称
    content: str                      # 条目内容
    content_hash: str                 # 内容哈希（用于快速比对）
    properties: Dict[str, Any]        # 属性
    
    # 时间属性
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]
    
    # 来源追踪
    source: str                       # 来源（world_info标签等）
    session_id: str                   # 所属会话
    
    # 状态
    status: str                       # active, deleted, superseded, expired
    status_reason: Optional[str]     # 状态原因


class WorldInfoState:
    """世界书状态跟踪器"""
    
    def __init__(self):
        self.entries: Dict[str, WorldInfoEntry] = {}  # entry_id -> entry
        self.entry_hashes: Dict[str, str] = {}       # content_hash -> entry_id
        self.timestamp: datetime = None
        self.version: int = 0
```

#### 6.2.2 条目ID计算

**关键设计**：基于条目类型和关键属性生成稳定ID

```python
# 伪代码：条目ID计算

def compute_entry_id(entry: WorldInfoEntry) -> str:
    """
    计算条目的唯一标识
    
    设计原则：
    - 基于条目类型和关键属性生成稳定ID
    - 名称微小变化不会导致ID变化
    - 相同实体在不同地方出现有相同ID
    - 支持条目重命名跟踪
    
    参数:
        entry: 世界书条目
    
    返回:
        str: 条目ID
    """
    # 标准化名称
    normalized_name = normalize_name(entry.name)
    
    # 生成ID
    if entry.entry_type == "location":
        entry_id = f"location:{normalized_name}"
    elif entry.entry_type == "character":
        entry_id = f"character:{normalized_name}"
    elif entry.entry_type == "concept":
        entry_id = f"concept:{normalized_name}"
    else:
        entry_id = f"{entry.entry_type}:{normalized_name}"
    
    return entry_id


def normalize_name(name: str) -> str:
    """
    标准化名称
    
    处理：
    1. 统一大小写
    2. 去除多余空格
    3. 标准化标点
    4. 去除特殊字符
    """
    # 转换为小写
    normalized = name.lower()
    
    # 去除多余空格
    normalized = re.sub(r'\s+', ' ', normalized)
    normalized = normalized.strip()
    
    # 标准化标点
    normalized = normalized.replace('：', ':')
    normalized = normalized.replace('（', '(').replace('）', ')')
    
    # 去除特殊字符（保留中文、字母、数字、空格、标点）
    normalized = re.sub(r'[^\w\s\u4e00-\u9fa5:：，。、；；！！？？（）（）【】""\'']', '', normalized)
    
    return normalized
```

#### 6.2.3 哈希计算

```python
# 伪代码：内容哈希计算

def compute_content_hash(content: str) -> str:
    """
    计算内容哈希
    
    算法：
    1. 文本标准化（去除空白、标点差异）
    2. 计算MD5哈希
    
    参数:
        content: 内容文本
    
    返回:
        str: MD5哈希值
    """
    import hashlib
    
    # 标准化
    normalized = normalize_content(content)
    
    # 计算哈希
    hash_value = hashlib.md5(normalized.encode('utf-8')).hexdigest()
    
    return hash_value


def normalize_content(content: str) -> str:
    """
    标准化内容
    
    处理：
    1. 统一换行符
    2. 去除多余空白
    3. 标准化标点
    """
    # 统一换行符
    normalized = content.replace('\r\n', '\n').replace('\r', '\n')
    
    # 去除首尾空白
    normalized = normalized.strip()
    
    # 去除多余空行
    normalized = re.sub(r'\n{3,}', '\n\n', normalized)
    
    # 标准化标点
    normalized = normalized.replace('：', ':')
    normalized = normalized.replace('，', ',')
    normalized = normalized.replace('。', '.')
    
    return normalized
```

#### 6.2.4 变化检测算法

```python
# 伪代码：World Info变化检测

def detect_worldinfo_changes(
    old_state: WorldInfoState,
    new_content: str
) -> Dict[str, List]:
    """
    检测World Info的变化
    
    算法：
    1. 解析新内容为条目
    2. 为每个新条目计算entry_id和content_hash
    3. 与旧状态比较
    4. 分类变化类型：新增、删除、修改、未变化
    
    参数:
        old_state: 旧的世界书状态
        new_content: 新的世界书内容
    
    返回:
        Dict: {
            "added": [新增条目],
            "removed": [删除条目],
            "modified": [修改详情],
            "unchanged": [未变化条目]
        }
    """
    changes = {
        "added": [],
        "removed": [],
        "modified": [],
        "unchanged": []
    }
    
    # 步骤1: 解析新内容为条目
    new_entries = parse_worldinfo_entries(new_content)
    
    # 步骤2: 为每个新条目计算特征
    new_entries_with_id = []
    for entry in new_entries:
        entry_id = compute_entry_id(entry)
        content_hash = compute_content_hash(entry.content)
        
        entry.entry_id = entry_id
        entry.content_hash = content_hash
        
        new_entries_with_id.append(entry)
    
    # 步骤3: 检测新增
    new_ids = {e.entry_id for e in new_entries_with_id}
    old_ids = set(old_state.entries.keys())
    
    added_ids = new_ids - old_ids
    for entry_id in added_ids:
        entry = next(e for e in new_entries_with_id if e.entry_id == entry_id)
        changes["added"].append(entry)
    
    # 步骤4: 检测删除
    removed_ids = old_ids - new_ids
    for entry_id in removed_ids:
        old_entry = old_state.entries[entry_id]
        changes["removed"].append(old_entry)
    
    # 步骤5: 检测修改
    common_ids = old_ids & new_ids
    for entry_id in common_ids:
        old_entry = old_state.entries[entry_id]
        new_entry = next(e for e in new_entries_with_id if e.entry_id == entry_id)
        
        if old_entry.content_hash != new_entry.content_hash:
            # 内容哈希不同，判定为修改
            changes["modified"].append({
                "entry_id": entry_id,
                "old": old_entry,
                "new": new_entry,
                "diff": compute_entry_diff(old_entry, new_entry)
            })
        else:
            # 未变化
            changes["unchanged"].append(new_entry)
    
    return changes
```

#### 6.2.5 条目差异分析

```python
# 伪代码：条目差异分析

def compute_entry_diff(old_entry: WorldInfoEntry, new_entry: WorldInfoEntry) -> Dict:
    """
    计算条目差异
    
    分析：
    1. 名称是否变化
    2. 内容是否变化
    3. 属性是否变化
    4. 计算变化类型和程度
    
    参数:
        old_entry: 旧条目
        new_entry: 新条目
    
    返回:
        Dict: 差异详情
    """
    diff = {
        "name_changed": False,
        "content_changed": False,
        "properties_changed": {},
        "change_type": None,  # update, expansion, reduction, replacement
        "change_percentage": 0.0
    }
    
    # 检查名称
    if old_entry.name != new_entry.name:
        diff["name_changed"] = True
    
    # 检查内容
    if old_entry.content != new_entry.content:
        diff["content_changed"] = True
        
        # 计算变化程度
        similarity = compute_text_similarity(old_entry.content, new_entry.content)
        diff["change_percentage"] = 1.0 - similarity
    
    # 检查属性
    old_props = old_entry.properties or {}
    new_props = new_entry.properties or {}
    
    all_prop_keys = set(old_props.keys()) | set(new_props.keys())
    
    for key in all_prop_keys:
        old_val = old_props.get(key)
        new_val = new_props.get(key)
        
        if old_val != new_val:
            diff["properties_changed"][key] = {
                "old": old_val,
                "new": new_val
            }
    
    # 确定变化类型
    if diff["content_changed"]:
        if diff["change_percentage"] > 0.7:
            diff["change_type"] = "replacement"  # 大部分内容改变
        elif len(new_entry.content) > len(old_entry.content) * 1.5:
            diff["change_type"] = "expansion"  # 内容大幅增加
        elif len(new_entry.content) < len(old_entry.content) * 0.7:
            diff["change_type"] = "reduction"  # 内容大幅减少
        else:
            diff["change_type"] = "update"  # 正常更新
    
    return diff
```

### 6.3 Chat History变化检测

#### 6.3.1 对话状态表示

```python
# 对话状态数据结构

class ChatMessage:
    """对话消息"""
    
    message_id: str                    # 消息ID
    role: str                         # User或Assistant
    content: str                      # 消息内容
    content_hash: str                 # 内容哈希
    timestamp: Optional[datetime]     # 时间戳
    turn_number: int                   # 轮次编号
    session_id: str                   # 会话ID
    
    # 元数据
    speaker_mapping: Optional[str]    # 原始说话者标识（如"Haruki"）


class ChatHistoryState:
    """对话历史状态跟踪器"""
    
    def __init__(self):
        self.messages: List[ChatMessage] = []
        self.message_hashes: List[str] = []
        self.total_hash: str = None
        self.version: int = 0
```

#### 6.3.2 增量变化检测

```python
# 伪代码：Chat History增量变化检测

def detect_chat_changes(
    old_state: ChatHistoryState,
    new_content: str,
    session_id: str
) -> Dict:
    """
    检测Chat History的变化
    
    算法：
    1. 解析新对话
    2. 基于消息哈希的精确匹配
    3. 增量分析（新增、删除、修改）
    4. 分类变化类型
    
    参数:
        old_state: 旧的对话状态
        new_content: 新的对话内容
        session_id: 会话ID
    
    返回:
        Dict: 变化详情
    """
    # 步骤1: 解析新对话
    new_messages = parse_chat_messages(new_content, session_id)
    
    # 步骤2: 计算新消息的哈希
    new_hashes = [m.content_hash for m in new_messages]
    old_hashes = old_state.message_hashes if old_state else []
    
    # 步骤3: 基于哈希的快速检测
    if old_hashes == new_hashes:
        # 完全相同
        return {
            "type": "no_change",
            "message_count": len(new_messages)
        }
    
    # 步骤4: 增量分析
    # 找出第一个不同的位置
    diff_index = find_first_diff_index(old_hashes, new_hashes)
    
    if diff_index is None:
        return {
            "type": "no_change",
            "message_count": len(new_messages)
        }
    
    # 判断变化类型
    if len(new_hashes) > len(old_hashes):
        # 消息数量增加，可能是追加
        if old_hashes[:diff_index] == new_hashes[:diff_index]:
            # 前面部分相同，后面新增
            new_messages_count = len(new_hashes) - len(old_hashes)
            
            # 检查新增的尾部消息
            new_messages_tail = new_messages[len(old_hashes):]
            
            return {
                "type": "append",
                "diff_index": diff_index,
                "new_messages": new_messages_tail,
                "new_messages_count": new_messages_count
            }
    
    if len(new_hashes) < len(old_hashes):
        # 消息数量减少，可能是截断
        if new_hashes == old_hashes[:len(new_hashes)]:
            # 新内容是旧内容的前部分
            return {
                "type": "truncation",
                "removed_messages_count": len(old_hashes) - len(new_hashes)
            }
    
    # 复杂变化（修改或中间插入/删除）
    # 使用更详细的diff算法
    detailed_diff = compute_detailed_diff(old_state.messages, new_messages)
    
    return {
        "type": "modification",
        "details": detailed_diff
    }


def find_first_diff_index(list1, list2) -> Optional[int]:
    """
    找出两个列表第一个不同的索引
    """
    min_len = min(len(list1), len(list2))
    
    for i in range(min_len):
        if list1[i] != list2[i]:
            return i
    
    if len(list1) != len(list2):
        return min_len
    
    return None  # 完全相同


def compute_detailed_diff(old_messages, new_messages):
    """
    计算详细的差异
    
    使用文本diff算法（如Myers diff）
    """
    # 这里简化实现，实际应使用difflib或类似库
    diff = {
        "added": [],
        "removed": [],
        "modified": []
    }
    
    # 简单的逐条比较
    max_len = max(len(old_messages), len(new_messages))
    
    for i in range(max_len):
        old_msg = old_messages[i] if i < len(old_messages) else None
        new_msg = new_messages[i] if i < len(new_messages) else None
        
        if old_msg is None:
            diff["added"].append(new_msg)
        elif new_msg is None:
            diff["removed"].append(old_msg)
        elif old_msg.content_hash != new_msg.content_hash:
            diff["modified"].append({
                "index": i,
                "old": old_msg,
                "new": new_msg
            })
    
    return diff
```

### 6.4 Graphiti同步更新

#### 6.4.1 新增内容的处理

```python
# 伪代码：新增内容处理

async def process_added_entries(
    graphiti_service: GraphitiService,
    entries: List[WorldInfoEntry],
    session_id: str
) -> Dict[str, int]:
    """
    处理新增的世界书条目
    
    流程：
    1. 实体关系提取（调用Graphiti LLM）
    2. 去重检查（与现有实体比对）
    3. 创建/更新图谱节点
    4. 建立关系
    5. 更新状态跟踪器
    
    参数:
        graphiti_service: Graphiti服务实例
        entries: 新增条目列表
        session_id: 会话ID
    
    返回:
        Dict: 处理结果统计
    """
    stats = {
        "entries_processed": 0,
        "entities_created": 0,
        "entities_merged": 0,
        "relationships_created": 0
    }
    
    for entry in entries:
        try:
            # 步骤1: 提取实体和关系
            # 调用Graphiti的add_episode方法
            # Graphiti内部会使用配置的LLM提取实体关系
            result = await graphiti_service.graphiti.add_episode(
                name=generate_episode_name(entry),
                episode_body=entry.content,
                source=EpisodeType.text,
                source_description=f"world_info:{entry.entry_type}",
                reference_time=datetime.now(timezone.utc),
                group_id=session_id
            )
            
            # 步骤2: 统计
            stats["entries_processed"] += 1
            stats["entities_created"] += len(result.nodes)
            stats["relationships_created"] += len(result.edges)
            
        except Exception as e:
            print(f"Error processing added entry {entry.entry_id}: {e}")
    
    return stats


def generate_episode_name(entry: WorldInfoEntry) -> str:
    """
    生成Episode名称
    
    格式：World Info - [类型] [名称]
    """
    return f"World Info - {entry.entry_type} - {entry.name}"
```

#### 6.4.2 删除内容的处理

**重要**：Graphiti是双时序数据库，使用`valid_from`和`valid_until`而非物理删除

```python
# 伪代码：删除内容处理

async def process_removed_entries(
    graphiti_service: GraphitiService,
    entries: List[WorldInfoEntry],
    session_id: str
) -> Dict[str, int]:
    """
    处理删除的世界书条目
    
    策略：
    不物理删除，而是设置valid_until标记为过期
    
    流程：
    1. 查找相关Episode节点
    2. 设置valid_until为当前时间
    3. 更新状态为"deleted"
    4. 记录删除原因和时间
    
    参数:
        graphiti_service: Graphiti服务实例
        entries: 被删除条目列表
        session_id: 会话ID
    
    返回:
        Dict: 处理结果统计
    """
    stats = {
        "entries_processed": 0,
        "episodes_marked_deleted": 0
    }
    
    current_time = datetime.now(timezone.utc)
    
    for entry in entries:
        try:
            # 步骤1: 构建Cypher查询
            # 查找匹配的Episode节点
            query = """
            MATCH (e:Episode)
            WHERE e.name CONTAINS $entry_name
              AND e.source_description = $source_desc
              AND e.group_id = $session_id
              AND (e.valid_until IS NULL OR e.valid_until > $current_time)
            RETURN e
            """
            
            params = {
                "entry_name": entry.name,
                "source_desc": f"world_info:{entry.entry_type}",
                "session_id": session_id,
                "current_time": current_time.isoformat()
            }
            
            # 步骤2: 执行查询和更新
            # 这里简化，实际应使用Graphiti的Neo4j驱动
            with graphiti_service.graphiti.driver.session() as session:
                result = session.run(query, params)
                
                for record in result:
                    episode = record["e"]
                    
                    # 设置valid_until
                    update_query = """
                    MATCH (e:Episode)
                    WHERE elementId(e) = $episode_id
                    SET e.valid_until = $valid_until,
                        e.status = 'deleted',
                        e.deleted_at = $deleted_at,
                        e.deletion_reason = 'removed_by_user'
                    """
                    
                    session.run(update_query, {
                        "episode_id": element_id(episode),
                        "valid_until": current_time.isoformat(),
                        "deleted_at": current_time.isoformat()
                    })
                    
                    stats["episodes_marked_deleted"] += 1
            
            stats["entries_processed"] += 1
            
        except Exception as e:
            print(f"Error processing removed entry {entry.entry_id}: {e}")
    
    return stats
```

**为什么使用valid_until而不是status字段？**

虽然两者都可以表示删除状态，但结合使用更佳：

| 维度 | valid_until (valid_from/valid_until) | status字段 |
|------|--------------------------------------|-----------|
| **核心功能** | 定义事实的时间有效性 | 定义事实的逻辑状态 |
| **查询维度** | 时间维度查询 | 逻辑状态过滤 |
| **语义表达** | "何时为真" | "为何失效" |
| **优势** | 天然支持时间旅行查询 | 表达丰富的状态信息 |

**最佳实践**：**同时使用**

```text
删除表示例：
{
  "entity_id": "e123",
  "content": "未花是茶会成员",
  
  # 时间维度
  "valid_from": "2024-01-01T00:00:00",
  "valid_until": "2024-03-15T00:00:00",  # 被删除的时间
  
  # 逻辑状态
  "status": "deleted",
  "status_reason": "removed_by_user",
  "deleted_at": "2024-03-15T00:00:00"
}
```

#### 6.4.3 修改内容的处理

```python
# 伪代码：修改内容处理

async def process_modified_entries(
    graphiti_service: GraphitiService,
    modifications: List[Dict],
    session_id: str
) -> Dict[str, int]:
    """
    处理修改的世界书条目
    
    策略：
    不直接修改旧Episode，而是创建新版本Episode
    
    流程：
    1. 标记旧Episode为superseded（被替代）
    2. 创建新Episode
    3. 设置旧Episode的valid_until
    4. 建立新旧Episode的关系（REPLACED_BY）
    
    参数:
        graphiti_service: Graphiti服务实例
        modifications: 修改详情列表
        session_id: 会话ID
    
    返回:
        Dict: 处理结果统计
    """
    stats = {
        "entries_processed": 0,
        "old_episodes_superseded": 0,
        "new_episodes_created": 0
    }
    
    current_time = datetime.now(timezone.utc)
    
    for mod in modifications:
        old_entry = mod["old"]
        new_entry = mod["new"]
        
        try:
            # 步骤1: 查找并标记旧Episode
            query = """
            MATCH (e:Episode)
            WHERE e.name CONTAINS $entry_name
              AND e.source_description = $source_desc
              AND e.group_id = $session_id
              AND (e.valid_until IS NULL OR e.valid_until > $current_time)
            RETURN e
            """
            
            params = {
                "entry_name": old_entry.name,
                "source_desc": f"world_info:{old_entry.entry_type}",
                "session_id": session_id,
                "current_time": current_time.isoformat()
            }
            
            with graphiti_service.graphiti.driver.session() as session:
                result = session.run(query, params)
                
                for record in result:
                    old_episode = record["e"]
                    
                    # 标记为superseded
                    update_query = """
                    MATCH (e:Episode)
                    WHERE elementId(e) = $episode_id
                    SET e.valid_until = $valid_until,
                        e.status = 'superseded',
                        e.superseded_at = $superseded_at,
                        e.superseded_by = $new_episode_id
                    """
                    
                    session.run(update_query, {
                        "episode_id": element_id(old_episode),
                        "valid_until": current_time.isoformat(),
                        "superseded_at": current_time.isoformat(),
                        "new_episode_id": None  # 稍后填充
                    })
                    
                    stats["old_episodes_superseded"] += 1
            
            # 步骤2: 创建新Episode
            new_result = await graphiti_service.graphiti.add_episode(
                name=f"World Info - {new_entry.entry_type} - {new_entry.name} (v{old_entry.version + 1})",
                episode_body=new_entry.content,
                source=EpisodeType.text,
                source_description=f"world_info:{new_entry.entry_type}",
                reference_time=current_time,
                group_id=session_id
            )
            
            # 步骤3: 建立新旧关系（如果找到旧Episode）
            if stats["old_episodes_superseded"] > 0:
                # 建立REPLACED_BY关系
                replacement_query = """
                MATCH (old:Episode), (new:Episode)
                WHERE old.uuid = $old_uuid
                  AND new.uuid = $new_uuid
                CREATE (old)-[:REPLACED_BY {replaced_at: $replaced_at}]->(new)
                """
                
                # 这里简化，实际需要保存新Episode的uuid
                pass
            
            stats["entries_processed"] += 1
            stats["new_episodes_created"] += 1
            
        except Exception as e:
            print(f"Error processing modified entry {old_entry.entry_id}: {e}")
    
    return stats
```

### 6.5 集成到主流程

```python
# 集成变化检测到主API流程

@app.post("/v1/chat/completions")
async def chat_completions(request: Request, body: ChatCompletionRequest):
    """
    OpenAI兼容的Chat Completions端点
    集成变化检测
    """
    
    # 步骤1: 提取session_id
    session_id = _extract_session_id(request, body)
    
    # 步骤2: 提取最后一个user消息
    last_user_message = _extract_last_user_message(body.messages)
    
    # 步骤3: 解析SillyTavern格式
    parsed_content = parser_service.parse(last_user_message.content)
    
    # 步骤4: 变化检测（新增功能）
    if hasattr(app.state, 'world_info_state') and parsed_content.world_info:
        old_world_info_state = app.state.world_info_state.get(session_id)
        
        if old_world_info_state:
            # 检测World Info变化
            changes = detect_worldinfo_changes(
                old_state=old_world_info_state,
                new_content=parsed_content.world_info_content
            )
            
            # 同步更新Graphiti
            if changes["added"]:
                await process_added_entries(
                    graphiti_service,
                    changes["added"],
                    session_id
                )
            
            if changes["removed"]:
                await process_removed_entries(
                    graphiti_service,
                    changes["removed"],
                    session_id
                )
            
            if changes["modified"]:
                await process_modified_entries(
                    graphiti_service,
                    changes["modified"],
                    session_id
                )
            
            # 更新状态跟踪器
            new_world_info_state = update_world_info_state(
                old_world_info_state,
                changes
            )
            app.state.world_info_state[session_id] = new_world_info_state
    
    # 步骤5: 记忆处理（处理新增和修改的内容）
    await graphiti_service.process_content(
        session_id=session_id,
        parsed_content=parsed_content
    )
    
    # 步骤6: 记忆检索
    related_memories = await graphiti_service.search_memories(
        session_id=session_id,
        query=last_user_message.content,
        limit=10
    )
    
    # 步骤7-9: 上下文优化、LLM调用、响应处理
    # ...（保持原有逻辑）
```

---

## 7. 第二阶段：心理连贯性建模

### 7.1 问题分析

**背景**：
- AIRP的核心需求是"角色的心理连贯性"
- 角色的心理状态会随着对话发展而演化
- 需要跟踪情绪、特质、信念的变化
- 需要度量心理连贯性（一致性得分）

**目标**：
1. 定义心理状态实体网络
2. 实现心理状态演化跟踪
3. 计算心理连贯性度量指标
4. 集成到Graphiti和LLM处理流程

### 7.2 心理状态实体网络

#### 7.2.1 实体类型定义

```python
# 心理状态实体模型

class PsychologicalState(BaseModel):
    """心理状态实体"""
    
    # 核心属性
    entity_id: str
    entity_type: Literal["psychological_state"] = "psychological_state"
    character_id: str           # 所属角色ID
    
    # 情绪混合
    emotional_mix: List[EmotionalMix]
    dominant_emotion: Optional[str]  # 主导情绪
    
    # 特质表现
    trait_manifestations: Dict[str, TraitManifestation]
    
    # 状态指标
    stability_score: float       # 稳定性得分 0.0-1.0
    intensity_level: float       # 强度水平 0.0-1.0
    arousal_level: float         # 唤醒水平 0.0-1.0
    
    # 时间属性
    observed_at: datetime
    valid_from: datetime
    valid_until: Optional[datetime]
    
    # 来源
    source: SourceRef
    context: Dict[str, Any]


class EmotionalMix(BaseModel):
    """情绪混合"""
    
    emotion_type: str            # 情绪类型：joy, sadness, anger, fear, etc.
    intensity: float             # 强度 0.0-1.0
    duration: Optional[float]     # 持续时间（秒）
    triggers: List[str]          # 触发因素
    manifestations: List[str]    # 表现形式


class TraitManifestation(BaseModel):
    """特质表现"""
    
    trait_name: str              # 特质名称
    strength: float              # 强度 0.0-1.0
    consistency: float           # 一致性 0.0-1.0（跨时间）
    behavior_examples: List[str]  # 行为示例
    situational_context: str     # 情境
```

#### 7.2.2 心理状态网络结构

```
心理状态建模体系：

┌─────────────────────────────────────┐
│         Character (角色)            │
└──────────────────┬──────────────────┘
                   │ HAS_PSYCHOLOGICAL_STATE
                   ▼
┌─────────────────────────────────────┐
│    PsychologicalState (心理状态)     │
│  • emotional_mix                    │
│  • dominant_emotion                 │
│  • stability_score                 │
│  • last_updated                     │
└──────────────────┬──────────────────┘
                   │ COMPOSED_OF
          ┌────────┼────────┐
          ▼        ▼        ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   EmotionNode   │ │   TraitNode     │ │  BeliefNode     │
│ • emotion_type  │ │ • trait_name    │ │ • belief_content│
│ • intensity     │ │ • strength      │ │ • confidence    │
│ • duration      │ │ • consistency   │ │ • origin        │
│ • triggers      │ │ • manifestations│ │ • implications  │
└─────────────────┘ └─────────────────┘ └─────────────────┘
          │                   │                   │
          └───────────────────┼───────────────────┘
                              │ INFLUENCES
                              ▼
                 ┌─────────────────────────┐
                 │   BehavioralPattern     │
                 │ • pattern_type          │
                 │ • activation_conditions │
                 │ • typical_actions       │
                 │ • success_rate          │
                 └─────────────────────────┘
```

### 7.3 心理状态演化跟踪

#### 7.3.1 状态转移机制

```python
# 伪代码：心理状态转移跟踪

class PsychologicalStateTracker:
    """心理状态跟踪器"""
    
    def __init__(self, graphiti_service: GraphitiService):
        self.graphiti_service = graphiti_service
        self.state_history: Dict[str, List[PsychologicalState]] = {}
    
    async def track_state_transition(
        self,
        character_id: str,
        old_state: PsychologicalState,
        new_state: PsychologicalState,
        trigger_event: str
    ):
        """
        跟踪心理状态转移
        
        流程：
        1. 比较新旧状态差异
        2. 识别触发因素
        3. 计算转移合理性
        4. 存储状态快照和转移记录
        """
        
        # 步骤1: 计算状态差异
        diff = compute_state_diff(old_state, new_state)
        
        # 步骤2: 创建状态转移记录
        transition = PsychologicalStateTransition(
            character_id=character_id,
            from_state=old_state.entity_id,
            to_state=new_state.entity_id,
            transition_type=determine_transition_type(diff),
            trigger_event=trigger_event,
            transition_reason=analyze_transition_reason(diff),
            rationality_score=calculate_rationality_score(diff)
        )
        
        # 步骤3: 存储到Graphiti
        await self.store_transition(transition)
        
        # 步骤4: 更新历史
        if character_id not in self.state_history:
            self.state_history[character_id] = []
        self.state_history[character_id].append(new_state)
    
    def compute_state_diff(
        self,
        old_state: PsychologicalState,
        new_state: PsychologicalState
    ) -> StateDiff:
        """
        计算状态差异
        
        分析维度：
        1. 情绪混合变化
        2. 特质强度变化
        3. 稳定性变化
        """
        diff = StateDiff()
        
        # 情绪变化
        old_emotions = {e.emotion_type: e.intensity for e in old_state.emotional_mix}
        new_emotions = {e.emotion_type: e.intensity for e in new_state.emotional_mix}
        
        for emotion_type in set(old_emotions.keys()) | set(new_emotions.keys()):
            old_intensity = old_emotions.get(emotion_type, 0.0)
            new_intensity = new_emotions.get(emotion_type, 0.0)
            
            if old_intensity != new_intensity:
                diff.emotion_changes.append({
                    "emotion_type": emotion_type,
                    "from": old_intensity,
                    "to": new_intensity,
                    "delta": new_intensity - old_intensity
                })
        
        # 特质变化
        old_traits = old_state.trait_manifestations
        new_traits = new_state.trait_manifestations
        
        for trait_name in set(old_traits.keys()) | set(new_traits.keys()):
            old_manifestation = old_traits.get(trait_name)
            new_manifestation = new_traits.get(trait_name)
            
            if old_manifestation and new_manifestation:
                if old_manifestation.strength != new_manifestation.strength:
                    diff.trait_changes.append({
                        "trait_name": trait_name,
                        "from_strength": old_manifestation.strength,
                        "to_strength": new_manifestation.strength,
                        "delta": new_manifestation.strength - old_manifestation.strength
                    })
        
        # 稳定性变化
        diff.stability_change = new_state.stability_score - old_state.stability_score
        
        return diff
```

#### 7.3.2 LLM驱动的心理状态分析

```python
# 伪代码：LLM心理状态分析

async def analyze_psychological_state(
    graphiti_service: GraphitiService,
    character_id: str,
    dialog_text: str,
    context: Dict[str, Any]
) -> PsychologicalState:
    """
    使用LLM分析角色的心理状态
    
    流程：
    1. 构建分析提示词
    2. 调用Graphiti的LLM（DeepSeek）
    3. 解析返回的JSON
    4. 构建PsychologicalState对象
    
    参数:
        graphiti_service: Graphiti服务
        character_id: 角色ID
        dialog_text: 对话文本
        context: 上下文信息
    
    返回:
        PsychologicalState: 分析结果
    """
    
    # 构建提示词
    prompt = f"""
你是一个角色心理分析专家。请分析以下对话中角色的心理状态。

## 分析维度
1. **情绪混合**：当前角色的主要情绪类型和强度（0.0-1.0）
   可能的情绪类型：joy, sadness, anger, fear, surprise, disgust, anticipation, trust
   
2. **主导情绪**：当前最强烈、最主导的情绪
   
3. **特质表现**：表现出的性格特质及其强度（0.0-1.0）
   示例特质：optimistic, anxious, aggressive, gentle, stubborn, flexible
   
4. **状态指标**：
   - 稳定性得分（0.0-1.0）：情绪是否稳定
   - 强度水平（0.0-1.0）：整体情绪强度
   - 唤醒水平（0.0-1.0）：能量水平高低

## 角色信息
角色ID: {character_id}
上下文: {context.get('character_description', '未知')}

## 对话文本
{dialog_text}

## 输出要求（JSON格式）:
{{
  "emotional_mix": [
    {{
      "emotion_type": "joy",
      "intensity": 0.8,
      "duration": null,
      "triggers": ["收到礼物", "被夸奖"],
      "manifestations": ["微笑", "跳跃", "语调轻快"]
    }}
  ],
  "dominant_emotion": "joy",
  "trait_manifestations": {{
    "optimistic": {{
      "strength": 0.9,
      "consistency": 0.8,
      "behavior_examples": ["积极面对困难", "鼓励他人"],
      "situational_context": "大部分情况"
    }}
  }},
  "stability_score": 0.8,
  "intensity_level": 0.7,
  "arousal_level": 0.9,
  "analysis_confidence": 0.85
}}
"""
    
    # 调用LLM（通过Graphiti的LLM客户端）
    # 使用Strict模式确保JSON格式正确
    response = await graphiti_service.llm_client.chat.completions.create(
        model=graphiti_service.config.deepseek.model,
        messages=[
            {"role": "system", "content": "你是一个专业的角色心理分析专家。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,  # 较低温度确保稳定性
        response_format={"type": "json_object"}
    )
    
    # 解析JSON
    json_content = json.loads(response.choices[0].message.content)
    
    # 构建PsychologicalState对象
    psychological_state = PsychologicalState(
        entity_id=f"psych_state_{character_id}_{int(time.time())}",
        character_id=character_id,
        emotional_mix=[
            EmotionalMix(**em) for em in json_content["emotional_mix"]
        ],
        dominant_emotion=json_content["dominant_emotion"],
        trait_manifestations={
            trait_name: TraitManifestation(**trait)
            for trait_name, trait in json_content["trait_manifestations"].items()
        },
        stability_score=json_content["stability_score"],
        intensity_level=json_content["intensity_level"],
        arousal_level=json_content["arousal_level"],
        observed_at=datetime.now(timezone.utc),
        valid_from=datetime.now(timezone.utc),
        valid_until=None,
        source=SourceRef(
            source_type="llm_analysis",
            source_id=f"dialog_{int(time.time())}",
            confidence=json_content.get("analysis_confidence", 0.8)
        ),
        context=context
    )
    
    return psychological_state
```

### 7.4 心理连贯性度量

#### 7.4.1 连贯性指标定义

```python
# 伪代码：心理连贯性度量

class PsychologicalCoherenceEvaluator:
    """心理连贯性评估器"""
    
    def __init__(self, graphiti_service: GraphitiService):
        self.graphiti_service = graphiti_service
    
    async def evaluate_coherence(
        self,
        character_id: str,
        time_window: timedelta = timedelta(days=7)
    ) -> CoherenceScore:
        """
        评估角色的心理连贯性
        
        维度：
        1. 特质一致性得分
           - 跨时间特质表现的一致性
           - 跨情境特质表现的一致性
        
        2. 情绪演化合理性得分
           - 情绪变化的因果关系合理性
           - 情绪强度的合理性
        
        3. 行为模式一致性得分
           - 行为与特质的匹配度
           - 行为与情绪的匹配度
        
        4. 记忆影响合理性得分
           - 过往经历对当前影响的合理性
        
        返回: CoherenceScore
        """
        
        # 步骤1: 获取时间窗口内的所有心理状态
        states = await self.get_psychological_states(
            character_id=character_id,
            time_window=time_window
        )
        
        if len(states) < 2:
            return CoherenceScore(
                overall_score=1.0,  # 数据不足，默认满分
                trait_consistency=1.0,
                emotional_rationality=1.0,
                behavioral_consistency=1.0,
                memory_rationality=1.0
            )
        
        # 步骤2: 计算各维度得分
        trait_score = self.evaluate_trait_consistency(states)
        emotional_score = self.evaluate_emotional_rationality(states)
        behavioral_score = self.evaluate_behavioral_consistency(states)
        memory_score = await self.evaluate_memory_rationality(character_id, states)
        
        # 步骤3: 综合得分
        overall_score = (
            trait_score * 0.3 +
            emotional_score * 0.3 +
            behavioral_score * 0.2 +
            memory_score * 0.2
        )
        
        return CoherenceScore(
            overall_score=overall_score,
            trait_consistency=trait_score,
            emotional_rationality=emotional_score,
            behavioral_consistency=behavioral_score,
            memory_rationality=memory_score
        )
    
    def evaluate_trait_consistency(
        self,
        states: List[PsychologicalState]
    ) -> float:
        """
        评估特质一致性
        
        算法：
        1. 对每个特质，计算跨时间的强度方差
        2. 方差越小，一致性越高
        3. 考虑特质的基础稳定性（某些特质本就更稳定）
        """
        if not states:
            return 1.0
        
        # 收集所有特质
        all_traits = set()
        for state in states:
            all_traits.update(state.trait_manifestations.keys())
        
        trait_scores = []
        
        for trait_name in all_traits:
            strengths = []
            for state in states:
                if trait_name in state.trait_manifestations:
                    strengths.append(
                        state.trait_manifestations[trait_name].strength
                    )
            
            if len(strengths) > 1:
                # 计算方差
                mean = sum(strengths) / len(strengths)
                variance = sum((s - mean) ** 2 for s in strengths) / len(strengths)
                
                # 标准差越小，一致性越高
                consistency = max(0.0, 1.0 - variance * 2)  # 转换为0-1分数
                trait_scores.append(consistency)
        
        # 平均所有特质的一致性
        if trait_scores:
            return sum(trait_scores) / len(trait_scores)
        else:
            return 1.0
    
    def evaluate_emotional_rationality(
        self,
        states: List[PsychologicalState]
    ) -> float:
        """
        评估情绪演化合理性
        
        算法：
        1. 检测情绪变化的幅度
        2. 检测情绪变化的频率
        3. 验证变化是否有合理触发因素
        """
        if len(states) < 2:
            return 1.0
        
        rationality_scores = []
        
        for i in range(1, len(states)):
            old_state = states[i - 1]
            new_state = states[i]
            
            # 计算情绪变化幅度
            old_emotions = {e.emotion_type: e.intensity for e in old_state.emotional_mix}
            new_emotions = {e.emotion_type: e.intensity for e in new_state.emotional_mix}
            
            all_emotion_types = set(old_emotions.keys()) | set(new_emotions.keys())
            
            max_change = 0.0
            for emotion_type in all_emotion_types:
                old_intensity = old_emotions.get(emotion_type, 0.0)
                new_intensity = new_emotions.get(emotion_type, 0.0)
                change = abs(new_intensity - old_intensity)
                max_change = max(max_change, change)
            
            # 变化幅度越大，合理性越低（除非有强烈触发）
            # 这里简化，实际应考虑触发因素
            if max_change < 0.3:
                rationality = 1.0
            elif max_change < 0.6:
                rationality = 0.7
            else:
                rationality = 0.4
            
            rationality_scores.append(rationality)
        
        return sum(rationality_scores) / len(rationality_scores) if rationality_scores else 1.0
```

### 7.5 集成到主流程

```python
# 集成心理状态分析到主流程

@app.post("/v1/chat/completions")
async def chat_completions(request: Request, body: ChatCompletionRequest):
    # ... (前面的步骤1-5保持不变)
    
    # 步骤5: 记忆处理
    process_result = await graphiti_service.process_content(
        session_id=session_id,
        parsed_content=parsed_content
    )
    
    # 新增：步骤5.5: 心理状态分析
    if parsed_content.chat_history:
        # 识别主要角色（从对话历史中）
        character_id = identify_main_character(parsed_content.chat_history)
        
        if character_id:
            # 提取最近的对话
            recent_dialog = parsed_content.chat_history[-5:]  # 最近5轮
            
            # 构建对话文本
            dialog_text = "\n".join([
                f"{msg.role}: {msg.content}" 
                for msg in recent_dialog
            ])
            
            # 分析心理状态
            new_state = await analyze_psychological_state(
                graphiti_service=graphiti_service,
                character_id=character_id,
                dialog_text=dialog_text,
                context={
                    "session_id": session_id,
                    "character_description": get_character_description(character_id)
                }
            )
            
            # 获取旧状态（如果存在）
            old_state = await get_last_psychological_state(
                graphiti_service,
                character_id
            )
            
            # 跟踪状态转移
            if old_state:
                await track_state_transition(
                    character_id=character_id,
                    old_state=old_state,
                    new_state=new_state,
                    trigger_event="dialog_interaction"
                )
            
            # 存储新状态
            await store_psychological_state(new_state)
    
    # ... (继续步骤6-9)
```

---

## 8. 第三阶段：因果逻辑链建模

### 8.1 问题分析

**背景**：
- AIRP需要"世界观与复杂事件的逻辑推演"
- 需要支持因果关系建模
- 需要支持事件推演
- 需要支持反事实推理

**目标**：
1. 定义因果逻辑链数据结构
2. 实现因果关系提取
3. 实现事件推演机制
4. 集成到Graphiti和检索流程

### 8.2 因果链数据结构

#### 8.2.1 基础关系类型

使用第1章设计的属性化关系模型：

```text
基础关系类型：HAS_CAUSAL_LINK

属性标签：
- relation_subtype: "causes", "contributes_to", "prevents", "enables", "requires"
- causal_strength: 0.0-1.0（因果强度）
- temporal_proximity: 时间接近度
- necessity_score: 必要性得分
- sufficiency_score: 充分性得分
- evidence_level: 证据级别
- conditions: 前提条件列表
- exceptions: 例外情况
```

#### 8.2.2 事件实体

```python
# 事件实体模型

class EventEntity(BaseModel):
    """事件实体"""
    
    # 核心属性
    entity_id: str
    entity_type: Literal["event"] = "event"
    name: str
    event_type: str                 # 事件类型：action, incident, outcome, etc.
    description: str
    
    # 参与者
    participants: List[str]        # 参与角色ID列表
    location: Optional[str]         # 地点ID
    
    # 时间属性
    start_time: datetime
    end_time: Optional[datetime]
    duration: Optional[float]      # 持续时间（秒）
    
    # 因果关系
    causes: List[str]              # 导致此事件的事件ID列表
    effects: List[str]             # 此事件导致的事件ID列表
    contributes_to: List[str]       # 此事件促成的目标/事件ID列表
    
    # 重要性
    significance: str                # 重要性：critical, major, minor, trivial
    impact_scope: str              # 影响范围
    
    # 状态
    status: str                     # 状态：planned, ongoing, completed, failed, cancelled
    outcome: Optional[str]         # 结果
    
    # 时间属性（Graphiti）
    valid_from: datetime
    valid_until: Optional[datetime]
```

### 8.3 因果关系提取

#### 8.3.1 LLM驱动的因果分析

```python
# 伪代码：LLM因果分析

async def extract_causal_relations(
    graphiti_service: GraphitiService,
    text: str,
    context: Dict[str, Any]
) -> List[CausalRelation]:
    """
    使用LLM提取因果关系
    
    流程：
    1. 构建分析提示词
    2. 调用Graphiti的LLM
    3. 解析返回的因果关系
    4. 构建CausalRelation对象
    
    参数:
        graphiti_service: Graphiti服务
        text: 文本内容
        context: 上下文
    
    返回:
        List[CausalRelation]: 因果关系列表
    """
    
    prompt = f"""
你是一个因果关系分析专家。请分析以下文本中的因果关系。

## 分析任务
1. 识别所有事件（动作、发生的事情、结果等）
2. 识别事件之间的因果关系
3. 评估因果关系的强度和类型
4. 识别必要条件和例外情况

## 输入文本
{text}

## 上下文信息
角色: {context.get('characters', '未知')}
地点: {context.get('location', '未知')}
时间: {context.get('time', '未知')}

## 因果关系类型
- causes: 直接导致（强因果）
- contributes_to: 促成/间接导致（弱因果）
- prevents: 阻止
- enables: 使能/提供条件
- requires: 需要/依赖

## 输出要求（JSON格式）:
{{
  "events": [
    {{
      "event_name": "事件描述",
      "event_type": "action/incident/outcome",
      "participants": ["角色1", "角色2"],
      "location": "地点",
      "time": "时间"
    }}
  ],
  "causal_relations": [
    {{
      "cause_event": "原因事件描述",
      "effect_event": "结果事件描述",
      "relation_type": "causes/contributes_to/prevents/enables/requires",
      "causal_strength": 0.9,  // 0.0-1.0
      "necessity_score": 0.8,  // 0.0-1.0
      "sufficiency_score": 0.7,  // 0.0-1.0
      "conditions": ["必要条件1", "必要条件2"],
      "exceptions": ["例外情况"],
      "evidence": "证据或理由",
      "confidence": 0.85
    }}
  ]
}}
"""
    
    # 调用LLM
    response = await graphiti_service.llm_client.chat.completions.create(
        model=graphiti_service.config.deepseek.model,
        messages=[
            {"role": "system", "content": "你是一个专业的因果关系分析专家。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        response_format={"type": "json_object"}
    )
    
    # 解析JSON
    json_content = json.loads(response.choices[0].message.content)
    
    # 构建CausalRelation对象列表
    causal_relations = []
    for rel_data in json_content["causal_relations"]:
        causal_relation = CausalRelation(
            cause_event_id=None,  # 稍后填充
            effect_event_id=None,  # 稍后填充
            relation_type=rel_data["relation_type"],
            causal_strength=rel_data["causal_strength"],
            temporal_proximity=None,  # 根据时间计算
            necessity_score=rel_data["necessity_score"],
            sufficiency_score=rel_data["sufficiency_score"],
            evidence_level=rel_data["confidence"],
            conditions=rel_data.get("conditions", []),
            exceptions=rel_data.get("exceptions", []),
            evidence=rel_data.get("evidence", "")
        )
        causal_relations.append(causal_relation)
    
    return causal_relations
```

#### 8.3.2 存储因果关系到Graphiti

```python
# 伪代码：存储因果关系到Graphiti

async def store_causal_chain(
    graphiti_service: GraphitiService,
    events: List[EventEntity],
    causal_relations: List[CausalRelation],
    session_id: str
):
    """
    存储因果链到Graphiti
    
    流程：
    1. 创建事件节点
    2. 创建因果关系边
    3. 设置时间属性
    
    参数:
        graphiti_service: Graphiti服务
        events: 事件列表
        causal_relations: 因果关系列表
        session_id: 会话ID
    """
    
    # 步骤1: 创建事件节点
    event_id_map = {}  # 事件描述 -> event_id
    
    for event in events:
        # 调用Graphiti创建Episode（事件）
        result = await graphiti_service.graphiti.add_episode(
            name=event.name,
            episode_body=event.description,
            source=EpisodeType.text,
            source_description=f"event:{event.event_type}",
            reference_time=event.start_time,
            group_id=session_id
        )
        
        # 保存事件ID
        event_id_map[event.name] = result.uuid
    
    # 步骤2: 创建因果关系边
    for rel in causal_relations:
        cause_event_id = event_id_map.get(rel.cause_event)
        effect_event_id = event_id_map.get(rel.effect_event)
        
        if cause_event_id and effect_event_id:
            # 创建HAS_CAUSAL_LINK关系
            await create_causal_relation_edge(
                graphiti_service=graphiti_service,
                from_id=cause_event_id,
                to_id=effect_event_id,
                causal_relation=rel,
                session_id=session_id
            )


async def create_causal_relation_edge(
    graphiti_service: GraphitiService,
    from_id: str,
    to_id: str,
    causal_relation: CausalRelation,
    session_id: str
):
    """
    创建因果关系边（直接使用Neo4j）
    """
    
    query = """
    MATCH (from:Episode), (to:Episode)
    WHERE from.uuid = $from_id
      AND to.uuid = $to_id
    CREATE (from)-[r:HAS_CAUSAL_LINK {
        relation_subtype: $relation_type,
        causal_strength: $causal_strength,
        temporal_proximity: $temporal_proximity,
        necessity_score: $necessity_score,
        sufficiency_score: $sufficiency_score,
        evidence_level: $evidence_level,
        conditions: $conditions,
        exceptions: $exceptions,
        evidence: $evidence,
        created_at: $created_at,
        group_id: $group_id
      }]->(to)
    RETURN r
    """
    
    with graphiti_service.graphiti.driver.session() as session:
        session.run(query, {
            "from_id": from_id,
            "to_id": to_id,
            "relation_type": causal_relation.relation_type,
            "causal_strength": causal_relation.causal_strength,
            "temporal_proximity": causal_relation.temporal_proximity,
            "necessity_score": causal_relation.necessity_score,
            "sufficiency_score": causal_relation.sufficiency_score,
            "evidence_level": causal_relation.evidence_level,
            "conditions": causal_relation.conditions,
            "exceptions": causal_relation.exceptions,
            "evidence": causal_relation.evidence,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "group_id": session_id
        })
```

### 8.4 事件推演机制

#### 8.4.1 因果链遍历

```python
# 伪代码：因果链遍历和推演

class CausalReasoningEngine:
    """因果推理引擎"""
    
    def __init__(self, graphiti_service: GraphitiService):
        self.graphiti_service = graphiti_service
    
    async def trace_causal_chain(
        self,
        start_event_id: str,
        direction: str = "forward",
        max_depth: int = 5,
        min_strength: float = 0.5
    ) -> CausalChain:
        """
        追踪因果链
        
        参数:
            start_event_id: 起始事件ID
            direction: "forward"（向前追踪后果）或"backward"（向后追溯原因）
            max_depth: 最大深度
            min_strength: 最小因果强度阈值
        
        返回:
            CausalChain: 因果链
        """
        
        if direction == "forward":
            query = """
            MATCH path = (start:Episode)-[:HAS_CAUSAL_LINK*1..{max_depth}]->(end:Episode)
            WHERE elementId(start) = $start_event_id
              AND all(r IN relationships(path) WHERE r.causal_strength >= $min_strength)
            RETURN path
            """
        else:  # backward
            query = """
            MATCH path = (end:Episode)<-[:HAS_CAUSAL_LINK*1..{max_depth}]-(start:Episode)
            WHERE elementId(start) = $start_event_id
              AND all(r IN relationships(path) WHERE r.causal_strength >= $min_strength)
            RETURN path
            """
        
        with self.graphiti_service.graphiti.driver.session() as session:
            result = session.run(query, {
                "start_event_id": start_event_id,
                "max_depth": max_depth,
                "min_strength": min_strength
            })
            
            causal_chain = CausalChain()
            
            for record in result:
                path = record["path"]
                
                # 提取事件和关系
                events = []
                relations = []
                
                for node in path.nodes:
                    events.append({
                        "id": node.element_id,
                        "name": node["name"],
                        "description": node["episode_body"]
                    })
                
                for rel in path.relationships:
                    relations.append({
                        "type": rel["relation_subtype"],
                        "strength": rel["caausal_strength"],
                        "from": rel.start_node.element_id,
                        "to": rel.end_node.element_id
                    })
                
                causal_chain.add_path(events, relations)
            
            return causal_chain
    
    async def deduce_consequences(
        self,
        current_event: str,
        scenario_conditions: Dict[str, Any]
    ) -> List[Consequence]:
        """
        推演事件后果
        
        算法：
        1. 追踪因果链
        2. 检查前提条件是否满足
        3. 评估可能性
        4. 返回可能的后果
        
        参数:
            current_event: 当前事件描述
            scenario_conditions: 场景条件
        
        返回:
            List[Consequence]: 可能的后果列表
        """
        
        # 步骤1: 查找匹配的事件节点
        query = """
        MATCH (e:Episode)
        WHERE e.name CONTAINS $event_name
          AND (e.valid_until IS NULL OR e.valid_until > $current_time)
        RETURN e
        ORDER BY e.created_at DESC
        LIMIT 1
        """
        
        with self.graphiti_service.graphiti.driver.session() as session:
            result = session.run(query, {
                "event_name": current_event,
                "current_time": datetime.now(timezone.utc).isoformat()
            })
            
            record = result.single()
            if not record:
                return []
            
            event_id = record["e"].element_id
        
        # 步骤2: 追踪因果链（向前）
        causal_chain = await self.trace_causal_chain(
            start_event_id=event_id,
            direction="forward",
            max_depth=3,
            min_strength=0.6
        )
        
        # 步骤3: 评估每个后果的可能性
        consequences = []
        
        for path in causal_chain.paths:
            final_event = path["events"][-1]
            final_relation = path["relations"][-1]
            
            # 检查条件
            conditions_met = self.check_conditions(
                final_relation.get("conditions", []),
                scenario_conditions
            )
            
            # 检查例外
            exceptions_applied = self.check_exceptions(
                final_relation.get("exceptions", []),
                scenario_conditions
            )
            
            # 计算可能性
            base_probability = final_relation["strength"]
            
            if not conditions_met:
                base_probability *= 0.3  # 条件不满足，可能性大幅降低
            
            if exceptions_applied:
                base_probability *= 0.1  # 有例外，可能性极低
            
            consequences.append(Consequence(
                event_id=final_event["id"],
                event_description=final_event["description"],
                probability=base_probability,
                steps=len(path["events"]) - 1,
                conditions_needed=final_relation.get("conditions", []),
                exceptions=final_relation.get("exceptions", [])
            ))
        
        # 按概率排序
        consequences.sort(key=lambda c: c.probability, reverse=True)
        
        return consequences
```

---

## 9. 第四阶段：并发处理与去重

### 9.1 并发处理队列

#### 9.1.1 问题分析

**当前问题**：
- 世界书解析中，条目按固定类型分配线程（"工作线程1：处理地点条目"）
- 导致负载不均，某些线程先完成退出，其他线程还在处理
- 无法充分利用CPU资源

**解决方案**：
- 使用通用工作线程池
- 动态任务分配
- 任务队列管理

#### 9.1.2 并发处理架构

```
┌─────────────────────────────────────┐
│         任务分发器 (Dispatcher)     │
│ • 接收所有待处理条目                │
│ • 维护任务队列                      │
│ • 监控线程状态                      │
└──────────────┬──────────────────────┘
               │
    ┌──────────┼──────────┐
    ▼          ▼          ▼
┌─────────┐┌─────────┐┌─────────┐
│工作线程1 ││工作线程2 ││工作线程N │
│通用处理器││通用处理器││通用处理器│
│任何条目  ││任何条目  ││任何条目  │
└─────────┘└─────────┘└─────────┘
    │          │          │
    └──────────┼──────────┘
               ▼
┌─────────────────────────────────────┐
│         结果收集器 (Collector)      │
│ • 接收所有处理结果                  │
│ • 合并和排序                        │
│ • 处理冲突                          │
└─────────────────────────────────────┘
```

#### 9.1.3 并发处理实现

```python
# 伪代码：并发处理队列

from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
import threading

class ConcurrentWorldInfoProcessor:
    """并发世界书处理器"""
    
    def __init__(self, max_workers=4):
        self.max_workers = max_workers
        self.entry_queue = Queue()
        self.result_queue = Queue()
        self.lock = threading.Lock()
    
    async def process_world_info_concurrent(
        self,
        text: str,
        session_id: str
    ) -> List[ProcessResult]:
        """
        并发处理世界书
        
        流程：
        1. 分条分割
        2. 加入任务队列
        3. 启动工作线程
        4. 收集结果
        5. 合并和去重
        
        参数:
            text: 世界书文本
            session_id: 会话ID
        
        返回:
            List[ProcessResult]: 处理结果列表
        """
        
        # 步骤1: 分条
        entries = self.segment_entries(text)
        
        # 步骤2: 创建任务
        tasks = [
            ProcessingTask(
                entry=entry,
                entry_id=compute_entry_id(entry),
                session_id=session_id
            )
            for entry in entries
        ]
        
        # 步骤3: 使用线程池并发处理
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_task = {
                executor.submit(self.process_entry, task): task
                for task in tasks
            }
            
            # 收集结果
            results = []
            for future in as_completed(future_to_task):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"Error processing entry: {e}")
        
        # 步骤4: 合并和去重
        merged_results = self.merge_results(results)
        
        return merged_results
    
    def segment_entries(self, text: str) -> List[WorldInfoEntry]:
        """
        分条分割世界书
        
        算法：
        1. 基于空行分割
        2. 基于条目模式识别
        3. 构建条目对象
        """
        entries = []
        lines = text.strip().split('\n')
        current_entry_lines = []
        
        for line in lines:
            if line.strip() == '':
                if current_entry_lines:
                    entry_text = '\n'.join(current_entry_lines).strip()
                    entry = self.parse_entry(entry_text)
                    if entry:
                        entries.append(entry)
                    current_entry_lines = []
            else:
                current_entry_lines.append(line)
        
        # 处理最后一个条目
        if current_entry_lines:
            entry_text = '\n'.join(current_entry_lines).strip()
            entry = self.parse_entry(entry_text)
            if entry:
                entries.append(entry)
        
        return entries
    
    def parse_entry(self, text: str) -> Optional[WorldInfoEntry]:
        """
        解析单个条目
        
        检测条目类型：
        - 地点("地点名")["描述"]
        - 角色("角色名")["描述"]
        - 概念("概念名")["描述"]
        - Character_Profile_of: 角色名
        """
        # 检测地点
        location_match = re.match(r'地点\("([^"]+)"\)', text)
        if location_match:
            return WorldInfoEntry(
                entry_type="location",
                name=location_match.group(1),
                content=text,
                properties=self.extract_properties(text)
            )
        
        # 检测角色
        character_match = re.match(r'角色\("([^"]+)"\)', text)
        if character_match:
            return WorldInfoEntry(
                entry_type="character",
                name=character_match.group(1),
                content=text,
                properties=self.extract_properties(text)
            )
        
        # 检测Character_Profile_of
        profile_match = re.match(r'Character_Profile_of:\s*([^\n]+)', text)
        if profile_match:
            return WorldInfoEntry(
                entry_type="character",
                name=profile_match.group(1).strip(),
                content=text,
                properties=self.extract_properties(text)
            )
        
        # 默认：通用条目
        return WorldInfoEntry(
            entry_type="general",
            name=text.split('\n')[0][:50],  # 使用第一行前50字符作为名称
            content=text,
            properties={}
        )
    
    def extract_properties(self, text: str) -> Dict[str, Any]:
        """
        提取条目属性
        
        算法：
        1. 识别属性对（key: value格式）
        2. 识别方括号属性["value"]
        3. 提取元数据
        """
        properties = {}
        
        # 提取方括号属性
        bracket_matches = re.findall(r'\["([^"]+)"\]', text)
        for i, match in enumerate(bracket_matches):
            if i == 0:
                properties["primary_description"] = match
            else:
                properties[f"attribute_{i}"] = match
        
        # 提取key: value属性
        kv_matches = re.findall(r'([^\s:]+):\s*([^\n]+)', text)
        for key, value in kv_matches:
            properties[key.strip()] = value.strip()
        
        return properties
    
    def process_entry(self, task: ProcessingTask) -> ProcessResult:
        """
        处理单个条目（通用处理器）
        
        参数:
            task: 处理任务
        
        返回:
            ProcessResult: 处理结果
        """
        # 根据条目类型选择处理策略
        if task.entry.entry_type == "location":
            processor = LocationEntryProcessor()
        elif task.entry.entry_type == "character":
            processor = CharacterEntryProcessor()
        else:
            processor = GenericEntryProcessor()
        
        result = processor.process(task.entry)
        
        return ProcessResult(
            entry_id=task.entry_id,
            result_type=result.result_type,
            data=result.data,
            success=result.success,
            error=result.error
        )
    
    def merge_results(
        self,
        results: List[ProcessResult]
    ) -> List[ProcessResult]:
        """
        合并结果并去重
        
        算法：
        1. 基于entry_id去重
        2. 合并相同条目的数据
        3. 解决冲突
        """
        merged = {}
        
        for result in results:
            if result.entry_id not in merged:
                merged[result.entry_id] = result
            else:
                # 合并数据
                existing = merged[result.entry_id]
                merged[result.entry_id] = self.merge_two_results(existing, result)
        
        return list(merged.values())
    
    def merge_two_results(
        self,
        r1: ProcessResult,
        r2: ProcessResult
    ) -> ProcessResult:
        """
        合并两个结果
        """
        # 保留成功的，合并数据
        if r1.success and r2.success:
            # 两个都成功，合并数据
            merged_data = {**r1.data, **r2.data}
            
            return ProcessResult(
                entry_id=r1.entry_id,
                result_type=r1.result_type,
                data=merged_data,
                success=True,
                error=None
            )
        elif r1.success:
            return r1
        else:
            return r2


# 处理器基类和具体实现

class EntryProcessor(ABC):
    """条目处理器基类"""
    
    @abstractmethod
    def process(self, entry: WorldInfoEntry) -> ProcessResult:
        pass


class LocationEntryProcessor(EntryProcessor):
    """地点条目处理器"""
    
    def process(self, entry: WorldInfoEntry) -> ProcessResult:
        # 提取地点信息
        location_info = self.extract_location_info(entry)
        
        return ProcessResult(
            entry_id=entry.entry_id,
            result_type="location",
            data=location_info,
            success=True,
            error=None
        )
    
    def extract_location_info(self, entry: WorldInfoEntry) -> Dict:
        # 使用LLM或规则提取地点属性
        # 这里简化为规则提取
        return {
            "name": entry.name,
            "type": "location",
            "properties": entry.properties,
            "content": entry.content
        }


class CharacterEntryProcessor(EntryProcessor):
    """角色条目处理器"""
    
    def process(self, entry: WorldInfoEntry) -> ProcessResult:
        # 提取角色信息
        character_info = self.extract_character_info(entry)
        
        return ProcessResult(
            entry_id=entry.entry_id,
            result_type="character",
            data=character_info,
            success=True,
            error=None
        )
    
    def extract_character_info(self, entry: WorldInfoEntry) -> Dict:
        return {
            "name": entry.name,
            "type": "character",
            "properties": entry.properties,
            "content": entry.content
        }


class GenericEntryProcessor(EntryProcessor):
    """通用条目处理器"""
    
    def process(self, entry: WorldInfoEntry) -> ProcessResult:
        return ProcessResult(
            entry_id=entry.entry_id,
            result_type="general",
            data={
                "name": entry.name,
                "content": entry.content,
                "properties": entry.properties
            },
            success=True,
            error=None
        )
```

### 9.2 多层次去重策略

#### 9.2.1 基于哈希的快速去重

```python
# 伪代码：哈希去重

class ContentDeduplicator:
    """内容去重器"""
    
    def __init__(self):
        self.content_hashes = {
            "exact": {},      # 完整哈希 -> entry_id
            "structural": {}, # 结构哈希 -> entry_id
            "semantic": {}   # 语义哈希 -> entry_id
        }
    
    def compute_content_hashes(self, content: str) -> Dict[str, str]:
        """
        计算内容的多级哈希
        
        返回:
            Dict: {
                "exact": MD5哈希,
                "structural": 结构哈希,
                "semantic": 语义哈希（可选）
            }
        """
        import hashlib
        
        # 精确哈希
        normalized = normalize_content(content)
        exact_hash = hashlib.md5(normalized.encode('utf-8')).hexdigest()
        
        # 结构哈希（去除具体内容，保留结构）
        structural = extract_structural_fingerprint(content)
        structural_hash = hashlib.md5(structural.encode('utf-8')).hexdigest()
        
        # 语义哈希（可选，如果启用LLM）
        semantic_hash = None
        # semantic_hash = compute_semantic_hash(content)  # 需要LLM
        
        return {
            "exact": exact_hash,
            "structural": structural_hash,
            "semantic": semantic_hash
        }
    
    def check_duplicate(
        self,
        content: str
    ) -> Tuple[bool, float, Optional[str]]:
        """
        检查是否重复
        
        参数:
            content: 内容文本
        
        返回:
            Tuple: (is_duplicate, confidence, duplicate_entry_id)
        """
        hashes = self.compute_content_hashes(content)
        
        # 第一级：精确匹配
        if hashes["exact"] in self.content_hashes["exact"]:
            return (True, 1.0, self.content_hashes["exact"][hashes["exact"]])
        
        # 第二级：结构匹配
        if hashes["structural"] in self.content_hashes["structural"]:
            return (True, 0.7, self.content_hashes["structural"][hashes["structural"]])
        
        # 第三级：语义匹配（可选）
        if hashes["semantic"] and hashes["semantic"] in self.content_hashes["semantic"]:
            # 需要计算语义相似度
            similarity = compute_semantic_similarity(hashes["semantic"])
            if similarity > 0.9:
                return (True, similarity, self.content_hashes["semantic"][hashes["semantic"]])
        
        return (False, 0.0, None)
    
    def add_content(self, entry_id: str, content: str):
        """
        添加内容到去重数据库
        """
        hashes = self.compute_content_hashes(content)
        
        self.content_hashes["exact"][hashes["exact"]] = entry_id
        self.content_hashes["structural"][hashes["structural"]] = entry_id
        
        if hashes["semantic"]:
            self.content_hashes["semantic"][hashes["semantic"]] = entry_id


def extract_structural_fingerprint(content: str) -> str:
    """
    提取结构指纹
    
    算法：
    1. 移除具体内容
    2. 保留结构特征（段落、列表、标题）
    3. 标准化
    """
    lines = content.split('\n')
    structural_lines = []
    
    for line in lines:
        # 识别结构标记
        if re.match(r'^#{1,6}\s', line):  # Markdown标题
            structural_lines.append('#' * len(re.match(r'^#+', line).group()))
        elif re.match(r'^\s*[-*+]\s', line):  # 列表项
            structural_lines.append('-')
        elif line.strip() == '':  # 空行
            structural_lines.append('')
        else:
            structural_lines.append('text')  # 普通文本
    
    return '\n'.join(structural_lines)


def compute_semantic_similarity(hash1: str, hash2: str) -> float:
    """
    计算语义相似度
    
    这里简化，实际应使用向量相似度
    """
    # 简化的Jaccard相似度
    set1 = set(hash1)
    set2 = set(hash2)
    
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    
    return intersection / union if union > 0 else 0.0
```

#### 9.2.2 实体级别去重

```python
# 伪代码：实体去重

class EntityDeduplicator:
    """实体去重器"""
    
    async def deduplicate_entities(
        self,
        new_entities: List[Entity],
        existing_entities: Dict[str, Entity],
        graphiti_service: GraphitiService
    ) -> Tuple[List[Entity], List[EntityOperation]]:
        """
        去重实体
        
        流程：
        1. 名称标准化
        2. 相似度计算
        3. 合并决策
        4. 执行操作
        
        返回:
            Tuple: (去重后的实体列表, 操作列表)
        """
        operations = []
        deduplicated = []
        
        for new_entity in new_entities:
            # 步骤1: 标准化名称
            normalized_name = normalize_name(new_entity.name)
            
            # 步骤2: 查找相似实体
            similar_entities = []
            for entity_id, existing_entity in existing_entities.items():
                if normalize_name(existing_entity.name) == normalized_name:
                    # 名称相同，进一步检查
                    similarity = self.compute_entity_similarity(new_entity, existing_entity)
                    similar_entities.append({
                        "entity": existing_entity,
                        "entity_id": entity_id,
                        "similarity": similarity
                    })
            
            # 步骤3: 合并决策
            if not similar_entities:
                # 没有相似实体，创建新实体
                deduplicated.append(new_entity)
                operations.append(EntityOperation(
                    type="create",
                    entity=new_entity
                ))
            else:
                # 找到相似实体
                best_match = max(similar_entities, key=lambda x: x["similarity"])
                
                if best_match["similarity"] > 0.9:
                    # 高相似度，合并
                    merged_entity = self.merge_entities(
                        best_match["entity"],
                        new_entity
                    )
                    
                    # 操作：更新
                    operations.append(EntityOperation(
                        type="update",
                        entity_id=best_match["entity_id"],
                        old_entity=best_match["entity"],
                        new_entity=merged_entity
                    ))
                elif best_match["similarity"] > 0.7:
                    # 中等相似度，创建关联关系
                    operations.append(EntityOperation(
                        type="relate",
                        entity_id=best_match["entity_id"],
                        new_entity=new_entity,
                        relation_type="SIMILAR_TO",
                        confidence=best_match["similarity"]
                    ))
                    
                    # 仍然创建新实体
                    deduplicated.append(new_entity)
                    operations.append(EntityOperation(
                        type="create",
                        entity=new_entity
                    ))
                else:
                    # 低相似度，创建新实体
                    deduplicated.append(new_entity)
                    operations.append(EntityOperation(
                        type="create",
                        entity=new_entity
                    ))
        
        return deduplicated, operations
    
    def compute_entity_similarity(
        self,
        entity1: Entity,
        entity2: Entity
    ) -> float:
        """
        计算实体相似度
        
        维度：
        1. 名称相似度（0.4）
        2. 类型相似度（0.2）
        3. 属性相似度（0.3）
        4. 描述相似度（0.1）
        """
        # 名称相似度
        name_sim = compute_text_similarity(entity1.name, entity2.name)
        
        # 类型相似度
        type_sim = 1.0 if entity1.entity_type == entity2.entity_type else 0.0
        
        # 属性相似度
        attr_sim = self.compute_attribute_similarity(entity1, entity2)
        
        # 描述相似度
        desc_sim = compute_text_similarity(
            entity1.description or "",
            entity2.description or ""
        )
        
        # 加权平均
        similarity = (
            name_sim * 0.4 +
            type_sim * 0.2 +
            attr_sim * 0.3 +
            desc_sim * 0.1
        )
        
        return similarity
    
    def merge_entities(self, entity1: Entity, entity2: Entity) -> Entity:
        """
        合并两个实体
        
        策略：
        1. 保留更详细的属性
        2. 合并冲突的属性
        3. 使用更新的来源
        """
        merged = entity1.copy()
        
        # 合并属性
        if entity2.properties:
            if not merged.properties:
                merged.properties = entity2.properties.copy()
            else:
                # 合并冲突
                for key, value in entity2.properties.items():
                    if key not in merged.properties:
                        merged.properties[key] = value
                    else:
                        # 冲突，保留更新的
                        merged.properties[key] = value
        
        # 合并描述
        if entity2.description and len(entity2.description) > len(merged.description or ""):
            merged.description = entity2.description
        
        # 更新时间
        merged.updated_at = datetime.now(timezone.utc)
        
        return merged
```

---

## 10. 第五阶段：高级上下文优化

### 10.1 问题分析

**当前实现**：
- 基础优化逻辑（指令保留+记忆替换+最近5轮对话）
- 缺少Token计算
- 缺少智能替换策略
- 缺少摘要生成

**目标**：
1. 实现Token计数和截断逻辑
2. 实现智能内容替换策略
3. 实现摘要生成
4. 优化Token使用效率

### 10.2 Token计数器

```python
# 伪代码：Token计数器

class TokenCounter:
    """Token计数器"""
    
    def __init__(self, model: str = "deepseek-chat"):
        self.model = model
        # 简化的Token估算：中文字符数 + 英文词数 * 1.3
        # 实际应使用tiktoken库
    
    def count_tokens(self, text: str) -> int:
        """
        计算文本的Token数量
        
        算法：
        1. 统计中文字符
        2. 统计英文单词
        3. 转换为Token数
        """
        # 中文字符
        chinese_chars = len(re.findall(r'[\u4e00-\u9fa5]', text))
        
        # 英文单词
        english_words = len(re.findall(r'\b[a-zA-Z]+\b', text))
        
        # 估算Token数
        tokens = chinese_chars + int(english_words * 1.3)
        
        return tokens
    
    def count_messages_tokens(self, messages: List[Dict[str, str]]) -> Dict[str, int]:
        """
        计算消息列表的Token数量
        
        返回:
            Dict: {
                "prompt_tokens": int,
                "completion_tokens": int,
                "total_tokens": int
            }
        """
        prompt_tokens = 0
        for msg in messages:
            prompt_tokens += self.count_tokens(msg.get("content", ""))
        
        # 估算completion_tokens（不实际生成）
        completion_tokens = int(prompt_tokens * 0.5)  # 假设回复是prompt的一半
        
        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens
        }
```

### 10.3 智能替换策略

```python
# 伪代码：智能上下文优化

class AdvancedContextOptimizer:
    """高级上下文优化器"""
    
    def __init__(self, token_counter: TokenCounter, max_tokens: int = 8000):
        self.token_counter = token_counter
        self.max_tokens = max_tokens
    
    def optimize_context(
        self,
        original_messages: List[Dict[str, str]],
        parsed_content: ParsedContent,
        memories: List[Dict],
        target_model: str
    ) -> Tuple[List[Dict[str, str]], OptimizationReport]:
        """
        优化上下文
        
        流程：
        1. 构建完整上下文
        2. 计算Token数量
        3. 如果超限，执行优化
        4. 返回优化后的上下文
        
        返回:
            Tuple: (优化后的消息列表, 优化报告)
        """
        
        # 步骤1: 构建完整上下文
        full_context = self.build_full_context(
            original_messages,
            parsed_content,
            memories
        )
        
        # 步骤2: 计算Token数量
        token_count = self.token_counter.count_messages_tokens(full_context)
        
        optimization_report = OptimizationReport(
            original_tokens=token_count["total_tokens"],
            optimized_tokens=token_count["total_tokens"],
            strategies_applied=[]
        )
        
        # 步骤3: 如果超限，执行优化
        if token_count["total_tokens"] > self.max_tokens:
            optimized_context = self.optimize_over_budget(
                full_context,
                parsed_content,
                memories,
                optimization_report
            )
        else:
            optimized_context = full_context
        
        optimization_report.optimized_tokens = self.token_counter.count_messages_tokens(
            optimized_context
        )["total_tokens"]
        optimization_report.saved_tokens = (
            optimization_report.original_tokens - optimization_report.optimized_tokens
        )
        
        return optimized_context, optimization_report
    
    def build_full_context(
        self,
        original_messages: List[Dict[str, str]],
        parsed_content: ParsedContent,
        memories: List[Dict]
    ) -> List[Dict[str, str]]:
        """
        构建完整上下文
        
        策略：
        1. 保留所有指令性内容
        2. 插入相关记忆摘要
        3. 保留最近对话历史
        4. 添加当前user消息
        """
        context = []
        
        # 部分1: 指令性内容
        for instruction in parsed_content.instructions:
            context.append({
                "role": "system",
                "content": instruction.content
            })
        
        # 部分2: 相关记忆摘要
        if memories:
            memory_summary = self.summarize_memories(memories)
            context.append({
                "role": "system",
                "content": f"【相关记忆】\n{memory_summary}"
            })
        
        # 部分3: 对话历史（保留最近N轮）
        recent_dialogs = parsed_content.chat_history[-10:]  # 最近10轮
        for dialog in recent_dialogs:
            context.append({
                "role": dialog.role.lower(),
                "content": dialog.content
            })
        
        # 部分4: 最后一个user消息
        if original_messages:
            context.append(original_messages[-1])
        
        return context
    
    def optimize_over_budget(
        self,
        context: List[Dict[str, str]],
        parsed_content: ParsedContent,
        memories: List[Dict],
        report: OptimizationReport
    ) -> List[Dict[str, str]]:
        """
        优化超预算的上下文
        
        策略（按优先级）：
        1. 保留所有指令性内容（必须）
        2. 保留记忆摘要（重要）
        3. 减少对话历史轮次
        4. 压缩记忆摘要
        5. 截断最后user消息
        """
        
        optimized = context.copy()
        
        # 策略1: 保留所有指令性内容
        instructions = [msg for msg in optimized if msg["role"] == "system"]
        instruction_tokens = sum(
            self.token_counter.count_tokens(msg["content"])
            for msg in instructions
        )
        
        remaining_tokens = self.max_tokens - instruction_tokens
        
        # 策略2: 保留记忆摘要
        memory_msg = next((msg for msg in optimized if "相关记忆" in msg["content"]), None)
        if memory_msg:
            memory_tokens = self.token_counter.count_tokens(memory_msg["content"])
            
            if memory_tokens <= remaining_tokens * 0.3:  # 记忆不超过剩余的30%
                remaining_tokens -= memory_tokens
            else:
                # 压缩记忆
                compressed_memory = self.compress_text(memory_msg["content"], remaining_tokens * 0.3)
                memory_msg["content"] = compressed_memory
                remaining_tokens -= self.token_counter.count_tokens(compressed_memory)
                report.strategies_applied.append("compress_memories")
        
        # 策略3: 减少对话历史轮次
        dialogs = [msg for msg in optimized if msg["role"] in ["user", "assistant"]]
        
        # 估算每轮对话的Token
        avg_dialog_tokens = sum(
            self.token_counter.count_tokens(msg["content"])
            for msg in dialogs[:3]
        ) / 3
        
        max_dialog_turns = int(remaining_tokens / avg_dialog_tokens)
        max_dialog_turns = min(max_dialog_turns, len(dialogs))
        
        if max_dialog_turns < len(dialogs):
            # 减少对话轮次
            optimized = [
                msg for msg in optimized
                if msg["role"] != "user" and msg["role"] != "assistant"
                or dialogs.index(msg) < max_dialog_turns
            ]
            report.strategies_applied.append(f"reduce_dialog_history_to_{max_dialog_turns}_turns")
        
        # 策略4: 如果仍然超限，截断最后一个user消息
        final_tokens = sum(
            self.token_counter.count_tokens(msg["content"])
            for msg in optimized
        )
        
        if final_tokens > self.max_tokens:
            excess = final_tokens - self.max_tokens
            last_msg = optimized[-1]
            last_msg_content = last_msg["content"]
            
            # 截断到剩余Token
            truncated_content = self.truncate_to_tokens(
                last_msg_content,
                self.token_counter.count_tokens(last_msg_content) - excess
            )
            last_msg["content"] = truncated_content
            report.strategies_applied.append("truncate_last_message")
        
        return optimized
    
    def summarize_memories(self, memories: List[Dict], max_tokens: int = 1000) -> str:
        """
        生成记忆摘要
        
        策略：
        1. 按相关性排序
        2. 提取关键信息
        3. 限制长度
        """
        # 按分数排序
        sorted_memories = sorted(memories, key=lambda m: m.get("score", 0), reverse=True)
        
        # 取前5个
        top_memories = sorted_memories[:5]
        
        # 提取关键信息
        summary_parts = []
        current_tokens = 0
        
        for mem in top_memories:
            fact = mem.get("fact", "")
            fact_tokens = self.token_counter.count_tokens(fact)
            
            if current_tokens + fact_tokens <= max_tokens:
                summary_parts.append(f"- {fact}")
                current_tokens += fact_tokens
            else:
                break
        
        return "\n".join(summary_parts)
    
    def compress_text(self, text: str, max_tokens: int) -> str:
        """
        压缩文本到指定Token数
        
        简化策略：截断
        实际应使用更智能的摘要算法
        """
        current_tokens = 0
        lines = text.split('\n')
        compressed_lines = []
        
        for line in lines:
            line_tokens = self.token_counter.count_tokens(line)
            
            if current_tokens + line_tokens <= max_tokens:
                compressed_lines.append(line)
                current_tokens += line_tokens
            else:
                break
        
        return '\n'.join(compressed_lines)
    
    def truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """
        截断文本到指定Token数
        """
        chars_per_token = len(text) / self.token_counter.count_tokens(text)
        max_chars = int(max_tokens * chars_per_token)
        
        return text[:max_chars]
```

---

## 11. 可选增强功能

### 11.1 动态角色名识别

**问题**：对话历史中的Assistant和User名字可能动态变化

**解决方案**：

```python
# 伪代码：动态角色名识别

class DynamicSpeakerIdentifier:
    """动态说话者识别器"""
    
    def __init__(self):
        self.speaker_mappings = {}  # 原始标识 -> 角色类型
    
    def identify_speakers(
        self,
        dialog_text: str
    ) -> Tuple[Dict[str, str], float]:
        """
        识别对话中的说话者
        
        参数:
            dialog_text: 对话文本
        
        返回:
            Tuple: (映射字典, 置信度)
        """
        # 提取所有可能的说话者标识
        pattern = r"^(User|Assistant|[A-Za-z\u4e00-\u9fa5]+):\s"
        matches = re.findall(pattern, dialog_text, re.MULTILINE)
        
        speakers = set(matches)
        
        if not speakers:
            return {}, 0.0
        
        # 如果只有User和Assistant
        if speakers == {"User:", "Assistant:"}:
            return {
                "User:": "User",
                "Assistant:": "Assistant"
            }, 1.0
        
        # 如果有自定义名称，推断角色类型
        mapping = {}
        confidence = 0.8  # 默认置信度
        
        for speaker in speakers:
            speaker_name = speaker.rstrip(":")
            
            if speaker_name.lower() == "user":
                mapping[speaker] = "User"
            elif speaker_name.lower() in ["assistant", "ai", "ai助手"]:
                mapping[speaker] = "Assistant"
            elif "assistant" not in mapping.values():
                # 第一个非User角色，判定为Assistant
                mapping[speaker] = "Assistant"
            else:
                # 已有Assistant，新角色可能是用户别名
                mapping[speaker] = "User"
        
        # 验证映射的一致性
        if self._validate_mapping(dialog_text, mapping):
            confidence = 0.9
        else:
            confidence = 0.7
        
        return mapping, confidence
    
    def _validate_mapping(self, dialog_text: str, mapping: Dict[str, str]) -> bool:
        """
        验证映射的一致性
        
        检查：
        1. 角色是否交替出现
        2. 映射是否合理
        """
        lines = dialog_text.split('\n')
        roles = []
        
        for line in lines:
            match = re.match(r"^([^:]+):", line)
            if match:
                speaker = match.group(1)
                role = mapping.get(speaker, None)
                if role:
                    roles.append(role)
        
        # 检查是否交替
        for i in range(len(roles) - 1):
            if roles[i] == roles[i + 1]:
                # 连续两个相同的角色，可能不合理
                return False
        
        return True
```

### 11.2 复杂世界书格式解析

**问题**：项目分析中的示例包含复杂YAML/JSON-like格式

**解决方案**：

```python
# 伪代码：复杂格式解析

class ComplexWorldInfoParser:
    """复杂世界书解析器"""
    
    def parse(self, text: str) -> List[WorldInfoEntry]:
        """
        解析复杂格式世界书
        
        支持格式：
        1. YAML格式
        2. JSON格式
        3. 自定义嵌套格式
        4. Markdown层次结构
        """
        # 尝试YAML
        try:
            import yaml
            data = yaml.safe_load(text)
            if isinstance(data, dict):
                return self.parse_yaml_structure(data)
        except:
            pass
        
        # 尝试JSON
        try:
            import json
            data = json.loads(text)
            if isinstance(data, dict):
                return self.parse_json_structure(data)
        except:
            pass
        
        # 使用自定义规则
        return self.parse_custom_format(text)
    
    def parse_yaml_structure(self, data: Dict) -> List[WorldInfoEntry]:
        """
        解析YAML结构
        """
        entries = []
        
        # 递归解析
        def parse_dict(obj, parent_key=""):
            for key, value in obj.items():
                full_key = f"{parent_key}.{key}" if parent_key else key
                
                if isinstance(value, dict):
                    parse_dict(value, full_key)
                elif isinstance(value, list):
                    for item in value:
                        entries.append(WorldInfoEntry(
                            entry_type="general",
                            name=full_key,
                            content=str(item),
                            properties={"source": "yaml"}
                        ))
                else:
                    entries.append(WorldInfoEntry(
                        entry_type="general",
                        name=full_key,
                        content=str(value),
                        properties={"source": "yaml"}
                    ))
        
        parse_dict(data)
        return entries
```

---

## 12. 测试与验证

### 12.1 测试策略

```python
# 测试计划

# 1. 单元测试
# 2. 集成测试
# 3. 端到端测试
# 4. 性能测试

# 示例：变化检测测试

def test_worldinfo_change_detection():
    """测试World Info变化检测"""
    
    # 创建旧状态
    old_state = WorldInfoState()
    old_state.entries = {
        "location:基沃托斯": WorldInfoEntry(
            entry_id="location:基沃托斯",
            entry_type="location",
            name="基沃托斯",
            content="地点('基沃托斯')['学园城市']",
            content_hash=compute_content_hash("地点('基沃托斯')['学园城市']")
        )
    }
    
    # 创建新内容（新增条目）
    new_content = """
地点('夏莱办公室大楼办公室')['位于夏莱办公大楼内部']
地点('阿拜多斯高中')['沙漠中的高中']
"""
    
    # 检测变化
    changes = detect_worldinfo_changes(old_state, new_content)
    
    # 验证
    assert len(changes["added"]) == 2
    assert changes["added"][0].name == "夏莱办公室大楼办公室"
    assert changes["added"][1].name == "阿拜多斯高中"
    assert len(changes["removed"]) == 0
    assert len(changes["modified"]) == 0


# 示例：心理状态分析测试

async def test_psychological_state_analysis():
    """测试心理状态分析"""
    
    # 模拟对话
    dialog_text = """
User: 你好
Assistant: 呀吼～！老师～这里这里！等好久了哦～
User: 你今天心情怎么样？
Assistant: 啊哈哈……没什么特别哒，一如既往地开心呢！不过今天天气真好，心情更棒了～
"""
    
    # 分析心理状态
    state = await analyze_psychological_state(
        graphiti_service=mock_graphiti_service,
        character_id="misono_mika",
        dialog_text=dialog_text,
        context={"character_description": "圣园未花"}
    )
    
    # 验证
    assert state.character_id == "misono_mika"
    assert state.dominant_emotion in ["joy", "happiness"]
    assert "optimistic" in state.trait_manifestations
```

---

## 13. 监控与运维

### 13.1 监控指标

```python
# 监控指标定义

MONITORING_METRICS = {
    # 性能指标
    "api_response_time": {
        "type": "histogram",
        "description": "API响应时间（毫秒）"
    },
    "graphiti_operation_time": {
        "type": "histogram",
        "description": "Graphiti操作时间（毫秒）"
    },
    "llm_latency": {
        "type": "histogram",
        "description": "LLM调用延迟（毫秒）"
    },
    
    # 业务指标
    "active_sessions": {
        "type": "gauge",
        "description": "活跃会话数"
    },
    "episodes_stored": {
        "type": "counter",
        "description": "存储的Episode数量"
    },
    "memories_retrieved": {
        "type": "counter",
        "description": "检索的记忆数量"
    },
    "psychological_state_analyses": {
        "type": "counter",
        "description": "心理状态分析次数"
    },
    "causal_relations_extracted": {
        "type": "counter",
        "description": "提取的因果关系数量"
    },
    
    # 错误指标
    "errors_total": {
        "type": "counter",
        "description": "总错误数"
    },
    "errors_by_type": {
        "type": "counter",
        "description": "按类型分类的错误数"
    }
}
```

---

## 附录：快速启动检查清单

### 部署前检查

- [ ] Docker和Docker Compose已安装
- [ ] Docker Compose版本 >= 2.0
- [ ] 端口7474, 7687, 8000未被占用
- [ ] 磁盘空间充足（至少50GB可用）
- [ ] 内存充足（至少8GB可用）
- [ ] DeepSeek API Key有效
- [ ] 硅基流动API Key有效

### 配置检查

- [ ] .env文件已创建
- [ ] 所有密码和密钥已修改为实际值
- [ ] NEO4J_URI配置正确（bolt://neo4j:7687用于容器内）
- [ ] DEEPSEEK_API_KEY已设置
- [ ] DEEPSEEK_BASE_URL根据需求选择（标准或beta）
- [ ] .env文件权限正确（chmod 600）

### 启动检查

- [ ] docker-compose up -d 成功执行
- [ ] 所有容器状态为Up（docker-compose ps）
- [ ] Neo4j健康检查通过（docker-compose logs neo4j）
- [ ] API服务健康检查通过（curl localhost:8000/health）

### 功能验证检查

- [ ] Neo4j Browser可访问（http://localhost:7474）
- [ ] 可以在Neo4j中查询数据
- [ ] API端点返回健康状态
- [ ] OpenAI兼容端点响应正常
- [ ] SillyTavern可以连接并获取回复
- [ ] 世界书和对话历史被Graphiti处理
- [ ] 记忆检索功能正常工作
- [ ] 变化检测功能工作正常
- [ ] 心理状态分析功能工作正常
- [ ] 因果关系提取功能工作正常

---

## 总结

本文档提供了完整的AIRP记忆系统实施指南，涵盖了：

**已实现的基础（100%）**：
- ✅ Neo4j Docker Compose v2部署
- ✅ OpenAI兼容API接口
- ✅ DeepSeek V3.2 LLM集成
- ✅ 硅基流动Embedding和Reranker集成
- ✅ Graphiti知识图谱存储
- ✅ 混合检索和Reranker重排序
- ✅ SillyTavern基础格式解析
- ✅ 配置管理和Docker部署

**第一至五阶段核心功能（0% → 100%）**：
- 🔴 变化检测与同步机制（Week 1-2）
- 🔴 心理连贯性建模（Week 3-4）
- 🔴 因果逻辑链建模（Week 5-6）
- 🟡 并发处理与去重（Week 7-8）
- 🟡 高级上下文优化（Week 9-10）

**关键技术设计**：
- 三层架构模式（核心基础层、通用适配层、动态扩展层）
- 属性化关系模型（基础关系类型 + 属性标签）
- LLM驱动的模式演化
- 并发处理队列（通用工作线程池）
- 多层次去重策略（哈希、特征、语义）
- 心理状态实体网络和演化跟踪
- 因果链建模和事件推演
- 双时序模型应用（valid_from/valid_until + status）

**实施优先级**：
1. 高优先级：变化检测、心理建模、因果链（AIRP核心需求）
2. 中优先级：并发处理、去重、上下文优化（性能和质量）
3. 低优先级：动态角色名、复杂格式、语义哈希（可选增强）

通过本指南的实施，系统将达到**100%完成度**，实现完整的AIRP记忆增强能力，包括心理连贯性建模、世界观逻辑推演、动态记忆检索和智能Token优化。

---

**文档版本**：v1.0  
**生成日期**：2026-01-05  
**基于文档**：
- 项目分析.md（需求分析）
- API服务实现计划.md（技术细节）
- 开发部署指南.md（部署流程）
- 项目实现情况检查报告.md（现状分析）
