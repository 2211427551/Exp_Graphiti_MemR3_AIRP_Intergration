import logging
import json
import httpx
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import hashlib
import os
from config.settings import settings

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)



logger = logging.getLogger(__name__)

class LLMService:
    """LLM服务，封装各种LLM调用"""
    
    def __init__(self):
        """初始化LLM服务"""
        self.deepseek_api_key = settings.DEEPSEEK_API_KEY
        self.deepseek_base_url = settings.DEEPSEEK_BASE_URL
        self.cache_enabled = True
        self.request_cache = {}
    
    async def call_deepseek(self, 
                          messages: List[Dict[str, str]],
                          model: str = "deepseek-chat",
                          temperature: float = 0.7,
                          max_tokens: int = 2000,
                          stream: bool = False) -> Optional[Dict[str, Any]]:
        """调用DeepSeek API"""
        if not self.deepseek_api_key:
            logger.error("DeepSeek API密钥未配置")
            return None
        
        try:
            request_data = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": stream
            }
            
            # 生成缓存键
            cache_key = self._generate_cache_key(request_data)
            
            # 检查缓存
            if self.cache_enabled and cache_key in self.request_cache:
                cached_data = self.request_cache[cache_key]
                if datetime.now().timestamp() - cached_data["timestamp"] < settings.GRAPHITI_CACHE_TTL:
                    logger.info("使用缓存的LLM响应")
                    return cached_data["response"]
            
            # 调用API
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {self.deepseek_api_key}",
                    "Content-Type": "application/json"
                }
                
                response = await client.post(
                    f"{self.deepseek_base_url}/chat/completions",
                    json=request_data,
                    headers=headers,
                    timeout=settings.GRAPHITI_TIMEOUT
                )
                
                if response.status_code != 200:
                    logger.error(f"DeepSeek API错误: {response.status_code} - {response.text}")
                    return None
                
                result = response.json()
                
                # 缓存结果
                if self.cache_enabled:
                    self.request_cache[cache_key] = {
                        "timestamp": datetime.now().timestamp(),
                        "response": result
                    }
                
                return result
                
        except httpx.TimeoutException:
            logger.error("DeepSeek API请求超时")
            return None
        except httpx.RequestError as e:
            logger.error(f"DeepSeek API请求错误: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"调用DeepSeek API失败: {str(e)}")
            return None
    
    async def analyze_text_structure(self, text: str, session_id: str) -> Optional[Dict[str, Any]]:
        """
        分析文本结构（首次处理逻辑）
        使用LLM识别SillyTavern输入格式中的标签和结构
        """
        try:
            prompt = f"""
            你是一个文本格式分析专家。请分析以下来自SillyTavern AI角色扮演平台的文本结构。
            
            ## 上下文信息
            - 会话ID: {session_id}
            - 文本类型: SillyTavern角色扮演提示词
            - 常见标签类型: <Information>, <Userpersona>, <CharacterWorldInfo>, <Scenario>, 
              <settings>, <用户角色>, <info>, <world_info_before>, <character>, <world_info_after>
            
            ## 待分析文本
            {text[:3000]}  # 限制文本长度
            
            ## 输出格式要求
            请按以下JSON格式输出分析结果：
            {{
                "detected_tags": [
                    {{
                        "tag_name": "标签名称",
                        "tag_type": "opening/closing/self-closing",
                        "content": "标签内的内容或指示符",
                        "semantic_category": "instruction/narrative/dialog/world_info/character_profile",
                        "confidence": 0.95
                    }}
                ],
                "document_structure": {{
                    "has_instructions": true/false,
                    "has_world_info": true/false,
                    "has_dialogue_history": true/false,
                    "has_character_profiles": true/false
                }},
                "parsing_rules": [
                    {{
                        "regex_pattern": "正则表达式模式",
                        "description": "模式描述",
                        "extraction_method": "如何提取内容"
                    }}
                ]
            }}
            
            ## 注意事项
            1. 标签名称可能包含特殊字符或变量（如{{{{user}}}}）
            2. 注意嵌套标签和属性
            3. 区分指令性内容和叙事性内容
            """
            
            messages = [
                {"role": "system", "content": "你是专业的文本格式分析专家，擅长解析结构化文本。"},
                {"role": "user", "content": prompt}
            ]
            
            result = await self.call_deepseek(
                messages=messages,
                model="deepseek-chat",
                temperature=0.3,  # 降低温度以提高一致性
                max_tokens=1500
            )
            
            if result and "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                try:
                    analysis_result = json.loads(content)
                    
                    # 验证结果格式
                    if self._validate_analysis_result(analysis_result):
                        logger.info(f"文本结构分析成功: {session_id}")
                        return analysis_result
                    else:
                        logger.warning(f"文本结构分析结果格式无效: {session_id}")
                        return None
                        
                except json.JSONDecodeError as e:
                    logger.error(f"解析LLM响应JSON失败: {str(e)}")
                    logger.debug(f"原始响应内容: {content}")
                    return None
                    
            else:
                logger.error("LLM响应格式错误")
                return None
                
        except Exception as e:
            logger.error(f"文本结构分析失败: {str(e)}")
            return None
    
    async def semantic_similarity_check(self, text_a: str, text_b: str) -> Optional[Dict[str, Any]]:
        """
        语义相似度检查（用于去重和实体合并）
        """
        try:
            prompt = f"""
            请判断以下两段文本是否描述相同或高度相似的内容。
            
            ## 文本A
            {text_a[:1000]}
            
            ## 文本B  
            {text_b[:1000]}
            
            ## 分析要求
            1. 判断语义相似度（不仅仅是表面文本相似）
            2. 考虑上下文和含义
            3. 识别核心实体和关系
            4. 评估信息重叠度
            
            ## 输出格式
            {{
                "is_similar": true/false,
                "similarity_score": 0.0-1.0,
                "overlap_type": "exact/paraphrase/partial/none",
                "reasoning": "判断理由（中文）",
                "key_entities_a": ["实体1", "实体2", ...],
                "key_entities_b": ["实体1", "实体2", ...],
                "overlapping_entities": ["实体1", "实体2", ...]
            }}
            """
            
            messages = [
                {"role": "system", "content": "你是专业的文本相似度分析专家，擅长判断文本语义相似性。"},
                {"role": "user", "content": prompt}
            ]
            
            result = await self.call_deepseek(
                messages=messages,
                model="deepseek-chat",
                temperature=0.2,  # 非常低的温度以确保一致性
                max_tokens=1000
            )
            
            if result and "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                try:
                    similarity_result = json.loads(content)
                    
                    # 验证结果格式
                    if self._validate_similarity_result(similarity_result):
                        logger.info(f"语义相似度检查完成")
                        return similarity_result
                    else:
                        logger.warning(f"语义相似度结果格式无效")
                        return None
                        
                except json.JSONDecodeError as e:
                    logger.error(f"解析相似度检查JSON失败: {str(e)}")
                    logger.debug(f"原始响应内容: {content}")
                    return None
                    
            else:
                logger.error("语义相似度检查LLM响应格式错误")
                return None
                
        except Exception as e:
            logger.error(f"语义相似度检查失败: {str(e)}")
            return None
    
    async def extract_entities_relations(self, text: str, 
                                       existing_entities: Optional[List[Dict[str, Any]]] = None) -> Optional[Dict[str, Any]]:
        """
        从文本中提取实体和关系（用于Graphiti数据生成）
        """
        try:
            existing_entities_info = ""
            if existing_entities:
                entity_names = [entity.get("name", "") for entity in existing_entities]
                existing_entities_info = f"已知实体: {', '.join(entity_names)}"
            
            prompt = f"""
            请从以下文本中提取实体、属性和关系，用于知识图谱构建。
            
            ## 待分析文本
            {text[:2000]}
            
            {existing_entities_info}
            
            ## 实体类型定义
            1. Character（角色）：人物，具有姓名、外貌、性格等属性
            2. Location（地点）：地点，具有位置、描述、功能等属性
            3. Event（事件）：事件，具有时间、参与者、结果等属性
            4. PsychologicalTrait（心理特质）：性格特点、情绪状态等
            5. Object（物品）：具体物品或抽象概念
            
            ## 关系类型定义
            1. HAS_RELATION_WITH：社交关系
            2. HAS_ASSOCIATION_WITH：关联关系
            3. HAS_TEMPORAL_ORDER：时序关系
            4. HAS_CAUSAL_LINK：因果关系
            5. HAS_SPATIAL_RELATION：空间关系
            
            ## 输出格式要求
            {{
                "entities": [
                    {{
                        "entity_id": "唯一标识（可选，如无则留空）",
                        "entity_type": "实体类型",
                        "name": "实体名称",
                        "properties": {{
                            "描述": "实体描述",
                            "其他属性": "属性值"
                        }},
                        "confidence": 0.95
                    }}
                ],
                "relationships": [
                    {{
                        "source_entity_name": "源实体名称",
                        "target_entity_name": "目标实体名称",
                        "relation_type": "关系类型",
                        "properties": {{
                            "强度": 0.8,
                            "上下文": "关系发生的上下文",
                            "置信度": 0.9
                        }},
                        "confidence": 0.9
                    }}
                ],
                "metadata": {{
                    "extraction_time": "提取时间",
                    "text_hash": "文本哈希",
                    "entities_count": "提取的实体数",
                    "relationships_count": "提取的关系数"
                }}
            }}
            
            ## 注意事项
            1. 优先使用文本中明确的实体名称
            2. 对于不确定的部分，降低置信度
            3. 避免重复提取相同实体
            4. 注意上下文相关的属性
            """
            
            messages = [
                {"role": "system", "content": "你是专业的实体关系提取专家，擅长构建知识图谱。"},
                {"role": "user", "content": prompt}
            ]
            
            result = await self.call_deepseek(
                messages=messages,
                model="deepseek-chat",
                temperature=0.3,
                max_tokens=2000
            )
            
            if result and "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                try:
                    extraction_result = json.loads(content)
                    
                    # 添加元数据
                    extraction_result["metadata"]["extraction_time"] = datetime.now().isoformat()
                    extraction_result["metadata"]["text_hash"] = hashlib.md5(text.encode()).hexdigest()[:16]
                    extraction_result["metadata"]["entities_count"] = len(extraction_result.get("entities", []))
                    extraction_result["metadata"]["relationships_count"] = len(extraction_result.get("relationships", []))
                    
                    logger.info(f"实体关系提取成功: {extraction_result['metadata']['entities_count']}个实体")
                    return extraction_result
                        
                except json.JSONDecodeError as e:
                    logger.error(f"解析实体关系提取JSON失败: {str(e)}")
                    logger.debug(f"原始响应内容: {content}")
                    return None
                    
            else:
                logger.error("实体关系提取LLM响应格式错误")
                return None
                
        except Exception as e:
            logger.error(f"实体关系提取失败: {str(e)}")
            return None
    
    async def analyze_psychological_state(self, character_data: Dict[str, Any], 
                                        dialogue_history: Optional[List[Dict[str, str]]] = None) -> Optional[Dict[str, Any]]:
        """
        分析角色心理状态
        包括性格特质、情绪状态、心理需求、决策倾向等
        """
        try:
            character_info = json.dumps(character_data, ensure_ascii=False, indent=2)
            dialogue_text = ""
            
            if dialogue_history:
                dialogue_text = "\n".join([
                    f"{entry.get('role', 'unknown')}: {entry.get('content', '')[:200]}"
                    for entry in dialogue_history[-5:]  # 取最近5条对话
                ])
            
            prompt = f"""
            请分析以下角色的心理状态和性格特质。
            
            ## 角色信息
            {character_info}
            
            ## 对话历史（最近部分）
            {dialogue_text}
            
            ## 心理分析维度
            1. 性格特质（Big Five模型）：开放性、尽责性、外向性、宜人性、神经质
            2. 当前情绪状态：高兴、悲伤、愤怒、恐惧、惊讶、厌恶等
            3. 心理需求：安全感、归属感、成就感、自主性等
            4. 认知模式：思维方式、决策倾向、问题解决风格
            5. 社交倾向：外向/内向、支配/服从、友好/敌对
            
            ## 输出格式
            {{
                "character_name": "角色名称",
                "psychological_profile": {{
                    "big_five_traits": {{
                        "openness": 0.0-1.0,
                        "conscientiousness": 0.0-1.0,
                        "extraversion": 0.0-1.0,
                        "agreeableness": 0.0-1.0,
                        "neuroticism": 0.0-1.0
                    }},
                    "current_emotions": [
                        {{
                            "emotion": "情感名称",
                            "intensity": 0.0-1.0,
                            "trigger": "触发原因"
                        }}
                    ],
                    "psychological_needs": [
                        {{
                            "need_type": "需求类型",
                            "priority": 0.0-1.0,
                            "satisfaction": 0.0-1.0
                        }}
                    ],
                    "cognitive_style": {{
                        "thinking_style": "思维方式",
                        "decision_tendency": "决策倾向",
                        "problem_solving": "问题解决风格"
                    }},
                    "social_tendency": {{
                        "orientation": "外向/内向",
                        "dominance": "支配/服从",
                        "friendliness": "友好/敌对"
                    }}
                }},
                "behavior_prediction": {{
                    "likely_reactions": [
                        "可能的反应1",
                        "可能的反应2"
                    ],
                    "relationship_preferences": [
                        "关系偏好1",
                        "关系偏好2"
                    ]
                }},
                "timestamp": "分析时间"
            }}
            
            ## 注意事项
            1. 基于角色信息和对话历史做出合理推断
            2. 心理特质应保持一致性和连续性
            3. 考虑角色的发展变化
            """
            
            messages = [
                {"role": "system", "content": "你是专业的心理学家，擅长分析角色心理状态和性格特质。"},
                {"role": "user", "content": prompt}
            ]
            
            result = await self.call_deepseek(
                messages=messages,
                model="deepseek-chat",
                temperature=0.4,
                max_tokens=1500
            )
            
            if result and "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                try:
                    analysis_result = json.loads(content)
                    
                    # 添加时间戳
                    analysis_result["timestamp"] = datetime.now().isoformat()
                    
                    logger.info(f"心理状态分析成功: {character_data.get('name', 'unknown')}")
                    return analysis_result
                    
                except json.JSONDecodeError as e:
                    logger.error(f"解析心理分析JSON失败: {str(e)}")
                    logger.debug(f"原始响应内容: {content}")
                    return None
                    
            else:
                logger.error("心理状态分析LLM响应格式错误")
                return None
                
        except Exception as e:
            logger.error(f"心理状态分析失败: {str(e)}")
            return None
    
    async def predict_psychological_reaction(self, character_name: str,
                                           psychological_profile: Dict[str, Any],
                                           situation_description: str) -> Optional[Dict[str, Any]]:
        """
        预测角色在特定情境下的心理反应
        """
        try:
            profile_info = json.dumps(psychological_profile, ensure_ascii=False, indent=2)
            
            prompt = f"""
            请预测角色在特定情境下的心理反应。
            
            ## 角色信息
            角色名称: {character_name}
            
            ## 心理概况
            {profile_info}
            
            ## 情境描述
            {situation_description}
            
            ## 预测维度
            1. 情绪反应：会感到什么情绪，强度如何
            2. 认知反应：会怎么想，会有什么想法
            3. 行为倾向：可能会采取什么行动
            4. 决策过程：会如何做决定
            5. 长期影响：对此事的长期心理影响
            
            ## 输出格式
            {{
                "character_name": "{character_name}",
                "situation": "{situation_description[:100]}...",
                "predicted_reactions": {{
                    "emotional_reactions": [
                        {{
                            "emotion": "情感名称",
                            "intensity": 0.0-1.0,
                            "duration": "short/medium/long"
                        }}
                    ],
                    "cognitive_responses": [
                        "认知反应1",
                        "认知反应2"
                    ],
                    "behavioral_tendencies": [
                        "行为倾向1",
                        "行为倾向2"
                    ],
                    "decision_making": {{
                        "likely_decision": "可能决策",
                        "decision_factors": ["因素1", "因素2"],
                        "confidence": 0.0-1.0
                    }},
                    "long_term_effects": [
                        "长期影响1",
                        "长期影响2"
                    ]
                }},
                "confidence_score": 0.0-1.0,
                "reasoning": "预测依据和理由"
            }}
            """
            
            messages = [
                {"role": "system", "content": "你是专业的心理学家，擅长预测人类心理反应和行为倾向。"},
                {"role": "user", "content": prompt}
            ]
            
            result = await self.call_deepseek(
                messages=messages,
                model="deepseek-chat",
                temperature=0.3,
                max_tokens=1200
            )
            
            if result and "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                try:
                    prediction_result = json.loads(content)
                    
                    logger.info(f"心理反应预测成功: {character_name}")
                    return prediction_result
                    
                except json.JSONDecodeError as e:
                    logger.error(f"解析心理预测JSON失败: {str(e)}")
                    logger.debug(f"原始响应内容: {content}")
                    return None
                    
            else:
                logger.error("心理反应预测LLM响应格式错误")
                return None
                
        except Exception as e:
            logger.error(f"心理反应预测失败: {str(e)}")
            return None
    
    async def update_psychological_model(self, character_name: str,
                                       current_profile: Dict[str, Any],
                                       new_observations: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        更新心理模型（基于新观察）
        """
        try:
            current_profile_str = json.dumps(current_profile, ensure_ascii=False, indent=2)
            observations_str = json.dumps(new_observations, ensure_ascii=False, indent=2)
            
            prompt = f"""
            请基于新的观察数据更新角色的心理模型。
            
            ## 角色信息
            角色名称: {character_name}
            
            ## 当前心理模型
            {current_profile_str}
            
            ## 新观察数据
            {observations_str}
            
            ## 更新原则
            1. 渐进式更新：心理特质不应突变，应平滑变化
            2. 证据权重：多条证据可以加强或减弱特定特质
            3. 一致性检查：确保更新的模型内部一致
            4. 时间衰减：较旧的观察影响力逐渐降低
            
            ## 输出格式
            {{
                "character_name": "{character_name}",
                "updated_profile": {{
                    "big_five_traits": {{
                        "openness": 0.0-1.0,
                        "conscientiousness": 0.0-1.0,
                        "extraversion": 0.0-1.0,
                        "agreeableness": 0.0-1.0,
                        "neuroticism": 0.0-1.0
                    }},
                    "current_emotions": [
                        {{
                            "emotion": "情感名称",
                            "intensity": 0.0-1.0,
                            "trigger": "触发原因"
                        }}
                    ],
                    "psychological_needs": [
                        {{
                            "need_type": "需求类型",
                            "priority": 0.0-1.0,
                            "satisfaction": 0.0-1.0
                        }}
                    ]
                }},
                "changes_detected": {{
                    "significant_changes": [
                        {{
                            "trait": "特质名称",
                            "old_value": 0.5,
                            "new_value": 0.7,
                            "magnitude": 0.2
                        }}
                    ],
                    "stability_analysis": {{
                        "stable_traits": ["特质1", "特质2"],
                        "changing_traits": ["特质3", "特质4"],
                        "overall_stability": "high/medium/low"
                    }}
                }},
                "confidence_level": "high/medium/low",
                "update_reasoning": "更新理由和依据"
            }}
            """
            
            messages = [
                {"role": "system", "content": "你是专业的心理建模专家，擅长基于新观察更新心理模型。"},
                {"role": "user", "content": prompt}
            ]
            
            result = await self.call_deepseek(
                messages=messages,
                model="deepseek-chat",
                temperature=0.2,
                max_tokens=1500
            )
            
            if result and "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                try:
                    update_result = json.loads(content)
                    
                    logger.info(f"心理模型更新成功: {character_name}")
                    return update_result
                    
                except json.JSONDecodeError as e:
                    logger.error(f"解析心理模型更新JSON失败: {str(e)}")
                    logger.debug(f"原始响应内容: {content}")
                    return None
                    
            else:
                logger.error("心理模型更新LLM响应格式错误")
                return None
                
        except Exception as e:
            logger.error(f"心理模型更新失败: {str(e)}")
            return None
    
    def _generate_cache_key(self, request_data: Dict[str, Any]) -> str:
        """生成缓存键"""
        import hashlib
        import json
        
        # 将请求数据转换为可哈希的字符串
        data_str = json.dumps(request_data, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()
    
    def _validate_analysis_result(self, result: Dict[str, Any]) -> bool:
        """验证分析结果格式"""
        required_fields = ["detected_tags", "document_structure", "parsing_rules"]
        
        for field in required_fields:
            if field not in result:
                return False
        
        # 检查detected_tags格式
        if not isinstance(result["detected_tags"], list):
            return False
        
        # 检查document_structure格式
        required_subfields = ["has_instructions", "has_world_info", "has_dialogue_history", "has_character_profiles"]
        for subfield in required_subfields:
            if subfield not in result["document_structure"]:
                return False
        
        return True
    
    def _validate_similarity_result(self, result: Dict[str, Any]) -> bool:
        """验证相似度检查结果格式"""
        required_fields = ["is_similar", "similarity_score", "overlap_type", "reasoning"]
        
        for field in required_fields:
            if field not in result:
                return False
        
        # 检查类型
        if not isinstance(result["is_similar"], bool):
            return False
        
        if not isinstance(result["similarity_score"], (int, float)):
            return False
        
        if not isinstance(result["reasoning"], str):
            return False
        
        return True
