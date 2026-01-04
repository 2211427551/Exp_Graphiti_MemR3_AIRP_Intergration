#!/usr/bin/env python3
"""
增强的Graphiti时序知识图谱服务

基于graphiti_core的封装，提供：
1. graphiti_core的完整双时序功能
2. 性能优化和缓存机制
3. 统一的API接口
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Union
import json
import uuid
from datetime import datetime, timezone
import time
import hashlib
from functools import lru_cache
import os
import sys

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 导入配置
try:
    from api_service.config.settings import settings
except ImportError:
    try:
        config_path = os.path.join(project_root, 'config', 'settings.py')
        import importlib.util
        spec = importlib.util.spec_from_file_location("settings", config_path)
        settings_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(settings_module)
        settings = settings_module.settings
    except Exception as e:
        print(f"导入配置失败: {e}")
        class DefaultSettings:
            TEMPORAL_QUERY_CACHE_TTL = 300
            TEMPORAL_QUERY_CACHE_SIZE = 10000
        settings = DefaultSettings()

logger = logging.getLogger(__name__)


class EnhancedGraphitiService:
    """增强的Graphiti服务，基于graphiti_core"""
    
    def __init__(self, driver=None):
        """初始化增强Graphiti服务"""
        # graphiti_core实例
        self._graphiti_core = None
        self._graphiti_core_enabled = False
        
        # 尝试初始化graphiti_core
        try:
            self._init_graphiti_core()
            logger.info("✅ graphiti_core初始化成功")
        except Exception as e:
            logger.warning(f"⚠️  graphiti_core初始化失败: {str(e)}")
            logger.info("💡 提示: 请确保Neo4j正在运行，且环境变量配置正确")
        
        # 性能优化缓存
        self._query_cache = {}
        self._cache_hits = 0
        self._cache_misses = 0
        
        logger.info("✅ 增强Graphiti服务初始化完成")
    
    def _init_graphiti_core(self):
        """初始化graphiti_core"""
        try:
            from graphiti_core import Graphiti
            from graphiti_core.llm_client import LLMClient
            
            # 从环境变量获取Neo4j连接信息
            neo4j_uri = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
            neo4j_user = os.environ.get('NEO4J_USER', 'neo4j')
            neo4j_password = os.environ.get('NEO4J_PASSWORD', 'password')
            
            # 获取OpenAI API配置
            openai_api_key = os.environ.get('OPENAI_API_KEY', '')
            openai_base_url = os.environ.get('OPENAI_BASE_URL', None)
            openai_model = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')
            
            logger.info(f"🔗 连接Neo4j: {neo4j_uri}")
            if openai_base_url:
                logger.info(f"🤖 使用自定义API端点: {openai_base_url}")
                logger.info(f"📦 使用LLM模型: {openai_model}")
            
            # 初始化graphiti_core，传递OpenAI API密钥
            if openai_api_key:
                # 先设置环境变量（graphiti_core会读取）
                os.environ['OPENAI_API_KEY'] = openai_api_key
                if openai_base_url:
                    os.environ['OPENAI_BASE_URL'] = openai_base_url
                os.environ['OPENAI_MODEL'] = openai_model
            
            # 创建Graphiti实例，配置LLM
            self._graphiti_core = Graphiti(neo4j_uri, neo4j_user, neo4j_password)
            self._graphiti_core_enabled = True
            
        except ImportError as e:
            raise ImportError(f"❌ 无法导入graphiti_core: {str(e)}。请运行: pip install graphiti-core")
        except Exception as e:
            raise Exception(f"❌ 初始化graphiti_core失败: {str(e)}")
    
    # ========== graphiti_core Episode管理 ==========
    
    def add_episode_graphiti_core(self, content: Union[str, Dict[str, Any]],
                                  episode_type: str = "text",
                                  name: Optional[str] = None,
                                  source: Optional[str] = None,
                                  source_description: Optional[str] = None,
                                  reference_time: Optional[Union[str, datetime]] = None,
                                  metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        使用graphiti_core添加Episode
        
        Args:
            content: Episode内容（文本或JSON）
            episode_type: Episode类型（text/json/message）
            name: Episode名称（可选）
            source: 来源标识
            source_description: 来源描述
            reference_time: 参考时间
            metadata: 元数据（可选）
            
        Returns:
            添加结果
        """
        if not self._graphiti_core_enabled:
            return {
                "success": False,
                "error": "graphiti_core未启用或初始化失败"
            }
        
        try:
            from graphiti_core.nodes import EpisodeType
            
            # 转换类型
            if episode_type == "text":
                episode_type_enum = EpisodeType.text
                episode_body = content
            elif episode_type == "json":
                episode_type_enum = EpisodeType.json
                if isinstance(content, dict):
                    episode_body = json.dumps(content)
                else:
                    episode_body = str(content)
            elif episode_type == "message":
                episode_type_enum = EpisodeType.message
                episode_body = json.dumps(content) if isinstance(content, dict) else str(content)
            else:
                episode_type_enum = EpisodeType.text
                episode_body = str(content)
            
            # 处理时间
            if reference_time:
                if isinstance(reference_time, str):
                    ref_time = datetime.fromisoformat(reference_time.replace('Z', '+00:00'))
                else:
                    ref_time = reference_time
            else:
                ref_time = datetime.now(timezone.utc)
            
            # 生成Episode名称
            episode_name = name or f"episode_{uuid.uuid4().hex[:8]}"
            
            # 异步执行添加Episode
            async def _add_episode():
                # 构建参数字典
                episode_params = {
                    "name": episode_name,
                    "episode_body": episode_body,
                    "source": episode_type_enum,
                    "source_description": source_description or "User input via EnhancedGraphitiService",
                    "reference_time": ref_time
                }
                
                # 只有当metadata不为None时才添加
                if metadata is not None:
                    episode_params["metadata"] = metadata
                
                return await self._graphiti_core.add_episode(**episode_params)
            
            result = asyncio.run(_add_episode())
            
            if result:
                return {
                    "success": True,
                    "episode_uuid": str(result.uuid) if hasattr(result, 'uuid') else None,
                    "name": episode_name,
                    "message": "Episode添加成功"
                }
            else:
                return {
                    "success": False,
                    "error": "Episode添加失败，返回结果为空"
                }
                
        except Exception as e:
            logger.error(f"❌ 添加Episode失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # ========== graphiti_core 搜索功能 ==========
    
    def search_episodes_graphiti_core(self, query: str,
                                       limit: int = 10,
                                       center_node_uuid: Optional[str] = None,
                                       valid_at: Optional[Union[str, datetime]] = None) -> Dict[str, Any]:
        """
        使用graphiti_core搜索Episodes
        
        Args:
            query: 搜索查询
            limit: 返回结果限制
            center_node_uuid: 可选的中心节点UUID（用于基于图的重新排序）
            valid_at: 可选的有效时间点（时间旅行查询）
            
        Returns:
            搜索结果
        """
        if not self._graphiti_core_enabled:
            return {
                "success": False,
                "error": "graphiti_core未启用或初始化失败"
            }
        
        try:
            # 异步执行搜索
            async def _search():
                if center_node_uuid:
                    results = await self._graphiti_core.search(
                        query=query,
                        center_node_uuid=center_node_uuid
                    )
                else:
                    results = await self._graphiti_core.search(query=query)
                return results
            
            results = asyncio.run(_search())
            
            # 转换结果格式
            formatted_results = []
            for result in results[:limit]:
                formatted_result = {
                    "uuid": str(result.uuid) if hasattr(result, 'uuid') else None,
                    "fact": result.fact if hasattr(result, 'fact') else None,
                }
                
                # 可选字段
                if hasattr(result, 'source_node_uuid') and result.source_node_uuid:
                    formatted_result["source_node_uuid"] = str(result.source_node_uuid)
                if hasattr(result, 'valid_at') and result.valid_at:
                    formatted_result["valid_at"] = result.valid_at.isoformat()
                if hasattr(result, 'invalid_at') and result.invalid_at:
                    formatted_result["invalid_at"] = result.invalid_at.isoformat()
                if hasattr(result, 'score'):
                    formatted_result["score"] = float(result.score) if hasattr(result.score, '__float__') else result.score
                
                formatted_results.append(formatted_result)
            
            return {
                "success": True,
                "query": query,
                "results": formatted_results,
                "total": len(formatted_results)
            }
            
        except Exception as e:
            logger.error(f"❌ 搜索Episodes失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def search_nodes_graphiti_core(self, query: str,
                                   limit: int = 5,
                                   use_hybrid_search: bool = True) -> Dict[str, Any]:
        """
        使用graphiti_core搜索节点（使用混合搜索）
        
        Args:
            query: 搜索查询
            limit: 返回结果限制
            use_hybrid_search: 是否使用混合搜索（语义+BM25）
            
        Returns:
            搜索结果
        """
        if not self._graphiti_core_enabled:
            return {
                "success": False,
                "error": "graphiti_core未启用或初始化失败"
            }
        
        try:
            from graphiti_core.search.search_config_recipes import NODE_HYBRID_SEARCH_RRF
            
            # 使用预设的搜索配置
            config = NODE_HYBRID_SEARCH_RRF.model_copy(deep=True)
            config.limit = limit
            
            # 异步执行搜索
            async def _search():
                return await self._graphiti_core._search(
                    query=query,
                    config=config
                )
            
            result = asyncio.run(_search())
            
            # 转换节点结果
            formatted_nodes = []
            if hasattr(result, 'nodes'):
                for node in result.nodes:
                    formatted_node = {
                        "uuid": str(node.uuid) if hasattr(node, 'uuid') else None,
                        "name": node.name if hasattr(node, 'name') else None,
                        "summary": node.summary if hasattr(node, 'summary') else None,
                    }
                    
                    # 可选字段
                    if hasattr(node, 'labels') and node.labels:
                        formatted_node["labels"] = list(node.labels)
                    if hasattr(node, 'created_at') and node.created_at:
                        formatted_node["created_at"] = node.created_at.isoformat()
                    if hasattr(node, 'attributes'):
                        formatted_node["attributes"] = node.attributes if isinstance(node.attributes, dict) else {}
                    
                    formatted_nodes.append(formatted_node)
            
            return {
                "success": True,
                "query": query,
                "nodes": formatted_nodes,
                "total": len(formatted_nodes),
                "search_type": "hybrid" if use_hybrid_search else "basic"
            }
            
        except Exception as e:
            logger.error(f"❌ 搜索节点失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # ========== 时间查询功能 ==========
    
    def get_graph_state_at_time_graphiti_core(self, query_time: Union[str, datetime],
                                              limit: int = 100) -> Dict[str, Any]:
        """
        获取指定时间点的图状态（时间旅行查询）
        
        Args:
            query_time: 查询时间点
            limit: 返回结果限制
            
        Returns:
            图状态数据
        """
        if not self._graphiti_core_enabled:
            return {
                "success": False,
                "error": "graphiti_core未启用或初始化失败"
            }
        
        try:
            # 处理时间
            if isinstance(query_time, str):
                query_dt = datetime.fromisoformat(query_time.replace('Z', '+00:00'))
            else:
                query_dt = query_time
            
            # 异步执行搜索获取所有结果
            async def _get_all():
                # 使用通配符获取所有结果
                results = await self._graphiti_core.search(query="*")
                return results
            
            results = asyncio.run(_get_all())
            
            # 过滤在指定时间点有效的结果
            valid_results = []
            for result in results[:limit]:
                is_valid = True
                
                # 检查valid_at
                if hasattr(result, 'valid_at') and result.valid_at:
                    valid_at_dt = result.valid_at
                    if valid_at_dt > query_dt:
                        is_valid = False
                
                # 检查invalid_at
                if hasattr(result, 'invalid_at') and result.invalid_at:
                    invalid_at_dt = result.invalid_at
                    if invalid_at_dt <= query_dt:
                        is_valid = False
                
                if is_valid:
                    formatted_result = {
                        "uuid": str(result.uuid) if hasattr(result, 'uuid') else None,
                        "fact": result.fact if hasattr(result, 'fact') else None,
                    }
                    valid_results.append(formatted_result)
            
            return {
                "success": True,
                "query_time": query_dt.isoformat(),
                "total_nodes": len(valid_results),
                "nodes": valid_results
            }
            
        except Exception as e:
            logger.error(f"❌ 获取图状态失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # ========== 状态查询方法 ==========
    
    def is_graphiti_core_enabled(self) -> bool:
        """
        检查graphiti_core是否可用
        
        Returns:
            True如果graphiti_core已启用
        """
        return self._graphiti_core_enabled
    
    def get_graphiti_core_info(self) -> Dict[str, Any]:
        """
        获取graphiti_core的集成信息
        
        Returns:
            graphiti_core状态信息
        """
        info = {
            "enabled": self._graphiti_core_enabled,
            "version": "unknown",
            "features": []
        }
        
        if self._graphiti_core_enabled:
            try:
                # 尝试获取版本信息
                import graphiti_core
                info["version"] = getattr(graphiti_core, "__version__", "0.25.0")
                
                # 列出可用的功能
                info["features"] = [
                    "add_episode",
                    "search_episodes",
                    "search_nodes_hybrid",
                    "search_with_center_node",
                    "time_based_query",
                    "bitemporal_model",
                    "hybrid_search"
                ]
                
            except Exception as e:
                info["error"] = str(e)
        
        return info
    
    # ========== 性能优化和缓存 ==========
    
    def _get_cache_key(self, operation: str, **kwargs) -> str:
        """生成缓存键"""
        param_str = json.dumps(kwargs, sort_keys=True)
        hash_obj = hashlib.md5(f"{operation}:{param_str}".encode())
        return hash_obj.hexdigest()
    
    @lru_cache(maxsize=settings.TEMPORAL_QUERY_CACHE_SIZE)
    def _cached_query(self, query_hash: str, query_func: callable) -> Any:
        """带缓存的查询执行"""
        return query_func()
    
    def query_with_cache(self, operation: str, query_func: callable,
                        cache_ttl: Optional[int] = None, **kwargs) -> Any:
        """执行带缓存的查询"""
        cache_ttl = cache_ttl or settings.TEMPORAL_QUERY_CACHE_TTL
        
        # 生成缓存键
        cache_key = self._get_cache_key(operation, **kwargs)
        
        # 检查缓存
        current_time = time.time()
        if cache_key in self._query_cache:
            cached_data, expiry_time = self._query_cache[cache_key]
            if current_time < expiry_time:
                self._cache_hits += 1
                logger.debug(f"✅ 缓存命中: {operation}")
                return cached_data
        
        # 缓存未命中，执行查询
        self._cache_misses += 1
        logger.debug(f"❌ 缓存未命中: {operation}")
        
        # 执行查询
        result = query_func()
        
        # 缓存结果
        expiry_time = current_time + cache_ttl
        self._query_cache[cache_key] = (result, expiry_time)
        
        # 清理过期缓存
        if len(self._query_cache) > settings.TEMPORAL_QUERY_CACHE_SIZE * 2:
            self._clean_expired_cache()
        
        return result
    
    def _clean_expired_cache(self):
        """清理过期的缓存条目"""
        current_time = time.time()
        expired_keys = [
            key for key, (_, expiry_time) in self._query_cache.items()
            if expiry_time < current_time
        ]
        
        for key in expired_keys:
            del self._query_cache[key]
        
        if expired_keys:
            logger.debug(f"🧹 清理了 {len(expired_keys)} 个过期缓存条目")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            "cache_size": len(self._query_cache),
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate": self._cache_hits / (self._cache_hits + self._cache_misses)
                if self._cache_hits + self._cache_misses > 0 else 0,
            "total_queries": self._cache_hits + self._cache_misses
        }
    
    # ========== 辅助方法 ==========
    
    def clear_cache(self):
        """清除所有缓存"""
        self._query_cache.clear()
        self._cached_query.cache_clear()
        self._cache_hits = 0
        self._cache_misses = 0
        logger.info("🧹 缓存已清除")
    
    def get_service_info(self) -> Dict[str, Any]:
        """获取服务信息"""
        cache_stats = self.get_cache_stats()
        
        return {
            "service_type": "EnhancedGraphitiService",
            "graphiti_core_enabled": self._graphiti_core_enabled,
            "graphiti_core_info": self.get_graphiti_core_info(),
            "cache_stats": cache_stats,
            "timestamp": datetime.now().isoformat()
        }
    
    def close(self):
        """关闭服务"""
        # 关闭缓存和资源
        self.clear_cache()
        
        # 关闭graphiti_core
        if self._graphiti_core:
            try:
                asyncio.run(self._graphiti_core.close())
                logger.info("✅ graphiti_core已关闭")
            except Exception as e:
                logger.warning(f"⚠️  关闭graphiti_core时出错: {str(e)}")
        
        logger.info("✅ 增强Graphiti服务已完全关闭")
