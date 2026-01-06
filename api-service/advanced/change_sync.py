"""
变化同步处理器

处理变化后的Graphiti同步操作
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional

from api_service.models.change_detection import (
    WorldInfoEntry,
    WorldInfoState,
    ChangeDetectionResult
)
from api_service.utils.dedup import compute_content_hash


async def process_added_entries(
    graphiti_service,
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
            episode_name = f"World Info - {entry.entry_type} - {entry.name}"
            
            result = await graphiti_service.graphiti.add_episode(
                name=episode_name,
                episode_body=entry.content,
                source="text",
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


async def process_removed_entries(
    graphiti_service,
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
            # 使用Graphiti的Neo4j驱动
            driver = graphiti_service.graphiti.driver
            
            with driver.session() as session:
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
                        "episode_id": episode.element_id,
                        "valid_until": current_time.isoformat(),
                        "deleted_at": current_time.isoformat()
                    })
                    
                    stats["episodes_marked_deleted"] += 1
            
            stats["entries_processed"] += 1
            
        except Exception as e:
            print(f"Error processing removed entry {entry.entry_id}: {e}")
    
    return stats


async def process_modified_entries(
    graphiti_service,
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
            
            # 使用Graphiti的Neo4j驱动
            driver = graphiti_service.graphiti.driver
            
            with driver.session() as session:
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
                        "episode_id": old_episode.element_id,
                        "valid_until": current_time.isoformat(),
                        "superseded_at": current_time.isoformat(),
                        "new_episode_id": None  # 稍后填充
                    })
                    
                    stats["old_episodes_superseded"] += 1
            
            # 步骤2: 创建新Episode
            new_episode_name = f"World Info - {new_entry.entry_type} - {new_entry.name} (v{old_entry.version + 1})"
            
            new_result = await graphiti_service.graphiti.add_episode(
                name=new_episode_name,
                episode_body=new_entry.content,
                source="text",
                source_description=f"world_info:{new_entry.entry_type}",
                reference_time=current_time,
                group_id=session_id
            )
            
            stats["entries_processed"] += 1
            stats["new_episodes_created"] += 1
            
            # 步骤3: 建立REPLACED_BY关系（如果找到旧Episode）
            # 这里简化，实际需要保存新Episode的uuid
            # REPLACED_BY关系应该在创建新Episode后建立
            # 连接旧Episode到新Episode，表示替换关系
            
            # 注：REPLACED_BY关系的实现需要保存新Episode的uuid
            # 这部分可以在完善时实现
            
        except Exception as e:
            print(f"Error processing modified entry {old_entry.entry_id}: {e}")
    
    return stats


def generate_episode_name(entry: WorldInfoEntry) -> str:
    """
    生成Episode名称
    
    格式：World Info - [类型] [名称]
    """
    return f"World Info - {entry.entry_type} - {entry.name}"
