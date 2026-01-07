# ============================================
# 辅助函数模块
# ============================================
import re
import uuid
from typing import Optional


def sanitize_input(text: str) -> str:
    """
    清理用户输入
    
    参数:
        text: str
                待清理的文本
    
    返回:
        str: 清理后的文本
    
    功能:
        - 移除危险字符
        - 限制长度
        - 标准化空白字符
    """
    if not text:
        return ""
    
    # 移除控制字符（保留换行符和制表符）
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    
    # 标准化空白字符
    cleaned = re.sub(r'[ \t]+', ' ', cleaned)
    cleaned = cleaned.strip()
    
    # 限制长度（防止过长的输入）
    max_length = 10000
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length] + "..."
    
    return cleaned


def generate_session_id() -> str:
    """
    生成会话ID
    
    返回:
        str: 唯一的会话ID
    """
    return f"sess-{uuid.uuid4().hex}"


def is_valid_email(email: str) -> bool:
    """
    验证电子邮件格式
    
    参数:
        email: str
                电子邮件地址
    
    返回:
        bool: 是否有效
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    截断文本
    
    参数:
        text: str
                待截断的文本
        max_length: int = 100
                最大长度
        suffix: str = "..."
                后缀
    
    返回:
        str: 截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def format_timestamp(timestamp: float) -> str:
    """
    格式化时间戳
    
    参数:
        timestamp: float
                Unix时间戳
    
    返回:
        str: 格式化的时间字符串
    """
    from datetime import datetime
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def compute_content_hash(content: str) -> str:
    """
    计算内容哈希
    
    参数:
        content: str
                待哈希的内容
    
    返回:
        str: MD5哈希字符串
    
    算法：
        1. 标准化内容（移除多余空格）
        2. 计算MD5哈希
    """
    import hashlib
    
    # 标准化内容
    normalized = re.sub(r'\s+', ' ', content)
    normalized = normalized.strip()
    
    # 计算MD5哈希
    return hashlib.md5(normalized.encode('utf-8')).hexdigest()


def normalize_content(content: str) -> str:
    """
    标准化内容
    
    参数:
        content: str
                待标准化的内容
    
    返回:
        str: 标准化后的内容
    
    算法：
        1. 移除多余空格
        2. 标准化空白字符
    """
    # 移除多余空格
    normalized = re.sub(r'\s+', ' ', content)
    
    # 标准化空白字符
    normalized = normalized.strip()
    
    return normalized


def compute_entry_id(entry_info) -> str:
    """
    计算条目ID
    
    参数:
        entry_info: dict 或 WorldInfoEntry
                条目信息，包含 entry_type 和 name
    
    返回:
        str: 条目ID字符串
    
    格式:
        entry_type:name (标准化)
    
    算法：
        1. 提取 entry_type 和 name
        2. 标准化名称
        3. 组合ID
    """
    # 提取类型和名称
    if hasattr(entry_info, 'entry_type'):
        entry_type = entry_info.entry_type
    else:
        entry_type = entry_info.get('entry_type', '')
    
    if hasattr(entry_info, 'name'):
        name = entry_info.name
    else:
        name = entry_info.get('name', '')
    
    # 标准化名称
    normalized_name = re.sub(r'[^\w\u4e00-\u9fa5]', '', name.lower())
    
    return f"{entry_type}:{normalized_name}"
