"""
并行处理服务
实现动态通用的工作线程池，任何任务类型都能处理
"""

import logging
import threading
from typing import Dict, Any, List, Optional, Callable, TypeVar, Generic
from dataclasses import dataclass
from datetime import datetime
from queue import Queue, Empty
import time
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, Future
import asyncio
import sys
import os
from enum import Enum

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    from config.settings import settings
except ImportError:
    # 向后兼容
    raise

logger = logging.getLogger(__name__)

T = TypeVar('T')
R = TypeVar('R')


class TaskPriority(Enum):
    """任务优先级"""
    HIGH = 1
    NORMAL = 2
    LOW = 3


@dataclass
class Task(Generic[T, R]):
    """任务定义"""
    task_id: str
    task_type: str
    payload: T
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: datetime = None
    timeout_seconds: int = 30
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class TaskResult(Generic[R]):
    """任务结果"""
    task_id: str
    success: bool
    result: Optional[R] = None
    error: Optional[str] = None
    processing_time_ms: float = 0.0
    completed_at: Optional[datetime] = None


class GenericWorker:
    """通用工作线程"""
    
    def __init__(self, worker_id: int, task_queue: Queue, result_queue: Queue):
        self.worker_id = worker_id
        self.task_queue = task_queue
        self.result_queue = result_queue
        self.is_running = True
        
    def run(self):
        """工作线程主循环"""
        logger.debug(f"工作线程 {self.worker_id} 启动")
        
        while self.is_running:
            try:
                # 从队列获取任务（阻塞式，最多等待1秒）
                task = self.task_queue.get(timeout=1.0)
                
                if task is None:  # 结束信号
                    logger.debug(f"工作线程 {self.worker_id} 收到结束信号")
                    break
                
                start_time = time.time()
                
                try:
                    # 处理任务（任何类型）
                    result = self._process_task(task)
                    
                    task_result = TaskResult(
                        task_id=task.task_id,
                        success=True,
                        result=result,
                        processing_time_ms=(time.time() - start_time) * 1000,
                        completed_at=datetime.now()
                    )
                    
                except Exception as e:
                    logger.error(f"工作线程 {self.worker_id} 处理任务失败: {str(e)}")
                    
                    task_result = TaskResult(
                        task_id=task.task_id,
                        success=False,
                        error=str(e),
                        processing_time_ms=(time.time() - start_time) * 1000,
                        completed_at=datetime.now()
                    )
                
                # 将结果放入结果队列
                self.result_queue.put(task_result)
                
                # 标记任务完成
                self.task_queue.task_done()
                
            except Empty:
                # 队列为空，继续循环
                continue
            except Exception as e:
                logger.error(f"工作线程 {self.worker_id} 发生未知错误: {str(e)}")
                time.sleep(0.1)
        
        logger.debug(f"工作线程 {self.worker_id} 停止")
    
    def _process_task(self, task: Task) -> Any:
        """处理任务的具体实现"""
        task_type = task.task_type
        
        # 根据任务类型分派处理
        if task_type == "entity_extraction":
            return self._process_entity_extraction(task.payload)
        elif task_type == "relationship_identification":
            return self._process_relationship_identification(task.payload)
        elif task_type == "semantic_analysis":
            return self._process_semantic_analysis(task.payload)
        elif task_type == "deduplication_check":
            return self._process_deduplication_check(task.payload)
        elif task_type == "text_parsing":
            return self._process_text_parsing(task.payload)
        else:
            # 通用处理：直接返回payload作为结果
            logger.warning(f"未知任务类型: {task_type}, 使用通用处理")
            return {
                "task_type": task_type,
                "payload": task.payload,
                "processed_at": datetime.now().isoformat()
            }
    
    def _process_entity_extraction(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """处理实体提取任务"""
        text = payload.get("text", "")
        session_id = payload.get("session_id", "")
        
        # 这里应该调用实际的实体提取逻辑
        # 目前返回模拟结果
        return {
            "entities": {
                "persons": ["用户A", "用户B"],
                "locations": ["城市X", "区域Y"],
                "organizations": ["公司Z"]
            },
            "processing_time": f"{len(text)} chars processed",
            "session_id": session_id
        }
    
    def _process_relationship_identification(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """处理关系识别任务"""
        entities = payload.get("entities", {})
        text = payload.get("text", "")
        
        # 这里应该调用实际的关系识别逻辑
        # 目前返回模拟结果
        relationships = []
        
        if "persons" in entities and len(entities["persons"]) >= 2:
            relationships.append({
                "source": entities["persons"][0],
                "target": entities["persons"][1],
                "type": "HAS_RELATION_WITH",
                "subtype": "friend",
                "confidence": 0.8
            })
        
        return {
            "relationships": relationships,
            "text_length": len(text)
        }
    
    def _process_semantic_analysis(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """处理语义分析任务"""
        text = payload.get("text", "")
        
        # 这里应该调用实际的语义分析逻辑
        # 目前返回模拟结果
        return {
            "sentiment": "neutral",
            "topics": ["对话", "关系"],
            "complexity_score": min(len(text) / 100, 1.0),
            "key_concepts": ["互动", "交流"]
        }
    
    def _process_deduplication_check(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """处理去重检查任务"""
        entity_data = payload.get("entity_data", {})
        
        # 这里应该调用实际的去重检查逻辑
        # 目前返回模拟结果
        return {
            "is_duplicate": False,
            "similarity_score": 0.2,
            "matched_entity": None
        }
    
    def _process_text_parsing(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """处理文本解析任务"""
        text = payload.get("text", "")
        
        # 这里应该调用实际的文本解析逻辑
        # 目前返回模拟结果
        return {
            "parsed_blocks": 3,
            "tags_found": ["对话", "场景"],
            "structure_type": "dialogue"
        }
    
    def stop(self):
        """停止工作线程"""
        self.is_running = False


class GenericWorkerPool:
    """通用工作线程池"""
    
    def __init__(self, num_workers: int = 4):
        """初始化工作线程池"""
        self.num_workers = num_workers
        self.task_queue = Queue()
        self.result_queue = Queue()
        self.workers = []
        self.worker_threads = []
        
        # 统计信息
        self.task_counter = 0
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.total_processing_time_ms = 0.0
        
        # 任务映射
        self.pending_tasks = {}  # task_id -> task
        self.completed_task_results = {}  # task_id -> result
        
        logger.info(f"通用工作线程池初始化: {num_workers} 个工作线程")
    
    def start(self):
        """启动工作线程池"""
        # 创建工作线程
        for i in range(self.num_workers):
            worker = GenericWorker(i, self.task_queue, self.result_queue)
            self.workers.append(worker)
            
            # 创建并启动工作线程
            worker_thread = threading.Thread(
                target=worker.run,
                name=f"GenericWorker-{i}"
            )
            worker_thread.daemon = True
            worker_thread.start()
            self.worker_threads.append(worker_thread)
        
        logger.info(f"工作线程池已启动: {self.num_workers} 个工作线程运行中")
    
    def submit_task(self, task_type: str, payload: Any, 
                   priority: TaskPriority = TaskPriority.NORMAL) -> str:
        """提交任务到线程池"""
        task_id = f"task_{self.task_counter}_{int(time.time())}"
        self.task_counter += 1
        
        task = Task(
            task_id=task_id,
            task_type=task_type,
            payload=payload,
            priority=priority,
            created_at=datetime.now()
        )
        
        # 将任务放入队列（根据优先级）
        self.task_queue.put(task)
        self.pending_tasks[task_id] = task
        
        logger.debug(f"提交任务: {task_id} ({task_type}), 优先级: {priority}")
        
        return task_id
    
    def get_result(self, task_id: str, timeout_seconds: float = 5.0) -> Optional[TaskResult]:
        """获取任务结果"""
        # 检查是否已有结果
        if task_id in self.completed_task_results:
            return self.completed_task_results[task_id]
        
        # 检查结果队列
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            try:
                result = self.result_queue.get(timeout=0.1)
                
                # 记录结果
                self.completed_task_results[result.task_id] = result
                
                # 更新统计信息
                self.completed_tasks += 1
                self.total_processing_time_ms += result.processing_time_ms
                
                if not result.success:
                    self.failed_tasks += 1
                
                # 如果是目标任务，返回结果
                if result.task_id == task_id:
                    return result
                
            except Empty:
                continue
            except Exception as e:
                logger.error(f"获取任务结果时发生错误: {str(e)}")
                break
        
        # 超时
        logger.warning(f"获取任务结果超时: {task_id}")
        return None
    
    def batch_submit(self, tasks: List[Dict[str, Any]]) -> List[str]:
        """批量提交任务"""
        task_ids = []
        
        for task_spec in tasks:
            task_type = task_spec.get("type", "generic")
            payload = task_spec.get("payload", {})
            priority_value = task_spec.get("priority", "normal")
            
            # 转换优先级字符串为枚举
            priority = TaskPriority.NORMAL
            if priority_value == "high":
                priority = TaskPriority.HIGH
            elif priority_value == "low":
                priority = TaskPriority.LOW
            
            task_id = self.submit_task(task_type, payload, priority)
            task_ids.append(task_id)
        
        logger.debug(f"批量提交 {len(tasks)} 个任务")
        return task_ids
    
    def batch_get_results(self, task_ids: List[str], 
                         timeout_seconds: float = 10.0) -> Dict[str, Optional[TaskResult]]:
        """批量获取任务结果"""
        results = {}
        remaining_task_ids = set(task_ids)
        
        start_time = time.time()
        
        while remaining_task_ids and time.time() - start_time < timeout_seconds:
            # 检查已完成的结果
            for task_id in list(remaining_task_ids):
                if task_id in self.completed_task_results:
                    results[task_id] = self.completed_task_results[task_id]
                    remaining_task_ids.remove(task_id)
            
            # 如果还有未完成的任务，等待新结果
            if remaining_task_ids:
                try:
                    result = self.result_queue.get(timeout=0.5)
                    
                    # 记录结果
                    self.completed_task_results[result.task_id] = result
                    
                    # 更新统计信息
                    self.completed_tasks += 1
                    self.total_processing_time_ms += result.processing_time_ms
                    
                    if not result.success:
                        self.failed_tasks += 1
                    
                    # 如果是目标任务，添加到结果
                    if result.task_id in remaining_task_ids:
                        results[result.task_id] = result
                        remaining_task_ids.remove(result.task_id)
                        
                except Empty:
                    continue
                except Exception as e:
                    logger.error(f"批量获取结果时发生错误: {str(e)}")
        
        # 设置超时的任务结果为None
        for task_id in remaining_task_ids:
            results[task_id] = None
        
        return results
    
    def monitor_progress(self) -> Dict[str, Any]:
        """监控线程池进度"""
        # 统计当前队列大小
        queue_size = self.task_queue.qsize()
        
        # 计算统计信息
        success_rate = 0.0
        if self.completed_tasks > 0:
            success_rate = (self.completed_tasks - self.failed_tasks) / self.completed_tasks
        
        avg_processing_time = 0.0
        if self.completed_tasks > 0:
            avg_processing_time = self.total_processing_time_ms / self.completed_tasks
        
        status = {
            "workers_count": self.num_workers,
            "queue_size": queue_size,
            "pending_tasks": len(self.pending_tasks) - self.completed_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "success_rate": f"{success_rate:.2%}",
            "avg_processing_time_ms": f"{avg_processing_time:.2f}",
            "total_processing_time_ms": f"{self.total_processing_time_ms:.2f}",
            "task_counter": self.task_counter
        }
        
        return status
    
    def resize_pool(self, new_num_workers: int):
        """调整线程池大小"""
        if new_num_workers == self.num_workers:
            logger.info("线程池大小无变化")
            return
        
        logger.info(f"调整线程池大小: {self.num_workers} -> {new_num_workers}")
        
        if new_num_workers < self.num_workers:
            # 减少工作线程
            workers_to_remove = self.num_workers - new_num_workers
            
            for i in range(workers_to_remove):
                if self.workers:
                    worker = self.workers.pop()
                    worker.stop()
        
        elif new_num_workers > self.num_workers:
            # 增加工作线程
            workers_to_add = new_num_workers - self.num_workers
            
            for i in range(workers_to_add):
                worker_id = self.num_workers + i
                worker = GenericWorker(worker_id, self.task_queue, self.result_queue)
                self.workers.append(worker)
                
                # 创建并启动新工作线程
                worker_thread = threading.Thread(
                    target=worker.run,
                    name=f"GenericWorker-{worker_id}"
                )
                worker_thread.daemon = True
                worker_thread.start()
                self.worker_threads.append(worker_thread)
        
        self.num_workers = new_num_workers
        logger.info(f"线程池大小调整完成: {self.num_workers} 个工作线程")
    
    def stop(self, wait_for_completion: bool = True):
        """停止工作线程池"""
        logger.info("停止工作线程池...")
        
        # 发送停止信号
        for _ in range(self.num_workers):
            self.task_queue.put(None)
        
        # 等待工作线程结束
        if wait_for_completion:
            for thread in self.worker_threads:
                thread.join(timeout=5.0)
        
        # 清理
        self.workers.clear()
        self.worker_threads.clear()
        
        logger.info("工作线程池已停止")


class ParallelProcessingService:
    """并行处理服务"""
    
    def __init__(self, initial_workers: int = 4):
        """初始化并行处理服务"""
        self.worker_pool = GenericWorkerPool(num_workers=initial_workers)
        self.worker_pool.start()
        
        # 异步支持
        self.executor = ThreadPoolExecutor(max_workers=initial_workers)
        
        logger.info(f"并行处理服务初始化: {initial_workers} 个工作线程")
    
    def process_batch(self, task_specs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """处理批量任务"""
        logger.info(f"开始处理批量任务: {len(task_specs)} 个任务")
        start_time = time.time()
        
        # 提交所有任务
        task_ids = self.worker_pool.batch_submit(task_specs)
        
        # 等待所有任务完成（动态超时）
        total_timeout = len(task_specs) * 2  # 每个任务2秒
        results = self.worker_pool.batch_get_results(task_ids, timeout_seconds=total_timeout)
        
        # 统计结果
        successful_results = []
        failed_results = []
        
        for task_id, result in results.items():
            if result and result.success:
                successful_results.append(result)
            else:
                failed_results.append({
                    "task_id": task_id,
                    "error": result.error if result else "timeout"
                })
        
        # 生成统计信息
        stats = self.worker_pool.monitor_progress()
        
        # 计算成功率
        success_rate = 0.0
        if len(task_specs) > 0:
            success_rate = len(successful_results) / len(task_specs)
        
        total_processing_ms = (time.time() - start_time) * 1000
        
        return {
            "total_tasks": len(task_specs),
            "successful_tasks": len(successful_results),
            "failed_tasks": len(failed_results),
            "success_rate": f"{success_rate:.2%}",
            "total_processing_time_ms": stats.get("total_processing_time_ms", "0.0"),
            "avg_processing_time_ms": stats.get("avg_processing_time_ms", "0.0"),
            "queue_size": stats.get("queue_size", 0),
            "processing_time_ms": f"{total_processing_ms:.2f}",
            "results_summary": {
                "successful": len(successful_results),
                "failed": len(failed_results),
                "pending": len(task_specs) - len(successful_results) - len(failed_results)
            }
        }
    
    async def async_process_batch(self, task_specs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """异步处理批量任务"""
        logger.info(f"开始异步处理批量任务: {len(task_specs)} 个任务")
        
        # 使用异步执行器处理任务
        loop = asyncio.get_event_loop()
        
        # 创建异步任务
        async_tasks = []
        for task_spec in task_specs:
            task_type = task_spec.get("type", "generic")
            payload = task_spec.get("payload", {})
            
            # 创建异步任务
            async_task = loop.run_in_executor(
                self.executor,
                self._process_async_task,
                task_type,
                payload
            )
            async_tasks.append(async_task)
        
        # 等待所有异步任务完成
        results = await asyncio.gather(*async_tasks, return_exceptions=True)
        
        # 统计结果
        successful_results = []
        failed_results = []
        
        for i, result in enumerate(results):
            task_spec = task_specs[i]
            
            if isinstance(result, Exception):
                failed_results.append({
                    "task_spec": task_spec,
                    "error": str(result)
                })
            elif isinstance(result, dict) and result.get("success", False):
                successful_results.append(result)
            else:
                failed_results.append({
                    "task_spec": task_spec,
                    "error": "Unknown error"
                })
        
        return {
            "total_tasks": len(task_specs),
            "successful_tasks": len(successful_results),
            "failed_tasks": len(failed_results),
            "success_rate": f"{len(successful_results) / len(task_specs):.2%}" if task_specs else "0%",
            "results": successful_results[:10] if len(successful_results) > 10 else successful_results
        }
    
    def _process_async_task(self, task_type: str, payload: Any) -> Dict[str, Any]:
        """处理异步任务（优化版）"""
        try:
            start_time = time.time()
            
            # 根据任务类型分派处理
            if task_type == "entity_extraction":
                result = self._extract_entities_async(payload)
            elif task_type == "relationship_analysis":
                result = self._analyze_relationships_async(payload)
            elif task_type == "semantic_processing":
                result = self._process_semantics_async(payload)
            elif task_type == "sillytavern_parsing":
                # 支持SillyTavern解析任务
                from .sillytavern_parser import SillyTavernParser
                parser = SillyTavernParser()
                text = payload.get("text", "")
                session_id = payload.get("session_id", "")
                result = parser.parse_sillytavern_input(text, session_id)
            elif task_type == "deduplication":
                # 支持去重任务
                from .deduplication_service import DeduplicationService
                service = DeduplicationService()
                result = service.check_and_deduplicate(payload)
            else:
                # 通用任务处理
                result = {
                    "success": True,
                    "task_type": task_type,
                    "payload": payload,
                    "processed": True,
                    "timestamp": datetime.now().isoformat()
                }
            
            # 添加处理时间统计
            result["processing_time_ms"] = (time.time() - start_time) * 1000
            
            return result
            
        except Exception as e:
            logger.error(f"处理异步任务失败: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "task_type": task_type,
                "processing_time_ms": 0.0
            }
    
    def _extract_entities_async(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """异步实体提取"""
        text = payload.get("text", "")
        
        # 模拟处理
        time.sleep(0.01 * min(len(text), 100))  # 模拟处理时间
        
        return {
            "success": True,
            "entities_count": min(len(text.split()), 10),
            "processing_time": f"{len(text)} chars"
        }
    
    def _analyze_relationships_async(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """异步关系分析"""
        entities = payload.get("entities", [])
        
        # 模拟处理
        time.sleep(0.05 * min(len(entities), 20))
        
        return {
            "success": True,
            "relationships_found": min(len(entities) * 2, 50)
        }
    
    def _process_semantics_async(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """异步语义处理"""
        text = payload.get("text", "")
        
        # 模拟处理
        time.sleep(0.02 * min(len(text), 200))
        
        return {
            "success": True,
            "semantic_score": min(len(text) / 500, 1.0),
            "key_topics": ["对话", "交互"]
        }
    
    def get_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        stats = self.worker_pool.monitor_progress()
        
        return {
            "service": "ParallelProcessingService",
            "status": "running",
            "worker_pool": stats,
            "async_executor": {
                "max_workers": self.executor._max_workers,
                "active_threads": threading.active_count(),
                "pool_size": self.executor._threads
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def resize_workers(self, new_size: int):
        """调整工作线程数量"""
        logger.info(f"调整工作线程数量: {self.worker_pool.num_workers} -> {new_size}")
        self.worker_pool.resize_pool(new_size)
        self.executor._max_workers = new_size
    
    def shutdown(self, wait_for_completion: bool = True):
        """关闭服务"""
        logger.info("关闭并行处理服务...")
        
        # 停止工作线程池
        self.worker_pool.stop(wait_for_completion)
        
        # 关闭异步执行器
        self.executor.shutdown(wait=wait_for_completion)
        
        logger.info("并行处理服务已关闭")


class ProcessingManager:
    """处理管理器（优化版）"""
    
    def __init__(self):
        """初始化处理管理器"""
        self.parallel_service = ParallelProcessingService()
        
        # 根据设置决定是否启用去重服务
        if hasattr(settings, 'DEEPSEEK_API_KEY') and settings.DEEPSEEK_API_KEY:
            try:
                from .deduplication_service import DeduplicationService
                self.deduplication_service = DeduplicationService()
            except ImportError:
                logger.warning("无法导入去重服务，去重功能将不可用")
                self.deduplication_service = None
        else:
            self.deduplication_service = None
        
        # 任务类型映射（扩展支持更多任务类型）
        self.task_handlers = {
            "entity_extraction": self._handle_entity_extraction,
            "relationship_analysis": self._handle_relationship_analysis,
            "semantic_processing": self._handle_semantic_processing,
            "text_parsing": self._handle_text_parsing,
            "sillytavern_parsing": self._handle_sillytavern_parsing,
            "deduplication": self._handle_deduplication,
            "complexity_analysis": self._handle_complexity_analysis
        }
        
        # 性能统计
        self.task_statistics = {
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "total_processing_time_ms": 0.0
        }
        
        logger.info("处理管理器初始化完成（优化版）")
    
    def process_single(self, task_type: str, payload: Dict[str, Any], 
                      priority: str = "normal") -> Dict[str, Any]:
        """处理单个任务（优化版）"""
        logger.debug(f"处理单个任务: {task_type}, 优先级: {priority}")
        
        # 更新任务统计
        self.task_statistics["total_tasks"] += 1
        
        # 检查任务类型
        if task_type not in self.task_handlers:
            error_msg = f"未知任务类型: {task_type}"
            logger.warning(error_msg)
            self.task_statistics["failed_tasks"] += 1
            
            return {
                "success": False,
                "error": error_msg,
                "task_type": task_type,
                "processing_time_ms": 0.0
            }
        
        try:
            start_time = time.time()
            
            # 调用相应的处理器
            handler = self.task_handlers[task_type]
            result = handler(payload)
            
            # 添加处理时间
            processing_time_ms = (time.time() - start_time) * 1000
            result["processing_time_ms"] = processing_time_ms
            
            # 更新统计
            if result.get("success", False):
                self.task_statistics["successful_tasks"] += 1
            else:
                self.task_statistics["failed_tasks"] += 1
            
            self.task_statistics["total_processing_time_ms"] += processing_time_ms
            
            # 添加优先级信息
            result["priority"] = priority
            
            return result
            
        except Exception as e:
            error_msg = f"处理任务失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.task_statistics["failed_tasks"] += 1
            
            return {
                "success": False,
                "error": error_msg,
                "task_type": task_type,
                "processing_time_ms": 0.0,
                "priority": priority
            }
    
    def _handle_entity_extraction(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """处理实体提取"""
        text = payload.get("text", "")
        session_id = payload.get("session_id", "")
        
        # 提交到并行处理服务
        task_spec = {
            "type": "entity_extraction",
            "payload": payload,
            "priority": "normal"
        }
        
        batch_result = self.parallel_service.process_batch([task_spec])
        
        if batch_result.get("successful_tasks", 0) > 0:
            return {
                "success": True,
                "task_type": "entity_extraction",
                "result": batch_result
            }
        else:
            return {
                "success": False,
                "error": "实体提取任务失败",
                "task_type": "entity_extraction"
            }
    
    def _handle_relationship_analysis(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """处理关系分析"""
        # 提交到并行处理服务
        task_spec = {
            "type": "relationship_analysis",
            "payload": payload,
            "priority": "normal"
        }
        
        batch_result = self.parallel_service.process_batch([task_spec])
        
        if batch_result.get("successful_tasks", 0) > 0:
            return {
                "success": True,
                "task_type": "relationship_analysis",
                "result": batch_result
            }
        else:
            return {
                "success": False,
                "error": "关系分析任务失败",
                "task_type": "relationship_analysis"
            }
    
    def _handle_semantic_processing(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """处理语义处理"""
        # 提交到并行处理服务
        task_spec = {
            "type": "semantic_processing",
            "payload": payload,
            "priority": "normal"
        }
        
        batch_result = self.parallel_service.process_batch([task_spec])
        
        if batch_result.get("successful_tasks", 0) > 0:
            return {
                "success": True,
                "task_type": "semantic_processing",
                "result": batch_result
            }
        else:
            return {
                "success": False,
                "error": "语义处理任务失败",
                "task_type": "semantic_processing"
            }
    
    def _handle_text_parsing(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """处理文本解析"""
        # 提交到并行处理服务
        task_spec = {
            "type": "text_parsing",
            "payload": payload,
            "priority": "normal"
        }
        
        batch_result = self.parallel_service.process_batch([task_spec])
        
        if batch_result.get("successful_tasks", 0) > 0:
            return {
                "success": True,
                "task_type": "text_parsing",
                "result": batch_result
            }
        else:
            return {
                "success": False,
                "error": "文本解析任务失败",
                "task_type": "text_parsing"
            }
    
    def get_processing_status(self) -> Dict[str, Any]:
        """获取处理状态（优化版）"""
        service_status = self.parallel_service.get_status()
        
        # 计算成功率
        success_rate = 0.0
        if self.task_statistics["total_tasks"] > 0:
            success_rate = self.task_statistics["successful_tasks"] / self.task_statistics["total_tasks"]
        
        # 计算平均处理时间
        avg_processing_time = 0.0
        if self.task_statistics["successful_tasks"] + self.task_statistics["failed_tasks"] > 0:
            avg_processing_time = self.task_statistics["total_processing_time_ms"] / (
                self.task_statistics["successful_tasks"] + self.task_statistics["failed_tasks"]
            )
        
        return {
            "manager_status": "active",
            "timestamp": datetime.now().isoformat(),
            "statistics": {
                "total_tasks": self.task_statistics["total_tasks"],
                "successful_tasks": self.task_statistics["successful_tasks"],
                "failed_tasks": self.task_statistics["failed_tasks"],
                "success_rate": f"{success_rate:.2%}",
                "total_processing_time_ms": round(self.task_statistics["total_processing_time_ms"], 2),
                "avg_processing_time_ms": round(avg_processing_time, 2)
            },
            "parallel_service": service_status,
            "deduplication_available": self.deduplication_service is not None,
            "supported_task_types": list(self.task_handlers.keys()),
            "active_handlers": len(self.task_handlers),
            "thread_pool_info": {
                "workers": self.parallel_service.worker_pool.num_workers,
                "queue_size": service_status.get("worker_pool", {}).get("queue_size", 0)
            }
        }
    
    def shutdown(self, wait_for_completion: bool = True):
        """关闭管理器（优化版）"""
        logger.info("关闭处理管理器...")
        
        # 记录关闭前的统计信息
        stats = self.get_processing_status()
        logger.info(f"最终任务统计: {stats['statistics']}")
        
        # 关闭并行服务
        self.parallel_service.shutdown(wait_for_completion)
        
        # 关闭去重服务（如果存在）
        if self.deduplication_service and hasattr(self.deduplication_service, 'shutdown'):
            try:
                self.deduplication_service.shutdown()
            except Exception as e:
                logger.warning(f"关闭去重服务时出错: {str(e)}")
        
        # 清理资源
        self.task_handlers.clear()
        
        logger.info("处理管理器已关闭")
