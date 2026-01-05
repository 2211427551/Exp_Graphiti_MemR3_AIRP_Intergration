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
