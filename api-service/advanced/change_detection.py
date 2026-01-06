"""
变化检测核心逻辑

实现World Info和Chat History的变化检测算法
"""

import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

from api_service.models.change_detection import (
    WorldInfoEntry,
    WorldInfoState,
    ChatMessage,
    ChatHistoryState,
    StateDiff,
    EntryDifference,
    ChangeDetectionResult,
    ChatChangeResult
)
from api_service.utils.dedup import (
    compute_entry_id,
    normalize_name,
    compute_content_hash,
    normalize_content,
    compute_text_similarity
)


def detect_worldinfo_changes(
    old_state: Optional[WorldInfoState],
    new_content: str,
    session_id: str
) -> ChangeDetectionResult:
    """
    检测World Info的变化
    
    算法：
    1. 解析新内容为条目
    2. 为每个新条目计算entry_id和content_hash
    3. 与旧状态比较
    4. 分类变化类型：新增、删除、修改、未变化
    
    参数:
        old_state: 旧的世界书状态
        new_content: 新的世界书内容
        session_id: 会话ID
    
    返回:
        Dict: {
            "added": [新增条目],
            "removed": [删除条目],
            "modified": [修改详情],
            "unchanged": [未变化条目]
        }
    """
    changes = {
        "added": [],
        "removed": [],
        "modified": [],
        "unchanged": []
    }
    
    # 步骤1: 解析新内容为条目
    new_entries = parse_worldinfo_entries(new_content)
    
    # 步骤2: 为每个新条目计算特征
    new_entries_with_id = []
    for entry in new_entries:
        entry_id = compute_entry_id(entry.entry_type, entry.name)
        content_hash = compute_content_hash(entry.content)
        
        entry.entry_id = entry_id
        entry.content_hash = content_hash
        entry.session_id = session_id
        entry.created_at = datetime.now(timezone.utc)
        
        new_entries_with_id.append(entry)
    
    # 如果没有旧状态，所有都是新增
    if old_state is None:
        changes["added"] = new_entries_with_id
        return changes
    
    # 步骤3: 检测新增
    new_ids = {e.entry_id for e in new_entries_with_id}
    old_ids = set(old_state.entries.keys())
    
    added_ids = new_ids - old_ids
    for entry_id in added_ids:
        entry = next(e for e in new_entries_with_id if e.entry_id == entry_id)
        changes["added"].append(entry)
    
    # 步骤4: 检测删除
    removed_ids = old_ids - new_ids
    for entry_id in removed_ids:
        old_entry = old_state.entries[entry_id]
        changes["removed"].append(old_entry)
    
    # 步骤5: 检测修改
    common_ids = old_ids & new_ids
    for entry_id in common_ids:
        old_entry = old_state.entries[entry_id]
        new_entry = next(e for e in new_entries_with_id if e.entry_id == entry_id)
        
        if old_entry.content_hash != new_entry.content_hash:
            # 内容哈希不同，判定为修改
            diff = compute_entry_diff(old_entry, new_entry)
            changes["modified"].append({
                "entry_id": entry_id,
                "old": old_entry,
                "new": new_entry,
                "diff": diff
            })
        else:
            # 未变化
            changes["unchanged"].append(new_entry)
    
    return changes


def parse_worldinfo_entries(content: str) -> List[WorldInfoEntry]:
    """
    解析世界书内容为条目
    
    支持格式：
    - 地点("地点名")["描述"]
    - 角色("角色名")["描述"]
    - 概念("概念名")["描述"]
    - Character_Profile_of: 角色名
    
    返回:
        List[WorldInfoEntry]: 条目列表
    """
    entries = []
    lines = content.strip().split('\n')
    current_entry_lines = []
    
    for line in lines:
        if line.strip() == '':
            if current_entry_lines:
                entry_text = '\n'.join(current_entry_lines).strip()
                entry = parse_entry(entry_text)
                if entry:
                    entries.append(entry)
                current_entry_lines = []
        else:
            current_entry_lines.append(line)
    
    # 处理最后一个条目
    if current_entry_lines:
        entry_text = '\n'.join(current_entry_lines).strip()
        entry = parse_entry(entry_text)
        if entry:
            entries.append(entry)
    
    return entries


def parse_entry(text: str) -> Optional[WorldInfoEntry]:
    """
    解析单个条目
    
    检测条目类型：
    - 地点("地点名")["描述"]
    - 角色("角色名")["描述"]
    - 概念("概念名")["描述"]
    - Character_Profile_of: 角色名
    
    返回:
        Optional[WorldInfoEntry]: 解析后的条目
    """
    # 检测地点
    location_match = re.match(r'地点\("([^"]+)"\)\)', text)
    if location_match:
        return WorldInfoEntry(
            entry_type="location",
            name=location_match.group(1),
            content=text,
            properties=extract_properties(text)
        )
    
    # 检测角色
    character_match = re.match(r'角色\("([^"]+)"\)\)', text)
    if character_match:
        return WorldInfoEntry(
            entry_type="character",
            name=character_match.group(1),
            content=text,
            properties=extract_properties(text)
        )
    
    # 检测概念
    concept_match = re.match(r'概念\("([^"]+)"\)\)', text)
    if concept_match:
        return WorldInfoEntry(
            entry_type="concept",
            name=concept_match.group(1),
            content=text,
            properties=extract_properties(text)
        )
    
    # 检测Character_Profile_of
    profile_match = re.match(r'Character_Profile_of:\s*([^\n]+)', text)
    if profile_match:
        return WorldInfoEntry(
            entry_type="character",
            name=profile_match.group(1).strip(),
            content=text,
            properties=extract_properties(text)
        )
    
    # 默认：通用条目（不匹配已知格式）
    if len(text.strip()) > 0:
        return WorldInfoEntry(
            entry_type="general",
            name=text.split('\n')[0][:50],  # 使用第一行前50字符作为名称
            content=text,
            properties={}
        )
    
    return None


def extract_properties(text: str) -> Dict[str, str]:
    """
    提取条目属性
    
    算法：
    1. 识别属性对（key: value格式）
    2. 识别方括号属性["value"]
    3. 提取元数据
    
    返回:
        Dict: 属性字典
    """
    properties = {}
    
    # 提取方括号属性
    bracket_matches = re.findall(r'\["([^"]+)"\]', text)
    for i, match in enumerate(bracket_matches):
        if i == 0:
            properties["primary_description"] = match
        else:
            properties[f"attribute_{i}"] = match
    
    # 提取key: value属性
    kv_matches = re.findall(r'([^\s:]+):\s*([^\n]+)', text)
    for key, value in kv_matches:
        properties[key.strip()] = value.strip()
    
    return properties


def compute_entry_diff(old_entry: WorldInfoEntry, new_entry: WorldInfoEntry) -> StateDiff:
    """
    计算条目差异
    
    分析：
    1. 名称是否变化
    2. 内容是否变化
    3. 属性是否变化
    4. 计算变化类型和程度
    
    参数:
        old_entry: 旧条目
        new_entry: 新条目
    
    返回:
        Dict: 差异详情
    """
    diff = StateDiff()
    
    # 检查名称
    if old_entry.name != new_entry.name:
        diff.name_changed = True
    
    # 检查内容
    if old_entry.content != new_entry.content:
        diff.content_changed = True
        
        # 计算变化程度
        similarity = compute_text_similarity(old_entry.content, new_entry.content)
        diff.change_percentage = 1.0 - similarity
    
    # 检查属性
    old_props = old_entry.properties or {}
    new_props = new_entry.properties or {}
    
    all_prop_keys = set(old_props.keys()) | set(new_props.keys())
    
    for key in all_prop_keys:
        old_val = old_props.get(key)
        new_val = new_props.get(key)
        
        if old_val != new_val:
            diff.properties_changed[key] = {
                "old": old_val,
                "new": new_val
            }
    
    # 确定变化类型
    if diff.content_changed:
        if diff.change_percentage > 0.7:
            diff.change_type = "replacement"  # 大部分内容改变
        elif len(new_entry.content) > len(old_entry.content) * 1.5:
            diff.change_type = "expansion"  # 内容大幅增加
        elif len(new_entry.content) < len(old_entry.content) * 0.7:
            diff.change_type = "reduction"  # 内容大幅减少
        else:
            diff.change_type = "update"  # 正常更新
    
    return diff


def detect_chat_changes(
    old_state: Optional[ChatHistoryState],
    new_content: str,
    session_id: str
) -> ChatChangeResult:
    """
    检测Chat History的变化
    
    算法：
    1. 解析新对话
    2. 基于消息哈希的精确匹配
    3. 增量分析（新增、删除、修改）
    4. 分类变化类型
    
    参数:
        old_state: 旧的对话状态
        new_content: 新的对话内容
        session_id: 会话ID
    
    返回:
        Dict: 变化详情
    """
    # 步骤1: 解析新对话
    new_messages = parse_chat_messages(new_content, session_id)
    
    # 步骤2: 计算新消息的哈希
    new_hashes = [m.content_hash for m in new_messages]
    old_hashes = old_state.message_hashes if old_state else []
    
    # 步骤3: 基于哈希的快速检测
    if old_hashes == new_hashes:
        # 完全相同
        return ChatChangeResult(
            type="no_change",
            message_count=len(new_messages)
        )
    
    # 步骤4: 增量分析
    # 找出第一个不同的位置
    diff_index = find_first_diff_index(old_hashes, new_hashes)
    
    if diff_index is None:
        return ChatChangeResult(
            type="no_change",
            message_count=len(new_messages)
        )
    
    # 判断变化类型
    if len(new_hashes) > len(old_hashes):
        # 消息数量增加，可能是追加
        if old_hashes[:diff_index] == new_hashes[:diff_index]:
            # 前面部分相同，后面新增
            new_messages_count = len(new_hashes) - len(old_hashes)
            
            # 检查新增的尾部消息
            new_messages_tail = new_messages[len(old_hashes):]
            
            return ChatChangeResult(
                type="append",
                diff_index=diff_index,
                new_messages=new_messages_tail,
                new_messages_count=new_messages_count
            )
    
    if len(new_hashes) < len(old_hashes):
        # 消息数量减少，可能是截断
        if new_hashes == old_hashes[:len(new_hashes)]:
            # 新内容是旧内容的前部分
            return ChatChangeResult(
                type="truncation",
                removed_messages_count=len(old_hashes) - len(new_hashes)
            )
    
    # 复杂变化（修改或中间插入/删除）
    # 使用更详细的diff算法
    detailed_diff = compute_detailed_diff(old_state.messages, new_messages)
    
    return ChatChangeResult(
        type="modification",
        details=detailed_diff,
        message_count=len(new_messages)
    )


def parse_chat_messages(content: str, session_id: str) -> List[ChatMessage]:
    """
    解析对话历史
    
    算法：
    1. 识别所有对话行
    2. 动态识别说话者名字
    3. 提取对话内容
    4. 构建ChatMessage对象
    
    返回:
        List[ChatMessage]: 对话消息列表
    """
    lines = content.strip().split('\n')
    turns = []
    turn_number = 0
    
    # 简单的说话者映射（第一轮User，后续Assistant）
    speaker_mapping = {}
    
    for line in lines:
        # 匹配对话行（支持User:或Assistant:或角色名:）
        match = re.match(r"^(User|Assistant|[A-Za-z\u4e00-\u9fa5]+):\s*(.+)$", line.strip())
        
        if match:
            speaker = match.group(1).strip()
            content = match.group(2).strip()
            
            # 动态角色名映射
            if speaker not in speaker_mapping:
                if speaker.lower() == "user":
                    speaker_mapping[speaker] = "User"
                elif speaker.lower() in ["assistant", "ai"]:
                    speaker_mapping[speaker] = "Assistant"
                else:
                    # 新角色名，默认判定为Assistant
                    speaker_mapping[speaker] = "Assistant"
            
            # 计算消息哈希
            content_hash = compute_content_hash(f"{speaker}:{content}")
            
            turns.append(ChatMessage(
                message_id=f"msg_{session_id}_{turn_number}",
                role=speaker_mapping[speaker],
                content=content,
                content_hash=content_hash,
                timestamp=datetime.now(timezone.utc),
                turn_number=turn_number,
                session_id=session_id,
                speaker_mapping=speaker
            ))
            
            turn_number += 1
    
    return turns


def find_first_diff_index(list1: List, list2: List) -> Optional[int]:
    """
    找出两个列表第一个不同的索引
    
    参数:
        list1: 列表1
        list2: 列表2
    
    返回:
        Optional[int]: 第一个不同的索引，完全相同返回None
    """
    min_len = min(len(list1), len(list2))
    
    for i in range(min_len):
        if list1[i] != list2[i]:
            return i
    
    if len(list1) != len(list2):
        return min_len
    
    return None  # 完全相同


def compute_detailed_diff(old_messages: List[ChatMessage], new_messages: List[ChatMessage]) -> List[Dict]:
    """
    计算详细的差异
    
    使用文本diff算法（简化版）
    
    参数:
        old_messages: 旧消息列表
        new_messages: 新消息列表
    
    返回:
        List[Dict]: 差异详情
    """
    diff = {
        "added": [],
        "removed": [],
        "modified": []
    }
    
    # 简单的逐条比较
    max_len = max(len(old_messages), len(new_messages))
    
    for i in range(max_len):
        old_msg = old_messages[i] if i < len(old_messages) else None
        new_msg = new_messages[i] if i < len(new_messages) else None
        
        if old_msg is None:
            diff["added"].append({
                "index": i,
                "message": new_msg
            })
        elif new_msg is None:
            diff["removed"].append({
                "index": i,
                "message": old_msg
            })
        elif old_msg.content_hash != new_msg.content_hash:
            diff["modified"].append({
                "index": i,
                "old_message": old_msg,
                "new_message": new_msg
            })
    
    return diff


def update_world_info_state(
    old_state: WorldInfoState,
    changes: Dict
) -> WorldInfoState:
    """
    更新世界书状态
    
    参数:
        old_state: 旧状态
        changes: 变化检测结果
    
    返回:
        WorldInfoState: 更新后的状态
    """
    new_state = WorldInfoState(
        entries=old_state.entries.copy(),
        entry_hashes=old_state.entry_hashes.copy(),
        timestamp=datetime.now(timezone.utc),
        version=old_state.version + 1
    )
    
    # 处理新增条目
    for entry in changes.get("added", []):
        new_state.entries[entry.entry_id] = entry
        new_state.entry_hashes[entry.content_hash] = entry.entry_id
    
    # 处理删除条目
    for entry in changes.get("removed", []):
        if entry.entry_id in new_state.entries:
            del new_state.entries[entry.entry_id]
        if entry.content_hash in new_state.entry_hashes:
            del new_state.entry_hashes[entry.content_hash]
    
    # 处理修改条目
    for mod in changes.get("modified", []):
        new_entry = mod["new"]
        new_state.entries[new_entry.entry_id] = new_entry
        new_state.entry_hashes[new_entry.content_hash] = new_entry.entry_id
    
    return new_state


def update_chat_history_state(
    old_state: Optional[ChatHistoryState],
    changes: ChatChangeResult
) -> ChatHistoryState:
    """
    更新对话历史状态
    
    参数:
        old_state: 旧状态
        changes: 对话变化检测结果
    
    返回:
        ChatHistoryState: 更新后的状态
    """
    if old_state is None:
        # 新状态
        if changes.type == "no_change":
            messages = parse_chat_messages("", "temp")  # 空内容
        else:
            # 这里应该不会执行到，因为没有实际内容
            messages = []
        
        new_state = ChatHistoryState(
            messages=messages,
            message_hashes=[m.content_hash for m in messages],
            total_hash=None,
            version=1
        )
        return new_state
    
    if changes.type == "no_change":
        # 完全相同，无需更新
        return old_state
    
    if changes.type == "append":
        # 追加新消息
        new_state = ChatHistoryState(
            messages=old_state.messages + changes.new_messages,
            message_hashes=old_state.message_hashes + [m.content_hash for m in changes.new_messages],
            total_hash=None,
            version=old_state.version + 1
        )
    
    elif changes.type == "truncation":
        # 截断消息
        new_count = len(old_state.messages) - changes.removed_messages_count
        new_state = ChatHistoryState(
            messages=old_state.messages[:new_count],
            message_hashes=old_state.message_hashes[:new_count],
            total_hash=None,
            version=old_state.version + 1
        )
    
    elif changes.type == "modification":
        # 复杂变化，重新计算
        new_messages = []
        new_hashes = []
        
        # 保留未修改的
        if changes.details:
            for detail in changes.details:
                if detail["type"] == "added":
                    new_messages.append(detail["message"])
                    new_hashes.append(detail["message"].content_hash)
                elif detail["type"] == "removed":
                    # 跳过
                    pass
                elif detail["type"] == "modified":
                    # 使用新消息
                    new_messages.append(detail["new_message"])
                    new_hashes.append(detail["new_message"].content_hash)
        
        new_state = ChatHistoryState(
            messages=new_messages,
            message_hashes=new_hashes,
            total_hash=None,
            version=old_state.version + 1
        )
    
    return new_state
