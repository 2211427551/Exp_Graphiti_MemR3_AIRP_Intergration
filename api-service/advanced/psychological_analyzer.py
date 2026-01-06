"""
心理状态分析服务

使用LLM分析对话内容，提取心理状态信息
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


class PsychologicalAnalyzer:
    """心理状态分析器"""
    
    def __init__(self, llm_service):
        self.llm_service = llm_service
    
    async def analyze_psychological_state(
        self,
        character_id: str,
        dialog_text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        使用LLM分析角色的心理状态
        
        流程：
        1. 构建分析提示词
        2. 调用LLM（通过Graphiti的LLM客户端）
        3. 解析返回的JSON
        4. 构建心理状态对象
        
        参数:
            llm_service: LLM服务
            character_id: 角色ID
            dialog_text: 对话文本
            context: 上下文信息
        
        返回:
            Dict: {
                "entity_id": str,
                "character_id": str,
                "emotional_mix": List[Dict],
                "dominant_emotion": str,
                "trait_manifestations": Dict[str, Dict],
                "stability_score": float,
                "intensity_level": float,
                "arousal_level": float,
                "analysis_confidence": float,
                "observed_at": datetime,
                "context": Dict
            }
        """
        
        # 构建提示词
        prompt = f"""你是一个角色心理分析专家。请分析以下对话中角色的心理状态。

## 分析维度
1. **情绪混合**：当前角色的主要情绪类型和强度（0.0-1.0）
   可能的情绪类型：joy, sadness, anger, fear, surprise, disgust, anticipation, trust

2. **主导情绪**：当前最强烈、最主导的情绪

3. **特质表现**：表现出的性格特质及其强度（0.0-1.0）
   示例特质：optimistic, anxious, aggressive, gentle, stubborn, flexible

4. **状态指标**：
   - 稳定性得分（0.0-1.0）：情绪是否稳定
   - 强度水平（0.0-1.0）：整体情绪强度
   - 唤醒水平（0.0-1.0）：能量水平高低

## 角色信息
角色ID: {character_id}
上下文: {context.get('character_description', '未知') if context else '无'}

## 对话文本
{dialog_text}

## 输出要求（JSON格式）:
{{
  "emotional_mix": [
    {{
      "emotion_type": "joy",
      "intensity": 0.8,
      "duration": null,
      "triggers": ["收到礼物", "被夸奖"],
      "manifestations": ["微笑", "跳跃", "语调轻快"]
    }}
  ],
  "dominant_emotion": "joy",
  "trait_manifestations": {{
    "optimistic": {{
      "strength": 0.9,
      "consistency": 0.8,
      "behavior_examples": ["积极面对困难", "鼓励他人"],
      "situational_context": "大部分情况"
    }}
  }},
  "stability_score": 0.8,
  "intensity_level": 0.7,
  "arousal_level": 0.9,
  "analysis_confidence": 0.85
}}
"""
        
        # 调用LLM（通过Graphiti的LLM客户端）
        try:
            response = await self.llm_service.client.chat.completions.create(
                model="deepseek-chat",  # 使用配置的模型
                messages=[
                    {"role": "system", "content": "你是一个专业的角色心理分析专家。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # 较低温度确保稳定性
                response_format={"type": "json_object"}  # 严格模式确保JSON格式
            )
            
            # 解析JSON
            json_content = json.loads(response.choices[0].message.content)
            
            # 构建返回结果
            result = {
                "entity_id": f"psych_state_{character_id}_{int(datetime.now(timezone.utc).timestamp())}",
                "character_id": character_id,
                "emotional_mix": [
                    {
                        "emotion_type": em["emotion_type"],
                        "intensity": em["intensity"],
                        "duration": em.get("duration"),
                        "triggers": em.get("triggers", []),
                        "manifestations": em.get("manifestations", [])
                    }
                    for em in json_content.get("emotional_mix", [])
                ],
                "dominant_emotion": json_content.get("dominant_emotion"),
                "trait_manifestations": {
                    trait_name: {
                        "strength": trait_data["strength"],
                        "consistency": trait_data.get("consistency", 0.8),
                        "behavior_examples": trait_data.get("behavior_examples", []),
                        "situational_context": trait_data.get("situational_context", "大部分情况")
                    }
                    for trait_name, trait_data in json_content.get("trait_manifestations", {}).items()
                },
                "stability_score": json_content.get("stability_score", 0.8),
                "intensity_level": json_content.get("intensity_level", 0.7),
                "arousal_level": json_content.get("arousal_level", 0.9),
                "analysis_confidence": json_content.get("analysis_confidence", 0.85),
                "observed_at": datetime.now(timezone.utc),
                "context": context or {}
            }
            
            return result
            
        except Exception as e:
            print(f"Error analyzing psychological state for character {character_id}: {e}")
            raise e
