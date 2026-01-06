"""
心理连贯性评估器

实现心理连贯性度量指标的计算
"""

from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from pydantic import BaseModel, Field

from api_service.models.change_detection import PsychologicalState


class PsychologicalCoherenceEvaluator:
    """心理连贯性评估器"""
    
    def __init__(self, graphiti_service):
        self.graphiti_service = graphiti_service
    
    async def evaluate_coherence(
        self,
        character_id: str,
        time_window: timedelta = timedelta(days=7)
    ) -> Dict[str, float]:
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
            # 数据不足，返回默认高分
            return {
                "trait_consistency": 1.0,
                "emotional_rationality": 1.0,
                "behavioral_consistency": 1.0,
                "memory_rationality": 1.0
            }
        
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
        
        return {
            "trait_consistency": trait_score,
            "emotional_rationality": emotional_score,
            "behavioral_consistency": behavioral_score,
            "memory_rationality": memory_score,
            "overall_score": overall_score
        }
    
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
        
        简化版：基于变化幅度的评估
        """
        if len(states) < 2:
            return 1.0
        
        rationality_scores = []
        
        for i in range(1, len(states)):
            old_state = states[i - 1]
            new_state = states[i]
            
            # 计算情绪变化幅度
            old_emotions = {
                e.emotion_type: e.intensity
                for e in old_state.emotional_mix
            }
            new_emotions = {
                e.emotion_type: e.intensity
                for e in new_state.emotional_mix
            }
            
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
                rationality = 1.0  # 小幅变化，合理
            elif max_change < 0.6:
                rationality = 0.7  # 中等变化，基本合理
            else:
                rationality = 0.4  # 大幅变化，除非有强烈触发
            
            rationality_scores.append(rationality)
        
        return sum(rationality_scores) / len(rationality_scores) if rationality_scores else 1.0
    
    def evaluate_behavioral_consistency(
        self,
        states: List[PsychologicalState]
    ) -> float:
        """
        评估行为模式一致性
        
        算法：
        1. 检查行为是否与特质一致
        2. 检查行为是否与情绪一致
        3. 评估行为模式的稳定性
        
        简化版：基于情绪和特质的一致性评估
        """
        if not states:
            return 1.0
        
        consistency_scores = []
        
        for state in states:
            # 获取主导特质
            if state.trait_manifestations:
                dominant_traits = sorted(
                    state.trait_manifestations.items(),
                    key=lambda x: x[1].strength,
                    reverse=True
                )
                
                if dominant_traits:
                    top_trait = dominant_traits[0][0]  # 最强特质
                    
                    # 检查情绪与特质是否匹配
                    if state.dominant_emotion:
                        if top_trait[0] in ["joy", "happiness"]:
                            # 积极情绪与积极特质匹配
                            consistency_score = 1.0
                        elif top_trait[0] in ["optimistic", "enthusiastic"]:
                            # 热情与积极特质匹配
                            consistency_score = 0.9
                        elif top_trait[0] in ["anxious", "aggressive", "stubborn"]:
                            # 消极情绪与消极特质匹配
                            consistency_score = 0.9
                        else:
                            # 不匹配，适度扣分
                            consistency_score = 0.7
                    else:
                        consistency_score = 0.5
                else:
                    consistency_score = 0.5
            else:
                consistency_score = 0.5
            
            consistency_scores.append(consistency_score)
        
        return sum(consistency_scores) / len(consistency_scores) if consistency_scores else 1.0
    
    async def evaluate_memory_rationality(
        self,
        character_id: str,
        states: List[PsychologicalState]
    ) -> float:
        """
        评估记忆影响合理性
        
        简化版：基于状态稳定性和情绪强度的合理性
        """
        if not states:
            return 1.0
        
        # 检查状态的稳定性
        stability_values = [state.stability_score for state in states]
        avg_stability = sum(stability_values) / len(stability_values) if stability_values else 0.5
        
        # 检查情绪强度和稳定性的关系
        intensity_values = [state.intensity_level for state in states]
        avg_intensity = sum(intensity_values) / len(intensity_values) if intensity_values else 0.5
        
        # 如果情绪强度高但稳定性低，可能不合理
        if avg_intensity > 0.7 and avg_stability < 0.5:
            rationality = 0.6
        elif avg_intensity > 0.5 and avg_stability < 0.7:
            rationality = 0.8
        else:
            rationality = 0.9
        
        return rationality
    
    async def get_psychological_states(
        self,
        character_id: str,
        time_window: timedelta
    ) -> List[PsychologicalState]:
        """
        获取时间窗口内的所有心理状态
        
        返回: List[PsychologicalState]
        """
        # TODO: 实现从Graphiti查询心理状态
        # 这里先返回空列表
        return []
