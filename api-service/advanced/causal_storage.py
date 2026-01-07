"""
因果链存储服务

处理事件和因果关系到Graphiti的存储操作
"""

from datetime import datetime, timezone
from typing import Dict, List

from .causal_modeling import (
    EventEntity,
    CausalRelation
)


async def store_causal_chain(
    graphiti_service,
    events: List[EventEntity],
    causal_relations: List[CausalRelation],
    session_id: str
) -> Dict[str, int]:
    """
    存储因果链到Graphiti
    
    流程：
    1. 创建事件节点
    2. 创建因果关系边
    3. 设置时间属性
    
    参数:
        graphiti_service: Graphiti服务实例
        events: 事件列表
        causal_relations: 因果关系列表
        session_id: 会话ID
    
    返回:
        Dict: 处理结果统计
    """
    
    # 步骤1: 创建事件节点
    event_id_map = {}  # 事件描述 -> event_id
    
    for event in events:
        # 调用Graphiti创建Episode（事件）
        result = await graphiti_service.graphiti.add_episode(
            name=event.name,
            episode_body=event.description,
            source="text",
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
    
    return {
        "events_stored": len(events),
        "relations_stored": len(causal_relations)
    }


async def create_causal_relation_edge(
    graphiti_service,
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
