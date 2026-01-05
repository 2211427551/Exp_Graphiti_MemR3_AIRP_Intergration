# ============================================
# SillyTavern格式解析服务
# ============================================
import re
import logging
from dataclasses import dataclass
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


@dataclass()
class NarrativeBlock:
    """叙事性内容块"""
    content: str                    # 原始内容
    block_type: str                 # 类型：world_info, dialog, general
    metadata: Dict[str, Any]          # 元数据
    confidence: float = 1.0          # 提取置信度


@dataclass()
class InstructionBlock:
    """指令性内容块"""
    content: str                    # 原始内容
    instruction_type: str            # 类型：core, style, constraint
    priority: int = 0              # 优先级


@dataclass()
class DialogTurn:
    """对话轮次"""
    role: str                      # User或Assistant
    content: str                   # 对话内容


@dataclass()
class ParsedContent:
    """解析后的完整内容"""
    instructions: List[InstructionBlock]      # 指令性内容列表
    narratives: List[NarrativeBlock]         # 叙事性内容列表
    chat_history: List[DialogTurn]           # 对话历史
    raw_metadata: Dict[str, Any]              # 原始元数据


class SillyTavernParser:
    """SillyTavern格式解析器"""
    
    def __init__(self):
        """
        初始化解析器
        
        配置:
            - 编译正则表达式模式
            - 加载标签映射表
        """
        # 步骤1: 编译正则表达式
        self.tag_pattern = re.compile(r'<([^>/]+)>([\s\S]*?)</\1>')
        self.pipe_pattern = re.compile(r'<\|([^|]+)\|>([^<]*)')
        
        # 步骤2: 初始化标签映射表
        self.tag_mappings = {
            '核心指导': 'core_instruction',
            '基础风格': 'style_instruction',
            '相关资料': 'world_info',
            '互动历史': 'dialog_history',
            '补充资料': 'supplementary_info'
        }
        
        logger.info("SillyTavern解析器初始化完成")
    
    def parse(self, text: str) -> ParsedContent:
        """
        解析SillyTavern格式的文本
        
        参数:
            text: str
                要解析的完整文本内容
        
        返回:
            ParsedContent: 解析后的结构化内容
        
        流程:
            1. 多级标签检测
               a. 第一级：精确标签匹配（<核心指导>等）
               b. 第二级：模糊标签识别（启发式）
               c. 第三级：模式匹配（User/Assistant交替）
            
            2. 内容提取
               a. 提取标签内容
               b. 识别内容类型
               c. 构建内容块对象
            
            3. 结构化表示
               a. 转换为统一的数据结构
               b. 保留位置信息
               c. 记录提取置信度
        
        异常:
            ValueError: 文本格式无法解析
        """
        logger.debug(f"开始解析文本，长度: {len(text)}")
        
        # 步骤1: 初始化结果对象
        result = ParsedContent(
            instructions=[],
            narratives=[],
            chat_history=[],
            raw_metadata={'original_length': len(text)}
        )
        
        # 步骤2: 第一级：精确标签匹配
        tagged_sections = self._extract_tagged_sections(text)
        logger.debug(f"提取到 {len(tagged_sections)} 个标记部分")
        
        # 步骤3: 处理每个标记部分
        for tag_name, tag_content in tagged_sections:
            mapped_type = self.tag_mappings.get(tag_name)
            
            if mapped_type in ['core_instruction', 'style_instruction']:
                # 指令性内容
                result.instructions.append(InstructionBlock(
                    content=tag_content,
                    instruction_type=mapped_type,
                    priority=self._get_priority(tag_name)
                ))
                logger.debug(f"添加指令块: {tag_name}")
                
            elif mapped_type == 'world_info':
                # 世界书信息
                world_entries = self._parse_world_info(tag_content)
                result.narratives.extend(world_entries)
                logger.debug(f"添加 {len(world_entries)} 个世界书条目")
                
            elif mapped_type == 'dialog_history':
                # 对话历史
                dialog_turns = self._parse_dialog_history(tag_content)
                result.chat_history.extend(dialog_turns)
                logger.debug(f"添加 {len(dialog_turns)} 个对话轮次")
                
            elif mapped_type == 'supplementary_info':
                # 补充资料
                result.narratives.append(NarrativeBlock(
                    content=tag_content,
                    block_type='supplementary',
                    metadata={'source': 'tagged'},
                    confidence=1.0
                ))
                logger.debug("添加补充资料")
        
        # 步骤4: 第二级：模糊标签识别
        untagged_content = self._remove_tagged_sections(text, tagged_sections)
        if untagged_content.strip():
            # 检测User/Assistant模式
            if self._has_dialog_pattern(untagged_content):
                dialog_turns = self._parse_dialog_history(untagged_content)
                result.chat_history.extend(dialog_turns)
                logger.debug(f"从未标记内容提取 {len(dialog_turns)} 个对话轮次")
            else:
                # 默认为一般叙事性内容
                result.narratives.append(NarrativeBlock(
                    content=untagged_content,
                    block_type='general',
                    metadata={'source': 'untagged'},
                    confidence=0.8
                ))
                logger.debug("添加一般叙事性内容")
        
        # 步骤5: 返回解析结果
        logger.info(f"解析完成: {len(result.instructions)} 指令, {len(result.narratives)} 叙事, {len(result.chat_history)} 对话")
        return result
    
    def _extract_tagged_sections(self, text: str) -> List[tuple]:
        """
        提取所有标记的部分
        
        参数:
            text: str
                原始文本
        
        返回:
            List[tuple]: [(tag_name, content), ...]
        """
        # 使用预编译的正则表达式
        matches = self.tag_pattern.finditer(text)
        return [(m.group(1), m.group(2)) for m in matches]
    
    def _parse_world_info(self, content: str) -> List[NarrativeBlock]:
        """
        解析世界书信息
        
        参数:
            content: str
                世界书标签内的内容
        
        返回:
            List[NarrativeBlock]: 世界书条目列表
        
        流程:
            1. 分条目分割（基于空行或分隔符）
            2. 每个条目独立解析
            3. 提取属性（地点、角色等）
        """
        entries = []
        lines = content.strip().split('\n')
        current_entry = []
        
        for line in lines:
            if line.strip() == '':
                if current_entry:
                    entry_text = '\n'.join(current_entry).strip()
                    entries.append(NarrativeBlock(
                        content=entry_text,
                        block_type='world_info',
                        metadata=self._extract_world_metadata(entry_text),
                        confidence=1.0
                    ))
                    current_entry = []
            else:
                current_entry.append(line)
        
        # 处理最后一个条目
        if current_entry:
            entry_text = '\n'.join(current_entry).strip()
            entries.append(NarrativeBlock(
                content=entry_text,
                block_type='world_info',
                metadata=self._extract_world_metadata(entry_text),
                confidence=1.0
            ))
        
        return entries
    
    def _extract_world_metadata(self, text: str) -> Dict[str, Any]:
        """
        提取世界书元数据
        
        参数:
            text: str
                世界书条目文本
        
        返回:
            Dict[str, Any]: 元数据字典
        """
        metadata = {}
        
        # 提取地点信息
        location_match = re.search(r'地点\s*\(\s*([^)]+)\s*\)', text)
        if location_match:
            metadata['location'] = location_match.group(1).strip()
        
        # 提取角色信息
        character_match = re.search(r'角色\s*\(\s*([^)]+)\s*\)', text)
        if character_match:
            metadata['character'] = character_match.group(1).strip()
        
        return metadata
    
    def _parse_dialog_history(self, content: str) -> List[DialogTurn]:
        """
        解析对话历史
        
        参数:
            content: str
                对话文本
        
        返回:
            List[DialogTurn]: 对话轮次列表
        """
        turns = []
        lines = content.strip().split('\n')
        
        for line in lines:
            if line.strip().startswith('User:'):
                turns.append(DialogTurn(
                    role='User',
                    content=line.strip()[5:].strip()
                ))
            elif line.strip().startswith('Assistant:'):
                turns.append(DialogTurn(
                    role='Assistant',
                    content=line.strip()[10:].strip()
                ))
        
        return turns
    
    def _has_dialog_pattern(self, text: str) -> bool:
        """
        检测是否包含对话模式
        
        参数:
            text: str
                待检测文本
        
        返回:
            bool: 是否包含对话模式
        """
        return bool(re.search(r'User:|Assistant:', text))
    
    def _remove_tagged_sections(self, text: str, tagged_sections: List[tuple]) -> str:
        """
        移除已标记的部分
        
        参数:
            text: str
                原始文本
            tagged_sections: List[tuple]
                已标记的部分
        
        返回:
            str: 移除标记后的文本
        """
        result = text
        for tag_name, _ in tagged_sections:
            pattern = re.compile(rf'<{tag_name}>[\s\S]*?</{tag_name}>', re.DOTALL)
            result = pattern.sub('', result)
        return result.strip()
    
    def _get_priority(self, tag_name: str) -> int:
        """
        获取标签优先级
        
        参数:
            tag_name: str
                标签名称
        
        返回:
            int: 优先级（数字越小优先级越高）
        """
        priorities = {
            '核心指导': 0,
            '基础风格': 1,
            '补充资料': 2
        }
        return priorities.get(tag_name, 99)
