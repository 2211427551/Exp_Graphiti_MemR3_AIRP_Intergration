"""
Graphiti服务封装

提供Graphiti操作的封装，包括记忆存储、检索、变化检测、
心理连贯性评估和因果链追踪。

作者: AIRP项目团队
日期: 2026-01-13
版本: v4.0 (集成高级功能)
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from loguru import logger
from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType

from config.settings import AppSettings

# 导入高级功能模块
from advanced.change_detection import (
    detect_worldinfo_changes,
    detect_chat_changes,
    update_world_info_state,
    update_chat_history_state
)
from advanced.change_sync import (
    process_added_entries,
    process_removed_entries,
    process_modified_entries
)
from advanced.psychological_coherence import PsychologicalCoherenceEvaluator
from advanced.psychological_tracker import PsychologicalStateTracker
from advanced.causal_analyzer import CausalAnalyzer
from advanced.causal_reasoning import CausalReasoningEngine

from models.change_detection import (
    WorldInfoState,
    ChatHistoryState
)


class GraphitiService:
    """Graphiti服务封装类（集成高级功能）"""
    
    def __init__(self, settings: AppSettings):
        """
        初始化Graphiti服务
        
        参数:
            settings: 应用设置
        """
        self.settings = settings
        
        # Graphiti实例将在应用启动时初始化
        self.graphiti = None
        
        # 会话状态管理（WorldInfo和ChatHistory）
        self.world_info_states: Dict[str, WorldInfoState] = {}
        self.chat_history_states: Dict[str, ChatHistoryState] = {}
        
        # 高级功能模块（将在initialize中初始化）
        self.psychological_coherence: Optional[PsychologicalCoherenceEvaluator] = None
        self.psychological_tracker: Optional[PsychologicalStateTracker] = None
        self.causal_analyzer: Optional[CausalAnalyzer] = None
        self.causal_reasoning: Optional[CausalReasoningEngine] = None
        
        logger.info("Graphiti服务初始化完成")
    
    async def initialize(self, graphiti: Graphiti, llm_service=None):
        """
        初始化Graphiti客户端和高级功能模块
        
        参数:
            graphiti: Graphiti实例
            llm_service: LLM服务实例（用于高级功能）
        """
        self.graphiti = graphiti
        logger.info("Graphiti客户端已连接")
        
        # 初始化高级功能模块
        if llm_service:
            self.psychological_coherence = PsychologicalCoherenceEvaluator(self)
            self.psychological_tracker = PsychologicalStateTracker(self)
            self.causal_analyzer = CausalAnalyzer(llm_service)
            self.causal_reasoning = CausalReasoningEngine(self)
            logger.info("高级功能模块已初始化")
    
    async def process_content(
        self,
        session_id: str,
        parsed_content: Any
    ) -> Dict[str, int]:
        """
        处理解析后的内容
        
        流程：
        1. 遍历叙事性内容
        2. 调用Graphiti添加Episode
        3. 统计信息
        
        参数:
            session_id: 会话ID
            parsed_content: 解析后的内容对象
        
        返回:
            Dict[str, int]: {
                "episodes_added": int,
                "entities_extracted": int,
                "relationships_created": int
            }
        """
        logger.info(f"开始处理内容，会话ID: {session_id}")
        
        stats = {
            "episodes_added": 0,
            "entities_extracted": 0,
            "relationships_created": 0
        }
        
        # 提取叙事性内容
        narratives = []
        if hasattr(parsed_content, 'world_info') and parsed_content.world_info:
            for entry in parsed_content.world_info:
                narratives.append({
                    "content": entry.get("content", ""),
                    "type": "world_info",
                    "block_type": "world_info"
                })
        
        if hasattr(parsed_content, 'chat_history') and parsed_content.chat_history:
            # 将对话历史作为整体处理
            dialog_text = "\n".join([
                f"{msg.role}: {msg.content}"
                for msg in parsed_content.chat_history[-10:]  # 最近10轮
            ])
            narratives.append({
                "content": dialog_text,
                "type": "dialog",
                "block_type": "dialog_history",
                "metadata": {
                    "message_count": len(parsed_content.chat_history)
                }
            })
        
        # 处理每个叙事内容
        for narrative in narratives:
            try:
                # 调用Graphiti添加Episode
                result = await self.graphiti.add_episode(
                    name=self._generate_episode_name(narrative),
                    episode_body=narrative["content"],
                    source=EpisodeType.text,
                    source_description=narrative["block_type"],
                    reference_time=None,
                    group_id=session_id
                )
                
                # 统计
                stats["episodes_added"] += 1
                stats["entities_extracted"] += len(result.nodes)
                stats["relationships_created"] += len(result.edges)
                
                logger.debug(f"已添加Episode: {result.uuid}")
                
            except Exception as e:
                logger.error(f"处理内容失败: {e}")
        
        logger.info(f"内容处理完成，统计: {stats}")
        return stats
    
    async def search_memories(
        self,
        session_id: str,
        query: str,
        num_results: int = 10,
        similarity_threshold: float = 0.7,
        filter_condition: str = None
    ) -> List[Dict[str, Any]]:
        """
        搜索相关记忆
        
        流程：
        1. 调用Graphiti搜索
        2. 格式化返回结果
        
        参数:
            session_id: 会话ID（用于过滤）
            query: 搜索查询
            num_results: 返回结果数量
            similarity_threshold: 相似度阈值
            filter_condition: 过滤条件
        
        返回:
            List[Dict]: 记忆列表
        """
        logger.info(f"搜索记忆，查询: {query}, 会话: {session_id}")
        
        try:
            # 调用Graphiti搜索
            results = await self.graphiti.search(
                query=query,
                num_results=num_results,
                group_ids=[session_id] if session_id else None
            )
            
            # 格式化返回结果
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "uuid": result.uuid,
                    "fact": result.fact,
                    "score": result.score,
                    "valid_at": result.created_at.isoformat() if result.created_at else None,
                    "created_at": result.created_at.isoformat() if result.created_at else None
                })
            
            logger.info(f"搜索完成，找到 {len(formatted_results)} 个相关记忆")
            return formatted_results
            
        except Exception as e:
            logger.error(f"搜索记忆失败: {e}")
            return []
    
    async def process_response(
        self,
        session_id: str,
        response_content: str
    ):
        """
        异步处理LLM响应
        
        流程：
        1. 提取新信息
        2. 作为Episode添加到Graphiti
        3. 异步执行，不阻塞响应
        
        参数:
            session_id: 会话ID
            response_content: LLM响应内容
        """
        logger.info(f"异步处理响应，会话ID: {session_id}")
        
        try:
            # 添加响应到Graphiti
            result = await self.graphiti.add_episode(
                name=f"AI Response - {session_id}",
                episode_body=response_content,
                source=EpisodeType.message,
                source_description="ai_response",
                reference_time=None,
                group_id=session_id
            )
            
            logger.info(f"响应已存储: {result.uuid}")
            
        except Exception as e:
            logger.error(f"异步处理响应失败: {e}")
    
    def _generate_episode_name(self, narrative: Dict) -> str:
        """
        生成Episode名称
        
        参数:
            narrative: 叙事内容字典
        
        返回:
            str: Episode名称
        """
        content_type = narrative.get("type", "general")
        
        if content_type == "world_info":
            entry_type = narrative.get("block_type", "")
            return f"World Info - {entry_type}"
        
        elif content_type == "dialog":
            message_count = narrative.get("metadata", {}).get("message_count", 0)
            return f"Dialog History - {message_count} messages"
        
        else:
            return f"General Content - {content_type}"
    
    # ========== 变化检测集成 ==========
    
    async def process_content_with_change_detection(
        self,
        session_id: str,
        parsed_content: Any
    ) -> Dict[str, Any]:
        """
        处理内容（集成变化检测）
        
        流程：
        1. 检测World Info变化
        2. 检测Chat History变化
        3. 同步变化到Graphiti
        4. 返回处理结果
        
        参数:
            session_id: 会话ID
            parsed_content: 解析后的内容对象
        
        返回:
            Dict: 处理结果，包括变化信息
        """
        logger.info(f"处理内容（带变化检测），会话ID: {session_id}")
        
        result = {
            "changes_detected": {},
            "sync_stats": {},
            "stats": {
                "episodes_added": 0,
                "entities_extracted": 0,
                "relationships_created": 0
            }
        }
        
        # 处理World Info变化
        if hasattr(parsed_content, 'world_info') and parsed_content.world_info:
            # 提取World Info内容
            world_info_content = "\n\n".join([
                entry.get("content", "") 
                for entry in parsed_content.world_info
            ])
            
            # 获取旧状态
            old_state = self.world_info_states.get(session_id)
            
            # 检测变化
            changes = detect_worldinfo_changes(old_state, world_info_content, session_id)
            
            result["changes_detected"]["world_info"] = {
                "added": len(changes["added"]),
                "removed": len(changes["removed"]),
                "modified": len(changes["modified"]),
                "unchanged": len(changes["unchanged"])
            }
            
            # 同步变化
            if changes["added"]:
                added_stats = await process_added_entries(
                    self, changes["added"], session_id
                )
                result["sync_stats"]["world_info_added"] = added_stats
                result["stats"]["episodes_added"] += added_stats.get("entries_processed", 0)
                result["stats"]["entities_extracted"] += added_stats.get("entities_created", 0)
                result["stats"]["relationships_created"] += added_stats.get("relationships_created", 0)
            
            if changes["removed"]:
                removed_stats = await process_removed_entries(
                    self, changes["removed"], session_id
                )
                result["sync_stats"]["world_info_removed"] = removed_stats
            
            if changes["modified"]:
                modified_stats = await process_modified_entries(
                    self, changes["modified"], session_id
                )
                result["sync_stats"]["world_info_modified"] = modified_stats
                result["stats"]["episodes_added"] += modified_stats.get("new_episodes_created", 0)
            
            # 更新状态
            new_state = update_world_info_state(old_state or WorldInfoState(), changes)
            self.world_info_states[session_id] = new_state
        
        # 处理Chat History变化
        if hasattr(parsed_content, 'chat_history') and parsed_content.chat_history:
            # 提取Chat History内容
            chat_content = "\n".join([
                f"{msg.role}: {msg.content}"
                for msg in parsed_content.chat_history
            ])
            
            # 获取旧状态
            old_state = self.chat_history_states.get(session_id)
            
            # 检测变化
            chat_changes = detect_chat_changes(old_state, chat_content, session_id)
            
            result["changes_detected"]["chat_history"] = {
                "type": chat_changes.type,
                "message_count": chat_changes.message_count
            }
            
            # 如果有变化，添加到Graphiti
            if chat_changes.type in ["append", "modification"]:
                dialog_text = "\n".join([
                    f"{msg.role}: {msg.content}"
                    for msg in parsed_content.chat_history[-10:]
                ])
                
                add_result = await self.graphiti.add_episode(
                    name=f"Dialog History - {chat_changes.message_count} messages",
                    episode_body=dialog_text,
                    source=EpisodeType.text,
                    source_description="dialog_history",
                    reference_time=None,
                    group_id=session_id
                )
                
                result["stats"]["episodes_added"] += 1
                result["stats"]["entities_extracted"] += len(add_result.nodes)
                result["stats"]["relationships_created"] += len(add_result.edges)
            
            # 更新状态
            new_state = update_chat_history_state(old_state, chat_changes)
            self.chat_history_states[session_id] = new_state
        
        logger.info(f"内容处理完成（带变化检测），结果: {result}")
        return result
    
    def get_session_state(self, session_id: str) -> Dict[str, Any]:
        """
        获取会话的当前状态
        
        参数:
            session_id: 会话ID
        
        返回:
            Dict: 会话状态信息
        """
        return {
            "session_id": session_id,
            "world_info_state": {
                "version": self.world_info_states.get(session_id, WorldInfoState()).version,
                "entry_count": len(self.world_info_states.get(session_id, WorldInfoState()).entries)
            },
            "chat_history_state": {
                "version": self.chat_history_states.get(session_id, ChatHistoryState()).version,
                "message_count": len(self.chat_history_states.get(session_id, ChatHistoryState()).messages)
            }
        }
    
    # ========== 心理连贯性集成 ==========
    
    async def evaluate_psychological_coherence(
        self,
        character_id: str,
        time_window_days: int = 7
    ) -> Optional[Dict[str, Any]]:
        """
        评估角色的心理连贯性
        
        参数:
            character_id: 角色ID
            time_window_days: 时间窗口（天）
        
        返回:
            Dict: 连贯性得分，如果未初始化则返回None
        """
        if not self.psychological_coherence:
            logger.warning("心理连贯性评估器未初始化")
            return None
        
        try:
            from datetime import timedelta
            coherence = await self.psychological_coherence.evaluate_coherence(
                character_id=character_id,
                time_window=timedelta(days=time_window_days)
            )
            
            return {
                "character_id": character_id,
                "overall_score": coherence.overall_score,
                "trait_consistency": coherence.trait_consistency,
                "emotional_rationality": coherence.emotional_rationality,
                "behavioral_consistency": coherence.behavioral_consistency,
                "memory_rationality": coherence.memory_rationality
            }
        except Exception as e:
            logger.error(f"评估心理连贯性失败: {e}")
            return None
    
    async def track_psychological_state_transition(
        self,
        character_id: str,
        old_state: Any,
        new_state: Any,
        trigger_event: str
    ) -> bool:
        """
        跟踪心理状态转移
        
        参数:
            character_id: 角色ID
            old_state: 旧的心理状态
            new_state: 新的心理状态
            trigger_event: 触发事件
        
        返回:
            bool: 是否成功
        """
        if not self.psychological_tracker:
            logger.warning("心理状态跟踪器未初始化")
            return False
        
        try:
            await self.psychological_tracker.track_state_transition(
                character_id=character_id,
                old_state=old_state,
                new_state=new_state,
                trigger_event=trigger_event
            )
            return True
        except Exception as e:
            logger.error(f"跟踪心理状态转移失败: {e}")
            return False
    
    def get_character_psychological_history(
        self,
        character_id: str,
        limit: int = 50
    ) -> List[Any]:
        """
        获取角色的心理状态历史
        
        参数:
            character_id: 角色ID
            limit: 最大返回数量
        
        返回:
            List: 心理状态列表
        """
        if not self.psychological_tracker:
            logger.warning("心理状态跟踪器未初始化")
            return []
        
        return self.psychological_tracker.get_character_history(
            character_id=character_id,
            limit=limit
        )
    
    # ========== 因果推理集成 ==========
    
    async def extract_causal_relations(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        从文本中提取因果关系
        
        参数:
            text: 文本内容
            context: 上下文信息
        
        返回:
            Dict: 因果关系，如果未初始化则返回None
        """
        if not self.causal_analyzer:
            logger.warning("因果分析器未初始化")
            return None
        
        try:
            return await self.causal_analyzer.extract_causal_relations(text, context)
        except Exception as e:
            logger.error(f"提取因果关系失败: {e}")
            return None
    
    async def trace_causal_chain(
        self,
        start_event_id: str,
        direction: str = "forward",
        max_depth: int = 5,
        min_strength: float = 0.5,
        session_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        追踪因果链
        
        参数:
            start_event_id: 起始事件ID
            direction: "forward"（向前）或"backward"（向后）
            max_depth: 最大深度
            min_strength: 最小因果强度
            session_id: 会话ID
        
        返回:
            Dict: 因果链，如果未初始化则返回None
        """
        if not self.causal_reasoning:
            logger.warning("因果推理引擎未初始化")
            return None
        
        try:
            chain = await self.causal_reasoning.trace_causal_chain(
                start_event_id=start_event_id,
                direction=direction,
                max_depth=max_depth,
                min_strength=min_strength,
                session_id=session_id
            )
            
            return {
                "start_event_id": start_event_id,
                "direction": direction,
                "total_paths": chain.total_paths,
                "max_depth": chain.max_depth,
                "min_strength": chain.min_strength,
                "paths": chain.paths
            }
        except Exception as e:
            logger.error(f"追踪因果链失败: {e}")
            return None
    
    async def deduce_consequences(
        self,
        current_event_id: str,
        scenario_conditions: Optional[Dict[str, Any]] = None,
        max_depth: int = 3,
        min_strength: float = 0.6,
        session_id: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        推演事件后果
        
        参数:
            current_event_id: 当前事件ID
            scenario_conditions: 场景条件
            max_depth: 最大深度
            min_strength: 最小因果强度
            session_id: 会话ID
        
        返回:
            List: 可能的后果列表，如果未初始化则返回None
        """
        if not self.causal_reasoning:
            logger.warning("因果推理引擎未初始化")
            return None
        
        try:
            consequences = await self.causal_reasoning.deduce_consequences(
                current_event_id=current_event_id,
                scenario_conditions=scenario_conditions,
                max_depth=max_depth,
                min_strength=min_strength,
                session_id=session_id
            )
            
            return [
                {
                    "event_id": c.event_id,
                    "event_description": c.event_description,
                    "probability": c.probability,
                    "steps": c.steps,
                    "conditions_needed": c.conditions_needed,
                    "exceptions": c.exceptions
                }
                for c in consequences
            ]
        except Exception as e:
            logger.error(f"推演事件后果失败: {e}")
            return None
