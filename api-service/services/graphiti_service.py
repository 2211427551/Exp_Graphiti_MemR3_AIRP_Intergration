# ============================================
# Graphiti服务封装
# ============================================
from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import logging

from services.parser_service import ParsedContent, NarrativeBlock

logger = logging.getLogger(__name__)


class GraphitiService:
    """Graphiti服务封装类"""
    
    def __init__(self, graphiti_client: Graphiti):
        """
        初始化Graphiti服务
        
        参数:
            graphiti_client: Graphiti
                Graphiti客户端实例
        """
        self.graphiti = graphiti_client
        logger.info("Graphiti服务初始化完成")
    
    async def process_content(
        self,
        session_id: str,
        parsed_content: ParsedContent
    ) -> Dict[str, int]:
        """
        处理解析后的内容
        
        参数:
            session_id: str
                会话ID
            parsed_content: ParsedContent
                解析后的内容
        
        返回:
            Dict[str, int]: 处理统计
                {
                    "episodes_added": int,
                    "entities_extracted": int,
                    "relationships_created": int
                }
        
        流程:
            1. 对于叙事性内容，调用add_episode()
            2. 实体关系提取
            3. 去重和合并
            4. 存储到知识图谱
        
        注意：
            - 指令性内容不入图谱
            - 每个NarrativeBlock作为一个Episode
        """
        stats = {
            "episodes_added": 0,
            "entities_extracted": 0,
            "relationships_created": 0
        }
        
        logger.info(f"处理内容 - 会话ID: {session_id}, 叙事块数: {len(parsed_content.narratives)}")
        
        # 步骤1: 处理叙事性内容
        for narrative in parsed_content.narratives:
            try:
                # 调用Graphiti的add_episode方法
                result = await self.graphiti.add_episode(
                    name=self._generate_episode_name(narrative),
                    episode_body=narrative.content,
                    source=self._determine_episode_type(narrative),
                    source_description=narrative.block_type,
                    reference_time=datetime.now(timezone.utc),
                    group_id=session_id
                )
                
                # 统计
                stats["episodes_added"] += 1
                stats["entities_extracted"] += len(result.nodes)
                stats["relationships_created"] += len(result.edges)
                
                logger.debug(f"Episode添加成功 - 名称: {result.episode.name}, 实体: {len(result.nodes)}, 关系: {len(result.edges)}")
                
            except Exception as e:
                # 记录错误但继续处理
                logger.error(f"添加Episode失败: {e}", exc_info=True)
        
        logger.info(f"内容处理完成 - Episodes: {stats['episodes_added']}, 实体: {stats['entities_extracted']}, 关系: {stats['relationships_created']}")
        return stats
    
    async def search_memories(
        self,
        session_id: str,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        搜索相关记忆
        
        参数:
            session_id: str
                会话ID（用于过滤）
            query: str
                搜索查询（自然语言）
            limit: int
                返回结果数量限制
        
        返回:
            List[Dict[str, Any]]: 检索到的记忆
                [
                    {
                        "uuid": str,
                        "fact": str,
                        "score": float,
                        "valid_at": str,
                        "created_at": str
                    },
                    ...
                ]
        
        流程:
            1. 调用Graphiti的search方法
            2. 指定group_id过滤（当前会话）
            3. 指定num_results限制
            4. 格式化返回结果
        
        注意：
            - 使用Graphiti的混合检索（向量+图）
            - 自动使用Reranker重排序
        """
        logger.debug(f"搜索记忆 - 会话ID: {session_id}, 查询: {query}, 限制: {limit}")
        
        try:
            # 调用Graphiti的search方法
            search_result = await self.graphiti.search(
                query=query,
                num_results=limit,
                group_ids=[session_id] if session_id else None
            )
            
            # 格式化返回结果
            formatted_memories = []
            for result in search_result.results:
                formatted_memories.append({
                    "uuid": result.uuid,
                    "fact": result.fact,
                    "score": result.score if hasattr(result, 'score') else 1.0,
                    "valid_at": result.valid_at.isoformat() if result.valid_at else None,
                    "created_at": result.created_at.isoformat() if result.created_at else None
                })
            
            logger.info(f"记忆搜索完成 - 找到 {len(formatted_memories)} 条记忆")
            return formatted_memories
            
        except Exception as e:
            logger.error(f"搜索记忆失败: {e}", exc_info=True)
            return []
    
    async def process_response(
        self,
        session_id: str,
        response_content: str
    ) -> None:
        """
        处理LLM响应（异步）
        
        参数:
            session_id: str
                会话ID
            response_content: str
                LLM响应内容
        
        流程:
            1. 提取新信息
            2. 作为Episode添加到Graphiti
            3. 异步执行，不阻塞响应
        
        注意：
            - 这个方法应该是异步的
            - 不影响主响应流程
        """
        logger.debug(f"处理LLM响应 - 会话ID: {session_id}, 长度: {len(response_content)}")
        
        try:
            # 添加响应作为Episode
            await self.graphiti.add_episode(
                name=f"Assistant Response - {datetime.now(timezone.utc).isoformat()}",
                episode_body=response_content,
                source=EpisodeType.message,
                source_description="LLM Response",
                reference_time=datetime.now(timezone.utc),
                group_id=session_id
            )
            logger.info(f"LLM响应已存储 - 会话ID: {session_id}")
            
        except Exception as e:
            logger.error(f"处理响应失败: {e}", exc_info=True)
    
    def _generate_episode_name(self, narrative: NarrativeBlock) -> str:
        """
        生成Episode名称
        
        参数:
            narrative: NarrativeBlock
                叙事性内容块
        
        返回:
            str: Episode名称
        """
        if narrative.block_type == 'world_info':
            location = narrative.metadata.get('location', 'Unknown')
            return f"World Info - {location}"
        elif narrative.block_type == 'dialog':
            return f"Dialog - {datetime.now(timezone.utc).isoformat()}"
        else:
            return f"General Content - {datetime.now(timezone.utc).isoformat()}"
    
    def _determine_episode_type(self, narrative: NarrativeBlock) -> EpisodeType:
        """
        确定Episode类型
        
        参数:
            narrative: NarrativeBlock
                叙事性内容块
        
        返回:
            EpisodeType: Graphiti Episode类型
        """
        type_mapping = {
            'world_info': EpisodeType.text,
            'dialog': EpisodeType.message,
            'supplementary': EpisodeType.text,
            'general': EpisodeType.text
        }
        return type_mapping.get(narrative.block_type, EpisodeType.text)
