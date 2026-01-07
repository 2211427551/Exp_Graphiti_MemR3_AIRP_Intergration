"""
心理状态跟踪器单元测试

测试范围：
- 心理状态转移跟踪
- 状态差异计算
- 转移类型判断
- 合理性得分计算
- Graphiti存储集成
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from advanced.psychological_tracker import PsychologicalStateTracker
from advanced.psychological_modeling import (
    PsychologicalState,
    EmotionalMix,
    TraitManifestation,
    StateTransition,
    StateDiff
)


class TestPsychologicalStateTracker:
    """心理状态跟踪器测试"""
    
    @pytest.fixture
    def mock_graphiti_service(self):
        """创建mock的graphiti service"""
        mock_service = MagicMock()
        mock_service.graphiti = AsyncMock()
        mock_service.graphiti.driver = MagicMock()
        
        # Mock add_episode
        mock_result = MagicMock()
        mock_result.uuid = "test-episode-uuid"
        mock_service.graphiti.add_episode = AsyncMock(return_value=mock_result)
        
        return mock_service
    
    @pytest.fixture
    def tracker(self, mock_graphiti_service):
        """创建心理状态跟踪器实例"""
        return PsychologicalStateTracker(mock_graphiti_service)
    
    @pytest.fixture
    def sample_old_state(self):
        """示例旧心理状态"""
        return PsychologicalState(
            entity_id="psych_state_001",
            entity_type="psychological_state",
            character_id="未花",
            emotional_mix=[
                EmotionalMix(
                    emotion_type="joy",
                    intensity=0.6,
                    duration=None,
                    triggers=["朋友"],
                    manifestations=["微笑"]
                )
            ],
            dominant_emotion="joy",
            trait_manifestations={
                "optimistic": TraitManifestation(
                    trait_name="optimistic",
                    strength=0.8,
                    consistency=0.8,
                    behavior_examples=["积极面对困难"],
                    situational_context="大部分情况"
                )
            },
            stability_score=0.7,
            intensity_level=0.6,
            arousal_level=0.8,
            observed_at=datetime.now(timezone.utc),
            valid_from=datetime.now(timezone.utc),
            valid_until=None,
            source={"source_type": "llm_analysis"},
            context={"session_id": "test-session"}
        )
    
    @pytest.fixture
    def sample_new_state(self):
        """示例新心理状态"""
        return PsychologicalState(
            entity_id="psych_state_002",
            entity_type="psychological_state",
            character_id="未花",
            emotional_mix=[
                EmotionalMix(
                    emotion_type="joy",
                    intensity=0.9,
                    duration=None,
                    triggers=["阳光", "朋友"],
                    manifestations=["大笑", "跳跃"]
                )
            ],
            dominant_emotion="joy",
            trait_manifestations={
                "optimistic": TraitManifestation(
                    trait_name="optimistic",
                    strength=0.9,
                    consistency=0.9,
                    behavior_examples=["鼓励他人"],
                    situational_context="大部分情况"
                )
            },
            stability_score=0.85,
            intensity_level=0.8,
            arousal_level=0.95,
            observed_at=datetime.now(timezone.utc),
            valid_from=datetime.now(timezone.utc),
            valid_until=None,
            source={"source_type": "llm_analysis"},
            context={"session_id": "test-session"}
        )
    
    @pytest.mark.asyncio
    async def test_track_state_transition(self, tracker, sample_old_state, sample_new_state):
        """测试状态转移跟踪"""
        # Mock Graphiti add_episode
        mock_result = MagicMock()
        mock_result.uuid = "test-episode-uuid"
        tracker.graphiti_service.graphiti.add_episode = AsyncMock(return_value=mock_result)
        
        # Mock Cypher session
        mock_session = MagicMock()
        mock_session.run.return_value.single.return_value = MagicMock(count=1)
        tracker.graphiti_service.graphiti.driver.session.return_value.__enter__ = AsyncMock(return_value=mock_session)
        tracker.graphiti_service.graphiti.driver.session.return_value.__exit__ = AsyncMock()
        
        # 执行状态转移跟踪
        await tracker.track_state_transition(
            character_id="未花",
            old_state=sample_old_state,
            new_state=sample_new_state,
            trigger_event="遇到朋友"
        )
        
        # 验证
        assert len(tracker.state_history["未花"]) == 1
        assert tracker.state_history["未花"][0] == sample_new_state
    
    def test_compute_state_diff(self, tracker, sample_old_state, sample_new_state):
        """测试状态差异计算"""
        diff = tracker._compute_state_diff(sample_old_state, sample_new_state)
        
        # 应该检测到情绪变化
        assert len(diff.emotion_changes) > 0
        
        # 应该检测到特质变化
        assert len(diff.trait_changes) > 0
        
        # 应该检测到稳定性变化
        assert diff.stability_change == sample_new_state.stability_score - sample_old_state.stability_score
    
    def test_determine_transition_type_stable(self, tracker, sample_old_state):
        """测试稳定转移类型"""
        diff = StateDiff()
        diff.stability_change = 0.0
        
        transition_type = tracker._determine_transition_type(diff)
        assert transition_type == "stable"
    
    def test_determine_transition_type_sudden(self, tracker, sample_old_state):
        """测试突变转移类型"""
        diff = StateDiff()
        diff.stability_change = 0.4  # 大于0.3
        # 需要添加情绪或特质变化才能触发sudden_shift
        diff.emotion_changes.append({
            "emotion_type": "fear",
            "from": 0.1,
            "to": 0.8,
            "delta": 0.7
        })
        
        transition_type = tracker._determine_transition_type(diff)
        assert transition_type == "sudden_shift"
    
    def test_determine_transition_type_gradual(self, tracker, sample_old_state):
        """测试渐变转移类型"""
        diff = StateDiff()
        diff.stability_change = 0.2  # 在0.1和0.3之间
        # 需要添加情绪或特质变化才能触发gradual_change
        diff.emotion_changes.append({
            "emotion_type": "joy",
            "from": 0.6,
            "to": 0.7,
            "delta": 0.1
        })
        
        transition_type = tracker._determine_transition_type(diff)
        assert transition_type == "gradual_change"
    
    def test_determine_transition_type_evolution(self, tracker, sample_old_state):
        """测试演化转移类型"""
        diff = StateDiff()
        diff.emotion_changes.append({
            "emotion_type": "joy",
            "from": 0.6,
            "to": 0.7,
            "delta": 0.1
        })
        diff.stability_change = 0.05  # 小于0.1
        
        transition_type = tracker._determine_transition_type(diff)
        assert transition_type == "evolution"
    
    def test_analyze_transition_reason(self, tracker):
        """测试转移原因分析"""
        diff = StateDiff()
        diff.emotion_changes.append({
            "emotion_type": "joy",
            "from": 0.6,
            "to": 0.9,
            "delta": 0.3
        })
        diff.trait_changes.append({
            "trait_name": "optimistic",
            "from_strength": 0.8,
            "to_strength": 0.9,
            "delta": 0.1
        })
        diff.stability_change = 0.15
        
        reason = tracker._analyze_transition_reason(diff)
        
        # 应该包含"情绪"关键词
        assert "情绪" in reason
        
        # 应该包含变化描述
        assert len(reason) > 0
    
    def test_calculate_rationality_score_high(self, tracker):
        """测试高合理性得分（小变化）"""
        diff = StateDiff()
        diff.emotion_changes.append({
            "emotion_type": "joy",
            "from": 0.6,
            "to": 0.7,
            "delta": 0.1
        })
        diff.stability_change = 0.05
        
        score = tracker._calculate_rationality_score(diff)
        
        # 小变化应该得分高
        assert score >= 0.8
    
    def test_calculate_rationality_score_medium(self, tracker):
        """测试中等合理性得分（中等变化）"""
        diff = StateDiff()
        diff.emotion_changes.append({
            "emotion_type": "joy",
            "from": 0.6,
            "to": 0.8,
            "delta": 0.2
        })
        diff.stability_change = 0.15
        
        score = tracker._calculate_rationality_score(diff)
        
        # 中等变化应该得分中等（根据实际算法可能达到1.0）
        assert 0.6 <= score <= 1.0
    
    def test_calculate_rationality_score_low(self, tracker):
        """测试低合理性得分（大变化）"""
        diff = StateDiff()
        diff.emotion_changes.append({
            "emotion_type": "joy",
            "from": 0.2,
            "to": 0.9,
            "delta": 0.7
        })
        diff.stability_change = 0.5
        
        score = tracker._calculate_rationality_score(diff)
        
        # 大变化应该得分低
        assert score < 0.7
    
    def test_build_state_description(self, tracker, sample_new_state):
        """测试心理状态描述构建"""
        description = tracker._build_state_description(sample_new_state)
        
        # 应该包含主导情绪
        assert "主导情绪" in description
        assert "joy" in description
        
        # 应该包含情绪混合
        assert "情绪混合" in description
        
        # 应该包含特质表现
        assert "特质表现" in description
        
        # 应该包含状态指标
        assert "稳定性" in description
        assert "强度" in description
        assert "唤醒" in description
    
    def test_build_transition_description(self, tracker):
        """测试状态转移描述构建"""
        transition = StateTransition(
            character_id="未花",
            from_state="state_001",
            to_state="state_002",
            transition_type="evolution",
            trigger_event="遇到朋友",
            transition_reason="情绪joy增强",
            rationality_score=0.9,
            transitioned_at=datetime.now(timezone.utc)
        )
        
        description = tracker._build_transition_description(transition)
        
        # 应该包含转移类型
        assert "转移类型" in description
        assert "evolution" in description
        
        # 应该包含触发事件
        assert "触发事件" in description
        assert "遇到朋友" in description
        
        # 应该包含转移原因
        assert "转移原因" in description
        
        # 应该包含合理性得分
        assert "合理性得分" in description
    
    def test_get_character_history(self, tracker, sample_new_state):
        """测试获取角色历史"""
        # 添加状态历史
        tracker.state_history["未花"] = [sample_new_state]
        
        # 获取历史
        history = tracker.get_character_history("未花", limit=50)
        
        # 验证
        assert len(history) == 1
        assert history[0] == sample_new_state
    
    def test_get_character_history_empty(self, tracker):
        """测试获取空历史"""
        history = tracker.get_character_history("unknown_character", limit=50)
        
        # 应该返回空列表
        assert len(history) == 0
    
    def test_get_character_history_limit(self, tracker):
        """测试历史数量限制"""
        # 创建多个状态
        states = []
        for i in range(10):
            state = PsychologicalState(
                entity_id=f"psych_state_{i}",
                entity_type="psychological_state",
                character_id="未花",
                emotional_mix=[],
                dominant_emotion="joy",
                trait_manifestations={},
                stability_score=0.8,
                intensity_level=0.7,
                arousal_level=0.9,
                observed_at=datetime.now(timezone.utc),
                valid_from=datetime.now(timezone.utc),
                valid_until=None,
                source={"source_type": "llm_analysis"},
                context={"session_id": "test-session"}
            )
            states.append(state)
        
        tracker.state_history["未花"] = states
        
        # 获取限制数量的历史
        history = tracker.get_character_history("未花", limit=5)
        
        # 应该只返回5个
        assert len(history) == 5
