import logging
from typing import Dict, Any, List, Optional
from neo4j import GraphDatabase
import json
import uuid
from datetime import datetime
import os
import sys

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 获取项目根目录
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_path = os.path.join(project_root, 'config', 'settings.py')

# 动态导入配置
import importlib.util
spec = importlib.util.spec_from_file_location("settings", config_path)
settings_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(settings_module)
settings = settings_module.settings

logger = logging.getLogger(__name__)

class GraphitiService:
    """Graphiti时序知识图谱服务"""
    
    # 基础关系类型定义（有限的5种类型）
    BASIC_RELATION_TYPES = {
        "HAS_RELATION_WITH",      # 社交关系基类
        "HAS_ASSOCIATION_WITH",   # 关联关系基类  
        "HAS_TEMPORAL_ORDER",     # 时序关系
        "HAS_CAUSAL_LINK",        # 因果关系
        "HAS_SPATIAL_RELATION"    # 空间关系
    }
    
    # 关系子类型标签枚举（可扩展）
    RELATION_SUBTYPES = {
        # HAS_RELATION_WITH子类型
        "friend": "朋友关系",
        "lover": "爱恋关系", 
        "enemy": "敌对关系",
        "family": "家庭关系",
        "colleague": "同事关系",
        "mentor": "导师关系",
        "rival": "竞争对手关系",
        "acquaintance": "熟人关系",
        "follower": "追随关系",
        
        # HAS_ASSOCIATION_WITH子类型
        "member_of": "成员关系",
        "owner_of": "拥有关系",
        "creator_of": "创造关系",
        "part_of": "组成部分关系",
        "related_to": "相关关系",
        
        # 通用子类型
        "similar_to": "相似关系",
        "different_from": "不同关系"
    }
    
    def __init__(self):
        """初始化Graphiti服务"""
        self.driver = None
        self._initialize_driver()
        
    def _initialize_driver(self):
        """初始化Neo4j驱动"""
        try:
            self.driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
            # 测试连接
            with self.driver.session() as session:
                result = session.run("RETURN 1 AS test")
                if result.single()["test"] == 1:
                    logger.info("Neo4j连接成功")
                else:
                    logger.error("Neo4j连接测试失败")
        except Exception as e:
            logger.error(f"Neo4j连接失败: {str(e)}")
            self.driver = None
    
    def close(self):
        """关闭驱动连接"""
        if self.driver:
            self.driver.close()
    
    def create_entity(self, session_id: str, entity_data: Dict[str, Any]) -> Optional[str]:
        """创建实体（支持双时序模型）"""
        if not self.driver:
            logger.error("Graphiti服务未初始化")
            return None
        
        try:
            entity_id = entity_data.get("entity_id") or str(uuid.uuid4())
            entity_type = entity_data.get("entity_type", "Unknown")
            name = entity_data.get("name", "")
            
            # 提取时间属性（支持双时序）
            properties = entity_data.get("properties", {})
            
            # 确保有时间属性
            if "valid_from" not in properties:
                properties["valid_from"] = datetime.now().isoformat()
            if "valid_until" not in properties:
                properties["valid_until"] = "infinity"  # 默认无限期有效
            
            # 状态字段（语义补充）
            if "status" not in properties:
                properties["status"] = "active"
            
            query = """
            CREATE (e:Entity {
                entity_id: $entity_id,
                session_id: $session_id,
                entity_type: $entity_type,
                name: $name,
                properties: $properties,
                created_at: $created_at,
                updated_at: $updated_at,
                valid_from: $valid_from,
                valid_until: $valid_until,
                status: $status
            })
            RETURN e.entity_id AS entity_id
            """
            
            with self.driver.session() as session:
                result = session.run(
                    query,
                    entity_id=entity_id,
                    session_id=session_id,
                    entity_type=entity_type,
                    name=name,
                    properties=json.dumps(properties),
                    created_at=datetime.now().isoformat(),
                    updated_at=datetime.now().isoformat(),
                    valid_from=properties["valid_from"],
                    valid_until=properties["valid_until"],
                    status=properties["status"]
                )
                
                entity_id = result.single()["entity_id"]
                logger.info(f"创建实体成功: {entity_id}")
                return entity_id
                
        except Exception as e:
            logger.error(f"创建实体失败: {str(e)}")
            return None
    
    def create_relationship(self, session_id: str, 
                          source_entity_id: str, 
                          target_entity_id: str,
                          relation_type: str,
                          properties: Optional[Dict[str, Any]] = None,
                          relation_subtype: Optional[str] = None,
                          time_bounds: Optional[Dict[str, str]] = None) -> Optional[str]:
        """创建关系（支持标签化模型和双时序）"""
        if not self.driver:
            logger.error("Graphiti服务未初始化")
            return None
        
        try:
            relationship_id = str(uuid.uuid4())
            
            # 构建关系属性
            props = properties or {}
            
            # 添加子类型标签
            if relation_subtype:
                props["relation_subtype"] = relation_subtype
                props["subtype_label"] = self.RELATION_SUBTYPES.get(relation_subtype, relation_subtype)
            
            # 添加时间边界（双时序支持）
            if time_bounds:
                props.update({
                    "valid_from": time_bounds.get("valid_from", datetime.now().isoformat()),
                    "valid_until": time_bounds.get("valid_until", "infinity")
                })
            else:
                props.update({
                    "valid_from": datetime.now().isoformat(),
                    "valid_until": "infinity"
                })
            
            # 关系状态
            if "status" not in props:
                props["status"] = "active"
            
            query = """
            MATCH (source:Entity {entity_id: $source_entity_id, session_id: $session_id})
            MATCH (target:Entity {entity_id: $target_entity_id, session_id: $session_id})
            CREATE (source)-[r:RELATIONSHIP {
                relationship_id: $relationship_id,
                relation_type: $relation_type,
                properties: $properties,
                created_at: $created_at,
                valid_from: $valid_from,
                valid_until: $valid_until,
                status: $status
            }]->(target)
            RETURN r.relationship_id AS relationship_id
            """
            
            with self.driver.session() as session:
                result = session.run(
                    query,
                    session_id=session_id,
                    source_entity_id=source_entity_id,
                    target_entity_id=target_entity_id,
                    relationship_id=relationship_id,
                    relation_type=relation_type,
                    properties=json.dumps(props),
                    created_at=datetime.now().isoformat(),
                    valid_from=props["valid_from"],
                    valid_until=props["valid_until"],
                    status=props["status"]
                )
                
                relationship_id = result.single()["relationship_id"]
                logger.info(f"创建关系成功: {relationship_id}")
                return relationship_id
                
        except Exception as e:
            logger.error(f"创建关系失败: {str(e)}")
            return None
    
    def search_entities(self, session_id: str, 
                       entity_type: Optional[str] = None,
                       name: Optional[str] = None,
                       properties: Optional[Dict[str, Any]] = None,
                       limit: int = 100) -> List[Dict[str, Any]]:
        """搜索实体"""
        if not self.driver:
            logger.error("Graphiti服务未初始化")
            return []
        
        try:
            conditions = []
            params = {"session_id": session_id, "limit": limit}
            
            if entity_type:
                conditions.append("e.entity_type = $entity_type")
                params["entity_type"] = entity_type
            
            if name:
                conditions.append("e.name CONTAINS $name")
                params["name"] = name
            
            # 简单属性搜索 - 可以扩展为更复杂的查询
            where_clause = " AND ".join(conditions) if conditions else "true"
            
            query = f"""
            MATCH (e:Entity {{session_id: $session_id}})
            WHERE {where_clause}
            RETURN e.entity_id AS entity_id,
                   e.entity_type AS entity_type,
                   e.name AS name,
                   e.properties AS properties,
                   e.created_at AS created_at,
                   e.updated_at AS updated_at,
                   e.valid_from AS valid_from,
                   e.valid_until AS valid_until,
                   e.status AS status
            LIMIT $limit
            """
            
            with self.driver.session() as session:
                result = session.run(query, **params)
                entities = []
                
                for record in result:
                    entity_data = {
                        "entity_id": record["entity_id"],
                        "entity_type": record["entity_type"],
                        "name": record["name"],
                        "properties": json.loads(record["properties"]) if record["properties"] else {},
                        "created_at": record["created_at"],
                        "updated_at": record["updated_at"],
                        "valid_from": record["valid_from"],
                        "valid_until": record["valid_until"],
                        "status": record["status"]
                    }
                    entities.append(entity_data)
                
                return entities
                
        except Exception as e:
            logger.error(f"搜索实体失败: {str(e)}")
            return []
    
    def get_related_entities(self, session_id: str, 
                           entity_id: str,
                           relation_types: Optional[List[str]] = None,
                           relation_subtypes: Optional[List[str]] = None,
                           direction: str = "both",
                           limit: int = 50) -> List[Dict[str, Any]]:
        """获取相关实体（支持关系子类型过滤）"""
        if not self.driver:
            logger.error("Graphiti服务未初始化")
            return []
        
        try:
            direction_clause = ""
            if direction == "outgoing":
                direction_clause = "->"
            elif direction == "incoming":
                direction_clause = "<-"
            else:  # both
                direction_clause = "-"
            
            params = {
                "session_id": session_id,
                "entity_id": entity_id,
                "limit": limit
            }
            
            relation_filter = []
            
            if relation_types and len(relation_types) > 0:
                relation_filter.append("r.relation_type IN $relation_types")
                params["relation_types"] = relation_types
            
            if relation_subtypes and len(relation_subtypes) > 0:
                relation_filter.append("r.properties.relation_subtype IN $relation_subtypes")
                params["relation_subtypes"] = relation_subtypes
            
            where_clause = " AND ".join(relation_filter) if relation_filter else "true"
            
            query = f"""
            MATCH (e:Entity {{entity_id: $entity_id, session_id: $session_id}})
            MATCH (e){direction_clause}[r]{direction_clause}(related:Entity {{session_id: $session_id}})
            WHERE {where_clause}
            RETURN related.entity_id AS entity_id,
                   related.entity_type AS entity_type,
                   related.name AS name,
                   related.properties AS properties,
                   related.valid_from AS valid_from,
                   related.valid_until AS valid_until,
                   r.relation_type AS relation_type,
                   r.properties AS relation_properties,
                   r.valid_from AS relation_valid_from,
                   r.valid_until AS relation_valid_until
            LIMIT $limit
            """
            
            with self.driver.session() as session:
                result = session.run(query, **params)
                related_entities = []
                
                for record in result:
                    # 解析属性
                    rel_props = json.loads(record["relation_properties"]) if record["relation_properties"] else {}
                    
                    entity_data = {
                        "entity_id": record["entity_id"],
                        "entity_type": record["entity_type"],
                        "name": record["name"],
                        "properties": json.loads(record["properties"]) if record["properties"] else {},
                        "valid_from": record["valid_from"],
                        "valid_until": record["valid_until"],
                        "relation_type": record["relation_type"],
                        "relation_subtype": rel_props.get("relation_subtype"),
                        "relation_properties": rel_props,
                        "relation_valid_from": record["relation_valid_from"],
                        "relation_valid_until": record["relation_valid_until"]
                    }
                    related_entities.append(entity_data)
                
                return related_entities
                
        except Exception as e:
            logger.error(f"获取相关实体失败: {str(e)}")
            return []
    
    def delete_session_data(self, session_id: str) -> bool:
        """删除会话数据"""
        if not self.driver:
            logger.error("Graphiti服务未初始化")
            return False
        
        try:
            query = """
            MATCH (e:Entity {session_id: $session_id})
            DETACH DELETE e
            RETURN count(e) AS deleted_count
            """
            
            with self.driver.session() as session:
                result = session.run(query, session_id=session_id)
                deleted_count = result.single()["deleted_count"]
                logger.info(f"删除会话数据成功: {session_id}, 删除实体数: {deleted_count}")
                return True
                
        except Exception as e:
            logger.error(f"删除会话数据失败: {str(e)}")
            return False
    
    def update_entity_status(self, session_id: str, entity_id: str, 
                           new_status: str, reason: Optional[str] = None,
                           replaced_by: Optional[str] = None,
                           valid_until: Optional[str] = None) -> bool:
        """更新实体状态（语义状态变更）"""
        if not self.driver:
            logger.error("Graphiti服务未初始化")
            return False
        
        try:
            # 获取当前实体
            query = """
            MATCH (e:Entity {session_id: $session_id, entity_id: $entity_id})
            RETURN e
            """
            
            with self.driver.session() as session:
                result = session.run(query, session_id=session_id, entity_id=entity_id)
                entity_record = result.single()
                
                if not entity_record:
                    logger.error(f"实体不存在: {entity_id}")
                    return False
                
                entity = entity_record["e"]
                
                # 更新状态和属性
                update_query = """
                MATCH (e:Entity {session_id: $session_id, entity_id: $entity_id})
                SET e.status = $new_status,
                    e.updated_at = $updated_at
                """
                
                params = {
                    "session_id": session_id,
                    "entity_id": entity_id,
                    "new_status": new_status,
                    "updated_at": datetime.now().isoformat()
                }
                
                # 如果有失效时间，更新valid_until
                if valid_until:
                    update_query += ", e.valid_until = $valid_until"
                    params["valid_until"] = valid_until
                
                # 更新属性
                properties = json.loads(entity["properties"]) if isinstance(entity["properties"], str) else entity["properties"]
                
                if reason:
                    properties["status_reason"] = reason
                if replaced_by:
                    properties["replaced_by"] = replaced_by
                
                update_query += ", e.properties = $properties"
                params["properties"] = json.dumps(properties)
                
                # 执行更新
                session.run(update_query, **params)
                
                logger.info(f"更新实体状态成功: {entity_id} -> {new_status}")
                return True
                
        except Exception as e:
            logger.error(f"更新实体状态失败: {str(e)}")
            return False
    
    def find_similar_entities(self, session_id: str, entity_data: Dict[str, Any], 
                            similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """查找相似实体（基于关键特征）"""
        if not self.driver:
            logger.error("Graphiti服务未初始化")
            return []
        
        try:
            # 提取关键特征
            key_features = {
                "entity_type": entity_data.get("entity_type", ""),
                "name": entity_data.get("name", ""),
                "main_properties": entity_data.get("properties", {})
            }
            
            # 简单相似度查询（可扩展为更复杂的算法）
            query = """
            MATCH (e:Entity {session_id: $session_id})
            WHERE e.entity_type = $entity_type 
               OR e.name CONTAINS $name_part
            RETURN e.entity_id AS entity_id,
                   e.entity_type AS entity_type,
                   e.name AS name,
                   e.properties AS properties,
                   e.valid_from AS valid_from,
                   e.status AS status
            LIMIT 20
            """
            
            params = {
                "session_id": session_id,
                "entity_type": key_features["entity_type"],
                "name_part": key_features["name"][:3] if len(key_features["name"]) > 3 else key_features["name"]
            }
            
            with self.driver.session() as session:
                result = session.run(query, **params)
                similar_entities = []
                
                for record in result:
                    entity_data = {
                        "entity_id": record["entity_id"],
                        "entity_type": record["entity_type"],
                        "name": record["name"],
                        "properties": json.loads(record["properties"]) if record["properties"] else {},
                        "valid_from": record["valid_from"],
                        "status": record["status"]
                    }
                    similar_entities.append(entity_data)
                
                return similar_entities
                
        except Exception as e:
            logger.error(f"查找相似实体失败: {str(e)}")
            return []
