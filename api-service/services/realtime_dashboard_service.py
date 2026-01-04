#!/usr/bin/env python3
"""
实时分析看板服务

提供实时监控、分析和可视化功能，支持：
1. 实时数据流处理
2. 动态可视化生成
3. 性能指标监控
4. 交互式查询和过滤
"""

import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict, deque
import asyncio
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

class RealtimeDashboardService:
    """实时分析看板服务类"""
    
    def __init__(self, temporal_service=None, pattern_service=None, causal_service=None):
        """初始化实时看板服务"""
        self.temporal_service = temporal_service
        self.pattern_service = pattern_service
        self.causal_service = causal_service
        
        # 实时数据流
        self.data_streams = defaultdict(deque)  # stream_id -> 数据队列
        self.subscriptions = defaultdict(set)   # session_id -> 订阅的stream_ids
        
        # 看板状态
        self.dashboards = {}  # dashboard_id -> 看板配置
        self.widgets = {}     # widget_id -> 小部件配置
        
        # 性能指标
        self.metrics_history = defaultdict(deque)  # metric_name -> 历史值
        
        # 最大数据点数量
        self.max_data_points = 1000
        self.max_metrics_history = 100
        
        logger.info("实时分析看板服务初始化完成")
    
    def create_dashboard(self, session_id: str, dashboard_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建看板
        
        Args:
            session_id: 会话ID
            dashboard_config: 看板配置
            
        Returns:
            创建的看板信息
        """
        try:
            dashboard_id = str(uuid.uuid4())
            
            default_config = {
                "name": f"看板-{dashboard_id[:8]}",
                "layout": "grid",
                "grid_columns": 4,
                "refresh_interval": 30,  # 秒
                "theme": "light",
                "widgets": []
            }
            
            # 合并配置
            merged_config = {**default_config, **dashboard_config}
            merged_config["dashboard_id"] = dashboard_id
            merged_config["session_id"] = session_id
            merged_config["created_at"] = datetime.now().isoformat()
            merged_config["updated_at"] = datetime.now().isoformat()
            merged_config["is_active"] = True
            
            self.dashboards[dashboard_id] = merged_config
            
            logger.info(f"看板创建成功: {dashboard_id}")
            
            return {
                "success": True,
                "dashboard": merged_config
            }
            
        except Exception as e:
            logger.error(f"创建看板失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def add_widget(self, dashboard_id: str, widget_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        添加小部件到看板
        
        Args:
            dashboard_id: 看板ID
            widget_config: 小部件配置
            
        Returns:
            添加的小部件信息
        """
        try:
            if dashboard_id not in self.dashboards:
                return {
                    "success": False,
                    "error": "看板不存在"
                }
            
            widget_id = str(uuid.uuid4())
            
            default_config = {
                "type": "chart",
                "chart_type": "line",
                "title": f"小部件-{widget_id[:8]}",
                "position": {"x": 0, "y": 0, "width": 2, "height": 2},
                "data_source": {
                    "type": "static",
                    "data": []
                },
                "refresh_interval": 60,
                "config": {}
            }
            
            # 合并配置
            merged_config = {**default_config, **widget_config}
            merged_config["widget_id"] = widget_id
            merged_config["dashboard_id"] = dashboard_id
            merged_config["created_at"] = datetime.now().isoformat()
            merged_config["updated_at"] = datetime.now().isoformat()
            
            # 存储小部件
            self.widgets[widget_id] = merged_config
            
            # 添加到看板
            dashboard = self.dashboards[dashboard_id]
            if "widgets" not in dashboard:
                dashboard["widgets"] = []
            
            dashboard["widgets"].append(widget_id)
            dashboard["updated_at"] = datetime.now().isoformat()
            
            logger.info(f"小部件添加成功: {widget_id} -> {dashboard_id}")
            
            return {
                "success": True,
                "widget": merged_config
            }
            
        except Exception as e:
            logger.error(f"添加小部件失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def update_widget_data(self, widget_id: str, data_update: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新小部件数据
        
        Args:
            widget_id: 小部件ID
            data_update: 数据更新
            
        Returns:
            更新结果
        """
        try:
            if widget_id not in self.widgets:
                return {
                    "success": False,
                    "error": "小部件不存在"
                }
            
            widget = self.widgets[widget_id]
            
            # 更新数据源
            if "data_source" in data_update:
                widget["data_source"] = data_update["data_source"]
            
            # 添加时间戳数据点
            if "data_point" in data_update:
                data_point = data_update["data_point"]
                if "timestamp" not in data_point:
                    data_point["timestamp"] = datetime.now().isoformat()
                
                # 添加到数据流
                if widget["data_source"]["type"] == "stream":
                    stream_id = widget["data_source"].get("stream_id")
                    if stream_id:
                        self._add_to_stream(stream_id, data_point)
            
            widget["updated_at"] = datetime.now().isoformat()
            
            logger.debug(f"小部件数据更新: {widget_id}")
            
            return {
                "success": True,
                "widget": widget
            }
            
        except Exception as e:
            logger.error(f"更新小部件数据失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _add_to_stream(self, stream_id: str, data_point: Dict[str, Any]):
        """添加数据点到流"""
        if stream_id not in self.data_streams:
            self.data_streams[stream_id] = deque(maxlen=self.max_data_points)
        
        self.data_streams[stream_id].append(data_point)
    
    def get_dashboard_data(self, dashboard_id: str, include_widget_data: bool = True) -> Dict[str, Any]:
        """
        获取看板数据
        
        Args:
            dashboard_id: 看板ID
            include_widget_data: 是否包含小部件数据
            
        Returns:
            看板数据
        """
        try:
            if dashboard_id not in self.dashboards:
                return {
                    "success": False,
                    "error": "看板不存在"
                }
            
            dashboard = self.dashboards[dashboard_id].copy()
            
            if include_widget_data and "widgets" in dashboard:
                widgets_data = []
                
                for widget_id in dashboard["widgets"]:
                    if widget_id in self.widgets:
                        widget_data = self._get_widget_data(widget_id)
                        widgets_data.append(widget_data)
                
                dashboard["widgets_data"] = widgets_data
            
            return {
                "success": True,
                "dashboard": dashboard
            }
            
        except Exception as e:
            logger.error(f"获取看板数据失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_widget_data(self, widget_id: str) -> Dict[str, Any]:
        """获取小部件数据"""
        widget = self.widgets[widget_id]
        widget_data = widget.copy()
        
        # 根据数据源类型获取数据
        data_source = widget.get("data_source", {})
        source_type = data_source.get("type", "static")
        
        if source_type == "stream":
            stream_id = data_source.get("stream_id")
            if stream_id in self.data_streams:
                widget_data["data"] = list(self.data_streams[stream_id])
        elif source_type == "query":
            # 执行查询获取数据
            query_config = data_source.get("query", {})
            query_result = self._execute_widget_query(query_config)
            widget_data["data"] = query_result.get("data", [])
        else:
            # 静态数据
            widget_data["data"] = data_source.get("data", [])
        
        # 处理时间序列数据
        if widget_data.get("data") and len(widget_data["data"]) > 0:
            widget_data["data"] = self._process_time_series_data(
                widget_data["data"], widget.get("config", {})
            )
        
        return widget_data
    
    def _execute_widget_query(self, query_config: Dict[str, Any]) -> Dict[str, Any]:
        """执行小部件查询"""
        try:
            query_type = query_config.get("type", "entity_metrics")
            time_range = query_config.get("time_range", "1h")
            limit = query_config.get("limit", 100)
            
            # 根据查询类型获取数据
            if query_type == "entity_metrics":
                entity_ids = query_config.get("entity_ids", [])
                metrics = query_config.get("metrics", ["count"])
                
                return self._get_entity_metrics(entity_ids, metrics, time_range, limit)
            
            elif query_type == "relationship_analysis":
                source_entity_id = query_config.get("source_entity_id")
                target_entity_id = query_config.get("target_entity_id")
                analysis_type = query_config.get("analysis_type", "interactions")
                
                return self._get_relationship_analysis(
                    source_entity_id, target_entity_id, analysis_type, time_range, limit
                )
            
            elif query_type == "anomaly_alerts":
                severity = query_config.get("severity", "medium")
                entity_type = query_config.get("entity_type")
                
                return self._get_anomaly_alerts(severity, entity_type, time_range, limit)
            
            else:
                return {
                    "success": True,
                    "data": [],
                    "metadata": {"query_type": query_type}
                }
                
        except Exception as e:
            logger.error(f"执行小部件查询失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "data": []
            }
    
    def _get_entity_metrics(self, entity_ids: List[str], metrics: List[str], 
                          time_range: str, limit: int) -> Dict[str, Any]:
        """获取实体指标"""
        try:
            if not self.temporal_service:
                return {
                    "success": False,
                    "error": "未提供时序数据服务",
                    "data": []
                }
            
            # 解析时间范围
            end_time = datetime.now()
            start_time = self._parse_time_range(time_range, end_time)
            
            data_points = []
            
            for entity_id in entity_ids[:10]:  # 限制实体数量
                # 查询实体历史
                history = self.temporal_service.query_entity_history(
                    entity_id=entity_id,
                    start_time=start_time.isoformat(),
                    end_time=end_time.isoformat(),
                    limit=limit
                )
                
                if history.get("success") and history.get("history"):
                    # 提取指标
                    for record in history["history"]:
                        timestamp = record.get("valid_time", datetime.now().isoformat())
                        properties = record.get("properties", {})
                        
                        point = {"timestamp": timestamp, "entity_id": entity_id}
                        
                        for metric in metrics:
                            if metric == "count":
                                point["value"] = 1
                            elif metric in properties:
                                point[metric] = properties[metric]
                            elif metric == "property_count":
                                point["value"] = len(properties)
                        
                        data_points.append(point)
            
            return {
                "success": True,
                "data": data_points[:limit],
                "metadata": {
                    "entity_count": len(entity_ids[:10]),
                    "time_range": time_range,
                    "data_points": len(data_points)
                }
            }
            
        except Exception as e:
            logger.error(f"获取实体指标失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "data": []
            }
    
    def _parse_time_range(self, time_range: str, base_time: datetime) -> datetime:
        """解析时间范围字符串"""
        time_range = time_range.lower()
        
        if time_range.endswith("h"):
            hours = int(time_range[:-1])
            return base_time - timedelta(hours=hours)
        elif time_range.endswith("d"):
            days = int(time_range[:-1])
            return base_time - timedelta(days=days)
        elif time_range.endswith("w"):
            weeks = int(time_range[:-1])
            return base_time - timedelta(weeks=weeks)
        elif time_range.endswith("m"):
            minutes = int(time_range[:-1])
            return base_time - timedelta(minutes=minutes)
        else:
            # 默认1小时
            return base_time - timedelta(hours=1)
    
    def _get_relationship_analysis(self, source_entity_id: Optional[str],
                                 target_entity_id: Optional[str],
                                 analysis_type: str,
                                 time_range: str,
                                 limit: int) -> Dict[str, Any]:
        """获取关系分析"""
        try:
            # 这里可以调用其他服务进行关系分析
            # 简化版返回示例数据
            
            if not source_entity_id and not target_entity_id:
                return {
                    "success": True,
                    "data": [],
                    "metadata": {"analysis_type": analysis_type}
                }
            
            # 生成示例数据
            data_points = []
            end_time = datetime.now()
            start_time = self._parse_time_range(time_range, end_time)
            
            time_diff = (end_time - start_time).total_seconds()
            
            for i in range(min(20, limit)):
                time_offset = timedelta(seconds=time_diff * i / min(20, limit))
                timestamp = (start_time + time_offset).isoformat()
                
                data_points.append({
                    "timestamp": timestamp,
                    "source_entity": source_entity_id or f"entity_{i}",
                    "target_entity": target_entity_id or f"entity_{(i+1) % 10}",
                    "interaction_count": np.random.randint(1, 10),
                    "strength": np.random.uniform(0.1, 1.0)
                })
            
            return {
                "success": True,
                "data": data_points,
                "metadata": {
                    "analysis_type": analysis_type,
                    "source_entity": source_entity_id,
                    "target_entity": target_entity_id,
                    "data_points": len(data_points)
                }
            }
            
        except Exception as e:
            logger.error(f"获取关系分析失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "data": []
            }
    
    def _get_anomaly_alerts(self, severity: str, entity_type: Optional[str],
                          time_range: str, limit: int) -> Dict[str, Any]:
        """获取异常警报"""
        try:
            if not self.pattern_service:
                return {
                    "success": False,
                    "error": "未提供模式检测服务",
                    "data": []
                }
            
            # 这里可以调用模式检测服务获取异常警报
            # 简化版返回示例数据
            
            # 生成示例警报数据
            data_points = []
            end_time = datetime.now()
            start_time = self._parse_time_range(time_range, end_time)
            
            time_diff = (end_time - start_time).total_seconds()
            
            alert_types = ["value_outlier", "behavior_shift", "population_change"]
            
            for i in range(min(15, limit)):
                time_offset = timedelta(seconds=time_diff * i / min(15, limit))
                timestamp = (start_time + time_offset).isoformat()
                
                alert_type = np.random.choice(alert_types)
                alert_severity = np.random.choice(["low", "medium", "high", "critical"])
                
                if severity == "all" or alert_severity == severity:
                    if entity_type is None or f"entity_{i%5}" == entity_type:
                        data_points.append({
                            "timestamp": timestamp,
                            "alert_type": alert_type,
                            "severity": alert_severity,
                            "entity_id": f"entity_{i%5}",
                            "entity_type": f"type_{(i%5)+1}",
                            "description": f"检测到{alert_type}异常",
                            "value": np.random.uniform(0.5, 5.0)
                        })
            
            return {
                "success": True,
                "data": data_points,
                "metadata": {
                    "severity": severity,
                    "entity_type": entity_type,
                    "data_points": len(data_points)
                }
            }
            
        except Exception as e:
            logger.error(f"获取异常警报失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "data": []
            }
    
    def _process_time_series_data(self, data: List[Dict], config: Dict[str, Any]) -> List[Dict]:
        """处理时间序列数据"""
        if not data:
            return data
        
        processed_data = []
        
        # 检查是否需要聚合
        if config.get("aggregation") and len(data) > 0:
            aggregation_type = config["aggregation"].get("type", "average")
            interval = config["aggregation"].get("interval", "1h")
            
            # 按时间间隔聚合
            aggregated = defaultdict(list)
            
            for point in data:
                timestamp_str = point.get("timestamp")
                if timestamp_str:
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        # 将时间戳对齐到间隔边界
                        if interval == "1h":
                            aligned_time = timestamp.replace(minute=0, second=0, microsecond=0)
                        elif interval == "1d":
                            aligned_time = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
                        elif interval == "1w":
                            # 对齐到周一开始
                            aligned_time = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
                            days_to_monday = timestamp.weekday()
                            aligned_time -= timedelta(days=days_to_monday)
                        else:
                            aligned_time = timestamp
                        
                        aligned_str = aligned_time.isoformat()
                        aggregated[aligned_str].append(point)
                        
                    except Exception:
                        aggregated[timestamp_str].append(point)
            
            # 应用聚合函数
            for time_key, points in aggregated.items():
                aggregated_point = {"timestamp": time_key}
                
                # 收集所有数值型字段
                numeric_fields = defaultdict(list)
                
                for point in points:
                    for key, value in point.items():
                        if key != "timestamp" and isinstance(value, (int, float)):
                            numeric_fields[key].append(value)
                
                # 计算聚合值
                for field, values in numeric_fields.items():
                    if values:
                        if aggregation_type == "average":
                            aggregated_point[field] = np.mean(values)
                        elif aggregation_type == "sum":
                            aggregated_point[field] = np.sum(values)
                        elif aggregation_type == "max":
                            aggregated_point[field] = np.max(values)
                        elif aggregation_type == "min":
                            aggregated_point[field] = np.min(values)
                        elif aggregation_type == "median":
                            aggregated_point[field] = np.median(values)
                
                processed_data.append(aggregated_point)
        else:
            processed_data = data
        
        # 排序数据
        processed_data.sort(key=lambda x: x.get("timestamp", ""))
        
        return processed_data
    
    def _process_time_series_data(self, data: List[Dict], config: Dict[str, Any]) -> List[Dict]:
        """处理时间序列数据"""
        if not data:
            return data
        
        processed_data = []
        
        # 检查是否需要聚合
        if config.get("aggregation") and len(data) > 0:
            aggregation_type = config["aggregation"].get("type", "average")
            interval = config["aggregation"].get("interval", "1h")
            
            # 按时间间隔聚合
            aggregated = defaultdict(list)
            
            for point in data:
                timestamp_str = point.get("timestamp")
                if timestamp_str:
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        # 将时间戳对齐到间隔边界
                        if interval == "1h":
                            aligned_time = timestamp.replace(minute=0, second=0, microsecond=0)
                        elif interval == "1d":
                            aligned_time = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
                        elif interval == "1w":
                            # 对齐到周一开始
                            aligned_time = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
                            days_to_monday = timestamp.weekday()
                            aligned_time -= timedelta(days=days_to_monday)
                        else:
                            aligned_time = timestamp
                        
                        aligned_str = aligned_time.isoformat()
                        aggregated[aligned_str].append(point)
                        
                    except Exception:
                        aggregated[timestamp_str].append(point)
            
            # 应用聚合函数
            for time_key, points in aggregated.items():
                aggregated_point = {"timestamp": time_key}
                
                # 收集所有数值型字段
                numeric_fields = defaultdict(list)
                
                for point in points:
                    for key, value in point.items():
                        if key != "timestamp" and isinstance(value, (int, float)):
                            numeric_fields[key].append(value)
                
                # 计算聚合值
                for field, values in numeric_fields.items():
                    if values:
                        if aggregation_type == "average":
                            aggregated_point[field] = np.mean(values)
                        elif aggregation_type == "sum":
                            aggregated_point[field] = np.sum(values)
                        elif aggregation_type == "max":
                            aggregated_point[field] = np.max(values)
                        elif aggregation_type == "min":
                            aggregated_point[field] = np.min(values)
                        elif aggregation_type == "median":
                            aggregated_point[field] = np.median(values)
                
                processed_data.append(aggregated_point)
        else:
            processed_data = data
        
        # 排序数据
        processed_data.sort(key=lambda x: x.get("timestamp", ""))
        
        return processed_data
    
    def _process_time_series_data(self, data: List[Dict], config: Dict[str, Any]) -> List[Dict]:
        """处理时间序列数据"""
        if not data:
            return data
        
        processed_data = []
        
        # 检查是否需要聚合
        if config.get("aggregation") and len(data) > 0:
            aggregation_type = config["aggregation"].get("type", "average")
            interval = config["aggregation"].get("interval", "1h")
            
            # 按时间间隔聚合
            aggregated = defaultdict(list)
            
            for point in data:
                timestamp_str = point.get("timestamp")
                if timestamp_str:
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        # 将时间戳对齐到间隔边界
                        if interval == "1h":
                            aligned_time = timestamp.replace(minute=0, second=0, microsecond=0)
                        elif interval == "1d":
                            aligned_time = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
                        elif interval == "1w":
                            # 对齐到周一开始
                            aligned_time = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
                            days_to_monday = timestamp.weekday()
                            aligned_time -= timedelta(days=days_to_monday)
                        else:
                            aligned_time = timestamp
                        
                        aligned_str = aligned_time.isoformat()
                        aggregated[aligned_str].append(point)
                        
                    except Exception:
                        aggregated[timestamp_str].append(point)
            
            # 应用聚合函数
            for time_key, points in aggregated.items():
                aggregated_point = {"timestamp": time_key}
                
                # 收集所有数值型字段
                numeric_fields = defaultdict(list)
                
                for point in points:
                    for key, value in point.items():
                        if key != "timestamp" and isinstance(value, (int, float)):
                            numeric_fields[key].append(value)
                
                # 计算聚合值
                for field, values in numeric_fields.items():
                    if values:
                        if aggregation_type == "average":
                            aggregated_point[field] = np.mean(values)
                        elif aggregation_type == "sum":
                            aggregated_point[field] = np.sum(values)
                        elif aggregation_type == "max":
                            aggregated_point[field] = np.max(values)
                        elif aggregation_type == "min":
                            aggregated_point[field] = np.min(values)
                        elif aggregation_type == "median":
                            aggregated_point[field] = np.median(values)
                
                processed_data.append(aggregated_point)
        else:
            processed_data = data
        
        # 排序数据
        processed_data.sort(key=lambda x: x.get("timestamp", ""))
        
        return processed_data
    
    def get_service_metrics(self, metric_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        获取服务性能指标
        
        Args:
            metric_names: 可选指标名称列表
            
        Returns:
            性能指标
        """
        try:
            metrics = {}
            
            # 收集服务指标
            service_metrics = {
                "active_dashboards": len(self.dashboards),
                "active_widgets": len(self.widgets),
                "active_streams": len(self.data_streams),
                "total_data_points": sum(len(stream) for stream in self.data_streams.values()),
                "avg_widgets_per_dashboard": len(self.widgets) / max(1, len(self.dashboards))
            }
            
            # 历史指标趋势
            for metric_name, history in self.metrics_history.items():
                if metric_names is None or metric_name in metric_names:
                    if len(history) > 0:
                        metrics[f"{metric_name}_current"] = history[-1]
                        metrics[f"{metric_name}_avg"] = np.mean(list(history))
                        metrics[f"{metric_name}_min"] = np.min(list(history))
                        metrics[f"{metric_name}_max"] = np.max(list(history))
                        metrics[f"{metric_name}_trend"] = "上升" if len(history) >= 2 and history[-1] > history[-2] else "下降"
            
            # 添加服务指标
            metrics.update(service_metrics)
            
            return {
                "success": True,
                "metrics": metrics,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取服务指标失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def update_metrics(self, metric_name: str, value: float):
        """更新指标"""
        if metric_name not in self.metrics_history:
            self.metrics_history[metric_name] = deque(maxlen=self.max_metrics_history)
        
        self.metrics_history[metric_name].append(value)
        
        # 限制历史记录大小
        if len(self.metrics_history[metric_name]) > self.max_metrics_history:
            self.metrics_history[metric_name].popleft()
    
    def delete_dashboard(self, dashboard_id: str) -> Dict[str, Any]:
        """
        删除看板
        
        Args:
            dashboard_id: 看板ID
            
        Returns:
            删除结果
        """
        try:
            if dashboard_id not in self.dashboards:
                return {
                    "success": False,
                    "error": "看板不存在"
                }
            
            # 删除相关小部件
            dashboard = self.dashboards[dashboard_id]
            if "widgets" in dashboard:
                for widget_id in dashboard["widgets"]:
                    if widget_id in self.widgets:
                        del self.widgets[widget_id]
            
            # 删除看板
            del self.dashboards[dashboard_id]
            
            logger.info(f"看板删除成功: {dashboard_id}")
            
            return {
                "success": True,
                "message": f"看板 {dashboard_id} 已删除"
            }
            
        except Exception as e:
            logger.error(f"删除看板失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_service_info(self) -> Dict[str, Any]:
        """获取服务信息"""
        info = {
            "service_type": "RealtimeDashboardService",
            "active_dashboards": len(self.dashboards),
            "active_widgets": len(self.widgets),
            "active_data_streams": len(self.data_streams),
            "total_data_points": sum(len(stream) for stream in self.data_streams.values()),
            "supported_widget_types": ["chart", "metric", "table", "alert_feed", "map"],
            "supported_chart_types": ["line", "bar", "area", "scatter", "pie", "heatmap"],
            "timestamp": datetime.now().isoformat()
        }
        
        return info
    
    def clear_data(self, session_id: Optional[str] = None):
        """清除数据"""
        if session_id:
            # 删除该会话相关的看板
            dashboards_to_delete = []
            for dashboard_id, dashboard in self.dashboards.items():
                if dashboard.get("session_id") == session_id:
                    dashboards_to_delete.append(dashboard_id)
            
            for dashboard_id in dashboards_to_delete:
                self.delete_dashboard(dashboard_id)
            
            logger.info(f"已清除会话 {session_id} 的数据")
        else:
            self.dashboards.clear()
            self.widgets.clear()
            self.data_streams.clear()
            self.metrics_history.clear()
            logger.info("已清除所有数据")
    
    def subscribe_to_stream(self, session_id: str, stream_id: str) -> Dict[str, Any]:
        """
        订阅数据流
        
        Args:
            session_id: 会话ID
            stream_id: 数据流ID
            
        Returns:
            订阅结果
        """
        try:
            if session_id not in self.subscriptions:
                self.subscriptions[session_id] = set()
            
            self.subscriptions[session_id].add(stream_id)
            
            logger.info(f"会话 {session_id} 订阅了数据流 {stream_id}")
            
            return {
                "success": True,
                "message": f"成功订阅数据流 {stream_id}"
            }
            
        except Exception as e:
            logger.error(f"订阅数据流失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def unsubscribe_from_stream(self, session_id: str, stream_id: str) -> Dict[str, Any]:
        """
        取消订阅数据流
        
        Args:
            session_id: 会话ID
            stream_id: 数据流ID
            
        Returns:
            取消订阅结果
        """
        try:
            if session_id in self.subscriptions and stream_id in self.subscriptions[session_id]:
                self.subscriptions[session_id].remove(stream_id)
                
                logger.info(f"会话 {session_id} 取消订阅了数据流 {stream_id}")
                
                return {
                    "success": True,
                    "message": f"成功取消订阅数据流 {stream_id}"
                }
            else:
                return {
                    "success": False,
                    "error": "未找到订阅记录"
                }
            
        except Exception as e:
            logger.error(f"取消订阅数据流失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_subscriptions(self, session_id: str) -> Dict[str, Any]:
        """
        获取会话的订阅列表
        
        Args:
            session_id: 会话ID
            
        Returns:
            订阅列表
        """
        try:
            subscriptions = list(self.subscriptions.get(session_id, set()))
            
            return {
                "success": True,
                "subscriptions": subscriptions,
                "count": len(subscriptions)
            }
            
        except Exception as e:
            logger.error(f"获取订阅列表失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
