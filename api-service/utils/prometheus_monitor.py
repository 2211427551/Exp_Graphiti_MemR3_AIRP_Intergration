"""
Prometheus监控模块

提供性能指标收集和监控，支持自定义指标和Prometheus集成。

作者: AIRP项目团队
日期: 2026-01-08
"""

import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from functools import wraps
import logging

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    Summary,
    Info
)
from prometheus_client import CONTENT_TYPE_LATEST

from loguru import logger


class PrometheusMetrics:
    """Prometheus指标管理类"""
    
    def __init__(self, app_name: str = "airp_api"):
        """
        初始化Prometheus指标管理器
        
        参数:
            app_name: 应用名称（用于指标前缀）
        """
        self.app_name = app_name
        
        # 创建CollectorRegistry
        self.registry = CollectorRegistry()
        
        # 创建所有指标
        self._init_counters()
        self._init_gauges()
        self._init_histograms()
        self._init_summaries()
        
        logger.info(f"Prometheus监控初始化完成 - 应用: {app_name}")
    
    def _init_counters(self):
        """初始化计数器指标"""
        # API请求计数
        self.api_requests_total = Counter(
            f"{self.app_name}_api_requests_total",
            "Total API requests",
            registry=self.registry
        )
        self.api_requests_success = Counter(
            f"{self.app_name}_api_requests_success",
            "Successful API requests",
            registry=self.registry
        )
        self.api_requests_failed = Counter(
            f"{self.app_name}_api_requests_failed",
            "Failed API requests",
            registry=self.registry
        )
        
        # Graphiti操作计数
        self.graphiti_operations_total = Counter(
            f"{self.app_name}_graphiti_operations_total",
            "Total Graphiti operations",
            registry=self.registry
        )
        self.graphiti_operations_success = Counter(
            f"{self.app_name}_graphiti_operations_success",
            "Successful Graphiti operations",
            registry=self.registry
        )
        
        # 缓存操作计数
        self.cache_hits_total = Counter(
            f"{self.app_name}_cache_hits_total",
            "Total cache hits",
            registry=self.registry
        )
        self.cache_misses_total = Counter(
            f"{self.app_name}_cache_misses_total",
            "Total cache misses",
            registry=self.registry
        )
        
        # 去重操作计数
        self.dedup_operations_total = Counter(
            f"{self.app_name}_dedup_operations_total",
            "Total dedup operations",
            registry=self.registry
        )
        self.dedup_duplicates_found = Counter(
            f"{self.app_name}_dedup_duplicates_found",
            "Duplicates found",
            registry=self.registry
        )
        
        # Token计数
        self.tokens_processed_total = Counter(
            f"{self.app_name}_tokens_processed_total",
            "Total tokens processed",
            registry=self.registry
        )
        
        # 上下文优化计数
        self.context_optimizations_total = Counter(
            f"{self.app_name}_context_optimizations_total",
            "Total context optimizations",
            registry=self.registry
        )
        self.tokens_saved_total = Counter(
            f"{self.app_name}_tokens_saved_total",
            "Total tokens saved",
            registry=self.registry
        )
        
        logger.info("计数器指标初始化完成")
    
    def _init_gauges(self):
        """初始化仪表指标"""
        # API响应时间（秒）
        self.api_response_time = Gauge(
            f"{self.app_name}_api_response_time_seconds",
            "API response time (seconds)",
            registry=self.registry
        )
        
        # Graphiti操作时间（秒）
        self.graphiti_operation_time = Gauge(
            f"{self.app_name}_graphiti_operation_time_seconds",
            "Graphiti operation time (seconds)",
            registry=self.registry
        )
        
        # 缓存响应时间（毫秒）
        self.cache_response_time = Gauge(
            f"{self.app_name}_cache_response_time_milliseconds",
            "Cache response time (milliseconds)",
            registry=self.registry
        )
        
        # Token计数时间（毫秒）
        self.token_count_time = Gauge(
            f"{self.app_name}_token_count_time_milliseconds",
            "Token count time (milliseconds)",
            registry=self.registry
        )
        
        # 去重操作时间（毫秒）
        self.dedup_operation_time = Gauge(
            f"{self.app_name}_dedup_operation_time_milliseconds",
            "Dedup operation time (milliseconds)",
            registry=self.registry
        )
        
        # 上下文优化时间（毫秒）
        self.context_optimization_time = Gauge(
            f"{self.app_name}_context_optimization_time_milliseconds",
            "Context optimization time (milliseconds)",
            registry=self.registry
        )
        
        # 活跃连接数
        self.active_connections = Gauge(
            f"{self.app_name}_active_connections",
            "Active connections",
            registry=self.registry
        )
        
        # 系统内存使用（MB）
        self.system_memory_usage = Gauge(
            f"{self.app_name}_system_memory_usage_megabytes",
            "System memory usage (MB)",
            registry=self.registry
        )
        
        # Redis连接状态
        self.redis_connected = Gauge(
            f"{self.app_name}_redis_connected",
            "Redis connected (1=connected, 0=disconnected)",
            registry=self.registry
        )
        
        logger.info("仪表指标初始化完成")
    
    def _init_histograms(self):
        """初始化直方图指标"""
        # API响应时间分布
        self.api_response_time_histogram = Histogram(
            f"{self.app_name}_api_response_time_seconds",
            "API response time distribution",
            buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=self.registry
        )
        
        # Graphiti操作时间分布
        self.graphiti_operation_time_histogram = Histogram(
            f"{self.app_name}_graphiti_operation_time_seconds",
            "Graphiti operation time distribution",
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
            registry=self.registry
        )
        
        # Token计数分布
        self.token_count_histogram = Histogram(
            f"{self.app_name}_token_count",
            "Token count distribution",
            buckets=[0, 100, 500, 1000, 2000, 5000, 10000],
            registry=self.registry
        )
        
        # 处理的Token数量分布
        self.tokens_per_request_histogram = Histogram(
            f"{self.app_name}_tokens_per_request",
            "Tokens per request distribution",
            buckets=[0, 100, 500, 1000, 2000, 5000, 10000, 20000, 50000],
            registry=self.registry
        )
        
        # 上下文优化Token节省分布
        self.tokens_saved_histogram = Histogram(
            f"{self.app_name}_tokens_saved",
            "Tokens saved by optimization",
            buckets=[0, 10, 50, 100, 200, 500, 1000, 2000],
            registry=self.registry
        )
        
        logger.info("直方图指标初始化完成")
    
    def _init_summaries(self):
        """初始化摘要指标"""
        # API请求摘要
        self.api_requests_summary = Summary(
            f"{self.app_name}_api_requests",
            "API requests summary",
            registry=self.registry
        )
        
        # API响应时间摘要
        self.api_response_time_summary = Summary(
            f"{self.app_name}_api_response_time",
            "API response time summary",
            registry=self.registry
        )
        
        # Graphiti操作摘要
        self.graphiti_operations_summary = Summary(
            f"{self.app_name}_graphiti_operations",
            "Graphiti operations summary",
            registry=self.registry
        )
        
        # 缓存性能摘要
        self.cache_performance_summary = Summary(
            f"{self.app_name}_cache_performance",
            "Cache performance summary",
            registry=self.registry
        )
        
        # Token处理摘要
        self.token_processing_summary = Summary(
            f"{self.app_name}_token_processing",
            "Token processing summary",
            registry=self.registry
        )
        
        # 去重性能摘要
        self.dedup_performance_summary = Summary(
            f"{self.app_name}_dedup_performance",
            "Dedup performance summary",
            registry=self.registry
        )
        
        logger.info("摘要指标初始化完成")
    
    def _init_info_metrics(self):
        """初始化信息指标"""
        self.app_info = Info(
            f"{self.app_name}_info",
            "Application info",
            registry=self.registry,
            info={
                "version": "2.0",
                "name": self.app_name,
                "stage": "performance_optimization"
            }
        )
        
        logger.info("信息指标初始化完成")
    
    def increment_api_request(self, success: bool = True, endpoint: str = ""):
        """
        记录API请求
        
        参数:
            success: 是否成功
            endpoint: API端点名称
        """
        self.api_requests_total.inc()
        
        if success:
            self.api_requests_success.inc()
        else:
            self.api_requests_failed.inc()
        
        # 记录端点
        if endpoint:
            self.api_requests_total.labels(endpoint=endpoint).inc()
            if success:
                self.api_requests_success.labels(endpoint=endpoint).inc()
            else:
                self.api_requests_failed.labels(endpoint=endpoint).inc()
        
        logger.debug(f"API请求: {endpoint}, 成功: {success}")
    
    def increment_graphiti_operation(self, operation_type: str, success: bool = True):
        """
        记录Graphiti操作
        
        参数:
            operation_type: 操作类型（add_episode, search等）
            success: 是否成功
        """
        self.graphiti_operations_total.inc()
        
        if success:
            self.graphiti_operations_success.inc()
        
        self.graphiti_operations_total.labels(operation_type=operation_type).inc()
        
        logger.debug(f"Graphiti操作: {operation_type}, 成功: {success}")
    
    def record_cache_hit(self, cache_type: str = "general"):
        """
        记录缓存命中
        
        参数:
            cache_type: 缓存类型（embedding, token, dedup等）
        """
        self.cache_hits_total.labels(cache_type=cache_type).inc()
        
        logger.debug(f"缓存命中: {cache_type}")
    
    def record_cache_miss(self, cache_type: str = "general"):
        """
        记录缓存未命中
        
        参数:
            cache_type: 缓存类型
        """
        self.cache_misses_total.labels(cache_type=cache_type).inc()
        
        logger.debug(f"缓存未命中: {cache_type}")
    
    def record_dedup_result(self, found_duplicates: int = 0):
        """
        记录去重结果
        
        参数:
            found_duplicates: 找到的重复数
        """
        self.dedup_operations_total.inc()
        self.dedup_duplicates_found.inc(found_duplicates)
        
        logger.debug(f"去重操作，重复数: {found_duplicates}")
    
    def record_tokens_processed(self, token_count: int, token_type: str = "input"):
        """
        记录处理的Token数量
        
        参数:
            token_count: Token数量
            token_type: Token类型
        """
        self.tokens_processed_total.inc(token_count, token_type=token_type)
        
        logger.debug(f"Token处理: {token_type}, 数量: {token_count}")
    
    def record_tokens_saved(self, saved_count: int):
        """
        记录通过优化节省的Token数量
        
        参数:
            saved_count: 节省的Token数量
        """
        self.tokens_saved_total.inc(saved_count)
        self.tokens_saved_histogram.observe(saved_count)
        
        logger.debug(f"Token节省: {saved_count}")
    
    def record_api_response_time(self, duration: float, endpoint: str = ""):
        """
        记录API响应时间
        
        参数:
            duration: 响应时间（秒）
            endpoint: API端点名称
        """
        self.api_response_time.set(duration)
        self.api_response_time_histogram.observe(duration)
        self.api_response_time_summary.observe(duration)
        
        if endpoint:
            self.api_response_time.labels(endpoint=endpoint).set(duration)
        
        logger.debug(f"API响应时间: {duration}秒, 端点: {endpoint}")
    
    def record_graphiti_operation_time(self, duration: float, operation_type: str):
        """
        记录Graphiti操作时间
        
        参数:
            duration: 操作时间（秒）
            operation_type: 操作类型
        """
        self.graphiti_operation_time.set(duration)
        self.graphiti_operation_time_histogram.observe(duration)
        self.graphiti_operations_summary.observe(duration)
        
        self.graphiti_operation_time.labels(operation_type=operation_type).set(duration)
        
        logger.debug(f"Graphiti操作时间: {duration}秒, 类型: {operation_type}")
    
    def record_cache_response_time(self, duration_ms: float, cache_type: str = "general"):
        """
        记录缓存响应时间
        
        参数:
            duration_ms: 响应时间（毫秒）
            cache_type: 缓存类型
        """
        self.cache_response_time.set(duration_ms)
        self.cache_response_time.labels(cache_type=cache_type).set(duration_ms)
        
        logger.debug(f"缓存响应时间: {duration_ms}ms, 类型: {cache_type}")
    
    def record_token_count_time(self, duration_ms: float):
        """
        记录Token计数时间
        
        参数:
            duration_ms: 计数时间（毫秒）
        """
        self.token_count_time.set(duration_ms)
        
        logger.debug(f"Token计数时间: {duration_ms}ms")
    
    def record_dedup_operation_time(self, duration_ms: float):
        """
        记录去重操作时间
        
        参数:
            duration_ms: 操作时间（毫秒）
        """
        self.dedup_operation_time.set(duration_ms)
        
        logger.debug(f"去重操作时间: {duration_ms}ms")
    
    def record_context_optimization_time(self, duration_ms: float):
        """
        记录上下文优化时间
        
        参数:
            duration_ms: 优化时间（毫秒）
        """
        self.context_optimization_time.set(duration_ms)
        self.context_optimizations_total.inc()
        
        logger.debug(f"上下文优化时间: {duration_ms}ms")
    
    def update_active_connections(self, count: int):
        """
        更新活跃连接数
        
        参数:
            count: 连接数
        """
        self.active_connections.set(count)
        
        logger.debug(f"活跃连接数: {count}")
    
    def update_redis_connected(self, connected: bool):
        """
        更新Redis连接状态
        
        参数:
            connected: 是否连接
        """
        self.redis_connected.set(1 if connected else 0)
        
        logger.debug(f"Redis连接: {connected}")
    
    def update_system_memory(self, memory_mb: float):
        """
        更新系统内存使用
        
        参数:
            memory_mb: 内存使用（MB）
        """
        self.system_memory_usage.set(memory_mb)
        
        logger.debug(f"系统内存使用: {memory_mb}MB")
    
    def observe(self, value: float, metric_name: str = ""):
        """
        记录自定义指标值
        
        参数:
            value: 指标值
            metric_name: 指标名称（可选）
        """
        # 使用自定义指标（如果提供了metric_name）
        if metric_name:
            self.api_response_time.labels(custom=metric_name).inc(value)
            logger.debug(f"自定义指标: {metric_name}, 值: {value}")
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """
        获取所有指标的当前值
        
        返回:
            Dict: 指标字典
        """
        metrics = {
            "counters": {
                "api_requests_total": self.api_requests_total._value.get(),
                "api_requests_success": self.api_requests_success._value.get(),
                "api_requests_failed": self.api_requests_failed._value.get(),
                "graphiti_operations_total": self.graphiti_operations_total._value.get(),
                "graphiti_operations_success": self.graphiti_operations_success._value.get(),
                "cache_hits_total": self.cache_hits_total._value.get(),
                "cache_misses_total": self.cache_misses_total._value.get(),
                "dedup_operations_total": self.dedup_operations_total._value.get(),
                "dedup_duplicates_found": self.dedup_duplicates_found._value.get(),
                "tokens_processed_total": self.tokens_processed_total._value.get(),
                "context_optimizations_total": self.context_optimizations_total._value.get(),
                "tokens_saved_total": self.tokens_saved_total._value.get(),
            },
            "gauges": {
                "api_response_time": self.api_response_time._value.get(),
                "graphiti_operation_time": self.graphiti_operation_time._value.get(),
                "cache_response_time": self.cache_response_time._value.get(),
                "token_count_time": self.token_count_time._value.get(),
                "dedup_operation_time": self.dedup_operation_time._value.get(),
                "context_optimization_time": self.context_optimization_time._value.get(),
                "active_connections": self.active_connections._value.get(),
                "system_memory_usage": self.system_memory_usage._value.get(),
                "redis_connected": self.redis_connected._value.get(),
            }
        }
        
        return metrics


class MetricsDecorator:
    """性能指标装饰器"""
    
    def __init__(self, metrics: PrometheusMetrics):
        """
        初始化装饰器
        
        参数:
            metrics: PrometheusMetrics指标管理器
        """
        self.metrics = metrics
    
    def record_api_call(self, endpoint: str = ""):
        """
        API调用装饰器
        
        使用方法：
            @metrics_decorator.record_api_call(endpoint="/chat")
            async def my_function():
                pass
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # 记录开始时间
                start_time = time.time()
                
                try:
                    # 执行函数
                    result = await func(*args, **kwargs)
                    
                    # 记录成功
                    duration = time.time() - start_time
                    self.metrics.increment_api_request(success=True, endpoint=endpoint)
                    self.metrics.record_api_response_time(duration, endpoint=endpoint)
                    
                    return result
                
                except Exception as e:
                    # 记录失败
                    duration = time.time() - start_time
                    self.metrics.increment_api_request(success=False, endpoint=endpoint)
                    
                    raise e
            
            return wrapper
        
        return decorator
    
    def measure_time(self, metric_name: str = "operation_time"):
        """
        测量操作时间装饰器
        
        使用方法：
            @metrics_decorator.measure_time(metric_name="graphiti_search")
            async def my_function():
                pass
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # 记录开始时间
                start_time = time.time()
                
                try:
                    # 执行函数
                    result = await func(*args, **kwargs)
                    
                    # 记录操作时间
                    duration = time.time() - start_time
                    
                    if "response_time" in metric_name.lower():
                        self.metrics.record_api_response_time(duration)
                    else:
                        self.metrics.observe(duration, metric_name)
                    
                    return result
                
                except Exception as e:
                    raise e
            
            return wrapper
        
        return decorator
    
    def measure_cache_operation(self, cache_type: str = "general"):
        """
        缓存操作装饰器
        
        使用方法：
            @metrics_decorator.measure_cache_operation(cache_type="embedding")
            async def get_embedding(text):
                pass
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # 记录开始时间
                start_time = time.time()
                
                try:
                    # 执行函数
                    result = await func(*args, **kwargs)
                    
                    # 记录缓存命中
                    if result is not None:  # 假设返回None表示未命中
                        self.metrics.record_cache_miss(cache_type)
                        duration = time.time() - start_time
                        self.metrics.record_cache_response_time(duration * 1000, cache_type)
                    else:
                        self.metrics.record_cache_hit(cache_type)
                        duration = time.time() - start_time
                        self.metrics.record_cache_response_time(duration * 1000, cache_type)
                    
                    return result
                
                except Exception as e:
                    self.metrics.record_cache_miss(cache_type)
                    raise e
            
            return wrapper
        
        return decorator


# 全局指标实例

prometheus_metrics = PrometheusMetrics(app_name="airp_api")
metrics_decorator = MetricsDecorator(prometheus_metrics)

# 便捷装饰器

record_api_call = metrics_decorator.record_api_call
measure_time = metrics_decorator.measure_time
measure_cache_operation = metrics_decorator.measure_cache_operation