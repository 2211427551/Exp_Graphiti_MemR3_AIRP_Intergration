"""
SillyTavern增强解析器
专门处理SillyTavern的复杂输入格式
"""

import re
import logging
import hashlib
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import json
from collections import defaultdict
import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
try:
    from config.settings import settings
except ImportError:
    # 向后兼容：如果直接运行文件，尝试相对导入
    from config.settings import settings

logger = logging.getLogger(__name__)


class ContentCategory(Enum):
    """内容分类枚举"""
    CORE_GUIDANCE = "core_guidance"          # 核心指导
    BASIC_STYLE = "basic_style"              # 基础风格
    CREATION_RULES = "creation_rules"        # 创作准则
    PERSONA_DESCRIPTION = "persona_description"  # 用户设定描述
    WORLD_INFO = "world_info"                # 世界书
    CHARACTER_DESCRIPTION = "character_description"  # 角色描述
    CHAT_HISTORY = "chat_history"            # 对话历史
    SUPPLEMENTARY = "supplementary"          # 补充资料
    NARRATIVE = "narrative"                  # 叙事内容
    UNKNOWN = "unknown"                      # 未知类型


@dataclass
class TagInfo:
    """标签信息"""
    tag_name: str
    tag_type: str  # opening, closing, self-closing, wikilink, variable
    full_match: str
    attributes: Optional[Dict[str, str]]
    parent_tag: Optional[str] = None
    content: str = ""
    semantic_category: Optional[ContentCategory] = None
    confidence: float = 0.7
    position: int = 0


@dataclass
class DocumentBlock:
    """文档块"""
    block_id: str
    category: ContentCategory
    content: str
    tags: List[TagInfo]
    metadata: Dict[str, Any]
    hash_value: str
    start_pos: int
    end_pos: int


class SillyTavernParser:
    """SillyTavern增强解析器"""
    
    def __init__(self):
        """初始化解析器"""
        self.compiled_patterns = self._compile_sillytavern_patterns()
        self.session_cache = {}
        self.tag_mapping = self._initialize_tag_mapping()
        
    def _compile_sillytavern_patterns(self) -> List[re.Pattern]:
        """编译SillyTavern专用正则表达式模式（优化版）"""
        patterns = []
        
        # SillyTavern常用标签模式（优化和扩展）
        sillytavern_patterns = [
            # 标准XML风格标签（支持嵌套和长内容）
            r'<(\w[\w-]*)>([\s\S]*?)</\1>',  # 成对标签：<核心指导>内容</核心指导>
            r'<(\w[\w-]*)\s+([^>]+)>([\s\S]*?)</\1>',  # 带属性的成对标签
            
            # SillyTavern特殊格式（优化检测）
            r'<\|(\w[\w\s]+)\|>([\s\S]*?)(?=<\||$)',  # <|User|>、<|Assistant|>（支持空格）
            r'\{\{([^{}]+)\}\}',  # 变量标签：{{character}}、{{user}}
            r'\[\[([^\[\]]+):([^\[\]]+)\]\]',  # 双链格式：[[location:夏莱办公室]]
            r'\*\*([^*]+)\*\*',  # 强调：**文本**
            r'\*([^*]+)\*',  # 斜体：*文本*
            r'`([^`]+)`',  # 代码：`代码`
            r'```([\s\S]*?)```',  # 代码块：```代码```
            
            # 世界书特定格式（增强型）
            r'地点\(([^)]+)\)\[([^\]]+)\]',  # 地点(名称)[描述]
            r'类别\(([^)]+)\)\[([^\]]+)\]',  # 类别(名称)[描述]
            r'概念\(([^)]+)\)\[([^\]]+)\]',  # 概念(名称)[描述]
            r'世界书条目\(([^)]+)\)\[([^\]]+)\]',  # 世界书条目(名称)[内容]
            
            # 角色描述格式（扩展）
            r'Character_Profile_of:\s*([^\n<]+)',  # Character_Profile_of: 角色名（支持复杂名称）
            r'character:\s*\{([^}]+)\}',  # character: {属性}
            r'角色：([^\n<]+)',  # 中文角色标签
            r'人物设定：([^\n<]+)',  # 中文人物设定标签
            
            # 对话格式（优化检测）
            r'([A-Za-z\u4e00-\u9fff]+)[：:]\s*([^\n<]+)',  # 角色名: 对话内容（支持中文）
            r'(?:User|用户)[：:]\s*([^\n<]+)\s*(?:Assistant|助手)[：:]\s*([^\n<]+)',  # 用户/助手对话格式
            
            # 章节/段落标记
            r'#\s+([^\n<]+)',  # 章节标题：## 章节名
            r'【([^】]+)】',  # 中文方括号标记
            r'《([^》]+)》',  # 中文书名号标记
            
            # 语义标记模式（新增）
            r'\[注意\]\s*([^\n<]+)',  # [注意] 内容
            r'\[警告\]\s*([^\n<]+)',  # [警告] 内容
            r'\[说明\]\s*([^\n<]+)',  # [说明] 内容
        ]
        
        # 为每种模式设置优先级和特性
        pattern_metadata = {
            0: {"description": "基础XML标签", "confidence": 0.9},
            1: {"description": "带属性XML标签", "confidence": 0.8},
            2: {"description": "SillyTavern竖线格式", "confidence": 0.95},
            3: {"description": "变量标签", "confidence": 0.9},
            4: {"description": "双链标签", "confidence": 0.85},
            5: {"description": "强调标签", "confidence": 0.8},
            6: {"description": "斜体标签", "confidence": 0.8},
            7: {"description": "代码标签", "confidence": 0.9},
            8: {"description": "代码块标签", "confidence": 0.85},
            9: {"description": "世界书地点", "confidence": 0.8},
            10: {"description": "世界书类别", "confidence": 0.8},
            11: {"description": "世界书概念", "confidence": 0.8},
            12: {"description": "世界书条目", "confidence": 0.75},
            13: {"description": "角色档案", "confidence": 0.9},
            14: {"description": "角色属性", "confidence": 0.8},
            15: {"description": "中文角色标记", "confidence": 0.7},
            16: {"description": "中文人物设定", "confidence": 0.7},
            17: {"description": "对话格式", "confidence": 0.85},
            18: {"description": "用户助手对话", "confidence": 0.9},
            19: {"description": "章节标题", "confidence": 0.8},
            20: {"description": "中文方括号", "confidence": 0.7},
            21: {"description": "中文书名号", "confidence": 0.7},
            22: {"description": "注意标记", "confidence": 0.85},
            23: {"description": "警告标记", "confidence": 0.9},
            24: {"description": "说明标记", "confidence": 0.8},
        }
        
        for i, pattern_str in enumerate(sillytavern_patterns):
            try:
                pattern = re.compile(pattern_str, re.DOTALL | re.MULTILINE)
                patterns.append(pattern)
            except re.error as e:
                logger.warning(f"无效的SillyTavern模式[{i}]: {pattern_str[:50]}..., 错误: {str(e)}")
        
        logger.info(f"已编译 {len(patterns)} 个SillyTavern专用解析模式（优化版）")
        self.pattern_metadata = pattern_metadata
        return patterns
    
    def _extract_sillytavern_tags(self, text: str) -> List[TagInfo]:
        """提取SillyTavern格式的所有标签（优化版）"""
        tags = []
        processed_positions = set()
        
        for pattern_idx, pattern in enumerate(self.compiled_patterns):
            matches = list(pattern.finditer(text))
            
            for match in matches:
                start_pos = match.start()
                end_pos = match.end()
                
                # 检查是否已经被其他模式处理（避免重复）
                if any(start_pos <= pos <= end_pos for pos in processed_positions):
                    continue
                
                # 创建标签对象
                tag = self._create_tag_from_sillytavern_match(match, pattern_idx, text)
                if tag:
                    tags.append(tag)
                    # 记录已处理的位置范围
                    processed_positions.update(range(start_pos, end_pos))
        
        # 按位置排序
        tags.sort(key=lambda x: x.position)
        
        # 分析标签关系和语义（使用优化算法）
        self._optimized_analyze_tag_relationships(tags)
        
        # 过滤低质量标签
        tags = self._filter_low_quality_tags(tags)
        
        logger.debug(f"提取到 {len(tags)} 个标签")
        return tags
    
    def _create_tag_from_sillytavern_match(self, match: re.Match, pattern_idx: int, text: str) -> Optional[TagInfo]:
        """从SillyTavern匹配创建标签对象（优化版）"""
        try:
            full_match = match.group()
            position = match.start()
            
            # 获取模式元数据
            pattern_meta = self.pattern_metadata.get(pattern_idx, {})
            base_confidence = pattern_meta.get("confidence", 0.7)
            
            # 分析标签类型（使用优化算法）
            tag_info = self._optimized_analyze_tag_type(full_match, position, pattern_idx)
            
            if not tag_info:
                return None
            
            # 提取标签内容（优化版）
            tag_info = self._optimized_extract_tag_content(tag_info, text, match)
            
            # 猜测语义类别（优化版）
            tag_info.semantic_category = self._optimized_guess_sillytavern_category(tag_info)
            
            # 计算置信度（考虑模式置信度和内容质量）
            tag_info.confidence = self._calculate_optimized_tag_confidence(tag_info, base_confidence)
            
            # 记录模式来源
            tag_info.metadata = {"pattern_idx": pattern_idx, "pattern_description": pattern_meta.get("description", "")}
            
            return tag_info
            
        except Exception as e:
            logger.debug(f"创建SillyTavern标签失败: {str(e)}, 匹配: {match.group()[:50]}...")
            return None
    
    def _optimized_analyze_tag_type(self, tag_text: str, position: int, pattern_idx: int) -> Optional[TagInfo]:
        """分析标签类型（优化版）"""
        tag_text_lower = tag_text.lower()
        
        # 快速分类
        if tag_text.startswith('</'):
            # 闭标签
            tag_name = tag_text[2:-1].strip()
            return TagInfo(
                tag_name=tag_name,
                tag_type="closing",
                full_match=tag_text,
                attributes=None,
                position=position
            )
        
        elif tag_text.endswith('/>'):
            # 自闭合标签
            inner = tag_text[1:-2].strip()
            parts = inner.split()
            tag_name = parts[0] if parts else ""
            attributes = self._optimized_extract_attributes(inner, tag_name) if len(parts) > 1 else None
            
            return TagInfo(
                tag_name=tag_name,
                tag_type="self-closing",
                full_match=tag_text,
                attributes=attributes,
                position=position
            )
        
        elif tag_text.startswith('<|') and tag_text.endswith('|>'):
            # SillyTavern竖线格式（支持复杂标签名）
            inner = tag_text[2:-2].strip()
            return TagInfo(
                tag_name=inner,
                tag_type="sillytavern_pipe",
                full_match=tag_text,
                attributes=None,
                position=position
            )
        
        elif tag_text.startswith('{{') and tag_text.endswith('}}'):
            # 变量标签
            inner = tag_text[2:-2].strip()
            return TagInfo(
                tag_name=inner,
                tag_type="variable",
                full_match=tag_text,
                attributes=None,
                position=position
            )
        
        elif tag_text.startswith('[[') and tag_text.endswith(']]'):
            # 双链标签
            inner = tag_text[2:-2].strip()
            if ':' in inner:
                link_type, target = inner.split(':', 1)
                return TagInfo(
                    tag_name=link_type.strip(),
                    tag_type="wikilink",
                    full_match=tag_text,
                    attributes={"target": target.strip()},
                    content=target.strip(),
                    position=position
                )
            else:
                return TagInfo(
                    tag_name=inner,
                    tag_type="wikilink",
                    full_match=tag_text,
                    attributes=None,
                    position=position
                )
        
        elif tag_text.startswith('<'):
            # 开标签（增强检测）
            inner = tag_text[1:-1].strip()
            parts = inner.split()
            tag_name = parts[0] if parts else ""
            
            # 处理可能的自闭合简写
            if tag_name.endswith('/'):
                tag_name = tag_name[:-1]
                return TagInfo(
                    tag_name=tag_name,
                    tag_type="self-closing",
                    full_match=tag_text,
                    attributes=self._optimized_extract_attributes(inner, tag_name) if len(parts) > 1 else None,
                    position=position
                )
            
            attributes = self._optimized_extract_attributes(inner, tag_name) if len(parts) > 1 else None
            
            return TagInfo(
                tag_name=tag_name,
                tag_type="opening",
                full_match=tag_text,
                attributes=attributes,
                position=position
            )
        
        elif ':' in tag_text or '：' in tag_text:
            # 对话格式（优化检测）
            colon_pos = tag_text.find(':') if ':' in tag_text else tag_text.find('：')
            role_name = tag_text[:colon_pos].strip()
            content = tag_text[colon_pos+1:].strip() if len(tag_text) > colon_pos+1 else ""
            
            # 扩展常见角色名列表
            common_roles = {
                "User", "Assistant", "System", 
                "用户", "助手", "系统", "旁白",
                "AI", "Bot", "Human", "Narrator",
                "角色A", "角色B", "人物1", "人物2"
            }
            
            if role_name in common_roles or len(role_name) <= 20:  # 限制角色名长度
                return TagInfo(
                    tag_name=role_name,
                    tag_type="dialogue",
                    full_match=tag_text,
                    attributes=None,
                    content=content,
                    position=position
                )
        
        # 特殊格式检测
        if re.search(r'【[^】]+】', tag_text):
            inner = re.search(r'【([^】]+)】', tag_text).group(1)
            return TagInfo(
                tag_name=inner,
                tag_type="chinese_bracket",
                full_match=tag_text,
                attributes=None,
                position=position
            )
        
        if re.search(r'《[^》]+》', tag_text):
            inner = re.search(r'《([^》]+)》', tag_text).group(1)
            return TagInfo(
                tag_name=inner,
                tag_type="chinese_quotation",
                full_match=tag_text,
                attributes=None,
                position=position
            )
        
        if re.search(r'\[(注意|警告|说明)\]\s*', tag_text):
            inner = re.search(r'\[(注意|警告|说明)\]\s*([^\n<]+)', tag_text)
            if inner:
                return TagInfo(
                    tag_name=inner.group(1),
                    tag_type="semantic_marker",
                    full_match=tag_text,
                    attributes={"content": inner.group(2).strip()},
                    content=inner.group(2).strip(),
                    position=position
                )
        
        return None
    
    def _optimized_extract_attributes(self, attribute_text: str, tag_name: str) -> Dict[str, str]:
        """提取标签属性（优化版）"""
        attributes = {}
        
        # 移除标签名
        remaining = attribute_text[len(tag_name):].strip()
        
        # 处理标准属性格式：name="value" 或 name='value'
        attr_pattern = r'(\w[\w-]*)\s*=\s*["\']([^"\']*)["\']'
        matches = re.findall(attr_pattern, remaining)
        
        for name, value in matches:
            attributes[name] = value
            # 移除已匹配部分
            remaining = re.sub(f'{re.escape(name)}\\s*=\\s*["\']{re.escape(value)}["\']', '', remaining)
        
        # 处理简化格式：name=value（无引号）
        simple_pattern = r'(\w[\w-]*)\s*=\s*(\S+)'
        simple_matches = re.findall(simple_pattern, remaining)
        
        for name, value in simple_matches:
            if name not in attributes:
                attributes[name] = value
        
        return attributes if attributes else None
    
    def _optimized_extract_tag_content(self, tag_info: TagInfo, text: str, match: re.Match) -> TagInfo:
        """提取标签内容（优化版）"""
        if tag_info.tag_type in ["opening", "self-closing"]:
            # 尝试提取直到下一个闭标签的内容
            if tag_info.tag_type == "opening":
                end_pattern = f'</{re.escape(tag_info.tag_name)}>'
                end_match = re.search(end_pattern, text[tag_info.position:])
                if end_match:
                    content_start = tag_info.position + len(tag_info.full_match)
                    content_end = tag_info.position + end_match.start()
                    tag_info.content = text[content_start:content_end].strip()
        
        # 如果通过正则匹配已有内容，使用它
        if len(match.groups()) > 1:
            for i, group in enumerate(match.groups()):
                if i > 0 and group and not tag_info.content:
                    tag_info.content = group.strip()
                    break
        
        return tag_info
    
    def _optimized_guess_sillytavern_category(self, tag_info: TagInfo) -> ContentCategory:
        """猜测SillyTavern标签的语义类别（优化版）"""
        
        # 首先检查映射表
        if tag_info.tag_name in self.tag_mapping:
            return self.tag_mapping[tag_info.tag_name]
        
        tag_name_lower = tag_info.tag_name.lower()
        content_lower = tag_info.content.lower() if tag_info.content else ""
        
        # 基于标签名称的精确匹配
        if tag_name_lower in ["核心指导", "core_guidance"]:
            return ContentCategory.CORE_GUIDANCE
        elif tag_name_lower in ["基础风格", "basic_style"]:
            return ContentCategory.BASIC_STYLE
        elif tag_name_lower in ["创作准则", "creation_rules"]:
            return ContentCategory.CREATION_RULES
        elif tag_name_lower in ["userpersona", "用户设定", "{{user}}"]:
            return ContentCategory.PERSONA_DESCRIPTION
        elif tag_name_lower in ["相关资料", "world_info", "worldinfo"]:
            return ContentCategory.WORLD_INFO
        elif tag_name_lower in ["character_profile_of", "character", "角色档案"]:
            return ContentCategory.CHARACTER_DESCRIPTION
        elif tag_name_lower in ["互动历史", "chat_history"]:
            return ContentCategory.CHAT_HISTORY
        elif tag_name_lower in ["补充资料", "supplementary"]:
            return ContentCategory.SUPPLEMENTARY
        elif tag_name_lower in ["user", "助手", "assistant", "用户", "system"]:
            return ContentCategory.CHAT_HISTORY
        
        # 基于内容的智能猜测
        combined_text = f"{tag_name_lower} {content_lower}"
        
        # 指令性内容检测
        instruction_keywords = ["必须", "不得", "应该", "禁止", "要求", "规则", "禁止", "avoid", "must", "should", "cannot"]
        if any(keyword in combined_text for keyword in instruction_keywords):
            if "风格" in combined_text or "style" in combined_text:
                return ContentCategory.BASIC_STYLE
            elif "指导" in combined_text or "guidance" in combined_text:
                return ContentCategory.CORE_GUIDANCE
            elif any(k in combined_text for k in ["规则", "准则", "rule"]):
                return ContentCategory.CREATION_RULES
        
        # 世界书内容检测
        worldbook_keywords = ["地点", "类别", "概念", "location", "category", "concept", "world_info", "相关资料"]
        if any(keyword in combined_text for keyword in worldbook_keywords):
            return ContentCategory.WORLD_INFO
        
        # 角色描述检测
        character_keywords = ["角色", "性格", "外貌", "背景", "character", "personality", "外表", "特征"]
        if any(keyword in combined_text for keyword in character_keywords):
            return ContentCategory.CHARACTER_DESCRIPTION
        
        # 对话检测
        dialogue_keywords = ["说", "问", "回答", "喊道", "笑道", "对话", "dialog", "chat", "said", "replied"]
        if any(keyword in combined_text for keyword in dialogue_keywords):
            return ContentCategory.CHAT_HISTORY
        
        # 叙事内容检测
        narrative_keywords = ["讲述", "描述", "写道", "画面", "场景", "开始", "结束", "narrative", "story"]
        if any(keyword in combined_text for keyword in narrative_keywords):
            return ContentCategory.NARRATIVE
        
        return ContentCategory.UNKNOWN
    
    def _calculate_optimized_tag_confidence(self, tag_info: TagInfo, base_confidence: float) -> float:
        """计算标签置信度（优化版）"""
        confidence = base_confidence
        
        # 标签名质量
        if 2 <= len(tag_info.tag_name) <= 30:
            confidence += 0.1
        
        # 标签类型明确性
        if tag_info.tag_type not in ["unknown", None]:
            confidence += 0.1
        
        # 语义类别明确性
        if tag_info.semantic_category != ContentCategory.UNKNOWN:
            confidence += 0.15
        
        # 内容质量评分
        if tag_info.content:
            content_len = len(tag_info.content)
            # 适中长度的内容置信度更高
            if 20 <= content_len <= 800:
                confidence += 0.1
            elif content_len < 10:
                confidence -= 0.05  # 内容太短可能不完整
            elif content_len > 1500:
                confidence -= 0.03  # 内容过长可能包含多个话题
        
        # 属性质量
        if tag_info.attributes and len(tag_info.attributes) > 0:
            confidence += 0.05
        
        # 模式优先级加成
        pattern_meta = self.pattern_metadata.get(tag_info.metadata.get("pattern_idx", -1), {})
        if pattern_meta.get("high_priority", False):
            confidence += 0.05
        
        # 确保置信度在合理范围内
        confidence = min(max(confidence, 0.1), 1.0)
        
        return round(confidence, 3)
    
    def _optimized_analyze_tag_relationships(self, tags: List[TagInfo]):
        """分析标签关系（优化版）"""
        stack = []
        
        for tag in tags:
            if tag.tag_type == "opening":
                # 设置父标签
                if stack:
                    tag.parent_tag = stack[-1].tag_name
                    tag.metadata["nesting_depth"] = len(stack)
                stack.append(tag)
            elif tag.tag_type == "closing":
                # 寻找对应的开标签
                for i in range(len(stack) - 1, -1, -1):
                    if stack[i].tag_name == tag.tag_name:
                        # 设置父标签
                        if i > 0:
                            tag.parent_tag = stack[i-1].tag_name
                        # 移除栈中元素
                        stack = stack[:i]
                        break
        
        # 处理语义继承关系
        for i, tag in enumerate(tags):
            if tag.parent_tag:
                # 寻找父标签的语义类别
                parent_tags = [t for t in tags[:i] if t.tag_name == tag.parent_tag]
                if parent_tags and parent_tags[-1].semantic_category:
                    parent_cat = parent_tags[-1].semantic_category
                    
                    # 特定语义类别的子标签置信度加成
                    if parent_cat in [ContentCategory.CORE_GUIDANCE, ContentCategory.BASIC_STYLE]:
                        tag.confidence = min(1.0, tag.confidence + 0.08)
                    elif parent_cat == ContentCategory.WORLD_INFO:
                        tag.confidence = min(1.0, tag.confidence + 0.05)
                    
                    # 如果子标签语义类别未知，尝试继承
                    if tag.semantic_category == ContentCategory.UNKNOWN:
                        tag.semantic_category = parent_cat
                        tag.confidence = max(tag.confidence, 0.7)
                        
    def _filter_low_quality_tags(self, tags: List[TagInfo]) -> List[TagInfo]:
        """过滤低质量标签"""
        filtered_tags = []
        
        for tag in tags:
            # 排除置信度过低的标签
            if tag.confidence < 0.4:
                continue
            
            # 排除无效标签名
            if len(tag.tag_name) < 1 or len(tag.tag_name) > 50:
                continue
            
            # 排除内容过长且置信度不高的标签
            if tag.content and len(tag.content) > 2000 and tag.confidence < 0.6:
                continue
            
            filtered_tags.append(tag)
        
        logger.debug(f"过滤后剩余 {len(filtered_tags)} 个标签（过滤掉 {len(tags) - len(filtered_tags)} 个）")
        return filtered_tags
