import logging
import re
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json
import heapq
from collections import defaultdict
from config.settings import settings

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)



logger = logging.getLogger(__name__)

@dataclass
class ParsedTag:
    """解析后的标签结构"""
    tag_name: str
    tag_type: str  # opening, closing, self-closing
    content: str
    semantic_category: str  # instruction, narrative, dialog, world_info, character_profile
    confidence: float
    position: int
    attributes: Optional[Dict[str, str]] = None
    parent_tag: Optional[str] = None

@dataclass
class DocumentSegment:
    """文档片段"""
    segment_id: str
    segment_type: str
    content: str
    tags: List[ParsedTag]
    metadata: Dict[str, Any]
    hash_value: str

class ParserService:
    """SillyTavern文本解析服务"""
    
    def __init__(self):
        """初始化解析服务"""
        self.compiled_patterns = self._compile_patterns()
        self.session_structure_cache = {}  # 会话结构缓存
        
    def _compile_patterns(self) -> List[re.Pattern]:
        """编译正则表达式模式"""
        patterns = []
        
        # 添加配置中的模式
        for pattern_str in settings.PARSER_REGEX_PATTERNS:
            try:
                pattern = re.compile(pattern_str, re.DOTALL)
                patterns.append(pattern)
            except re.error as e:
                logger.warning(f"无效的正则表达式模式: {pattern_str}, 错误: {str(e)}")
        
        # 添加启发式规则中的模式
        for category, pattern_list in settings.PARSER_HEURISTIC_RULES.items():
            for pattern_str in pattern_list:
                try:
                    pattern = re.compile(pattern_str, re.DOTALL)
                    patterns.append(pattern)
                except re.error as e:
                    logger.warning(f"无效的启发式模式: {pattern_str}, 错误: {str(e)}")
        
        # 添加常用SillyTavern标签模式
        common_patterns = [
            r'<\s*([a-zA-Z_][a-zA-Z0-9_-]*)\s*([^>]*)>',  # 开标签带属性
            r'<\s*/\s*([a-zA-Z_][a-zA-Z0-9_-]*)\s*>',  # 闭标签
            r'<\s*([a-zA-Z_][a-zA-Z0-9_-]*)\s*/?>',  # 自闭合标签
            r'\[\[([^:\]]+):([^\]]+)\]\]',  # 双链格式
            r'\{\{([^}]+)\}\}',  # 变量引用
        ]
        
        for pattern_str in common_patterns:
            try:
                pattern = re.compile(pattern_str, re.DOTALL)
                patterns.append(pattern)
            except re.error as e:
                logger.warning(f"无效的常用模式: {pattern_str}, 错误: {str(e)}")
        
        logger.info(f"已编译 {len(patterns)} 个解析模式")
        return patterns
    
    def parse_text(self, text: str, session_id: str) -> Tuple[List[DocumentSegment], List[ParsedTag]]:
        """
        解析SillyTavern文本
        返回文档片段和所有标签
        """
        try:
            # 生成文本哈希用于缓存
            text_hash = hashlib.md5(text.encode()).hexdigest()[:16]
            
            # 检查是否使用缓存的结构分析
            if session_id in self.session_structure_cache:
                cached_structure = self.session_structure_cache[session_id]
                logger.info(f"使用缓存的会话结构: {session_id}")
            else:
                cached_structure = None
            
            # 提取所有标签
            all_tags = self._extract_tags(text, session_id)
            
            # 分析文档结构
            document_structure = self._analyze_document_structure(text, all_tags, cached_structure)
            
            # 分割文档片段
            segments = self._segment_document(text, all_tags, document_structure, session_id, text_hash)
            
            # 更新缓存
            if cached_structure is None:
                self.session_structure_cache[session_id] = {
                    "document_structure": document_structure,
                    "tags_count": len(all_tags),
                    "timestamp": datetime.now().isoformat()
                }
            
            logger.info(f"文本解析成功: {len(segments)}个片段, {len(all_tags)}个标签")
            return segments, all_tags
            
        except Exception as e:
            logger.error(f"解析文本失败: {str(e)}")
            return [], []
    
    def _extract_tags(self, text: str, session_id: str) -> List[ParsedTag]:
        """从文本中提取标签"""
        tags = []
        
        for pattern in self.compiled_patterns:
            matches = list(pattern.finditer(text))
            
            for match in matches:
                try:
                    tag = self._create_tag_from_match(match, text, session_id)
                    if tag:
                        tags.append(tag)
                except Exception as e:
                    logger.debug(f"创建标签失败: {str(e)}, 匹配: {match.group()}")
        
        # 按位置排序
        tags.sort(key=lambda x: x.position)
        
        # 识别标签类型和语义类别
        self._classify_tags(tags)
        
        return tags
    
    def _create_tag_from_match(self, match: re.Match, text: str, session_id: str) -> Optional[ParsedTag]:
        """从正则匹配创建标签对象"""
        try:
            tag_name = ""
            tag_type = "unknown"
            content = match.group()
            position = match.start()
            
            # 分析匹配内容
            full_match = match.group()
            
            # 判断标签类型
            if full_match.startswith('</'):  # 闭标签
                tag_type = "closing"
                # 提取标签名
                inner = full_match[2:-1].strip()
                tag_name = inner
                
            elif full_match.endswith('/>'):  # 自闭合标签
                tag_type = "self-closing"
                # 提取标签名和属性
                inner = full_match[1:-2].strip()
                parts = inner.split()
                if parts:
                    tag_name = parts[0]
                    
            elif full_match.startswith('<'):  # 开标签
                tag_type = "opening"
                # 提取标签名和属性
                inner = full_match[1:-1].strip()
                parts = inner.split()
                if parts:
                    tag_name = parts[0]
                    
            elif full_match.startswith('[['):  # 双链
                tag_type = "wikilink"
                inner = full_match[2:-2].strip()
                if ':' in inner:
                    parts = inner.split(':', 1)
                    tag_name = parts[0]  # 双链类型
                    content = parts[1]  # 目标内容
                    
            elif full_match.startswith('{{'):  # 变量
                tag_type = "variable"
                inner = full_match[2:-2].strip()
                tag_name = inner
                
            else:
                # 尝试从其他模式识别
                if ':' in full_match:  # 角色对话
                    tag_type = "dialogue"
                    parts = full_match.split(':', 1)
                    tag_name = parts[0].strip()
                    content = parts[1].strip() if len(parts) > 1 else ""
            
            # 检查标签名的有效性
            if not tag_name or len(tag_name) > 50:
                return None
            
            # 提取属性
            attributes = self._extract_attributes(full_match) if tag_type in ["opening", "self-closing"] else None
            
            # 确定语义类别（初始值，后面会细化）
            semantic_category = self._guess_semantic_category(tag_name, content, tag_type)
            
            return ParsedTag(
                tag_name=tag_name,
                tag_type=tag_type,
                content=content,
                semantic_category=semantic_category,
                confidence=0.7,  # 初始置信度
                position=position,
                attributes=attributes
            )
            
        except Exception as e:
            logger.debug(f"创建标签失败: {str(e)}")
            return None
    
    def _extract_attributes(self, tag_content: str) -> Dict[str, str]:
        """提取标签属性"""
        attributes = {}
        
        # 简单的属性提取：name="value" 或 name='value'
        attr_pattern = r'(\w+)\s*=\s*["\']([^"\']*)["\']'
        matches = re.findall(attr_pattern, tag_content)
        
        for name, value in matches:
            attributes[name] = value
        
        # 处理无引号的简单属性
        simple_pattern = r'(\w+)\s*=\s*(\S+)'
        simple_matches = re.findall(simple_pattern, tag_content)
        
        for name, value in simple_matches:
            if name not in attributes:
                attributes[name] = value
        
        return attributes if attributes else None
    
    def _guess_semantic_category(self, tag_name: str, content: str, tag_type: str) -> str:
        """猜测标签的语义类别"""
        tag_name_lower = tag_name.lower()
        
        # 常见指令性标签
        instruction_tags = {
            'information', 'settings', 'scenario', 'instruction', 'prompt',
            '用户角色', '角色设定', '剧情背景', '对话风格'
        }
        
        # 世界信息标签
        world_info_tags = {
            'characterworldinfo', 'worldinfo', 'world_info', 'worldbook',
            '地点', '概念', '类别', 'npc'
        }
        
        # 角色档案标签
        character_tags = {
            'character', 'persona', '用户画像', 'userpersona',
            '角色档案', 'character_profile'
        }
        
        # 对话标签
        dialogue_tags = {
            'user', 'assistant', 'system', '用户', '助手', '助理',
            '对话', 'dialog', '聊天'
        }
        
        if tag_name_lower in instruction_tags:
            return "instruction"
        elif tag_name_lower in world_info_tags:
            return "world_info"
        elif tag_name_lower in character_tags:
            return "character_profile"
        elif tag_type == "dialogue":
            return "dialog"
        else:
            # 根据内容进一步判断
            content_lower = content.lower()
            if any(word in content_lower for word in ['说', '问', '回答', '笑道', '喊道']):
                return "dialog"
            elif any(word in content_lower for word in ['背景', '设定', '描述', '环境']):
                return "world_info"
            elif any(word in content_lower for word in ['你', '我', '他', '她']):
                return "dialog"
            else:
                return "narrative"
    
    def _classify_tags(self, tags: List[ParsedTag]):
        """对标签进行最终分类"""
        # 更新标签的分类和置信度
        for tag in tags:
            # 根据标签名和内容精化分类
            if tag.tag_name in ["User", "Assistant", "用户", "助手"]:
                tag.semantic_category = "dialog"
                tag.confidence = 0.95
            
            # 根据内容长度调整置信度
            if len(tag.content) < 5:
                tag.confidence *= 0.8  # 短内容置信度较低
            elif len(tag.content) > 100:
                tag.confidence *= 0.9  # 长内容可能包含复杂语义
        
        # 识别嵌套关系
        self._identify_nesting(tags)
    
    def _identify_nesting(self, tags: List[ParsedTag]):
        """识别标签的嵌套关系"""
        stack = []
        
        for tag in tags:
            if tag.tag_type == "opening":
                # 设置父标签
                if stack:
                    tag.parent_tag = stack[-1].tag_name
                stack.append(tag)
            elif tag.tag_type == "closing":
                # 寻找对应的开标签
                for i in range(len(stack) - 1, -1, -1):
                    if stack[i].tag_name == tag.tag_name:
                        # 移除栈中元素
                        stack = stack[:i]
                        break
                # 设置闭标签的父标签
                if stack:
                    tag.parent_tag = stack[-1].tag_name if stack else None
    
    def _analyze_document_structure(self, 
                                  text: str, 
                                  tags: List[ParsedTag],
                                  cached_structure: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """分析文档结构"""
        if cached_structure:
            return cached_structure.get("document_structure", {})
        
        structure = {
            "has_instructions": False,
            "has_world_info": False,
            "has_dialogue_history": False,
            "has_character_profiles": False,
            "segments": [],
            "tag_density": len(tags) / max(1, len(text.split()) / 100),  # 每100词的标签数
        }
        
        # 分析标签分布
        tag_categories = defaultdict(int)
        for tag in tags:
            tag_categories[tag.semantic_category] += 1
        
        # 判断文档特征
        if tag_categories["instruction"] > 0:
            structure["has_instructions"] = True
        
        if tag_categories["world_info"] > 0:
            structure["has_world_info"] = True
        
        if tag_categories["dialog"] > 5:  # 对话标签较多
            structure["has_dialogue_history"] = True
        
        if tag_categories["character_profile"] > 0:
            structure["has_character_profiles"] = True
        
        return structure
    
    def _segment_document(self, 
                         text: str, 
                         tags: List[ParsedTag], 
                         structure: Dict[str, Any],
                         session_id: str,
                         text_hash: str) -> List[DocumentSegment]:
        """分割文档为片段"""
        segments = []
        
        # 如果没有标签，创建单个片段
        if not tags:
            segment = DocumentSegment(
                segment_id=f"{session_id}_seg_0",
                segment_type="text",
                content=text,
                tags=[],
                metadata={
                    "position": 0,
                    "length": len(text),
                    "word_count": len(text.split()),
                    "structure_type": "plain_text"
                },
                hash_value=text_hash
            )
            segments.append(segment)
            return segments
        
        # 基于标签分割文档
        last_pos = 0
        segment_index = 0
        
        for i, tag in enumerate(tags):
            # 创建标签前的文本片段
            if tag.position > last_pos:
                pre_text = text[last_pos:tag.position].strip()
                if pre_text:
                    segment = self._create_text_segment(
                        content=pre_text,
                        index=segment_index,
                        session_id=session_id,
                        text_hash=text_hash,
                        preceding_tag=tags[i-1] if i > 0 else None,
                        following_tag=tag
                    )
                    segments.append(segment)
                    segment_index += 1
            
            # 创建标签片段
            tag_segment = self._create_tag_segment(
                tag=tag,
                index=segment_index,
                session_id=session_id,
                text_hash=text_hash
            )
            segments.append(tag_segment)
            segment_index += 1
            
            last_pos = tag.position + len(tag.content)
        
        # 添加最后的文本片段
        if last_pos < len(text):
            post_text = text[last_pos:].strip()
            if post_text:
                segment = self._create_text_segment(
                    content=post_text,
                    index=segment_index,
                    session_id=session_id,
                    text_hash=text_hash,
                    preceding_tag=tags[-1] if tags else None,
                    following_tag=None
                )
                segments.append(segment)
        
        return segments
    
    def _create_text_segment(self,
                           content: str,
                           index: int,
                           session_id: str,
                           text_hash: str,
                           preceding_tag: Optional[ParsedTag] = None,
                           following_tag: Optional[ParsedTag] = None) -> DocumentSegment:
        """创建文本片段"""
        segment_type = "text"
        
        # 根据上下文判断片段类型
        if preceding_tag:
            if preceding_tag.semantic_category == "dialog":
                segment_type = "dialog_content"
            elif preceding_tag.semantic_category == "instruction":
                segment_type = "instruction_content"
        
        metadata = {
            "position": index,
            "length": len(content),
            "word_count": len(content.split()),
            "segment_type": segment_type,
            "preceding_tag": preceding_tag.tag_name if preceding_tag else None,
            "following_tag": following_tag.tag_name if following_tag else None,
            "is_dialogue": segment_type == "dialog_content",
            "has_names": any(name in content for name in ['说', '问', '回答', ':', '：'])
        }
        
        return DocumentSegment(
            segment_id=f"{session_id}_seg_{index}",
            segment_type=segment_type,
            content=content,
            tags=[],
            metadata=metadata,
            hash_value=hashlib.md5(content.encode()).hexdigest()[:16]
        )
    
    def _create_tag_segment(self,
                          tag: ParsedTag,
                          index: int,
                          session_id: str,
                          text_hash: str) -> DocumentSegment:
        """创建标签片段"""
        metadata = {
            "position": index,
            "tag_position": tag.position,
            "tag_length": len(tag.content),
            "semantic_category": tag.semantic_category,
            "confidence": tag.confidence,
            "attributes": tag.attributes,
            "parent_tag": tag.parent_tag
        }
        
        return DocumentSegment(
            segment_id=f"{session_id}_tag_{index}",
            segment_type="tag",
            content=tag.content,
            tags=[tag],
            metadata=metadata,
            hash_value=hashlib.md5(tag.content.encode()).hexdigest()[:16]
        )
