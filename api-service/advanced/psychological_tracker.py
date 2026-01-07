"""
心理状态跟踪器

跟踪角色的心理状态演化，管理状态转移和一致性评估
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from .psychological_modeling import (
    PsychologicalState,
    StateTransition,
    StateDiff,
    EmotionalMix,
    TraitManifestation
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
        
        参数:
            character_id: 角色ID
            old_state: 旧的心理状态
            new_state: 新的心理状态
            trigger_event: 触发事件
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
        await self._store_transition(transition, old_state, new_state)
        
        # 步骤4: 更新历史
        if character_id not in self.state_history:
            self.state_history[character_id] = []
        self.state_history[character_id].append(new_state)
    
    def _compute_state_diff(self, old_state: PsychologicalState, new_state: PsychologicalState) -> StateDiff:
        """
        计算状态差异
        
        分析维度：
        1. 情绪混合变化
        2. 特质强度变化
        3. 稳定性变化
        """
        diff = StateDiff()
        
        # 情绪变化
        old_emotions = {e.emotion_type: e.intensity for e in old_state.emotional_mix}
        new_emotions = {e.emotion_type: e.intensity for e in new_state.emotional_mix}
        
        for emotion_type in set(old_emotions.keys()) | set(new_emotions.keys()):
            old_intensity = old_emotions.get(emotion_type, 0.0)
            new_intensity = new_emotions.get(emotion_type, 0.0)
            
            if old_intensity != new_intensity:
                diff.emotion_changes.append({
                    "emotion_type": emotion_type,
                    "from": old_intensity,
                    "to": new_intensity,
                    "delta": new_intensity - old_intensity
                })
        
        # 特质变化
        old_traits = old_state.trait_manifestations or {}
        new_traits = new_state.trait_manifestations or {}
        
        for trait_name in set(old_traits.keys()) | set(new_traits.keys()):
            old_manifestation = old_traits.get(trait_name)
            new_manifestation = new_traits.get(trait_name)
            
            if old_manifestation and new_manifestation:
                if old_manifestation.strength != new_manifestation.strength:
                    diff.trait_changes.append({
                        "trait_name": trait_name,
                        "from_strength": old_manifestation.strength,
                        "to_strength": new_manifestation.strength,
                        "delta": new_manifestation.strength - old_manifestation.strength
                    })
        
        # 稳定性变化
        diff.stability_change = new_state.stability_score - old_state.stability_score
        
        return diff
    
    def _determine_transition_type(self, diff: StateDiff) -> str:
        """
        确定转移类型
        
        类型：
        - stable: 无显著变化
        - gradual_change: 缓慢变化
        - sudden_shift: 突然变化
        - evolution: 自然演化
        """
        if not diff.emotion_changes and not diff.trait_changes:
            return "stable"
        elif abs(diff.stability_change) > 0.3:
            return "sudden_shift"
        elif abs(diff.stability_change) > 0.1:
            return "gradual_change"
        else:
            return "evolution"
    
    def _analyze_transition_reason(self, diff: StateDiff) -> str:
        """
        分析转移原因
        
        基于情绪和特质变化生成原因描述
        """
        reasons = []
        
        # 情绪变化原因
        for emotion_change in diff.emotion_changes:
            delta = emotion_change["delta"]
            if delta > 0.3:
                reasons.append(f"情绪'{emotion_change['emotion_type']}'显著增强")
            elif delta < -0.3:
                reasons.append(f"情绪'{emotion_change['emotion_type']}'显著减弱")
            elif abs(delta) > 0.1:
                direction = "增强" if delta > 0 else "减弱"
                reasons.append(f"情绪'{emotion_change['emotion_type']}'{direction}")
        
        # 特质变化原因
        for trait_change in diff.trait_changes:
            delta = trait_change["delta"]
            if abs(delta) > 0.2:
                direction = "增强" if delta > 0 else "减弱"
                reasons.append(f"特质'{trait_change['trait_name']}'强度显著{direction}")
        
        # 稳定性变化
        if abs(diff.stability_change) > 0.2:
            direction = "提升" if diff.stability_change > 0 else "下降"
            reasons.append(f"心理稳定性{direction}")
        
        return "; ".join(reasons) if reasons else "自然演化"
    
    def _calculate_rationality_score(self, diff: StateDiff) -> float:
        """
        计算转移合理性得分
        
        评分标准：
        1. 情绪变化幅度（变化太大可能不合理）
        2. 特质稳定性（特质变化太大可能不合理）
        3. 稳定性变化（稳定性突变可能不合理）
        """
        score = 1.0
        
        # 情绪变化幅度评分
        if diff.emotion_changes:
            emotion_deltas = [abs(c["delta"]) for c in diff.emotion_changes]
            avg_change = sum(emotion_deltas) / len(emotion_deltas)
            max_change = max(emotion_deltas)
            
            # 平均变化过大扣分
            if avg_change > 0.4:
                score -= 0.3
            elif avg_change > 0.2:
                score -= 0.1
            
            # 最大变化过大扣分
            if max_change > 0.6:
                score -= 0.2
        
        # 特质稳定性评分
        if diff.trait_changes:
            trait_deltas = [abs(t["delta"]) for t in diff.trait_changes]
            avg_change = sum(trait_deltas) / len(trait_deltas)
            
            if avg_change > 0.3:
                score -= 0.2
        
        # 稳定性变化评分
        if abs(diff.stability_change) > 0.2:
            score -= 0.2
        
        # 返回限制在0.0-1.0之间
        return max(0.0, min(1.0, score))
    
    async def _store_transition(
        self,
        transition: StateTransition,
        old_state: PsychologicalState,
        new_state: PsychologicalState
    ):
        """
        存储状态转移到Graphiti
        
        策略：
        1. 将新心理状态作为Episode存储
        2. 创建角色与心理状态的关系
        3. 存储状态转移记录
        """
        try:
            # 步骤1: 存储新心理状态
            state_description = self._build_state_description(new_state)
            
            result = await self.graphiti_service.graphiti.add_episode(
                name=f"Psychological State - {new_state.character_id}",
                episode_body=state_description,
                source=self.graphiti_service.graphiti.EpisodeType.text,
                source_description=f"psychological_state:{new_state.character_id}",
                reference_time=new_state.observed_at,
                group_id=new_state.context.get("session_id", "default")
            )
            
            # 步骤2: 存储状态转移（作为独立的Episode）
            transition_description = self._build_transition_description(transition)
            
            transition_result = await self.graphiti_service.graphiti.add_episode(
                name=f"State Transition - {transition.character_id}",
                episode_body=transition_description,
                source=self.graphiti_service.graphiti.EpisodeType.text,
                source_description=f"state_transition:{transition.character_id}",
                reference_time=transition.transitioned_at,
                group_id=new_state.context.get("session_id", "default")
            )
            
            # 步骤3: 创建角色与心理状态的关联（通过Cypher）
            await self._create_character_state_relation(
                transition.character_id,
                result.uuid,
                transition.transitioned_at
            )
            
        except Exception as e:
            print(f"Error storing psychological state transition: {e}")
            raise e
    
    def _build_state_description(self, state: PsychologicalState) -> str:
        """构建心理状态描述"""
        parts = []
        
        # 主导情绪
        if state.dominant_emotion:
            parts.append(f"主导情绪: {state.dominant_emotion}")
        
        # 情绪混合
        if state.emotional_mix:
            emotions = ", ".join([
                f"{e.emotion_type}({e.intensity:.2f})" 
                for e in state.emotional_mix[:5]
            ])
            parts.append(f"情绪混合: {emotions}")
        
        # 特质表现
        if state.trait_manifestations:
            traits = ", ".join([
                f"{name}({manifestation.strength:.2f})" 
                for name, manifestation in list(state.trait_manifestations.items())[:5]
            ])
            parts.append(f"特质表现: {traits}")
        
        # 状态指标
        parts.append(
            f"稳定性: {state.stability_score:.2f}, "
            f"强度: {state.intensity_level:.2f}, "
            f"唤醒: {state.arousal_level:.2f}"
        )
        
        return "\n".join(parts)
    
    def _build_transition_description(self, transition: StateTransition) -> str:
        """构建状态转移描述"""
        parts = [
            f"转移类型: {transition.transition_type}",
            f"触发事件: {transition.trigger_event}",
            f"转移原因: {transition.transition_reason}",
            f"合理性得分: {transition.rationality_score:.2f}",
            f"转移时间: {transition.transitioned_at.isoformat()}",
            f"从状态: {transition.from_state}",
            f"到状态: {transition.to_state}"
        ]
        
        return "\n".join(parts)
    
    async def _create_character_state_relation(
        self,
        character_id: str,
        state_id: str,
        transition_time: datetime
    ):
        """
        创建角色与心理状态的关系
        
        使用Cypher直接创建关系，因为Graphiti可能不支持这种自定义关系
        """
        query = """
        MATCH (c:Episode), (s:Episode)
        WHERE c.uuid = $character_id
          AND s.uuid = $state_id
        CREATE (c)-[r:HAS_PSYCHOLOGICAL_STATE {
            relation_started: $transition_time,
            created_at: $now
          }]->(s)
        RETURN r
        """
        
        with self.graphiti_service.graphiti.driver.session() as session:
            session.run(query, {
                "character_id": character_id,
                "state_id": state_id,
                "transition_time": transition_time.isoformat(),
                "now": datetime.now(timezone.utc).isoformat()
            })
    
    def get_character_history(
        self,
        character_id: str,
        limit: int = 50
    ) -> List[PsychologicalState]:
        """
        获取角色的心理状态历史
        
        参数:
            character_id: 角色ID
            limit: 最大返回数量
        
        返回:
            List[PsychologicalState]: 心理状态列表
        """
        if character_id in self.state_history:
            return self.state_history[character_id][-limit:]
        else:
            return []
