"""
去重工具

提供内容哈希计算、文本标准化和去重检查功能
"""

import hashlib
import re
from typing import Dict, Tuple, Optional


def normalize_name(name: str) -> str:
    """
    标准化名称
    
    处理：
    1. 统一大小写
    2. 去除多余空格
    3. 标准化标点
    4. 保留中文字符、字母、数字
    
    参数:
        name: 条目/实体名称
    
    返回:
        str: 标准化后的名称
    """
    import string
    
    # 转换为小写
    normalized = name.lower()
    
    # 去除多余空格
    normalized = re.sub(r'\s+', ' ', normalized)
    normalized = normalized.strip()
    
    # 标准化中文标点
    normalized = normalized.replace('：', ':')
    normalized = normalized.replace('（', '(').replace('）', ')')
    normalized = normalized.replace('【', '[').replace('】', ']')
    
    # 构建允许的字符集
    # 保留：中文字符、英文字母、数字、基本标点
    result = []
    for char in normalized:
        # 保留中文字符（Unicode范围）
        if '\u4e00' <= char <= '\u9fff':
            result.append(char)
        # 保留英文字母和数字
        elif char in string.ascii_letters + string.digits:
            result.append(char)
        # 保留基本标点
        elif char in ' :(),.-_':
            result.append(char)
        # 其他字符跳过
    
    return ''.join(result)


def normalize_content(content: str) -> str:
    """
    标准化内容
    
    处理：
    1. 统一换行符
    2. 去除首尾空白
    3. 去除多余空行
    4. 标准化标点
    
    参数:
        content: 内容文本
    
    返回:
        str: 标准化后的内容
    """
    # 统一换行符
    normalized = content.replace('\r\n', '\n').replace('\r', '\n')
    
    # 去除首尾空白
    normalized = normalized.strip()
    
    # 去除多余空行
    normalized = re.sub(r'\n{3,}', '\n\n', normalized)
    
    # 标准化标点
    normalized = normalized.replace('：', ':')
    normalized = normalized.replace('，', ',')
    normalized = normalized.replace('。', '.')
    
    return normalized


def compute_content_hash(content: str) -> str:
    """
    计算内容哈希
    
    算法：
    1. 文本标准化（去除空白、标点差异）
    2. 计算MD5哈希
    
    参数:
        content: 内容文本
    
    返回:
        str: MD5哈希值
    """
    import hashlib
    
    # 标准化
    normalized = normalize_content(content)
    
    # 计算哈希
    hash_value = hashlib.md5(normalized.encode('utf-8')).hexdigest()
    
    return hash_value


def compute_content_hashes(content: str) -> Dict[str, str]:
    """
    计算内容的多级哈希
    
    返回:
        Dict: {
            "exact": MD5哈希,
            "structural": 结构哈希,
            "semantic": 语义哈希（可选，当前为None）
        }
    """
    import hashlib
    
    # 精确哈希
    normalized = normalize_content(content)
    exact_hash = hashlib.md5(normalized.encode('utf-8')).hexdigest()
    
    # 结构哈希（去除具体内容，保留结构）
    structural = extract_structural_fingerprint(content)
    structural_hash = hashlib.md5(structural.encode('utf-8')).hexdigest()
    
    # 语义哈希（可选，当前不实现）
    semantic_hash = None  # TODO: 实现基于embedding的语义哈希
    
    return {
        "exact": exact_hash,
        "structural": structural_hash,
        "semantic": semantic_hash
    }


def extract_structural_fingerprint(content: str) -> str:
    """
    提取结构指纹
    
    算法：
    1. 移除具体内容
    2. 保留结构特征（段落、列表、标题）
    3. 标准化
    
    参数:
        content: 内容文本
    
    返回:
        str: 结构指纹
    """
    lines = content.split('\n')
    structural_lines = []
    
    for line in lines:
        # 识别结构标记
        if re.match(r'^#{1,6}\s', line):  # Markdown标题
            match_result = re.match(r'^#+', line)
            if match_result:
                structural_lines.append('#' * len(match_result.group()))
            else:
                structural_lines.append('#')
        elif re.match(r'^\s*[-*+]\s', line):  # 列表项
            structural_lines.append('-')
        elif line.strip() == '':  # 空行
            structural_lines.append('')
        else:
            structural_lines.append('text')  # 普通文本
    
    return '\n'.join(structural_lines)


def compute_entry_id(entry_type: str, name: str) -> str:
    """
    计算条目的唯一标识
    
    设计原则：
    - 基于条目类型和关键属性生成稳定ID
    - 名称微小变化不会导致ID变化
    - 相同实体在不同地方出现有相同ID
    - 支持条目重命名跟踪
    
    参数:
        entry_type: 条目类型（location, character, concept等）
        name: 条目名称
    
    返回:
        str: 条目ID
    """
    # 标准化名称
    normalized_name = normalize_name(name)
    
    # 生成ID
    if entry_type == "location":
        entry_id = f"location:{normalized_name}"
    elif entry_type == "character":
        entry_id = f"character:{normalized_name}"
    elif entry_type == "concept":
        entry_id = f"concept:{normalized_name}"
    else:
        entry_id = f"{entry_type}:{normalized_name}"
    
    return entry_id


def compute_text_similarity(text1: str, text2: str) -> float:
    """
    计算文本相似度
    
    算法：
    1. 字符级Jaccard相似度（基于字符集的交集与并集）
    
    参数:
        text1: 文本1
        text2: 文本2
    
    返回:
        float: 相似度（0.0-1.0）
    """
    set1 = set(text1)
    set2 = set(text2)
    
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    
    return intersection / union if union > 0 else 0.0


def find_first_diff_index(list1, list2) -> Optional[int]:
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
