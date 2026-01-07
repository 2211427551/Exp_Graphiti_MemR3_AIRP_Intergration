"""
因果推理引擎

实现因果链遍历、事件推演和后果预测
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from .causal_modeling import EventEntity, CausalRelation, CausalChain, Consequence


class CausalReasoningEngine:
    """因果推理引擎"""
    
    def __init__(self, graphiti_service):
        self.graphiti_service = graphiti_service
    
    async def trace_causal_chain(
        self,
        start_event_id: str,
        direction: str = "forward",
        max_depth: int = 5,
        min_strength: float = 0.5,
        session_id: str = None
    ) -> CausalChain:
        """
        追踪因果链
        
        参数:
            start_event_id: 起始事件ID
            direction: "forward"（向前追踪后果）或"backward"（向后追溯原因）
            max_depth: 最大深度
            min_strength: 最小因果强度阈值
            session_id: 会话ID
        
        返回:
            CausalChain: 因果链
        """
        
        # 构建Cypher查询
        if direction == "forward":
            query = """
            MATCH path = (start:Episode)-[:HAS_CAUSAL_LINK*1..{max_depth}]->(end:Episode)
            WHERE elementId(start) = $start_event_id
              AND (start.valid_until IS NULL OR start.valid_until > $current_time)
              AND (end.valid_until IS NULL OR end.valid_until > $current_time)
            AND all(r IN relationships(path) WHERE r.causal_strength >= $min_strength)
            """
            
            if session_id:
                query += "AND start.group_id = $session_id"
                query += "AND end.group_id = $session_id"
                
                query_params = {
                    "start_event_id": start_event_id,
                    "current_time": datetime.now(timezone.utc).isoformat(),
                    "session_id": session_id,
                    "max_depth": max_depth,
                    "min_strength": min_strength
                }
            else:
                query_params = {
                    "start_event_id": start_event_id,
                    "current_time": datetime.now(timezone.utc).isoformat(),
                    "max_depth": max_depth,
                    "min_strength": min_strength
                }
        else:  # backward
            query = """
            MATCH path = (end:Episode)<-[:HAS_CAUSAL_LINK*1..{max_depth}]-(start:Episode)
            WHERE elementId(start) = $start_event_id
              AND (start.valid_until IS NULL OR start.valid_until > $current_time)
              AND (end.valid_until IS NULL OR end.valid_until > $current_time)
              AND all(r IN relationships(path) WHERE r.causal_strength >= $min_strength)
            """
            
            if session_id:
                query += "AND start.group_id = $session_id"
                query += "AND end.group_id = $session_id"
                
                query_params = {
                    "start_event_id": start_event_id,
                    "current_time": datetime.now(timezone.utc).isoformat(),
                    "session_id": session_id,
                    "max_depth": max_depth,
                    "min_strength": min_strength
                }
            else:
                query_params = {
                    "start_event_id": start_event_id,
                    "current_time": datetime.now(timezone.utc).isoformat(),
                    "max_depth": max_depth,
                    "min_strength": min_strength
                }
        
        # 执行查询
        driver = self.graphiti_service.graphiti.driver
        
        causal_chain = CausalChain(paths=[], total_paths=0, max_depth=0, min_strength=0.0)
        
        with driver.session() as session:
            result = session.run(query, query_params)
            
            for record in result:
                path = record["path"]
                
                # 提取事件和关系
                events = []
                relations = []
                
                for node in path.nodes:
                    events.append({
                        "id": node.element_id,
                        "name": node["name"],
                        "description": node["episode_body"],
                        "event_type": node.get("source_description", "")
                    })
                
                for rel in path.relationships:
                    relations.append({
                        "type": rel["relation_subtype"],
                        "strength": rel["causal_strength"],
                        "from": rel.start_node.element_id,
                        "to": rel.end_node.element_id,
                        "necessity_score": rel.get("necessity_score", 0.5),
                        "sufficiency_score": rel.get("sufficiency_score", 0.5)
                    })
                
                causal_chain.paths.append({
                    "events": events,
                    "relations": relations
                })
                
                causal_chain.total_paths += 1
        
        return causal_chain
    
    async def deduce_consequences(
        self,
        current_event_id: str,
        scenario_conditions: Optional[Dict[str, Any]] = None,
        max_depth: int = 3,
        min_strength: float = 0.6,
        session_id: str = None
    ) -> List[Consequence]:
        """
        推演事件后果
        
        算法：
        1. 追踪因果链（向前）
        2. 检查前提条件是否满足
        3. 评估可能性
        4. 返回可能的后果
        
        参数:
            current_event_id: 当前事件ID
            scenario_conditions: 场景条件
            max_depth: 最大深度
            min_strength: 最小因果强度
            session_id: 会话ID
        
        返回:
            List[Consequence]: 可能的后果列表
        """
        
        # 步骤1: 追踪因果链（向前）
        causal_chain = await self.trace_causal_chain(
            start_event_id=current_event_id,
            direction="forward",
            max_depth=max_depth,
            min_strength=min_strength,
            session_id=session_id
        )
        
        # 步骤2: 评估每个后果的可能性
        consequences = []
        
        for path in causal_chain.paths:
            if len(path["events"]) > 1:  # 至少有一个后续事件
                final_event = path["events"][-1]
                final_relation = path["relations"][-1]
                
                # 检查条件
                conditions_met = self._check_conditions(
                    final_relation.get("conditions", []),
                    scenario_conditions or {}
                )
                
                # 检查例外
                exceptions_applied = self._check_exceptions(
                    final_relation.get("exceptions", []),
                    scenario_conditions or {}
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
                    exceptions=final_relation.get("exceptions", []),
                    causal_path=path
                ))
        
        # 按概率排序
        consequences.sort(key=lambda c: c.probability, reverse=True)
        
        return consequences
    
    def _check_conditions(self, conditions: List[str], scenario: Dict[str, Any]) -> bool:
        """
        检查前提条件是否满足
        
        参数:
            conditions: 条件列表
            scenario: 场景条件
        
        返回:
            bool: 所有条件是否满足
        """
        if not conditions:
            return True
        
        for condition in conditions:
            # 简化的条件检查
            condition_lower = condition.lower()
            
            # 检查角色
            if "角色" in condition_lower:
                role_name = condition.split("角色")[-1].strip()
                if f"character_{role_name}" not in scenario:
                    return False
            
            # 检查地点
            elif "地点" in condition_lower:
                location_name = condition.split("地点")[-1].strip()
                if f"location_{location_name}" not in scenario:
                    return False
            
            # 检查时间
            elif "时间" in condition_lower:
                # 时间条件检查需要具体实现
                pass
            
            # 检查状态
            elif "状态" in condition_lower:
                status_name = condition.split("状态")[-1].strip()
                if scenario.get(f"state_{status_name}", "") != "true":
                    return False
        
        return True
    
    def _check_exceptions(self, exceptions: List[str], scenario: Dict[str, Any]) -> bool:
        """
        检查是否触发例外情况
        
        参数:
            exceptions: 例外列表
            scenario: 场景条件
        
        返回:
            bool: 是否触发任何例外
        """
        if not exceptions:
            return False
        
        for exception in exceptions:
            exception_lower = exception.lower()
            
            # 检查角色例外
            if "角色" in exception_lower:
                role_name = exception.split("角色")[-1].strip()
                if f"character_{role_name}" in scenario:
                    return True
            
            # 检查地点例外
            elif "地点" in exception_lower:
                location_name = exception.split("地点")[-1].strip()
                if f"location_{location_name}" in scenario:
                    return True
            
            # 检查状态例外
            elif "状态" in exception_lower:
                status_name = exception.split("状态")[-1].strip()
                if scenario.get(f"state_{status_name}", "") == "true":
                    return True
        
        return False
