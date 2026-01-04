"""
语义去重服务
实现三级去重系统：
1. 文本指纹层（MinHash）：快速去重
2. 特征比对层（实体/关系比较）：中等精度
3. LLM语义层：高精度边界处理
"""

import logging
import hashlib
import json
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime
import re
from collections import defaultdict
import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    from config.settings import settings
    from services.llm_service import LLMService
except ImportError:
    # 向后兼容
    raise

logger = logging.getLogger(__name__)


@dataclass
class DeduplicationResult:
    """去重结果"""
    is_duplicate: bool
    similarity_score: float
    deduplication_level: str  # fingerprint/feature/llm
    reason: str
    matched_entity_id: Optional[str] = None
    confidence: float = 0.0


class DeduplicationService:
    """语义去重服务"""
    
    def __init__(self):
        """初始化去重服务"""
        self.llm_service = LLMService() if hasattr(settings, 'DEEPSEEK_API_KEY') else None
        self.fingerprint_cache = {}  # 指纹缓存
        self.minhash_shingles = 5   # MinHash shingle大小
        self.minhash_permutations = 128  # 置换次数
        
        logger.info("语义去重服务初始化成功")
    
    def deduplicate_entity(self, session_id: str, entity_data: Dict[str, Any],
                          existing_entities: List[Dict[str, Any]]) -> DeduplicationResult:
        """
        实体去重处理
        
        流程：
        1. 文本指纹去重（快速）
        2. 特征比对去重（中等精度）
        3. LLM语义去重（高精度）
        """
        logger.debug(f"开始实体去重: session={session_id}, 实体名={entity_data.get('name', 'unknown')}")
        
        # 第一级：文本指纹去重
        fingerprint_result = self._fingerprint_deduplication(entity_data, existing_entities)
        if fingerprint_result.is_duplicate:
            logger.debug(f"指纹去重检测到重复: 相似度={fingerprint_result.similarity_score}")
            return fingerprint_result
        
        # 第二级：特征比对去重
        feature_result = self._feature_deduplication(entity_data, existing_entities)
        if feature_result.is_duplicate:
            logger.debug(f"特征去重检测到重复: 相似度={feature_result.similarity_score}")
            return feature_result
        
        # 第三级：LLM语义去重（仅在需要时）
        if self._should_use_llm_deduplication(entity_data, existing_entities):
            llm_result = self._llm_semantic_deduplication(entity_data, existing_entities)
            if llm_result.is_duplicate:
                logger.debug(f"LLM去重检测到重复: 相似度={llm_result.similarity_score}")
                return llm_result
        
        # 无重复
        return DeduplicationResult(
            is_duplicate=False,
            similarity_score=0.0,
            deduplication_level="none",
            reason="与现有实体无显著相似性"
        )
    
    def _fingerprint_deduplication(self, entity_data: Dict[str, Any],
                                  existing_entities: List[Dict[str, Any]]) -> DeduplicationResult:
        """文本指纹去重（快速，覆盖90%情况）"""
        # 提取实体关键文本信息
        key_text = self._extract_entity_key_text(entity_data)
        fingerprint = self._generate_text_fingerprint(key_text)
        
        # 与现有实体比对
        best_match = None
        highest_similarity = 0.0
        
        for existing in existing_entities:
            existing_text = self._extract_entity_key_text(existing)
            existing_fingerprint = self._generate_text_fingerprint(existing_text)
            
            # 计算指纹相似度（Jaccard相似度）
            similarity = self._calculate_fingerprint_similarity(fingerprint, existing_fingerprint)
            
            if similarity > highest_similarity:
                highest_similarity = similarity
                best_match = existing
            
            # 完全匹配（相似度>0.95）
            if similarity > 0.95:
                return DeduplicationResult(
                    is_duplicate=True,
                    similarity_score=similarity,
                    deduplication_level="fingerprint",
                    reason=f"文本指纹高度相似 (相似度: {similarity:.2f})",
                    matched_entity_id=existing.get("entity_id"),
                    confidence=similarity
                )
        
        # 高度相似（相似度>0.8）
        if highest_similarity > 0.8 and best_match:
            return DeduplicationResult(
                is_duplicate=True,
                similarity_score=highest_similarity,
                deduplication_level="fingerprint",
                reason=f"文本指纹高度相似 (相似度: {highest_similarity:.2f})",
                matched_entity_id=best_match.get("entity_id"),
                confidence=highest_similarity
            )
        
        # 无显著相似性
        return DeduplicationResult(
            is_duplicate=False,
            similarity_score=highest_similarity,
            deduplication_level="fingerprint",
            reason=f"指纹相似度低 (相似度: {highest_similarity:.2f})"
        )
    
    def _feature_deduplication(self, entity_data: Dict[str, Any],
                              existing_entities: List[Dict[str, Any]]) -> DeduplicationResult:
        """特征比对去重（中等精度，覆盖7%情况）"""
        # 提取实体特征
        entity_features = self._extract_entity_features(entity_data)
        
        best_match = None
        highest_similarity = 0.0
        
        for existing in existing_entities:
            existing_features = self._extract_entity_features(existing)
            
            # 计算特征相似度
            similarity = self._calculate_feature_similarity(entity_features, existing_features)
            
            if similarity > highest_similarity:
                highest_similarity = similarity
                best_match = existing
            
            # 高度相似（相似度>0.85）
            if similarity > 0.85:
                return DeduplicationResult(
                    is_duplicate=True,
                    similarity_score=similarity,
                    deduplication_level="feature",
                    reason=f"实体特征高度相似 (相似度: {similarity:.2f})",
                    matched_entity_id=existing.get("entity_id"),
                    confidence=similarity
                )
        
        # 中等相似（相似度>0.7）
        if highest_similarity > 0.7 and best_match:
            return DeduplicationResult(
                is_duplicate=True,
                similarity_score=highest_similarity,
                deduplication_level="feature",
                reason=f"实体特征中等相似 (相似度: {highest_similarity:.2f})",
                matched_entity_id=best_match.get("entity_id"),
                confidence=highest_similarity * 0.8  # 降低置信度
            )
        
        # 无显著相似性
        return DeduplicationResult(
            is_duplicate=False,
            similarity_score=highest_similarity,
            deduplication_level="feature",
            reason=f"特征相似度低 (相似度: {highest_similarity:.2f})"
        )
    
    async def _llm_semantic_deduplication(self, entity_data: Dict[str, Any],
                                         existing_entities: List[Dict[str, Any]]) -> DeduplicationResult:
        """LLM语义去重（高精度，处理边界情况3%）"""
        if not self.llm_service:
            logger.warning("LLM服务未配置，跳过语义去重")
            return DeduplicationResult(
                is_duplicate=False,
                similarity_score=0.0,
                deduplication_level="llm",
                reason="LLM服务未配置"
            )
        
        try:
            # 准备用于LLM比较的文本
            entity_desc = self._prepare_entity_description(entity_data)
            
            best_match = None
            highest_similarity = 0.0
            
            # 与现有实体进行LLM比较（最多比较5个）
            for existing in existing_entities[:5]:
                existing_desc = self._prepare_entity_description(existing)
                
                # 调用LLM进行语义相似度判断
                llm_result = await self.llm_service.semantic_similarity_check(
                    entity_desc, existing_desc
                )
                
                if llm_result and llm_result.get("success", False):
                    similarity = llm_result.get("similarity_score", 0.0)
                    
                    if similarity > highest_similarity:
                        highest_similarity = similarity
                        best_match = existing
                    
                    # LLM判定为相似（相似度>0.75）
                    if similarity > 0.75:
                        return DeduplicationResult(
                            is_duplicate=True,
                            similarity_score=similarity,
                            deduplication_level="llm",
                            reason=f"语义内容相似 (LLM相似度: {similarity:.2f})",
                            matched_entity_id=existing.get("entity_id"),
                            confidence=similarity * 0.9  # LLM置信度调整
                        )
            
            # LLM未发现显著相似性
            return DeduplicationResult(
                is_duplicate=False,
                similarity_score=highest_similarity,
                deduplication_level="llm",
                reason=f"LLM判定无显著语义相似性 (相似度: {highest_similarity:.2f})"
            )
            
        except Exception as e:
            logger.error(f"LLM语义去重失败: {str(e)}")
            return DeduplicationResult(
                is_duplicate=False,
                similarity_score=0.0,
                deduplication_level="llm",
                reason=f"去重处理异常: {str(e)}"
            )
    
    def _extract_entity_key_text(self, entity_data: Dict[str, Any]) -> str:
        """提取实体关键文本信息"""
        parts = []
        
        # 实体名称
        if "name" in entity_data and entity_data["name"]:
            parts.append(str(entity_data["name"]))
        
        # 实体类型
        if "entity_type" in entity_data and entity_data["entity_type"]:
            parts.append(str(entity_data["entity_type"]))
        
        # 关键属性
        if "properties" in entity_data and entity_data["properties"]:
            props = entity_data["properties"]
            if isinstance(props, dict):
                key_props = ["description", "title", "label", "type", "category"]
                for key in key_props:
                    if key in props and props[key]:
                        parts.append(str(props[key]))
        
        return " ".join(parts)
    
    def _generate_text_fingerprint(self, text: str) -> str:
        """生成文本指纹（简化的MinHash）"""
        if not text:
            return ""
        
        # 简化处理：使用MD5哈希作为指纹
        # 实际应用中可使用更复杂的MinHash算法
        text_normalized = self._normalize_text(text)
        
        # 生成shingles（字符级）
        shingles = []
        for i in range(0, len(text_normalized) - self.minhash_shingles + 1):
            shingle = text_normalized[i:i + self.minhash_shingles]
            shingles.append(shingle)
        
        # 生成哈希签名
        hash_signatures = []
        for i in range(min(self.minhash_permutations, 10)):  # 简化，只取10个置换
            # 对shingles排序后取哈希
            sorted_shingles = sorted(shingles)
            combined = "".join(sorted_shingles[:5]) if sorted_shingles else ""
            if combined:
                hash_val = hashlib.md5(combined.encode()).hexdigest()[:8]
                hash_signatures.append(hash_val)
        
        return ":".join(hash_signatures) if hash_signatures else ""
    
    def _calculate_fingerprint_similarity(self, fingerprint1: str, fingerprint2: str) -> float:
        """计算指纹相似度"""
        if not fingerprint1 or not fingerprint2:
            return 0.0
        
        # 简单字符串匹配相似度
        parts1 = set(fingerprint1.split(":"))
        parts2 = set(fingerprint2.split(":"))
        
        if not parts1 or not parts2:
            return 0.0
        
        # Jaccard相似度
        intersection = len(parts1.intersection(parts2))
        union = len(parts1.union(parts2))
        
        return intersection / union if union > 0 else 0.0
    
    def _extract_entity_features(self, entity_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取实体特征"""
        features = {
            "name": entity_data.get("name", ""),
            "entity_type": entity_data.get("entity_type", ""),
            "property_keys": [],
            "property_values": [],
            "metadata_fields": []
        }
        
        # 提取属性键
        if "properties" in entity_data and entity_data["properties"]:
            props = entity_data["properties"]
            if isinstance(props, dict):
                features["property_keys"] = list(props.keys())
                # 提取属性值的前几个字符作为特征
                for key, value in props.items():
                    if isinstance(value, str) and value:
                        features["property_values"].append(value[:20])
        
        # 提取元数据字段
        if "metadata" in entity_data and entity_data["metadata"]:
            features["metadata_fields"] = list(entity_data["metadata"].keys())
        
        return features
    
    def _calculate_feature_similarity(self, features1: Dict[str, Any], 
                                     features2: Dict[str, Any]) -> float:
        """计算特征相似度"""
        similarity = 0.0
        
        # 名称相似度
        name1 = features1.get("name", "").lower()
        name2 = features2.get("name", "").lower()
        if name1 and name2:
            if name1 == name2:
                similarity += 0.4
            elif name1 in name2 or name2 in name1:
                similarity += 0.2
        
        # 类型相似度
        type1 = features1.get("entity_type", "").lower()
        type2 = features2.get("entity_type", "").lower()
        if type1 and type2 and type1 == type2:
            similarity += 0.3
        
        # 属性键相似度
        keys1 = set(features1.get("property_keys", []))
        keys2 = set(features2.get("property_keys", []))
        if keys1 and keys2:
            keys_similarity = len(keys1.intersection(keys2)) / max(len(keys1), len(keys2))
            similarity += keys_similarity * 0.2
        
        # 属性值相似度
        values1 = features1.get("property_values", [])
        values2 = features2.get("property_values", [])
        if values1 and values2:
            # 简单字符串匹配
            common_values = 0
            for v1 in values1:
                for v2 in values2:
                    if v1 and v2 and (v1 in v2 or v2 in v1):
                        common_values += 1
                        break
            
            if values1 or values2:
                values_similarity = common_values / max(len(values1), len(values2))
                similarity += values_similarity * 0.1
        
        # 确保在0-1之间
        return min(max(similarity, 0.0), 1.0)
    
    def _should_use_llm_deduplication(self, entity_data: Dict[str, Any],
                                      existing_entities: List[Dict[str, Any]]) -> bool:
        """判断是否应该使用LLM去重"""
        # 条件1：实体内容较长且复杂
        entity_text = self._extract_entity_key_text(entity_data)
        if len(entity_text) > 200:
            return True
        
        # 条件2：实体是重要类型（角色、事件等）
        important_types = ["character", "person", "event", "location"]
        entity_type = entity_data.get("entity_type", "").lower()
        if entity_type in important_types:
            return True
        
        # 条件3：已有相似指纹但不确定（指纹相似度0.6-0.8）
        fingerprint = self._generate_text_fingerprint(entity_text)
        for existing in existing_entities[:5]:  # 只检查前5个
            existing_text = self._extract_entity_key_text(existing)
            existing_fingerprint = self._generate_text_fingerprint(existing_text)
            similarity = self._calculate_fingerprint_similarity(fingerprint, existing_fingerprint)
            
            if 0.6 <= similarity <= 0.8:
                return True
        
        return False
    
    def _prepare_entity_description(self, entity_data: Dict[str, Any]) -> str:
        """准备实体描述用于LLM比较"""
        description = []
        
        # 基本信息
        if "name" in entity_data and entity_data["name"]:
            description.append(f"名称: {entity_data['name']}")
        
        if "entity_type" in entity_data and entity_data["entity_type"]:
            description.append(f"类型: {entity_data['entity_type']}")
        
        # 关键属性
        if "properties" in entity_data and entity_data["properties"]:
            props = entity_data["properties"]
            if isinstance(props, dict):
                # 提取重要的描述性属性
                important_keys = ["description", "bio", "background", "summary", "details"]
                for key in important_keys:
                    if key in props and props[key]:
                        value = str(props[key])
                        if len(value) > 100:
                            value = value[:100] + "..."
                        description.append(f"{key}: {value}")
        
        # 其他重要字段
        if "created_at" in entity_data:
            description.append(f"创建时间: {entity_data['created_at']}")
        
        # 组合描述
        return "\n".join(description) if description else "（无描述信息）"
    
    def _normalize_text(self, text: str) -> str:
        """文本归一化处理"""
        if not text:
            return ""
        
        # 转换为小写
        text = text.lower()
        
        # 移除多余空白
        text = re.sub(r'\s+', ' ', text)
        
        # 移除标点符号（保留中文字符）
        text = re.sub(r'[^\w\s\u4e00-\u9fff]', '', text)
        
        return text.strip()
    
    def deduplicate_relationship(self, session_id: str, relationship_data: Dict[str, Any],
                                existing_relationships: List[Dict[str, Any]]) -> DeduplicationResult:
        """关系去重处理"""
        logger.debug(f"开始关系去重: session={session_id}")
        
        # 第一级：关键特征比对
        # 提取关系关键信息
        key_features = self._extract_relationship_key_features(relationship_data)
        
        for existing in existing_relationships:
            existing_features = self._extract_relationship_key_features(existing)
            
            # 计算特征相似度
            similarity = self._calculate_relationship_similarity(key_features, existing_features)
            
            if similarity > 0.9:  # 高度相似
                return DeduplicationResult(
                    is_duplicate=True,
                    similarity_score=similarity,
                    deduplication_level="relationship_feature",
                    reason=f"关系特征高度相似 (相似度: {similarity:.2f})",
                    matched_entity_id=existing.get("relationship_id"),
                    confidence=similarity
                )
            
            if similarity > 0.7:  # 中等相似
                return DeduplicationResult(
                    is_duplicate=True,
                    similarity_score=similarity,
                    deduplication_level="relationship_feature",
                    reason=f"关系特征中等相似 (相似度: {similarity:.2f})",
                    matched_entity_id=existing.get("relationship_id"),
                    confidence=similarity * 0.8
                )
        
        # 无显著相似性
        return DeduplicationResult(
            is_duplicate=False,
            similarity_score=0.0,
            deduplication_level="relationship_feature",
            reason="与现有关系无显著相似性"
        )
    
    def _extract_relationship_key_features(self, relationship_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取关系关键特征"""
        features = {
            "source_id": relationship_data.get("source_entity_id", ""),
            "target_id": relationship_data.get("target_entity_id", ""),
            "relation_type": relationship_data.get("relation_type", ""),
            "relation_subtype": relationship_data.get("relation_subtype", ""),
            "key_properties": []
        }
        
        # 提取关键属性
        if "properties" in relationship_data and relationship_data["properties"]:
            props = relationship_data["properties"]
            if isinstance(props, dict):
                key_props = ["intensity", "confidence", "context", "time_bounds"]
                for key in key_props:
                    if key in props:
                        features["key_properties"].append(key)
        
        return features
    
    def _calculate_relationship_similarity(self, features1: Dict[str, Any],
                                         features2: Dict[str, Any]) -> float:
        """计算关系相似度"""
        similarity = 0.0
        
        # 相同源和目标实体（权重最高）
        if (features1["source_id"] and features1["target_id"] and
            features1["source_id"] == features2["source_id"] and
            features1["target_id"] == features2["target_id"]):
            similarity += 0.6
        
        # 相同关系类型
        if (features1["relation_type"] and features2["relation_type"] and
            features1["relation_type"] == features2["relation_type"]):
            similarity += 0.3
        
        # 相同子类型
        if (features1["relation_subtype"] and features2["relation_subtype"] and
            features1["relation_subtype"] == features2["relation_subtype"]):
            similarity += 0.1
        
        # 关键属性匹配
        props1 = set(features1.get("key_properties", []))
        props2 = set(features2.get("key_properties", []))
        if props1 and props2:
            props_similarity = len(props1.intersection(props2)) / max(len(props1), len(props2))
            similarity += props_similarity * 0.2
        
        return min(max(similarity, 0.0), 1.0)
    
    def clear_cache(self, session_id: Optional[str] = None):
        """清除缓存"""
        if session_id:
            if session_id in self.fingerprint_cache:
                del self.fingerprint_cache[session_id]
                logger.debug(f"清除缓存: session={session_id}")
        else:
            self.fingerprint_cache.clear()
            logger.debug("清除所有缓存")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            "fingerprint_cache_size": len(self.fingerprint_cache),
            "total_cache_entries": sum(len(v) for v in self.fingerprint_cache.values()),
            "minhash_config": {
                "shingle_size": self.minhash_shingles,
                "permutations": self.minhash_permutations
            },
            "llm_available": self.llm_service is not None
        }
        
        return stats
