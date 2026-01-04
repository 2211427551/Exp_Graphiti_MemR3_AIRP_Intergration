#!/usr/bin/env python3
"""
因果推理服务

基于双时序数据分析和推断实体间的因果关系。
支持：
1. 因果关系发现
2. 因果强度评估
3. 反事实推理
4. 干预效果预测
"""

import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime
import numpy as np
from collections import defaultdict
import networkx as nx
import json
import uuid
import os
import sys

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 导入配置
config_path = os.path.join(project_root, 'config', 'settings.py')
import importlib.util
spec = importlib.util.spec_from_file_location("settings", config_path)
settings_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(settings_module)
settings = settings_module.settings

logger = logging.getLogger(__name__)

class CausalInferenceService:
    """因果推理服务类"""
    
    def __init__(self, temporal_service=None):
        """初始化因果推理服务"""
        self.temporal_service = temporal_service
        self.causal_graphs = {}  # session_id -> 因果图
        self.causal_rules = {}   # session_id -> 因果关系规则
        
        logger.info("因果推理服务初始化完成")
    
    def discover_causal_relationships(self, session_id: str,
                                     time_window: Optional[Tuple[str, str]] = None,
                                     min_confidence: float = 0.7,
                                     min_support: int = 2) -> Dict[str, Any]:
        """
        发现会话中的因果关系
        
        Args:
            session_id: 会话ID
            time_window: 可选时间窗口 (start_time, end_time)
            min_confidence: 最小置信度阈值
            min_support: 最小支持度阈值
            
        Returns:
            发现的因果关系
        """
        try:
            if not self.temporal_service:
                return {
                    "success": False,
                    "error": "未提供时序数据服务"
                }
            
            # 获取时间窗口内的实体历史
            time_points = []
            
            if time_window:
                start_time, end_time = time_window
                # 按时间点采样查询
                from datetime import datetime, timedelta
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                
                # 生成时间点采样
                interval = (end_dt - start_dt) / 10  # 10个采样点
                for i in range(11):
                    sample_time = start_dt + interval * i
                    time_points.append(sample_time.isoformat())
            else:
                # 使用所有时间点
                time_points = ["now"]  # 简化版，实际应查询所有时间点
            
            # 收集实体状态变化
            entity_changes = self._collect_entity_changes(
                session_id, time_points
            )
            
            # 计算因果关系
            causal_relationships = self._calculate_causal_relationships(
                entity_changes, min_confidence, min_support
            )
            
            # 构建因果图
            causal_graph = self._build_causal_graph(
                session_id, causal_relationships
            )
            
            # 存储结果
            self.causal_graphs[session_id] = causal_graph
            self.causal_rules[session_id] = causal_relationships
            
            return {
                "success": True,
                "discovered_relationships": causal_relationships,
                "causal_graph_nodes": len(causal_graph.nodes()),
                "causal_graph_edges": len(causal_graph.edges()),
                "time_points_analyzed": len(time_points)
            }
            
        except Exception as e:
            logger.error(f"因果关系发现失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _collect_entity_changes(self, session_id: str, time_points: List[str]) -> Dict[str, List[Dict]]:
        """收集实体在时间点上的状态变化"""
        entity_changes = defaultdict(list)
        
        for i, time_point in enumerate(time_points):
            try:
                # 查询该时间点有效的实体
                entities = self.temporal_service.query_valid_at_time(
                    session_id=session_id,
                    query_time=time_point,
                    entity_type=None,
                    limit=100
                )
                
                # 记录实体状态
                for entity in entities:
                    entity_id = entity.get("entity_id")
                    entity_changes[entity_id].append({
                        "time_index": i,
                        "time_point": time_point,
                        "state": entity.get("properties", {}),
                        "entity_type": entity.get("entity_type"),
                        "name": entity.get("name")
                    })
                    
            except Exception as e:
                logger.warning(f"收集实体状态失败 (时间点={time_point}): {str(e)}")
                continue
        
        return entity_changes
    
    def _calculate_causal_relationships(self, entity_changes: Dict[str, List[Dict]],
                                       min_confidence: float, min_support: int) -> List[Dict[str, Any]]:
        """计算因果关系"""
        relationships = []
        
        # 获取所有实体ID
        entity_ids = list(entity_changes.keys())
        
        if len(entity_ids) < 2:
            return relationships
        
        # 预处理实体状态序列
        state_sequences = {}
        for entity_id, changes in entity_changes.items():
            # 按时间索引排序
            changes.sort(key=lambda x: x["time_index"])
            state_sequences[entity_id] = changes
        
        # 分析因果关系
        for i in range(len(entity_ids)):
            for j in range(len(entity_ids)):
                if i == j:
                    continue
                
                cause_id = entity_ids[i]
                effect_id = entity_ids[j]
                
                cause_seq = state_sequences.get(cause_id, [])
                effect_seq = state_sequences.get(effect_id, [])
                
                if len(cause_seq) < min_support or len(effect_seq) < min_support:
                    continue
                
                # 计算格兰杰因果关系（简化版）
                causality_score = self._calculate_granger_causality(
                    cause_seq, effect_seq
                )
                
                # 计算置信度和支持度
                confidence = causality_score
                support = min(len(cause_seq), len(effect_seq))
                
                if confidence >= min_confidence and support >= min_support:
                    # 分析具体的变化关系
                    change_patterns = self._analyze_change_patterns(
                        cause_seq, effect_seq
                    )
                    
                    relationships.append({
                        "relationship_id": str(uuid.uuid4()),
                        "cause_entity_id": cause_id,
                        "effect_entity_id": effect_id,
                        "confidence": confidence,
                        "support": support,
                        "causality_score": causality_score,
                        "change_patterns": change_patterns,
                        "relationship_type": "causal"
                    })
        
        # 按置信度排序
        relationships.sort(key=lambda x: x["confidence"], reverse=True)
        
        return relationships
    
    def _calculate_granger_causality(self, cause_seq: List[Dict], effect_seq: List[Dict]) -> float:
        """计算格兰杰因果关系（简化版）"""
        # 实际实现应使用统计方法，这里返回一个简化值
        if len(cause_seq) < 2 or len(effect_seq) < 2:
            return 0.0
        
        # 提取数值属性
        cause_states = [self._extract_numeric_state(state["state"]) for state in cause_seq]
        effect_states = [self._extract_numeric_state(state["state"]) for state in effect_seq]
        
        # 计算相关系数
        if cause_states and effect_states:
            # 对齐长度
            min_len = min(len(cause_states), len(effect_states))
            cause_aligned = cause_states[:min_len]
            effect_aligned = effect_states[:min_len]
            
            # 计算滞后相关系数
            if min_len > 1:
                # 使用交叉相关性
                cross_corr = np.corrcoef(cause_aligned, effect_aligned)[0, 1]
                return abs(cross_corr)
        
        return 0.0
    
    def _extract_numeric_state(self, state: Dict[str, Any]) -> float:
        """从实体状态中提取数值表示"""
        if not state:
            return 0.0
        
        # 尝试提取数值属性
        numeric_sum = 0.0
        count = 0
        
        for key, value in state.items():
            if isinstance(value, (int, float)):
                numeric_sum += float(value)
                count += 1
            elif isinstance(value, str):
                # 字符串长度作为数值
                numeric_sum += len(value)
                count += 1
            elif isinstance(value, bool):
                numeric_sum += 1.0 if value else 0.0
                count += 1
        
        return numeric_sum / max(count, 1)
    
    def _analyze_change_patterns(self, cause_seq: List[Dict], effect_seq: List[Dict]) -> List[Dict]:
        """分析具体的变化模式"""
        patterns = []
        
        # 对齐时间序列
        cause_by_time = {state["time_index"]: state for state in cause_seq}
        effect_by_time = {state["time_index"]: state for state in effect_seq}
        
        common_times = set(cause_by_time.keys()) & set(effect_by_time.keys())
        
        for time_idx in sorted(common_times):
            cause_state = cause_by_time[time_idx]["state"]
            effect_state = effect_by_time[time_idx]["state"]
            
            # 检测显著变化
            cause_changes = self._detect_state_changes(cause_state, cause_by_time.get(time_idx-1, {}).get("state", {}))
            effect_changes = self._detect_state_changes(effect_state, effect_by_time.get(time_idx-1, {}).get("state", {}))
            
            if cause_changes and effect_changes:
                patterns.append({
                    "time_index": time_idx,
                    "time_point": cause_by_time[time_idx]["time_point"],
                    "cause_changes": cause_changes,
                    "effect_changes": effect_changes,
                    "pattern_type": "simultaneous_change"
                })
        
        return patterns
    
    def _detect_state_changes(self, current_state: Dict, previous_state: Dict) -> List[str]:
        """检测状态变化"""
        changes = []
        
        # 比较当前状态和先前状态
        all_keys = set(current_state.keys()) | set(previous_state.keys())
        
        for key in all_keys:
            current_val = current_state.get(key)
            previous_val = previous_state.get(key)
            
            if current_val != previous_val:
                change_desc = f"{key}: {previous_val} -> {current_val}"
                changes.append(change_desc)
        
        return changes
    
    def _build_causal_graph(self, session_id: str, relationships: List[Dict]) -> nx.DiGraph:
        """构建因果图"""
        graph = nx.DiGraph()
        
        for rel in relationships:
            cause_id = rel["cause_entity_id"]
            effect_id = rel["effect_entity_id"]
            confidence = rel["confidence"]
            causality_score = rel["causality_score"]
            
            # 添加节点
            graph.add_node(cause_id, type="entity")
            graph.add_node(effect_id, type="entity")
            
            # 添加边（因果关系）
            graph.add_edge(cause_id, effect_id, 
                          weight=confidence,
                          causality_score=causality_score,
                          relationship_id=rel["relationship_id"])
        
        return graph
    
    def get_causal_paths(self, session_id: str, 
                        source_entity_id: str, target_entity_id: str,
                        max_path_length: int = 5) -> List[Dict[str, Any]]:
        """
        获取两个实体间的因果路径
        
        Args:
            session_id: 会话ID
            source_entity_id: 源实体ID
            target_entity_id: 目标实体ID
            max_path_length: 最大路径长度
            
        Returns:
            因果路径列表
        """
        try:
            causal_graph = self.causal_graphs.get(session_id)
            
            if not causal_graph:
                return []
            
            # 查找所有路径
            paths = []
            try:
                all_paths = nx.all_simple_paths(
                    causal_graph, 
                    source=source_entity_id,
                    target=target_entity_id,
                    cutoff=max_path_length
                )
                
                for path in all_paths:
                    # 计算路径总强度
                    path_strength = 1.0
                    for i in range(len(path) - 1):
                        edge_data = causal_graph.get_edge_data(path[i], path[i+1])
                        if edge_data:
                            path_strength *= edge_data.get("weight", 0.5)
                    
                    paths.append({
                        "path": path,
                        "length": len(path) - 1,
                        "strength": path_strength
                    })
                    
            except nx.NetworkXNoPath:
                logger.debug(f"未找到从 {source_entity_id} 到 {target_entity_id} 的因果路径")
            
            # 按强度排序
            paths.sort(key=lambda x: x["strength"], reverse=True)
            
            return paths
            
        except Exception as e:
            logger.error(f"获取因果路径失败: {str(e)}")
            return []
    
    def predict_intervention_effect(self, session_id: str,
                                  intervention_entity_id: str,
                                  intervention_changes: Dict[str, Any],
                                  target_entity_id: str,
                                  confidence_threshold: float = 0.6) -> Dict[str, Any]:
        """
        预测干预效果（如果对某个实体进行干预，会影响哪些实体）
        
        Args:
            session_id: 会话ID
            intervention_entity_id: 干预目标实体ID
            intervention_changes: 干预变化
            target_entity_id: 目标实体ID
            confidence_threshold: 置信度阈值
            
        Returns:
            预测效果
        """
        try:
            causal_graph = self.causal_graphs.get(session_id)
            
            if not causal_graph:
                return {
                    "success": False,
                    "error": "未找到因果图"
                }
            
            # 检查干预实体是否存在
            if intervention_entity_id not in causal_graph:
                return {
                    "success": False,
                    "error": f"干预实体 {intervention_entity_id} 不存在"
                }
            
            # 检查目标实体是否存在
            if target_entity_id not in causal_graph:
                return {
                    "success": False,
                    "error": f"目标实体 {target_entity_id} 不存在"
                }
            
            # 查找从干预实体到目标实体的路径
            paths = []
            try:
                all_paths = nx.all_simple_paths(
                    causal_graph,
                    source=intervention_entity_id,
                    target=target_entity_id,
                    cutoff=10
                )
                
                for path in all_paths:
                    # 计算路径强度和置信度
                    path_strength = 1.0
                    min_confidence = 1.0
                    
                    for i in range(len(path) - 1):
                        edge_data = causal_graph.get_edge_data(path[i], path[i+1])
                        if edge_data:
                            edge_weight = edge_data.get("weight", 0.5)
                            path_strength *= edge_weight
                            min_confidence = min(min_confidence, edge_weight)
                    
                    # 路径传播衰减因子
                    attenuation = 0.8 ** (len(path) - 1)
                    predicted_effect = path_strength * attenuation
                    
                    if min_confidence >= confidence_threshold:
                        paths.append({
                            "path": path,
                            "length": len(path) - 1,
                            "path_strength": path_strength,
                            "min_confidence": min_confidence,
                            "predicted_effect": predicted_effect,
                            "attenuation_factor": attenuation
                        })
                        
            except nx.NetworkXNoPath:
                logger.debug(f"未找到从干预实体到目标实体的路径")
            
            # 排序并选择最佳路径
            if paths:
                paths.sort(key=lambda x: x["predicted_effect"], reverse=True)
                best_path = paths[0]
                
                # 分析干预可能的影响
                intervention_analysis = self._analyze_intervention(
                    causal_graph, intervention_entity_id, intervention_changes, target_entity_id
                )
                
                return {
                    "success": True,
                    "prediction": {
                        "intervention_entity": intervention_entity_id,
                        "target_entity": target_entity_id,
                        "best_path": best_path["path"],
                        "path_length": best_path["length"],
                        "predicted_effect_strength": best_path["predicted_effect"],
                        "confidence": best_path["min_confidence"],
                        "total_paths_found": len(paths),
                        "intervention_analysis": intervention_analysis
                    }
                }
            else:
                return {
                    "success": True,
                    "prediction": {
                        "intervention_entity": intervention_entity_id,
                        "target_entity": target_entity_id,
                        "effect_predicted": False,
                        "reason": "未找到有效因果路径或置信度过低"
                    }
                }
            
        except Exception as e:
            logger.error(f"预测干预效果失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _analyze_intervention(self, causal_graph: nx.DiGraph,
                            intervention_entity_id: str,
                            intervention_changes: Dict[str, Any],
                            target_entity_id: str) -> Dict[str, Any]:
        """分析干预的潜在影响"""
        analysis = {
            "direct_effects": [],
            "indirect_effects": [],
            "collateral_effects": []
        }
        
        # 直接效应（干预实体的直接下游）
        for neighbor in causal_graph.successors(intervention_entity_id):
            edge_data = causal_graph.get_edge_data(intervention_entity_id, neighbor)
            if edge_data:
                analysis["direct_effects"].append({
                    "entity_id": neighbor,
                    "relationship_type": "direct",
                    "causal_strength": edge_data.get("weight", 0.5)
                })
        
        # 间接效应（通过中介变量）
        for path in nx.all_simple_paths(causal_graph, source=intervention_entity_id, target=target_entity_id, cutoff=5):
            if len(path) > 2:  # 至少有一个中介变量
                indirect_effect = 1.0
                for i in range(len(path) - 1):
                    edge_data = causal_graph.get_edge_data(path[i], path[i+1])
                    if edge_data:
                        indirect_effect *= edge_data.get("weight", 0.5)
                
                analysis["indirect_effects"].append({
                    "path": path,
                    "intermediate_entities": path[1:-1],
                    "indirect_effect_strength": indirect_effect
                })
        
        # 附带效应（影响其他非目标实体）
        reachable_nodes = nx.descendants(causal_graph, intervention_entity_id)
        for node in reachable_nodes:
            if node != target_entity_id:
                # 检查是否有路径到该节点
                try:
                    shortest_path = nx.shortest_path(causal_graph, source=intervention_entity_id, target=node)
                    path_strength = 1.0
                    for i in range(len(shortest_path) - 1):
                        edge_data = causal_graph.get_edge_data(shortest_path[i], shortest_path[i+1])
                        if edge_data:
                            path_strength *= edge_data.get("weight", 0.5)
                    
                    analysis["collateral_effects"].append({
                        "entity_id": node,
                        "path_length": len(shortest_path) - 1,
                        "effect_strength": path_strength
                    })
                except nx.NetworkXNoPath:
                    continue
        
        return analysis
    
    def get_service_info(self) -> Dict[str, Any]:
        """获取服务信息"""
        info = {
            "service_type": "CausalInferenceService",
            "active_sessions": len(self.causal_graphs),
            "total_rules": sum(len(rules) for rules in self.causal_rules.values()),
            "causal_graphs_summary": {
                session_id: {
                    "nodes": len(graph.nodes()),
                    "edges": len(graph.edges())
                }
                for session_id, graph in self.causal_graphs.items()
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return info
    
    def clear_data(self, session_id: Optional[str] = None):
        """清除数据"""
        if session_id:
            if session_id in self.causal_graphs:
                del self.causal_graphs[session_id]
            if session_id in self.causal_rules:
                del self.causal_rules[session_id]
            logger.info(f"已清除会话 {session_id} 的因果推理数据")
        else:
            self.causal_graphs.clear()
            self.causal_rules.clear()
            logger.info("已清除所有因果推理数据")
