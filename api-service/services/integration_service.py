"""
AIRP记忆系统集成服务
集成SillyTavern解析器、实体提取和Graphiti记忆系统
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import uuid
import json
import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 导入现有服务
try:
    from config.settings import settings
    from services.sillytavern_parser import SillyTavernParser, ContentCategory
    from services.graphiti_service import GraphitiService
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.error(f"导入失败: {str(e)}")
    # 尝试相对导入
    try:
        from config.settings import settings
        from services.sillytavern_parser import SillyTavernParser, ContentCategory
        from services.graphiti_service import GraphitiService
    except ImportError:
        raise

logger = logging.getLogger(__name__)


class AIRPIntegrationService:
    """AIRP记忆系统集成服务"""
    
    def __init__(self):
        """初始化集成服务"""
        self.parser = SillyTavernParser()
        self.graphiti_service = GraphitiService()
        self.session_cache = {}  # 会话缓存
        
        logger.info("AIRP集成服务初始化成功")
    
    async def process_sillytavern_input(self, 
                                       text: str, 
                                       session_id: str,
                                       user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        处理SillyTavern输入文本，执行完整处理流程
        
        流程:
        1. 解析SillyTavern格式文本
        2. 提取实体和关系
        3. 存储到Graphiti知识图谱
        4. 检索相关记忆
        5. 返回处理结果
        """
        logger.info(f"处理SillyTavern输入: session={session_id}, 文本长度={len(text)}")
        
        try:
            # 步骤1: 解析SillyTavern格式文本
            parse_result = self.parser.parse_sillytavern_input(text, session_id)
            
            if parse_result.get("error"):
                logger.error(f"解析失败: {parse_result['error']}")
                return {
                    "success": False,
                    "error": parse_result["error"],
                    "step": "parsing"
                }
            
            logger.info(f"解析成功: {len(parse_result['blocks'])} 个块, {len(parse_result['tags'])} 个标签")
            
            # 步骤2: 提取实体
            entities = self.parser.extract_entities_from_text(text)
            
            # 步骤3: 提取关系
            relationships = self.parser.identify_relationships(entities, text)
            
            logger.info(f"实体提取: {sum(len(v) for v in entities.values())} 个实体")
            logger.info(f"关系识别: {len(relationships)} 个关系")
            
            # 步骤4: 存储到Graphiti知识图谱
            storage_result = await self._store_to_graphiti(
                session_id=session_id,
                text=text,
                parse_result=parse_result,
                entities=entities,
                relationships=relationships,
                user_id=user_id
            )
            
            if not storage_result["success"]:
                logger.error(f"存储到Graphiti失败: {storage_result.get('error', '未知错误')}")
                return storage_result
            
            # 步骤5: 检索相关记忆
            retrieval_result = await self._retrieve_relevant_memory(
                session_id=session_id,
                text=text,
                entities=entities,
                parse_result=parse_result
            )
            
            # 步骤6: 生成处理摘要
            summary = self._generate_processing_summary(
                parse_result=parse_result,
                entities=entities,
                relationships=relationships,
                storage_result=storage_result,
                retrieval_result=retrieval_result
            )
            
            # 步骤7: 缓存结果
            self._cache_session_data(session_id, {
                "parse_result": parse_result,
                "entities": entities,
                "relationships": relationships,
                "last_processed": datetime.now().isoformat()
            })
            
            result = {
                "success": True,
                "session_id": session_id,
                "summary": summary,
                "parsing": {
                    "blocks_count": len(parse_result["blocks"]),
                    "tags_count": len(parse_result["tags"]),
                    "complexity_score": parse_result["structure_analysis"]["complexity_score"],
                    "processing_time": parse_result["processing_time"]
                },
                "extraction": {
                    "entities_count": sum(len(v) for v in entities.values()),
                    "relationships_count": len(relationships),
                    "entities_breakdown": {k: len(v) for k, v in entities.items()}
                },
                "storage": storage_result,
                "retrieval": retrieval_result,
                "recommendations": self._generate_recommendations(summary)
            }
            
            logger.info(f"处理完成: session={session_id}, 总实体数={sum(len(v) for v in entities.values())}")
            
            return result
            
        except Exception as e:
            logger.error(f"处理SillyTavern输入时发生错误: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "step": "general_processing"
            }
    
    async def _store_to_graphiti(self,
                                session_id: str,
                                text: str,
                                parse_result: Dict[str, Any],
                                entities: Dict[str, List[str]],
                                relationships: List[Dict[str, Any]],
                                user_id: Optional[str] = None) -> Dict[str, Any]:
        """存储信息到Graphiti知识图谱"""
        logger.info(f"开始存储到Graphiti: session={session_id}")
        
        try:
            # 创建主文档实体
            document_id = str(uuid.uuid4())
            document_data = {
                "entity_id": document_id,
                "entity_type": "document",
                "name": f"session_{session_id}_document",
                "properties": {
                    "session_id": session_id,
                    "text_length": len(text),
                    "blocks_count": len(parse_result["blocks"]),
                    "tags_count": len(parse_result["tags"]),
                    "user_id": user_id,
                    "processed_at": datetime.now().isoformat(),
                    "content_hash": parse_result["content_hash"],
                    "complexity_score": parse_result["structure_analysis"]["complexity_score"],
                    "summary": parse_result["summary"]
                }
            }
            
            # 存储文档实体
            stored_document_id = self.graphiti_service.create_entity(session_id, document_data)
            
            if not stored_document_id:
                logger.error("存储文档实体失败")
                return {
                    "success": False,
                    "error": "存储文档实体失败",
                    "step": "document_storage"
                }
            
            # 存储提取的实体
            stored_entities = []
            for entity_type, entity_list in entities.items():
                for entity_name in entity_list:
                    if not entity_name or len(entity_name.strip()) < 2:
                        continue
                    
                    entity_data = {
                        "entity_id": str(uuid.uuid4()),
                        "entity_type": entity_type,
                        "name": entity_name.strip(),
                        "properties": {
                            "source_session": session_id,
                            "extracted_at": datetime.now().isoformat(),
                            "original_document_id": stored_document_id
                        }
                    }
                    
                    entity_id = self.graphiti_service.create_entity(session_id, entity_data)
                    if entity_id:
                        stored_entities.append({
                            "entity_id": entity_id,
                            "type": entity_type,
                            "name": entity_name.strip()
                        })
                        
                        # 创建文档-实体关系
                        self.graphiti_service.create_relationship(
                            session_id=session_id,
                            source_entity_id=stored_document_id,
                            target_entity_id=entity_id,
                            relation_type="contains",
                            properties={
                                "extraction_method": "regex_pattern",
                                "confidence": 0.7,
                                "timestamp": datetime.now().isoformat()
                            }
                        )
            
            # 存储提取的关系
            stored_relationships = []
            for rel in relationships:
                if not rel.get("source") or not rel.get("target"):
                    continue
                
                # 寻找源实体
                source_entity = None
                for stored_entity in stored_entities:
                    if stored_entity["name"] == rel["source"]:
                        source_entity = stored_entity
                        break
                
                # 寻找目标实体
                target_entity = None
                for stored_entity in stored_entities:
                    if stored_entity["name"] == rel["target"]:
                        target_entity = stored_entity
                        break
                
                if source_entity and target_entity:
                    relationship_id = self.graphiti_service.create_relationship(
                        session_id=session_id,
                        source_entity_id=source_entity["entity_id"],
                        target_entity_id=target_entity["entity_id"],
                        relation_type=rel["type"],
                        properties={
                            "confidence": rel.get("confidence", 0.7),
                            "context": rel.get("context", ""),
                            "extraction_method": "pattern_matching",
                            "timestamp": datetime.now().isoformat()
                        }
                    )
                    
                    if relationship_id:
                        stored_relationships.append({
                            "relationship_id": relationship_id,
                            "source": rel["source"],
                            "target": rel["target"],
                            "type": rel["type"]
                        })
            
            # 存储元数据
            metadata_id = str(uuid.uuid4())
            metadata_data = {
                "entity_id": metadata_id,
                "entity_type": "metadata",
                "name": f"session_{session_id}_metadata",
                "properties": {
                    "session_id": session_id,
                    "user_id": user_id,
                    "processing_timestamp": datetime.now().isoformat(),
                    "entities_count": len(stored_entities),
                    "relationships_count": len(stored_relationships),
                    "document_id": stored_document_id,
                    "parsing_stats": parse_result["summary"],
                    "retrieval_hints": self._generate_retrieval_hints(entities, relationships)
                }
            }
            
            stored_metadata_id = self.graphiti_service.create_entity(session_id, metadata_data)
            
            # 创建元数据-文档关系
            if stored_metadata_id and stored_document_id:
                self.graphiti_service.create_relationship(
                    session_id=session_id,
                    source_entity_id=stored_metadata_id,
                    target_entity_id=stored_document_id,
                    relation_type="describes",
                    properties={
                        "timestamp": datetime.now().isoformat()
                    }
                )
            
            result = {
                "success": True,
                "document_id": stored_document_id,
                "metadata_id": stored_metadata_id,
                "stored_entities_count": len(stored_entities),
                "stored_relationships_count": len(stored_relationships),
                "stored_entities": stored_entities,
                "stored_relationships": stored_relationships
            }
            
            logger.info(f"存储到Graphiti成功: {len(stored_entities)} 个实体, {len(stored_relationships)} 个关系")
            
            return result
            
        except Exception as e:
            logger.error(f"存储到Graphiti时发生错误: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "step": "graphiti_storage"
            }
    
    async def _retrieve_relevant_memory(self,
                                       session_id: str,
                                       text: str,
                                       entities: Dict[str, List[str]],
                                       parse_result: Dict[str, Any]) -> Dict[str, Any]:
        """检索相关记忆"""
        logger.info(f"检索相关记忆: session={session_id}")
        
        try:
            # 提取主要实体用于检索
            primary_entities = []
            for entity_type, entity_list in entities.items():
                # 取每个类型的前几个实体作为主要实体
                primary_entities.extend(entity_list[:2])
            
            # 搜索相关实体
            relevant_entities = []
            related_relationships = []
            
            for entity in primary_entities:
                if not entity or len(entity.strip()) < 2:
                    continue
                
                # 搜索实体
                found_entities = self.graphiti_service.search_entities(
                    session_id=session_id,
                    name=entity
                )
                
                relevant_entities.extend(found_entities[:3])  # 取前3个相关实体
                
                # 搜索相关关系
                for found_entity in found_entities[:2]:
                    found_relationships = self.graphiti_service.get_related_entities(
                        session_id=session_id,
                        entity_id=found_entity["entity_id"],
                        limit=3
                    )
                    related_relationships.extend(found_relationships)
            
            # 去重
            unique_entities = []
            seen_entity_ids = set()
            for entity in relevant_entities:
                if entity["entity_id"] not in seen_entity_ids:
                    unique_entities.append(entity)
                    seen_entity_ids.add(entity["entity_id"])
            
            unique_relationships = []
            seen_rel_ids = set()
            for rel in related_relationships:
                rel_id = f"{rel['entity_id']}_{rel['relation_type']}_{rel.get('related_entity_id', '')}"
                if rel_id not in seen_rel_ids:
                    unique_relationships.append(rel)
                    seen_rel_ids.add(rel_id)
            
            # 计算相关性分数
            relevance_score = self._calculate_relevance_score(text, unique_entities, unique_relationships)
            
            result = {
                "success": True,
                "relevant_entities_count": len(unique_entities),
                "relevant_relationships_count": len(unique_relationships),
                "relevance_score": relevance_score,
                "entities": unique_entities[:5],  # 只返回前5个实体
                "relationships": unique_relationships[:5],  # 只返回前5个关系
                "retrieval_strategy": "entity_based_semantic_search",
                "context_enhancement": self._enhance_context_with_memory(
                    text, unique_entities, unique_relationships
                )
            }
            
            logger.info(f"记忆检索成功: {len(unique_entities)} 个相关实体, 相关性分数: {relevance_score}")
            
            return result
            
        except Exception as e:
            logger.error(f"检索相关记忆时发生错误: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "step": "memory_retrieval"
            }
    
    def _calculate_relevance_score(self,
                                  text: str,
                                  entities: List[Dict[str, Any]],
                                  relationships: List[Dict[str, Any]]) -> float:
        """计算相关性分数"""
        score = 0.0
        
        # 基于匹配的实体数量
        if entities:
            score += min(len(entities) * 0.1, 0.5)
        
        # 基于匹配的关系数量
        if relationships:
            score += min(len(relationships) * 0.05, 0.3)
        
        # 基于文本长度和内容复杂性
        word_count = len(text.split())
        if word_count > 100:
            score += 0.1
        elif word_count > 50:
            score += 0.05
        
        # 确保分数在0-1之间
        score = min(max(score, 0.0), 1.0)
        
        return round(score, 3)
    
    def _enhance_context_with_memory(self,
                                    text: str,
                                    entities: List[Dict[str, Any]],
                                    relationships: List[Dict[str, Any]]) -> Dict[str, Any]:
        """使用记忆增强上下文"""
        enhanced_context = {
            "original_text": text[:500] + "..." if len(text) > 500 else text,
            "related_entities": [],
            "related_concepts": [],
            "timeline_hints": [],
            "potential_connections": []
        }
        
        # 提取相关实体信息
        for entity in entities[:3]:  # 前3个实体
            entity_info = {
                "name": entity.get("name", ""),
                "type": entity.get("entity_type", ""),
                "properties": entity.get("properties", {}),
                "relevance_hint": "在知识图谱中发现的相关实体"
            }
            enhanced_context["related_entities"].append(entity_info)
        
        # 提取相关关系信息
        for rel in relationships[:3]:  # 前3个关系
            if "relation_type" in rel:
                connection = {
                    "type": rel.get("relation_type", ""),
                    "source": rel.get("name", ""),
                    "target": rel.get("related_entity_id", ""),
                    "confidence": rel.get("properties", {}).get("confidence", 0.7)
                }
                enhanced_context["potential_connections"].append(connection)
        
        # 根据文本内容添加概念
        text_lower = text.lower()
        if "角色" in text_lower or "character" in text_lower:
            enhanced_context["related_concepts"].append("角色设定")
        if "背景" in text_lower or "scenario" in text_lower:
            enhanced_context["related_concepts"].append("故事背景")
        if "对话" in text_lower or "dialogue" in text_lower:
            enhanced_context["related_concepts"].append("对话历史")
        if "规则" in text_lower or "rule" in text_lower:
            enhanced_context["related_concepts"].append("创作准则")
        
        return enhanced_context
    
    def _generate_processing_summary(self,
                                    parse_result: Dict[str, Any],
                                    entities: Dict[str, List[str]],
                                    relationships: List[Dict[str, Any]],
                                    storage_result: Dict[str, Any],
                                    retrieval_result: Dict[str, Any]) -> Dict[str, Any]:
        """生成处理摘要"""
        summary = {
            "parsing": {
                "blocks_identified": len(parse_result["blocks"]),
                "tags_extracted": len(parse_result["tags"]),
                "complexity_assessment": parse_result["structure_analysis"]["complexity_score"],
                "semantic_categories": list(set(b.category.value for b in parse_result["blocks"]))
            },
            "extraction": {
                "entities_by_type": {k: len(v) for k, v in entities.items()},
                "total_entities": sum(len(v) for v in entities.values()),
                "relationships_identified": len(relationships),
                "relationship_types": list(set(r["type"] for r in relationships)) if relationships else []
            },
            "storage": {
                "success": storage_result.get("success", False),
                "entities_stored": storage_result.get("stored_entities_count", 0),
                "relationships_stored": storage_result.get("stored_relationships_count", 0),
                "document_created": True if storage_result.get("document_id") else False
            },
            "retrieval": {
                "success": retrieval_result.get("success", False),
                "relevant_entities_found": retrieval_result.get("relevant_entities_count", 0),
                "relevance_score": retrieval_result.get("relevance_score", 0),
                "context_enhanced": True if retrieval_result.get("context_enhancement") else False
            }
        }
        
        return summary
    
    def _generate_retrieval_hints(self, 
                                 entities: Dict[str, List[str]], 
                                 relationships: List[Dict[str, Any]]) -> List[str]:
        """生成检索提示"""
        hints = []
        
        # 基于主要实体生成提示
        primary_entities = []
        for entity_type, entity_list in entities.items():
            primary_entities.extend(entity_list[:3])
        
        for entity in primary_entities[:3]:
            hints.append(f"搜索与'{entity}'相关的实体")
        
        # 基于关系生成提示
        for rel in relationships[:2]:
            hints.append(f"探索'{rel['source']}'和'{rel['target']}'之间的关系")
        
        # 通用提示
        hints.append("考虑对话上下文和历史信息")
        hints.append("使用语义相似性和关键词匹配的组合")
        
        return hints
    
    def _generate_recommendations(self, summary: Dict[str, Any]) -> List[str]:
        """生成处理建议"""
        recommendations = []
        
        parsing = summary.get("parsing", {})
        extraction = summary.get("extraction", {})
        storage = summary.get("storage", {})
        retrieval = summary.get("retrieval", {})
        
        # 解析相关建议
        if parsing.get("blocks_identified", 0) < 2:
            recommendations.append("输入文本结构简单，建议提供更多结构化信息")
        
        complexity = parsing.get("complexity_assessment", 0)
        if complexity > 7:
            recommendations.append("文本复杂度较高，考虑分步骤处理")
        elif complexity < 3:
            recommendations.append("文本复杂度较低，可以直接进行完整处理")
        
        # 提取相关建议
        total_entities = extraction.get("total_entities", 0)
        if total_entities < 3:
            recommendations.append("实体提取较少，可以添加更多命名实体识别规则")
        
        relationships_count = extraction.get("relationships_identified", 0)
        if relationships_count == 0:
            recommendations.append("未识别到关系，可以添加更多关系提取模式")
        
        # 检索相关建议
        relevance_score = retrieval.get("relevance_score", 0)
        if relevance_score < 0.3:
            recommendations.append("相关性分数较低，建议扩展知识图谱或优化检索策略")
        
        # 通用建议
        recommendations.append("考虑添加用户特定偏好和习惯到记忆系统")
        recommendations.append("定期清理和优化知识图谱数据")
        
        return recommendations
    
    def _cache_session_data(self, session_id: str, data: Dict[str, Any]):
        """缓存会话数据"""
        cache_entry = {
            "data": data,
            "cached_at": datetime.now().isoformat(),
            "access_count": 0
        }
        
        # 限制缓存大小
        if len(self.session_cache) > 100:
            # 移除最旧的缓存项
            oldest_key = min(self.session_cache.keys(), 
                           key=lambda k: self.session_cache[k]["cached_at"])
            del self.session_cache[oldest_key]
        
        self.session_cache[session_id] = cache_entry
        logger.debug(f"会话数据缓存: session={session_id}, 缓存大小={len(self.session_cache)}")
    
    def get_cached_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取缓存的会话数据"""
        if session_id in self.session_cache:
            cache_entry = self.session_cache[session_id]
            cache_entry["access_count"] += 1
            logger.debug(f"获取缓存数据: session={session_id}, 访问次数={cache_entry['access_count']}")
            return cache_entry["data"]
        return None
    
    def clear_session_cache(self, session_id: str) -> bool:
        """清除会话缓存"""
        if session_id in self.session_cache:
            del self.session_cache[session_id]
            logger.info(f"清除会话缓存: session={session_id}")
            return True
        return False
    
    async def enhance_chat_context(self,
                                 messages: List[Dict[str, str]],
                                 session_id: str,
                                 user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        增强聊天上下文
        
        返回:
        {
            "original_context": List[Dict],  # 原始对话上下文
            "enhanced_context": Dict,        # 增强的上下文信息
            "recommendations": List[str],    # 响应建议
            "memory_summary": Dict           # 记忆系统摘要
        }
        """
        logger.info(f"增强聊天上下文: session={session_id}, 消息数={len(messages)}")
        
        try:
            # 提取最近的消息
            recent_text = ""
            if messages:
                # 取最后3条消息
                recent_messages = messages[-3:] if len(messages) >= 3 else messages
                recent_text = "\n".join([f"{m.get('role', 'unknown')}: {m.get('content', '')}" 
                                        for m in recent_messages])
            
            if not recent_text or len(recent_text.strip()) < 5:
                logger.warning("聊天上下文太短，无法有效增强")
                return {
                    "success": False,
                    "error": "聊天上下文太短",
                    "original_context": messages,
                    "enhanced_context": {},
                    "recommendations": ["提供更多的对话上下文以获得更好的增强效果"]
                }
            
            # 使用集成服务处理文本
            processing_result = await self.process_sillytavern_input(
                text=recent_text,
                session_id=session_id,
                user_id=user_id
            )
            
            if not processing_result.get("success"):
                return {
                    "success": False,
                    "error": processing_result.get("error", "未知错误"),
                    "original_context": messages,
                    "enhanced_context": {},
                    "recommendations": ["处理输入时发生错误，请检查输入格式"]
                }
            
            # 构建增强的上下文
            enhanced_context = {
                "text_analysis": {
                    "complexity": processing_result["parsing"]["complexity_score"],
                    "semantic_categories": processing_result["summary"]["parsing"]["semantic_categories"]
                },
                "extracted_entities": processing_result["summary"]["extraction"]["entities_by_type"],
                "memory_retrieval": {
                    "relevance_score": processing_result["retrieval"].get("relevance_score", 0),
                    "enhancement_hints": processing_result["retrieval"].get("context_enhancement", {}),
                    "retrieved_entities_count": processing_result["retrieval"].get("relevant_entities_count", 0)
                },
                "processing_stats": {
                    "blocks_parsed": processing_result["parsing"]["blocks_count"],
                    "entities_extracted": processing_result["extraction"]["entities_count"],
                    "relationships_identified": processing_result["extraction"]["relationships_count"],
                    "storage_success": processing_result["storage"]["success"],
                    "retrieval_success": processing_result["retrieval"]["success"]
                }
            }
            
            # 基于记忆系统生成响应建议
            recommendations = self._generate_response_recommendations(
                processing_result=processing_result,
                messages=messages
            )
            
            result = {
                "success": True,
                "original_context": messages,
                "enhanced_context": enhanced_context,
                "recommendations": recommendations,
                "memory_summary": {
                    "session_id": session_id,
                    "processing_time": processing_result["parsing"]["processing_time"],
                    "total_entities_stored": processing_result["storage"]["stored_entities_count"],
                    "relevance_confidence": processing_result["retrieval"].get("relevance_score", 0),
                    "system_status": "active"
                }
            }
            
            logger.info(f"上下文增强成功: session={session_id}, 增强实体数={processing_result['storage']['stored_entities_count']}")
            
            return result
            
        except Exception as e:
            logger.error(f"增强聊天上下文时发生错误: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "original_context": messages,
                "enhanced_context": {},
                "recommendations": ["上下文增强过程中发生错误"]
            }
    
    def _generate_response_recommendations(self,
                                         processing_result: Dict[str, Any],
                                         messages: List[Dict[str, str]]) -> List[str]:
        """生成响应建议"""
        recommendations = []
        
        # 基于实体提取生成建议
        entities_by_type = processing_result["summary"]["extraction"]["entities_by_type"]
        persons = entities_by_type.get("persons", [])
        locations = entities_by_type.get("locations", [])
        
        if persons:
            recommendations.append(f"在响应中提及: {', '.join(persons[:2])}")
        
        if locations:
            recommendations.append(f"考虑地点背景: {', '.join(locations[:2])}")
        
        # 基于关系生成建议
        relationships = processing_result["retrieval"].get("relationships", [])
        if relationships:
            for rel in relationships[:2]:
                recommendations.append(f"探索关系: {rel.get('source', '')} {rel.get('type', '')} {rel.get('target', '')}")
        
        # 基于文本复杂度生成建议
        complexity = processing_result["parsing"]["complexity_score"]
        if complexity > 8:
            recommendations.append("文本高度复杂，建议分步骤或确认理解")
        elif complexity < 4:
            recommendations.append("文本相对简单，可以直接完整响应")
        
        # 基于记忆检索结果生成建议
        relevance_score = processing_result["retrieval"].get("relevance_score", 0)
        if relevance_score > 0.7:
            recommendations.append("找到高度相关记忆，可以深度利用")
        elif relevance_score < 0.3:
            recommendations.append("相关记忆较少，建议主要基于当前对话")
        
        # 通用建议
        recommendations.append("保持一致的对话风格和语气")
        recommendations.append("考虑对话的历史上下文")
        
        return recommendations
    
    async def analyze_memory_usage(self,
                                 session_id: str,
                                 timeframe_hours: int = 24) -> Dict[str, Any]:
        """分析记忆系统使用情况"""
        logger.info(f"分析记忆使用情况: session={session_id}, 时间范围={timeframe_hours}小时")
        
        try:
            # 这里将实现实际的内存使用分析
            # 目前返回模拟数据
            
            analysis = {
                "session_id": session_id,
                "analysis_timeframe_hours": timeframe_hours,
                "summary": {
                    "total_entities": 0,  # 待实现
                    "total_relationships": 0,  # 待实现
                    "memory_utilization": "0%",  # 待实现
                    "retrieval_success_rate": "0%",  # 待实现
                    "average_processing_time": "0ms"  # 待实现
                },
                "trends": {
                    "entities_growth": "stable",  # 待实现
                    "relationships_complexity": "low",  # 待实现
                    "memory_efficiency": "high"  # 待实现
                },
                "recommendations": [
                    "定期清理不再使用的实体",
                    "优化关系存储结构",
                    "监控记忆检索性能"
                ],
                "status": "success"
            }
            
            logger.info(f"记忆分析完成: session={session_id}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"分析记忆使用情况时发生错误: {str(e)}")
            return {
                "session_id": session_id,
                "error": str(e),
                "status": "failed"
            }
