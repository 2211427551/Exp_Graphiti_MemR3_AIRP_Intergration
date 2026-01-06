"""
心理状态跟踪器

跟踪角色的心理状态演化，管理状态转移和一致性评估
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from api_service.models.change_detection import (
    PsychologicalState,
    StateTransition
)


class PsychologicalStateTracker:
    """心理状态跟踪器"""
    
    def __init__(self, graphiti_service):
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
        diff = self._compute_state_diff(old_state, new_state)
        
        # 步骤2: 创建状态转移记录
        transition = StateTransition(
            character_id=character_id,
            from_state=old_state.entity_id,
            to_state=new_state.entity_id,
            transition_type=self._determine_transition_type(diff),
            trigger_event=trigger_event,
            transition_reason=self._analyze_transition_reason(diff),
            rationality_score=self._calculate_rationality_score(diff),
            transitioned_at=datetime.now(timezone.utc)
        )
        
        # 步骤3: 存储到Graphiti
        await self._store_transition(transition)
        
        # 步骤4: 更新历史
        if character_id not in self.state_history:
            self.state_history[character_id] = []
        self.state_history[character_id].append(new_state)
    
    def _compute_state_diff(self, old_state, new_state):
        """计算状态差异"""
        diff = {
            "emotion_changes": [],
            "trait_changes": [],
            "stability_change": new_state.stability_score - old_state.stability_score
        }
        
        # 情绪变化
        old_emotions = {e.emotion_type: e.intensity for e in old_state.emotional_mix}
        new_emotions = {e.emotion_type: e.intensity for e in new_state.emotional_mix}
        
        for emotion_type in set(old_emotions.keys()) | set(new_emotions.keys()):
            old_intensity = old_emotions.get(emotion_type, 0.0)
            new_intensity = new_emotions.get(emotion_type, 0.0)
            
            if old_intensity != new_intensity:
                diff["emotion_changes"].append({
                    "emotion_type": emotion_type,
                    "from": old_intensity,
                    "to": new_intensity,
                    "delta": new_intensity - old_intensity
                })
        
        # 特质变化
        old_traits = old_state.trait_manifestations or {}
        new_traits = new_state.trait_manifestations or {}
        
        for trait_name in set(old_traits.keys()) | set(new_traits.keys()):
            old_trait = old_traits.get(trait_name)
            new_trait = new_traits.get(trait_name)
            
            if old_trait and new_trait:
                if old_trait.strength != new_trait.strength:
                    diff["trait_changes"].append({
                        "trait_name": trait_name,
                        "from_strength": old_trait.strength,
                        "to_strength": new_trait.strength
                    })
        
        return diff
    
    def _determine_transition_type(self, diff):
        """确定转移类型"""
        if not diff["emotion_changes"] and not diff["trait_changes"]:
            return "stable"
        elif abs(diff["stability_change"]) < 0.1:
            return "gradual_change"
        elif abs(diff["stability_change"]) > 0.3:
            return "sudden_shift"
        else:
            return "evolution"
    
    def _analyze_transition_reason(self, diff):
        """分析转移原因"""
        reasons = []
        
        for emotion_change in diff["emotion_changes"]:
            if emotion_change["delta"] > 0.3:
                reasons.append(f"情绪'{emotion_change['emotion_type']}'显著增强")
            elif emotion_change["delta"] < -0.3:
                reasons.append(f"情绪'{emotion_change['emotion_type']}'显著减弱")
        
        for trait_change in diff["trait_changes"]:
            if abs(trait_change["delta"]) > 0.2:
                reasons.append(f"特质'{trait_change['trait_name']}'强度显著变化")
        
        return "; ".join(reasons) if reasons else "自然演化"
    
    def _calculate_rationality_score(self, diff):
        """计算转移合理性得分"""
        score = 1.0
        
        # 情绪变化幅度
        if diff["emotion_changes"]:
            emotion_changes = [abs(c["delta"]) for c in diff["emotion_changes"]]
            avg_change = sum(emotion_changes) / len(emotion_changes)
            
            if avg_change > 0.4:
                score -= 0.3
            elif avg_change > 0.2:
                score -= 0.1
        
        # 特质稳定性
        if diff["trait_changes"]:
            trait_changes = [abs(t["delta"]) for t in diff["trait_changes"]]
            avg_change = sum(trait_changes) / len(trait_changes)
            
            if avg_change > 0.3:
                score -= 0.2
        
        # 稳定性变化
        if abs(diff["stability_change"]) > 0.2:
            score -= 0.2
        
        # 返回限制在0.0-1.0之间
        return max(0.0, min(1.0, score))
    
    async def _store_transition(self, transition):
        """存储状态转移到Graphiti"""
        # TODO: 实现Graphiti存储逻辑
        # 将状态转移作为Episode存储，记录状态变化
        pass
