"""
因果分析服务

使用LLM从文本中提取因果关系和事件
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


class CausalAnalyzer:
    """因果分析器"""
    
    def __init__(self, llm_service):
        self.llm_service = llm_service
    
    async def extract_causal_relations(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        使用LLM提取因果关系
        
        流程：
        1. 构建分析提示词
        2. 调用LLM
        3. 解析返回的JSON
        4. 构建因果链对象
        
        参数:
            llm_service: LLM服务
            text: 文本内容
            context: 上下文
        
        返回:
            Dict: {
                "events": [...],
                "causal_relations": [...]
            }
        """
        
        # 构建提示词
        prompt = f"""你是一个因果关系分析专家。请分析以下文本中的因果关系。

## 分析任务
1. 识别所有事件（动作、发生的事情、结果等）
2. 识别事件之间的因果关系
3. 评估因果关系的强度和类型
4. 识别必要条件和例外情况

## 输入文本
{text}

## 上下文信息
角色: {context.get('characters', '未知') if context else '无'}
地点: {context.get('location', '未知') if context else '无'}
时间: {context.get('time', '未知') if context else '无'}

## 因果关系类型
- causes: 直接导致（强因果）
- contributes_to: 促成/间接导致（弱因果）
- prevents: 阻止
- enables: 使能/提供条件
- requires: 需要/依赖

## 输出要求（JSON格式）:
{{
  "events": [
    {{
      "event_name": "事件描述",
      "event_type": "action/incident/outcome",
      "participants": ["角色1", "角色2"],
      "location": "地点",
      "time": "时间"
    }}
  ],
  "causal_relations": [
    {{
      "cause_event": "原因事件描述",
      "effect_event": "结果事件描述",
      "relation_type": "causes/contributes_to/prevents/enables/requires",
      "causal_strength": 0.9,  // 0.0-1.0
      "necessity_score": 0.8,  // 0.0-1.0
      "sufficiency_score": 0.7,  // 0.0-1.0
      "conditions": ["必要条件1", "必要条件2"],
      "exceptions": ["例外情况"],
      "evidence": "证据或理由",
      "confidence": 0.85
    }}
  ]
}}
"""
        
        # 调用LLM
        try:
            response = await self.llm_service.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是一个专业的因果关系分析专家。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            # 解析JSON
            json_content = json.loads(response.choices[0].message.content)
            
            # 构建返回结果
            result = {
                "events": json_content.get("events", []),
                "causal_relations": json_content.get("causal_relations", []),
                "analysis_time": datetime.now(timezone.utc).isoformat()
            }
            
            return result
            
        except Exception as e:
            print(f"Error extracting causal relations: {e}")
            raise e
    
    def parse_events(self, events_data: List[Dict]) -> List[Dict[str, Any]]:
        """
        解析事件数据
        
        参数:
            events_data: 事件数据列表
        
        返回:
            List[Dict]: 解析后的事件对象
        """
        parsed_events = []
        
        for i, event_data in enumerate(events_data):
            parsed_event = {
                "event_id": f"event_{int(datetime.now(timezone.utc).timestamp())}_{i}",
                "name": event_data.get("event_name", f"Event {i+1}"),
                "event_type": event_data.get("event_type", "action"),
                "description": event_data.get("event_name", ""),
                "participants": event_data.get("participants", []),
                "location": event_data.get("location"),
                "start_time": datetime.now(timezone.utc),
                "end_time": None,
                "duration": None,
                "causes": [],
                "effects": [],
                "contributes_to": [],
                "significance": "minor",
                "impact_scope": "local",
                "status": "planned",
                "outcome": None,
                "valid_from": datetime.now(timezone.utc),
                "valid_until": None
            }
            
            parsed_events.append(parsed_event)
        
        return parsed_events
    
    def parse_causal_relations(
        self,
        relations_data: List[Dict],
        events_map: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        解析因果关系数据
        
        参数:
            relations_data: 关系数据列表
            events_map: 事件名到ID的映射
        
        返回:
            List[Dict]: 解析后的因果关系对象
        """
        parsed_relations = []
        
        for rel_data in relations_data:
            cause_name = rel_data.get("cause_event", "")
            effect_name = rel_data.get("effect_event", "")
            
            # 查找事件ID
            cause_id = events_map.get(cause_name)
            effect_id = events_map.get(effect_name)
            
            if cause_id and effect_id:
                parsed_relation = {
                    "cause_event_id": cause_id,
                    "effect_event_id": effect_id,
                    "relation_type": rel_data.get("relation_type", "causes"),
                    "causal_strength": rel_data.get("causal_strength", 0.8),
                    "temporal_proximity": None,
                    "necessity_score": rel_data.get("necessity_score", 0.7),
                    "sufficiency_score": rel_data.get("sufficiency_score", 0.7),
                    "evidence_level": rel_data.get("confidence", 0.8),
                    "evidence": rel_data.get("evidence", ""),
                    "conditions": rel_data.get("conditions", []),
                    "exceptions": rel_data.get("exceptions", []),
                    "created_at": datetime.now(timezone.utc)
                }
                
                parsed_relations.append(parsed_relation)
        
        return parsed_relations
