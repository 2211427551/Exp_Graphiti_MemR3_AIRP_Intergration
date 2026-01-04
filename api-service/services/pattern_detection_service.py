#!/usr/bin/env python3
"""
模式检测和异常识别服务

基于双时序数据分析实体行为模式，检测异常行为和潜在风险。
支持：
1. 行为模式分析
2. 异常检测
3. 趋势预测
4. 风险预警
"""

import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict
from scipy import stats
import json
import uuid
import os
import sys

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 导入配置
config_path = os.path.join(project_root, 'config', 'settings.py')
import importlib.util
spec = importlib.util.spec_from_file_location("settings", config_path)
settings_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(settings_module)
settings = settings_module.settings

logger = logging.getLogger(__name__)

class PatternDetectionService:
    """模式检测和异常识别服务类"""
    
    def __init__(self, temporal_service=None):
        """初始化模式检测服务"""
        self.temporal_service = temporal_service
        self.behavior_profiles = {}  # session_id -> 实体行为画像
        self.anomaly_history = {}    # session_id -> 异常历史记录
        
        logger.info("模式检测服务初始化完成")
    
    def analyze_entity_patterns(self, session_id: str,
                               entity_ids: Optional[List[str]] = None,
                               analysis_window: Optional[Tuple[str, str]] = None,
                               sensitivity: float = 0.8) -> Dict[str, Any]:
        """
        分析实体行为模式
        
        Args:
            session_id: 会话ID
            entity_ids: 可选实体ID列表（为空则分析所有实体）
            analysis_window: 可选分析时间窗口 (start_time, end_time)
            sensitivity: 检测灵敏度（0.0-1.0，值越高越敏感）
            
        Returns:
            行为模式分析结果
        """
        try:
            if not self.temporal_service:
                return {
                    "success": False,
                    "error": "未提供时序数据服务"
                }
            
            # 确定时间窗口
            if analysis_window:
                start_time, end_time = analysis_window
            else:
                # 默认分析最近7天
                end_time = datetime.now().isoformat()
                start_time = (datetime.now() - timedelta(days=7)).isoformat()
            
            # 收集实体行为数据
            behavior_data = self._collect_behavior_data(
                session_id, start_time, end_time, entity_ids
            )
            
            if not behavior_data:
                return {
                    "success": False,
                    "error": "未找到行为数据"
                }
            
            # 分析行为模式
            pattern_analysis = self._analyze_behavior_patterns(
                behavior_data, sensitivity
            )
            
            # 更新行为画像
            self.behavior_profiles[session_id] = {
                "entity_profiles": pattern_analysis["entity_profiles"],
                "group_profiles": pattern_analysis["group_profiles"],
                "last_analysis_time": datetime.now().isoformat(),
                "analysis_window": analysis_window
            }
            
            return {
                "success": True,
                "analysis": {
                    "analysis_window": analysis_window,
                    "entities_analyzed": len(behavior_data),
                    "behavior_patterns": pattern_analysis["patterns"],
                    "anomalies_detected": len(pattern_analysis["anomalies"]),
                    "trends_identified": len(pattern_analysis["trends"]),
                    "entity_profiles": pattern_analysis["entity_profiles"],
                    "group_profiles": pattern_analysis["group_profiles"],
                    "timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"行为模式分析失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _collect_behavior_data(self, session_id: str, start_time: str, end_time: str,
                              entity_ids: Optional[List[str]] = None) -> Dict[str, List[Dict]]:
        """收集实体行为数据"""
        behavior_data = defaultdict(list)
        
        # 生成时间点采样
        from datetime import datetime
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        
        # 生成采样时间点（每小时采样）
        total_hours = int((end_dt - start_dt).total_seconds() / 3600)
        if total_hours <= 0:
            total_hours = 24
        
        time_points = []
        for i in range(total_hours + 1):
            sample_time = start_dt + timedelta(hours=i)
            time_points.append(sample_time.isoformat())
        
        # 收集每个时间点的实体状态
        for time_point in time_points:
            try:
                # 查询该时间点有效的实体
                entities = self.temporal_service.query_valid_at_time(
                    session_id=session_id,
                    query_time=time_point,
                    entity_type=None,
                    limit=100
                )
                
                for entity in entities:
                    entity_id = entity.get("entity_id")
                    
                    # 如果指定了实体ID列表，只收集指定实体的数据
                    if entity_ids and entity_id not in entity_ids:
                        continue
                    
                    behavior_data[entity_id].append({
                        "timestamp": time_point,
                        "entity_data": entity
                    })
                    
            except Exception as e:
                logger.warning(f"收集行为数据失败 (时间点={time_point}): {str(e)}")
                continue
        
        return behavior_data
    
    def _analyze_behavior_patterns(self, behavior_data: Dict[str, List[Dict]],
                                  sensitivity: float) -> Dict[str, Any]:
        """分析行为模式"""
        analysis_results = {
            "patterns": [],
            "anomalies": [],
            "trends": [],
            "entity_profiles": {},
            "group_profiles": {}
        }
        
        # 分析每个实体的行为模式
        for entity_id, records in behavior_data.items():
            if len(records) < 3:  # 至少需要3个数据点
                continue
            
            entity_profile = self._create_entity_profile(entity_id, records, sensitivity)
            analysis_results["entity_profiles"][entity_id] = entity_profile
            
            # 检测异常
            anomalies = self._detect_anomalies(entity_id, records, entity_profile, sensitivity)
            analysis_results["anomalies"].extend(anomalies)
            
            # 识别行为模式
            patterns = self._identify_behavior_patterns(entity_id, records)
            analysis_results["patterns"].extend(patterns)
        
        # 分析群体模式
        if len(analysis_results["entity_profiles"]) > 1:
            group_profiles = self._analyze_group_patterns(analysis_results["entity_profiles"])
            analysis_results["group_profiles"] = group_profiles
            
            # 识别群体异常
            group_anomalies = self._detect_group_anomalies(group_profiles)
            analysis_results["anomalies"].extend(group_anomalies)
        
        # 识别趋势
        trends = self._identify_trends(behavior_data)
        analysis_results["trends"] = trends
        
        return analysis_results
    
    def _create_entity_profile(self, entity_id: str, records: List[Dict],
                              sensitivity: float) -> Dict[str, Any]:
        """创建实体行为画像"""
        profile = {
            "entity_id": entity_id,
            "entity_type": records[0]["entity_data"].get("entity_type", "unknown"),
            "entity_name": records[0]["entity_data"].get("name", entity_id),
            "activity_metrics": {},
            "stability_metrics": {},
            "interaction_metrics": {},
            "risk_indicators": {}
        }
        
        # 提取数值属性序列
        numeric_sequences = defaultdict(list)
        timestamps = []
        
        for record in records:
            timestamp = record["timestamp"]
            entity_data = record["entity_data"]
            properties = entity_data.get("properties", {})
            
            timestamps.append(timestamp)
            
            for key, value in properties.items():
                if isinstance(value, (int, float)):
                    numeric_sequences[key].append(float(value))
                elif isinstance(value, str):
                    numeric_sequences[key].append(len(value))
                elif isinstance(value, bool):
                    numeric_sequences[key].append(1.0 if value else 0.0)
        
        # 计算活动指标
        if numeric_sequences:
            for prop_name, values in numeric_sequences.items():
                if len(values) >= 3:
                    profile["activity_metrics"][prop_name] = {
                        "mean": np.mean(values),
                        "std": np.std(values),
                        "min": np.min(values),
                        "max": np.max(values),
                        "median": np.median(values),
                        "q1": np.percentile(values, 25),
                        "q3": np.percentile(values, 75),
                        "count": len(values)
                    }
        
        # 计算稳定性指标
        profile["stability_metrics"]["record_count"] = len(records)
        
        if len(records) > 1:
            # 计算更新频率
            time_diffs = []
            for i in range(1, len(records)):
                time1 = datetime.fromisoformat(records[i-1]["timestamp"].replace('Z', '+00:00'))
                time2 = datetime.fromisoformat(records[i]["timestamp"].replace('Z', '+00:00'))
                time_diffs.append((time2 - time1).total_seconds())
            
            if time_diffs:
                profile["stability_metrics"]["update_frequency_mean"] = np.mean(time_diffs)
                profile["stability_metrics"]["update_frequency_std"] = np.std(time_diffs)
                profile["stability_metrics"]["update_frequency_cv"] = np.std(time_diffs) / np.mean(time_diffs) if np.mean(time_diffs) > 0 else 0
        
        # 计算风险指标
        if len(records) >= 5:
            # 检测值突变
            for prop_name, values in numeric_sequences.items():
                if len(values) >= 5:
                    # 计算相邻点变化率
                    changes = np.abs(np.diff(values))
                    change_rate = changes / np.abs(values[:-1]) if np.any(values[:-1] != 0) else changes
                    
                    # 检测异常变化
                    if len(change_rate) >= 2:
                        mean_change = np.mean(change_rate)
                        std_change = np.std(change_rate)
                        
                        if std_change > 0:
                            # 识别异常变化点
                            z_scores = (change_rate - mean_change) / std_change
                            anomalies = np.where(np.abs(z_scores) > (2 - sensitivity))[0]
                            
                            if len(anomalies) > 0:
                                if "abrupt_changes" not in profile["risk_indicators"]:
                                    profile["risk_indicators"]["abrupt_changes"] = []
                                
                                for idx in anomalies:
                                    profile["risk_indicators"]["abrupt_changes"].append({
                                        "property": prop_name,
                                        "time_index": idx,
                                        "change_rate": change_rate[idx],
                                        "z_score": z_scores[idx],
                                        "timestamp": timestamps[idx + 1]
                                    })
        
        return profile
    
    def _detect_anomalies(self, entity_id: str, records: List[Dict],
                         entity_profile: Dict[str, Any], sensitivity: float) -> List[Dict[str, Any]]:
        """检测异常行为"""
        anomalies = []
        
        if len(records) < 3:
            return anomalies
        
        # 检查数值属性的异常值
        for i, record in enumerate(records):
            timestamp = record["timestamp"]
            entity_data = record["entity_data"]
            properties = entity_data.get("properties", {})
            
            for key, value in properties.items():
                if isinstance(value, (int, float)):
                    # 获取该属性的统计信息
                    prop_stats = entity_profile["activity_metrics"].get(key)
                    
                    if prop_stats:
                        mean = prop_stats["mean"]
                        std = prop_stats["std"]
                        
                        if std > 0:
                            z_score = (float(value) - mean) / std
                            threshold = 3.0 - (sensitivity * 2.0)  # 灵敏度越高，阈值越低
                            
                            if np.abs(z_score) > threshold:
                                anomalies.append({
                                    "entity_id": entity_id,
                                    "timestamp": timestamp,
                                    "property": key,
                                    "value": value,
                                    "mean": mean,
                                    "std": std,
                                    "z_score": z_score,
                                    "anomaly_type": "value_outlier",
                                    "severity": min(1.0, np.abs(z_score) / 5.0)
                                })
        
        # 检测行为模式变化
        if len(records) >= 5:
            # 计算稳定性指标
            values_by_prop = defaultdict(list)
            
            for record in records:
                properties = record["entity_data"].get("properties", {})
                for key, value in properties.items():
                    if isinstance(value, (int, float)):
                        values_by_prop[key].append(float(value))
            
            for prop_name, values in values_by_prop.items():
                if len(values) >= 5:
                    # 分割序列为两个部分
                    split_idx = len(values) // 2
                    first_half = values[:split_idx]
                    second_half = values[split_idx:]
                    
                    if len(first_half) >= 2 and len(second_half) >= 2:
                        # 比较两个部分的统计特征
                        mean1, std1 = np.mean(first_half), np.std(first_half)
                        mean2, std2 = np.mean(second_half), np.std(second_half)
                        
                        # 计算变化显著性
                        mean_change = abs(mean2 - mean1) / max(mean1, 0.001)
                        std_change = abs(std2 - std1) / max(std1, 0.001)
                        
                        if mean_change > (0.5 * (2 - sensitivity)) or std_change > (0.5 * (2 - sensitivity)):
                            anomalies.append({
                                "entity_id": entity_id,
                                "timestamp": records[split_idx]["timestamp"],
                                "property": prop_name,
                                "mean_change": mean_change,
                                "std_change": std_change,
                                "anomaly_type": "behavior_shift",
                                "severity": max(mean_change, std_change)
                            })
        
        return anomalies
    
    def _identify_behavior_patterns(self, entity_id: str, records: List[Dict]) -> List[Dict[str, Any]]:
        """识别行为模式"""
        patterns = []
        
        if len(records) < 5:
            return patterns
        
        # 提取数值属性序列
        numeric_sequences = defaultdict(list)
        
        for record in records:
            properties = record["entity_data"].get("properties", {})
            for key, value in properties.items():
                if isinstance(value, (int, float)):
                    numeric_sequences[key].append(float(value))
        
        # 分析周期性模式
        for prop_name, values in numeric_sequences.items():
            if len(values) >= 7:
                # 检查是否存在每日模式
                daily_patterns = self._detect_daily_pattern(values)
                
                if daily_patterns["detected"]:
                    patterns.append({
                        "entity_id": entity_id,
                        "pattern_type": "daily_cycle",
                        "property": prop_name,
                        "strength": daily_patterns["strength"],
                        "period": 24,  # 24小时周期
                        "description": f"实体 {entity_id} 的 {prop_name} 属性呈现每日周期性变化"
                    })
                
                # 检查趋势
                trend_result = self._detect_trend(values)
                if trend_result["detected"]:
                    patterns.append({
                        "entity_id": entity_id,
                        "pattern_type": trend_result["trend_type"],
                        "property": prop_name,
                        "strength": trend_result["strength"],
                        "slope": trend_result["slope"],
                        "description": f"实体 {entity_id} 的 {prop_name} 属性呈现{trend_result['trend_type']}趋势"
                    })
        
        return patterns
    
    def _detect_daily_pattern(self, values: List[float]) -> Dict[str, Any]:
        """检测每日模式"""
        result = {
            "detected": False,
            "strength": 0.0,
            "period": 24
        }
        
        if len(values) < 7:
            return result
        
        # 简化版：检查是否存在明显的周期性
        try:
            # 使用傅里叶变换检测周期性
            n = len(values)
            y = np.fft.fft(values)
            frequencies = np.fft.fftfreq(n)
            
            # 忽略零频率分量
            idx = np.where(frequencies > 0)
            frequencies = frequencies[idx]
            amplitudes = np.abs(y[idx])
            
            # 寻找主要频率
            if len(amplitudes) > 0:
                max_amp_idx = np.argmax(amplitudes)
                dominant_freq = frequencies[max_amp_idx]
                dominant_amp = amplitudes[max_amp_idx]
                
                # 计算每日周期对应的频率
                daily_freq = 1.0 / 24  # 如果每小时一个数据点
                
                # 检查是否有接近每日频率的成分
                freq_diff = abs(dominant_freq - daily_freq)
                if freq_diff < 0.05:  # 允许5%的频率误差
                    # 计算强度：标准化后的振幅
                    total_amp = np.sum(amplitudes)
                    strength = dominant_amp / total_amp if total_amp > 0 else 0
                    
                    result["detected"] = strength > 0.3  # 阈值
                    result["strength"] = float(strength)
        
        except Exception as e:
            logger.warning(f"检测每日模式失败: {str(e)}")
        
        return result
    
    def _detect_trend(self, values: List[float]) -> Dict[str, Any]:
        """检测趋势"""
        result = {
            "detected": False,
            "trend_type": "none",
            "strength": 0.0,
            "slope": 0.0
        }
        
        if len(values) < 3:
            return result
        
        try:
            # 使用线性回归检测趋势
            x = np.arange(len(values))
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, values)
            
            if abs(r_value) > 0.5:  # 相关性较强
                result["detected"] = True
                result["strength"] = abs(float(r_value))
                result["slope"] = float(slope)
                
                if slope > 0.01:
                    result["trend_type"] = "上升"
                elif slope < -0.01:
                    result["trend_type"] = "下降"
                else:
                    result["trend_type"] = "稳定"
        
        except Exception as e:
            logger.warning(f"检测趋势失败: {str(e)}")
        
        return result
    
    def _analyze_group_patterns(self, entity_profiles: Dict[str, Dict]) -> Dict[str, Any]:
        """分析群体模式"""
        group_profiles = {
            "summary_stats": {},
            "clusters": [],
            "outliers": [],
            "correlations": []
        }
        
        if len(entity_profiles) < 2:
            return group_profiles
        
        try:
            # 计算群体统计
            entity_types = defaultdict(list)
            activity_metrics = defaultdict(list)
            
            for entity_id, profile in entity_profiles.items():
                entity_type = profile.get("entity_type", "unknown")
                entity_types[entity_type].append(entity_id)
                
                # 收集活动指标
                for prop_name, metrics in profile.get("activity_metrics", {}).items():
                    activity_metrics[f"{entity_type}_{prop_name}"].append(metrics["mean"])
            
            # 总结统计
            for entity_type, entities in entity_types.items():
                group_profiles["summary_stats"][entity_type] = {
                    "count": len(entities),
                    "entity_ids": entities
                }
            
            # 检测异常实体
            for entity_id, profile in entity_profiles.items():
                entity_type = profile.get("entity_type", "unknown")
                
                # 检查是否存在显著不同的行为
                is_outlier = self._detect_entity_outlier(entity_id, profile, entity_profiles)
                if is_outlier:
                    group_profiles["outliers"].append({
                        "entity_id": entity_id,
                        "entity_type": entity_type,
                        "reason": "行为模式显著偏离同类实体",
                        "severity": 0.7
                    })
        
        except Exception as e:
            logger.warning(f"分析群体模式失败: {str(e)}")
        
        return group_profiles
    
    def _detect_entity_outlier(self, entity_id: str, entity_profile: Dict[str, Any],
                              all_profiles: Dict[str, Dict]) -> bool:
        """检测实体异常"""
        if len(all_profiles) < 3:
            return False
        
        entity_type = entity_profile.get("entity_type", "unknown")
        same_type_profiles = [
            p for eid, p in all_profiles.items()
            if p.get("entity_type", "unknown") == entity_type
        ]
        
        if len(same_type_profiles) < 3:
            return False
        
        try:
            # 比较实体的关键指标
            key_properties = ["activity_metrics", "stability_metrics"]
            
            for prop_category in key_properties:
                profile_metrics = entity_profile.get(prop_category, {})
                
                for metric_name, metric_value in profile_metrics.items():
                    if isinstance(metric_value, dict) and "mean" in metric_value:
                        entity_value = metric_value["mean"]
                        
                        # 收集同类实体的值
                        other_values = []
                        for profile in same_type_profiles:
                            if profile["entity_id"] != entity_id:
                                metrics = profile.get(prop_category, {})
                                if metric_name in metrics and "mean" in metrics[metric_name]:
                                    other_values.append(metrics[metric_name]["mean"])
                        
                        if len(other_values) >= 2:
                            mean_other = np.mean(other_values)
                            std_other = np.std(other_values)
                            
                            if std_other > 0:
                                z_score = abs(entity_value - mean_other) / std_other
                                if z_score > 2.5:  # 显著异常
                                    return True
        
        except Exception as e:
            logger.warning(f"检测实体异常失败: {str(e)}")
        
        return False
    
    def _detect_group_anomalies(self, group_profiles: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检测群体异常"""
        anomalies = []
        
        try:
            # 检测群体行为突变
            summary_stats = group_profiles.get("summary_stats", {})
            
            for entity_type, stats_info in summary_stats.items():
                count = stats_info.get("count", 0)
                
                # 如果某类实体数量显著变化（简化版）
                if "expected_count" in stats_info:
                    expected = stats_info["expected_count"]
                    if expected > 0 and abs(count - expected) / expected > 0.5:
                        anomalies.append({
                            "anomaly_type": "population_change",
                            "entity_type": entity_type,
                            "current_count": count,
                            "expected_count": expected,
                            "deviation": abs(count - expected) / expected,
                            "severity": min(1.0, abs(count - expected) / expected),
                            "description": f"{entity_type}类实体数量异常变化"
                        })
        
        except Exception as e:
            logger.warning(f"检测群体异常失败: {str(e)}")
        
        return anomalies
    
    def _identify_trends(self, behavior_data: Dict[str, List[Dict]]) -> List[Dict[str, Any]]:
        """识别趋势"""
        trends = []
        
        if len(behavior_data) == 0:
            return trends
        
        try:
            # 分析总体活跃度趋势
            for entity_id, records in behavior_data.items():
                if len(records) >= 5:
                    # 计算活跃度指标
                    activity_scores = []
                    for record in records:
                        props = record["entity_data"].get("properties", {})
                        # 简化活跃度计算
                        score = 0
                        for key, value in props.items():
                            if isinstance(value, (int, float)):
                                score += abs(float(value))
                            elif isinstance(value, str):
                                score += len(value)
                            elif isinstance(value, bool):
                                score += 1 if value else 0
                        activity_scores.append(score)
                    
                    # 分析趋势
                    trend_result = self._detect_trend(activity_scores)
                    if trend_result["detected"]:
                        trends.append({
                            "entity_id": entity_id,
                            "trend_type": trend_result["trend_type"],
                            "strength": trend_result["strength"],
                            "slope": trend_result["slope"],
                            "description": f"实体 {entity_id} 活跃度呈{trend_result['trend_type']}趋势"
                        })
        
        except Exception as e:
            logger.warning(f"识别趋势失败: {str(e)}")
        
        return trends
    
    def get_risk_assessment(self, session_id: str, entity_id: str) -> Dict[str, Any]:
        """
        获取实体风险评估
        
        Args:
            session_id: 会话ID
            entity_id: 实体ID
            
        Returns:
            风险评估结果
        """
        try:
            profile = self.behavior_profiles.get(session_id, {}).get("entity_profiles", {}).get(entity_id)
            
            if not profile:
                return {
                    "success": False,
                    "error": "实体行为画像不存在"
                }
            
            # 计算风险分数
            risk_score = 0.0
            risk_factors = []
            
            # 分析活动指标
            activity_metrics = profile.get("activity_metrics", {})
            for prop_name, metrics in activity_metrics.items():
                std = metrics.get("std", 0)
                mean = metrics.get("mean", 0)
                
                # 高波动性增加风险
                if mean > 0 and std / mean > 0.5:
                    risk_score += 0.2
                    risk_factors.append({
                        "factor": f"高波动性 ({prop_name})",
                        "contribution": 0.2,
                        "details": f"{prop_name}属性波动性较高 (std/mean = {std/mean:.2f})"
                    })
            
            # 分析风险指标
            risk_indicators = profile.get("risk_indicators", {})
            for indicator_type, indicators in risk_indicators.items():
                if indicators:
                    risk_score += min(0.5, len(indicators) * 0.1)
                    risk_factors.append({
                        "factor": f"{indicator_type}",
                        "contribution": min(0.5, len(indicators) * 0.1),
                        "details": f"检测到{len(indicators)}个{indicator_type}异常"
                    })
            
            # 确定风险等级
            risk_level = "低风险"
            if risk_score > 0.6:
                risk_level = "高风险"
            elif risk_score > 0.3:
                risk_level = "中风险"
            
            return {
                "success": True,
                "assessment": {
                    "entity_id": entity_id,
                    "risk_score": min(1.0, risk_score),
                    "risk_level": risk_level,
                    "risk_factors": risk_factors,
                    "entity_type": profile.get("entity_type", "unknown"),
                    "entity_name": profile.get("entity_name", entity_id),
                    "timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"获取风险评估失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def generate_alert(self, session_id: str, anomaly: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成警报
        
        Args:
            session_id: 会话ID
            anomaly: 异常信息
            
        Returns:
            警报信息
        """
        try:
            # 初始化异常历史记录
            if session_id not in self.anomaly_history:
                self.anomaly_history[session_id] = []
            
            # 添加时间戳
            anomaly["alert_timestamp"] = datetime.now().isoformat()
            anomaly["alert_id"] = str(uuid.uuid4())
            
            # 根据异常类型确定警报级别
            anomaly_type = anomaly.get("anomaly_type", "unknown")
            
            if anomaly_type in ["value_outlier", "abrupt_change"]:
                severity = anomaly.get("severity", 0.5)
                
                if severity > 0.8:
                    alert_level = "紧急"
                elif severity > 0.6:
                    alert_level = "高"
                elif severity > 0.4:
                    alert_level = "中"
                else:
                    alert_level = "低"
                
                anomaly["alert_level"] = alert_level
                
                # 添加描述
                if anomaly_type == "value_outlier":
                    anomaly["description"] = (
                        f"实体 {anomaly.get('entity_id')} 的 {anomaly.get('property')} 属性 "
                        f"出现异常值 ({anomaly.get('value'):.2f}), Z分数: {anomaly.get('z_score', 0):.2f}"
                    )
                elif anomaly_type == "abrupt_change":
                    anomaly["description"] = (
                        f"实体 {anomaly.get('entity_id')} 的 {anomaly.get('property')} 属性 "
                        f"发生突变, 变化率: {anomaly.get('change_rate', 0):.2f}"
                    )
            
            # 记录异常
            self.anomaly_history[session_id].append(anomaly)
            
            # 限制历史记录大小
            if len(self.anomaly_history[session_id]) > 100:
                self.anomaly_history[session_id] = self.anomaly_history[session_id][-100:]
            
            return {
                "success": True,
                "alert": anomaly
            }
            
        except Exception as e:
            logger.error(f"生成警报失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_alert_history(self, session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取警报历史
        
        Args:
            session_id: 会话ID
            limit: 返回记录限制
            
        Returns:
            警报历史列表
        """
        try:
            history = self.anomaly_history.get(session_id, [])
            
            # 按时间排序（最新优先）
            history.sort(key=lambda x: x.get("alert_timestamp", ""), reverse=True)
            
            return history[:limit]
            
        except Exception as e:
            logger.error(f"获取警报历史失败: {str(e)}")
            return []
    
    def get_service_info(self) -> Dict[str, Any]:
        """获取服务信息"""
        info = {
            "service_type": "PatternDetectionService",
            "active_sessions": len(self.behavior_profiles),
            "anomaly_history_count": sum(len(h) for h in self.anomaly_history.values()),
            "profiled_entities": sum(len(p["entity_profiles"]) for p in self.behavior_profiles.values()),
            "timestamp": datetime.now().isoformat()
        }
        
        return info
    
    def clear_data(self, session_id: Optional[str] = None):
        """清除数据"""
        if session_id:
            if session_id in self.behavior_profiles:
                del self.behavior_profiles[session_id]
            if session_id in self.anomaly_history:
                del self.anomaly_history[session_id]
            logger.info(f"已清除会话 {session_id} 的数据")
        else:
            self.behavior_profiles.clear()
            self.anomaly_history.clear()
            logger.info("已清除所有数据")
