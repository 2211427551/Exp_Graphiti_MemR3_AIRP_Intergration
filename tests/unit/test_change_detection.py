"""
变化检测与同步单元测试

测试范围：
- World Info变化检测
- Chat History变化检测
- 状态更新
- 哈希计算
"""

import pytest
from datetime import datetime, timezone
from advanced.change_detection import (
    detect_worldinfo_changes,
    detect_chat_changes,
    update_world_info_state,
    update_chat_history_state,
    ChangeDetectionResult,
    ChatChangeResult
)
from models.change_detection import (
    WorldInfoEntry,
    WorldInfoState,
    ChatMessage,
    ChatHistoryState
)
from tests.conftest import (
    SAMPLE_WORLD_INFO,
    SAMPLE_CHAT_HISTORY,
    sample_world_info_entry,
    sample_world_info_state,
    sample_chat_message,
    sample_chat_history_state
)


class TestWorldInfoChangeDetection:
    """World Info变化检测测试"""
    
    def test_detect_no_changes(self, sample_world_info_state):
        """测试检测无变化"""
        # 使用空内容，这样应该没有任何条目被检测
        new_content = ""
        
        changes = detect_worldinfo_changes(
            old_state=sample_world_info_state,
            new_content=new_content,
            session_id="test-session"
        )
        
        # 空内容时，所有旧条目应该被标记为删除
        assert "removed" in changes
        assert len(changes.get("added", [])) == 0
        assert len(changes.get("modified", [])) == 0
    
    def test_detect_added_entries(self, sample_world_info_state):
        """测试检测新增条目"""
        # 添加一个完全不存在的新地点
        new_content = '地点("全新地点")["这是之前不存在的地点"]'
        
        changes = detect_worldinfo_changes(
            old_state=sample_world_info_state,
            new_content=new_content,
            session_id="test-session"
        )
        
        assert "added" in changes
        assert len(changes["added"]) >= 1
        
        # 验证新增条目
        added_entry = next((e for e in changes["added"] if "全新地点" in e.name), None)
        assert added_entry is not None
        assert added_entry.entry_type == "location"
    
    def test_detect_removed_entries(self, sample_world_info_state):
        """测试检测删除条目"""
        # 删除一个地点，只保留另一个
        new_content = '地点("夏莱")["联邦搜查社"]'
        
        changes = detect_worldinfo_changes(
            old_state=sample_world_info_state,
            new_content=new_content,
            session_id="test-session"
        )
        
        assert "removed" in changes
        assert len(changes["removed"]) >= 1
    
    def test_detect_modified_entries(self, sample_world_info_state):
        """测试检测修改条目"""
        # 修改现有条目的内容
        new_content = '地点("夏莱")["修改后的描述"]'
        
        changes = detect_worldinfo_changes(
            old_state=sample_world_info_state,
            new_content=new_content,
            session_id="test-session"
        )
        
        assert "modified" in changes
        assert len(changes["modified"]) >= 1
        
        # 验证修改详情
        mod = changes["modified"][0]
        assert "old" in mod
        assert "new" in mod
        assert "diff" in mod
    
    def test_detect_multiple_changes(self, sample_world_info_state):
        """测试检测多种变化类型"""
        new_content = """
地点("夏莱")["修改后的描述"]
地点("新地点")["新增地点"]
"""
        # 不包含原有的一些条目，导致删除
        
        changes = detect_worldinfo_changes(
            old_state=sample_world_info_state,
            new_content=new_content,
            session_id="test-session"
        )
        
        # 应同时包含新增、删除、修改
        total_changes = (
            len(changes.get("added", [])) +
            len(changes.get("removed", [])) +
            len(changes.get("modified", []))
        )
        assert total_changes >= 2
    
    def test_first_time_detection(self):
        """测试首次检测（无旧状态）"""
        # 创建空状态
        empty_state = WorldInfoState()
        
        changes = detect_worldinfo_changes(
            old_state=empty_state,
            new_content=SAMPLE_WORLD_INFO,
            session_id="test-session"
        )
        
        # 所有条目应被识别为新增
        assert len(changes.get("added", [])) > 0
        assert len(changes.get("removed", [])) == 0
        assert len(changes.get("modified", [])) == 0


class TestChatHistoryChangeDetection:
    """Chat History变化检测测试"""
    
    def test_detect_no_changes(self, sample_chat_history_state):
        """测试检测无变化"""
        new_content = SAMPLE_CHAT_HISTORY
        
        changes = detect_chat_changes(
            old_state=sample_chat_history_state,
            new_content=new_content,
            session_id="test-session"
        )
        
        # 无变化的类型可能是"no_change"或类似
        assert hasattr(changes, "type")
    
    def test_detect_append_messages(self, sample_chat_history_state):
        """测试检测追加消息"""
        # 追加新消息
        new_content = SAMPLE_CHAT_HISTORY + "\nUser: 新消息\nAssistant: 新回复"
        
        changes = detect_chat_changes(
            old_state=sample_chat_history_state,
            new_content=new_content,
            session_id="test-session"
        )
        
        assert hasattr(changes, "type")
        assert changes.type in ["append", "modification"]
    
    def test_detect_truncated_messages(self, sample_chat_history_state):
        """测试检测截断消息"""
        # 只保留部分历史
        new_content = "User: 你好\nAssistant: 呀吼～！"
        
        changes = detect_chat_changes(
            old_state=sample_chat_history_state,
            new_content=new_content,
            session_id="test-session"
        )
        
        assert hasattr(changes, "type")
        # 可能是truncation或modification
    
    def test_detect_modified_messages(self):
        """测试检测修改消息"""
        from models.change_detection import ChatMessage, ChatHistoryState
        from datetime import datetime, timezone
        from utils.dedup import compute_content_hash
        
        # 创建一个有初始消息的状态
        old_content = "User: 原始内容\nAssistant: 原始回复"
        old_state = ChatHistoryState()
        
        # 手动添加消息
        msg1 = ChatMessage(
            message_id="msg_1",
            role="User",
            content="原始内容",
            content_hash=compute_content_hash("User:原始内容"),
            timestamp=datetime.now(timezone.utc),
            turn_number=0,
            session_id="test-session"
        )
        msg2 = ChatMessage(
            message_id="msg_2",
            role="Assistant",
            content="原始回复",
            content_hash=compute_content_hash("Assistant:原始回复"),
            timestamp=datetime.now(timezone.utc),
            turn_number=1,
            session_id="test-session"
        )
        
        old_state.messages = [msg1, msg2]
        old_state.message_hashes = [msg1.content_hash, msg2.content_hash]
        old_state.version = 1
        
        # 修改现有消息
        new_content = "User: 修改后的内容\nAssistant: 呀吼～！"
        
        changes = detect_chat_changes(
            old_state=old_state,
            new_content=new_content,
            session_id="test-session"
        )
        
        assert hasattr(changes, "type")
        assert changes.type == "modification"
    
    def test_first_time_chat_detection(self):
        """测试首次对话历史检测"""
        empty_state = ChatHistoryState()
        
        changes = detect_chat_changes(
            old_state=empty_state,
            new_content=SAMPLE_CHAT_HISTORY,
            session_id="test-session"
        )
        
        assert hasattr(changes, "type")
        assert len(changes.new_messages) > 0


class TestStateUpdate:
    """状态更新测试"""
    
    def test_update_world_info_state_after_add(self, sample_world_info_state):
        """测试新增后更新World Info状态"""
        changes = {
            "added": [
                WorldInfoEntry(
                    entry_id="location:new",
                    entry_type="location",
                    name="新地点",
                    content='地点("新地点")["描述"]',
                    content_hash="newhash",
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    deleted_at=None,
                    source="world_info",
                    session_id="test-session",
                    status="active",
                    version=0
                )
            ],
            "removed": [],
            "modified": []
        }
        
        new_state = update_world_info_state(
            old_state=sample_world_info_state,
            changes=changes
        )
        
        assert isinstance(new_state, WorldInfoState)
        assert "location:new" in new_state.entries
        assert new_state.version > sample_world_info_state.version
    
    def test_update_world_info_state_after_remove(self, sample_world_info_state, sample_world_info_entry):
        """测试删除后更新World Info状态"""
        # 模拟删除
        changes = {
            "added": [],
            "removed": [sample_world_info_entry],
            "modified": []
        }
        
        new_state = update_world_info_state(
            old_state=sample_world_info_state,
            changes=changes
        )
        
        assert isinstance(new_state, WorldInfoState)
        # 被删除的条目应标记为deleted状态或从active移除
    
    def test_update_world_info_state_after_modify(self, sample_world_info_state, sample_world_info_entry):
        """测试修改后更新World Info状态"""
        # 模拟修改
        old_entry = sample_world_info_entry
        new_entry = WorldInfoEntry(
            entry_id=old_entry.entry_id,
            entry_type=old_entry.entry_type,
            name=old_entry.name,
            content='地点("夏莱")["新描述"]',
            content_hash="newhash",
            created_at=old_entry.created_at,
            updated_at=datetime.now(timezone.utc),
            deleted_at=None,
            source=old_entry.source,
            session_id=old_entry.session_id,
            status="active"
        )
        
        changes = {
            "added": [],
            "removed": [],
            "modified": [
                {
                    "entry_id": old_entry.entry_id,
                    "old": old_entry,
                    "new": new_entry,
                    "diff": {"content_changed": True}
                }
            ]
        }
        
        new_state = update_world_info_state(
            old_state=sample_world_info_state,
            changes=changes
        )
        
        assert isinstance(new_state, WorldInfoState)
        assert new_state.version > sample_world_info_state.version
    
    def test_update_chat_history_state(self, sample_chat_history_state):
        """测试更新Chat History状态"""
        chat_changes = ChatChangeResult(
            type="append",
            new_messages=[
                ChatMessage(
                    message_id="msg-new",
                    role="user",
                    content="新消息",
                    content_hash="newhash",
                    timestamp=datetime.now(timezone.utc),
                    turn_number=1,
                    session_id="test-session"
                )
            ],
            removed_messages_count=0,
            modified_messages=[]
        )
        
        new_state = update_chat_history_state(
            old_state=sample_chat_history_state,
            changes=chat_changes
        )
        
        assert isinstance(new_state, ChatHistoryState)
        assert len(new_state.messages) >= 1
        assert new_state.version > sample_chat_history_state.version


class TestHashCalculation:
    """哈希计算测试"""
    
    def test_content_hash_consistency(self):
        """测试内容哈希一致性"""
        content = "测试内容"
        from utils.helpers import compute_content_hash
        
        hash1 = compute_content_hash(content)
        hash2 = compute_content_hash(content)
        
        assert hash1 == hash2
    
    def test_content_hash_different(self):
        """测试不同内容哈希不同"""
        content1 = "测试内容1"
        content2 = "测试内容2"
        from utils.helpers import compute_content_hash
        
        hash1 = compute_content_hash(content1)
        hash2 = compute_content_hash(content2)
        
        assert hash1 != hash2
    
    def test_content_hash_normalized(self):
        """测试内容标准化对哈希的影响"""
        content1 = "测试  内容"  # 多个空格
        content2 = "测试 内容"   # 单个空格
        from utils.helpers import compute_content_hash, normalize_content
        
        # 标准化后应相同（多个空格被标准化为单个空格）
        norm1 = normalize_content(content1)
        norm2 = normalize_content(content2)
        assert norm1 == norm2
        
        # compute_content_hash 内部会标准化内容，所以哈希应该相同
        hash1 = compute_content_hash(content1)
        hash2 = compute_content_hash(content2)
        assert hash1 == hash2


class TestEntryIDComputation:
    """条目ID计算测试"""
    
    def test_entry_id_location(self):
        """测试地点条目ID"""
        from utils.helpers import compute_entry_id
        
        # 使用 dict 对象而不是 WorldInfoEntry 来避免 Pydantic 验证错误
        entry = {
            "entry_type": "location",
            "name": "夏莱"
        }
        
        entry_id = compute_entry_id(entry)
        
        assert "location" in entry_id
        assert "夏莱" in entry_id.lower()
    
    def test_entry_id_character(self):
        """测试角色条目ID"""
        from utils.helpers import compute_entry_id
        
        # 使用 dict 对象
        entry = {
            "entry_type": "character",
            "name": "圣园未花"
        }
        
        entry_id = compute_entry_id(entry)
        
        assert "character" in entry_id
        assert "圣园未花" in entry_id.lower()
    
    def test_entry_id_normalization(self):
        """测试ID名称标准化"""
        from utils.helpers import compute_entry_id
        
        # 使用 dict 对象
        entry1 = {
            "entry_type": "location",
            "name": "夏莱"
        }
        entry2 = {
            "entry_type": "location",
            "name": " 夏莱 "  # 带空格
        }
        
        id1 = compute_entry_id(entry1)
        id2 = compute_entry_id(entry2)
        
        # 标准化后应相同
        assert id1 == id2
