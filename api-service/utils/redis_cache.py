"""
Redis缓存层

提供高性能缓存支持，用于缓存Embedding向量、
去重结果、Token计数等，减少API调用和计算成本。

作者: AIRP项目团队
日期: 2026-01-08
"""

import json
import hashlib
from typing import Optional, Any, List, Dict
from datetime import datetime, timedelta

import redis.asyncio as redis_async

from loguru import logger


class RedisCacheManager:
    """Redis缓存管理器"""
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        db: int = 0,
        password: Optional[str] = None,
        default_ttl: int = 3600  # 1小时
    ):
        """
        初始化Redis缓存管理器
        
        参数:
            redis_url: Redis连接URL
            db: 数据库编号
            password: Redis密码
            default_ttl: 默认过期时间（秒）
        """
        self.redis_url = redis_url
        self.db = db
        self.password = password
        self.default_ttl = default_ttl
        self._redis = None
        self._async_redis = None
        
        logger.info(f"Redis缓存管理器初始化完成 - URL: {redis_url}, DB: {db}")
    
    async def connect(self):
        """连接Redis"""
        try:
            # 同步Redis客户端（用于阻塞操作）
            import redis as redis_sync
            self._redis = redis_sync.Redis(
                host=self._extract_host(self.redis_url),
                port=self._extract_port(self.redis_url),
                db=self.db,
                password=self.password,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            
            # 异步Redis客户端（用于异步操作）
            self._async_redis = await redis_async.from_url(
                self.redis_url,
                db=self.db,
                password=self.password,
                decode_responses=True
            )
            
            # 测试连接
            await self._async_redis.ping()
            
            logger.info("Redis连接成功")
            return True
            
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            return False
    
    async def disconnect(self):
        """断开Redis连接"""
        try:
            if self._redis:
                self._redis.close()
            
            if self._async_redis:
                await self._async_redis.close()
            
            logger.info("Redis连接已关闭")
            
        except Exception as e:
            logger.error(f"断开Redis连接失败: {e}")
    
    def _extract_host(self, url: str) -> str:
        """从URL提取主机"""
        if "://" in url:
            return url.split("://")[1].split(":")[0].split("/")[0]
        return "localhost"
    
    def _extract_port(self, url: str) -> int:
        """从URL提取端口"""
        if "://" in url:
            parts = url.split("://")[1].split(":")
            if len(parts) > 1:
                try:
                    return int(parts[1].split("/")[0])
                except ValueError:
                    return 6379  # 默认Redis端口
        return 6379
    
    async def get_embedding_cache(
        self,
        text: str,
        embedding_model: str
    ) -> Optional[List[float]]:
        """
        获取Embedding缓存
        
        参数:
            text: 文本内容
            embedding_model: Embedding模型名称
        
        返回:
            List[float]: Embedding向量，如果未缓存则返回None
        """
        cache_key = self._generate_embedding_key(text, embedding_model)
        
        try:
            cached = await self._async_redis.get(cache_key)
            
            if cached:
                embedding = json.loads(cached)
                logger.debug(f"Embedding缓存命中: {embedding_model}")
                return embedding
            
            logger.debug(f"Embedding缓存未命中: {embedding_model}")
            return None
            
        except Exception as e:
            logger.error(f"获取Embedding缓存失败: {e}")
            return None
    
    async def set_embedding_cache(
        self,
        text: str,
        embedding_model: str,
        embedding: List[float],
        ttl: Optional[int] = None
    ):
        """
        设置Embedding缓存
        
        参数:
            text: 文本内容
            embedding_model: Embedding模型名称
            embedding: Embedding向量
            ttl: 过期时间（秒），如果为None则使用默认值
        """
        cache_key = self._generate_embedding_key(text, embedding_model)
        ttl = ttl or self.default_ttl
        
        try:
            await self._async_redis.setex(
                cache_key,
                json.dumps(embedding),
                ttl
            )
            logger.debug(f"Embedding缓存已设置: {embedding_model}, TTL: {ttl}秒")
            
        except Exception as e:
            logger.error(f"设置Embedding缓存失败: {e}")
    
    async def get_token_count_cache(
        self,
        text: str,
        model: str
    ) -> Optional[int]:
        """
        获取Token计数缓存
        
        参数:
            text: 文本内容
            model: 模型名称
        
        返回:
            int: Token数量，如果未缓存则返回None
        """
        cache_key = self._generate_token_key(text, model)
        
        try:
            cached = await self._async_redis.get(cache_key)
            
            if cached:
                token_count = int(cached)
                logger.debug(f"Token计数缓存命中: {model}")
                return token_count
            
            logger.debug(f"Token计数缓存未命中: {model}")
            return None
            
        except Exception as e:
            logger.error(f"获取Token计数缓存失败: {e}")
            return None
    
    async def set_token_count_cache(
        self,
        text: str,
        model: str,
        token_count: int,
        ttl: Optional[int] = None
    ):
        """
        设置Token计数缓存
        
        参数:
            text: 文本内容
            model: 模型名称
            token_count: Token数量
            ttl: 过期时间（秒），如果为None则使用默认值
        """
        cache_key = self._generate_token_key(text, model)
        ttl = ttl or self.default_ttl
        
        try:
            await self._async_redis.setex(
                cache_key,
                str(token_count),
                ttl
            )
            logger.debug(f"Token计数缓存已设置: {model}, 计数: {token_count}, TTL: {ttl}秒")
            
        except Exception as e:
            logger.error(f"设置Token计数缓存失败: {e}")
    
    async def get_semantic_hash_cache(
        self,
        text: str
    ) -> Optional[str]:
        """
        获取语义哈希缓存
        
        参数:
            text: 文本内容
        
        返回:
            str: 语义哈希，如果未缓存则返回None
        """
        cache_key = self._generate_semantic_hash_key(text)
        
        try:
            cached = await self._async_redis.get(cache_key)
            
            if cached:
                hash_value = cached.decode('utf-8')
                logger.debug(f"语义哈希缓存命中")
                return hash_value
            
            logger.debug(f"语义哈希缓存未命中")
            return None
            
        except Exception as e:
            logger.error(f"获取语义哈希缓存失败: {e}")
            return None
    
    async def set_semantic_hash_cache(
        self,
        text: str,
        hash_value: str,
        ttl: Optional[int] = None
    ):
        """
        设置语义哈希缓存
        
        参数:
            text: 文本内容
            hash_value: 语义哈希
            ttl: 过期时间（秒），如果为None则使用默认值
        """
        cache_key = self._generate_semantic_hash_key(text)
        ttl = ttl or (self.default_ttl * 24)  # 语义哈希缓存24小时
        
        try:
            await self._async_redis.setex(
                cache_key,
                hash_value,
                ttl
            )
            logger.debug(f"语义哈希缓存已设置，TTL: {ttl}秒")
            
        except Exception as e:
            logger.error(f"设置语义哈希缓存失败: {e}")
    
    async def get_dedup_result_cache(
        self,
        content_hash: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取去重结果缓存
        
        参数:
            content_hash: 内容哈希
        
        返回:
            Dict: 去重结果，如果未缓存则返回None
        """
        cache_key = f"dedup:{content_hash}"
        
        try:
            cached = await self._async_redis.get(cache_key)
            
            if cached:
                result = json.loads(cached)
                logger.debug(f"去重结果缓存命中")
                return result
            
            logger.debug(f"去重结果缓存未命中")
            return None
            
        except Exception as e:
            logger.error(f"获取去重结果缓存失败: {e}")
            return None
    
    async def set_dedup_result_cache(
        self,
        content_hash: str,
        result: Dict[str, Any],
        ttl: Optional[int] = None
    ):
        """
        设置去重结果缓存
        
        参数:
            content_hash: 内容哈希
            result: 去重结果
            ttl: 过期时间（秒），如果为None则使用默认值
        """
        cache_key = f"dedup:{content_hash}"
        ttl = ttl or (self.default_ttl * 6)  # 去重结果缓存6小时
        
        try:
            await self._async_redis.setex(
                cache_key,
                json.dumps(result),
                ttl
            )
            logger.debug(f"去重结果缓存已设置，TTL: {ttl}秒")
            
        except Exception as e:
            logger.error(f"设置去重结果缓存失败: {e}")
    
    def _generate_embedding_key(self, text: str, model: str) -> str:
        """
        生成Embedding缓存键
        
        参数:
            text: 文本内容
            model: 模型名称
        
        返回:
            str: 缓存键
        """
        # 使用文本和模型的哈希
        key_content = f"{text}:{model}"
        return f"embedding:{hashlib.md5(key_content.encode('utf-8')).hexdigest()}"
    
    def _generate_token_key(self, text: str, model: str) -> str:
        """
        生成Token计数缓存键
        
        参数:
            text: 文本内容
            model: 模型名称
        
        返回:
            str: 缓存键
        """
        # 使用文本和模型的哈希
        key_content = f"{text}:{model}"
        return f"token:{hashlib.md5(key_content.encode('utf-8')).hexdigest()}"
    
    def _generate_semantic_hash_key(self, text: str) -> str:
        """
        生成语义哈希缓存键
        
        参数:
            text: 文本内容
        
        返回:
            str: 缓存键
        """
        # 使用文本的哈希
        return f"semantic_hash:{hashlib.md5(text.encode('utf-8')).hexdigest()}"
    
    async def batch_get_embeddings(
        self,
        texts: List[str],
        embedding_model: str
    ) -> List[Optional[List[float]]]:
        """
        批量获取Embedding缓存
        
        参数:
            texts: 文本列表
            embedding_model: Embedding模型名称
        
        返回:
            List[Optional[List[float]]]: Embedding向量列表，未缓存的为None
        """
        import asyncio
        
        # 并发获取所有缓存
        tasks = [
            self.get_embedding_cache(text, embedding_model)
            for text in texts
        ]
        
        results = await asyncio.gather(*tasks)
        
        logger.debug(f"批量获取Embedding缓存完成，共 {len(results)} 个")
        return results
    
    async def batch_set_embeddings(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        embedding_model: str,
        ttl: Optional[int] = None
    ):
        """
        批量设置Embedding缓存
        
        参数:
            texts: 文本列表
            embeddings: Embedding向量列表
            embedding_model: Embedding模型名称
            ttl: 过期时间（秒）
        """
        import asyncio
        
        ttl = ttl or self.default_ttl
        
        # 并发设置所有缓存
        tasks = [
            self.set_embedding_cache(text, embedding_model, emb, ttl)
            for text, emb in zip(texts, embeddings)
        ]
        
        await asyncio.gather(*tasks)
        
        logger.info(f"批量设置Embedding缓存完成，共 {len(texts)} 个，TTL: {ttl}秒")
    
    async def clear_cache(
        self,
        pattern: str = "*"
    ):
        """
        清除缓存
        
        参数:
            pattern: 键匹配模式，默认清除所有
        """
        try:
            keys = await self._async_redis.keys(pattern)
            
            if keys:
                await self._async_redis.delete(*keys)
                logger.info(f"已清除 {len(keys)} 个缓存键（模式: {pattern}）")
            else:
                logger.info(f"没有匹配的缓存键（模式: {pattern}）")
                
        except Exception as e:
            logger.error(f"清除缓存失败: {e}")
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        返回:
            Dict: 缓存统计
                {
                    "db_size": int,
                    "key_count": int,
                    "used_memory": int
                }
        """
        try:
            info = await self._async_redis.info()
            
            stats = {
                "db_size": 0,
                "key_count": 0,
                "used_memory": 0
            }
            
            if info:
                stats["db_size"] = info.get("used_memory", 0)
                stats["key_count"] = info.get("db_size", 0)
                stats["used_memory"] = info.get("used_memory", 0)
            
            logger.info(f"Redis缓存统计: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"获取缓存统计失败: {e}")
            return {
                "db_size": 0,
                "key_count": 0,
                "used_memory": 0,
                "error": str(e)
            }
    
    async def warmup_cache(
        self,
        texts: List[str],
        embedding_model: str,
        embeddings: List[List[float]]
    ):
        """
        预热缓存
        
        参数:
            texts: 文本列表
            embedding_model: Embedding模型名称
            embeddings: Embedding向量列表
        """
        logger.info(f"开始预热缓存，共 {len(texts)} 个Embedding")
        
        # 批量设置缓存
        await self.batch_set_embeddings(texts, embeddings, embedding_model, ttl=86400)  # 24小时
        
        # 获取统计信息
        stats = await self.get_cache_stats()
        
        logger.info(
            f"预热缓存完成，"
            f"缓存键数: {stats['key_count']}, "
            f"内存使用: {stats['used_memory'] / 1024 / 1024:.2f} KB"
        )


# 便捷函数

async def create_redis_cache(
    redis_url: str = "redis://localhost:6379",
    db: int = 0,
    password: Optional[str] = None,
    default_ttl: int = 3600
) -> RedisCacheManager:
    """
    创建Redis缓存管理器（便捷函数）
    
    参数:
        redis_url: Redis连接URL
        db: 数据库编号
        password: Redis密码
        default_ttl: 默认过期时间（秒）
    
    返回:
        RedisCacheManager: Redis缓存管理器
    """
    cache_manager = RedisCacheManager(
        redis_url=redis_url,
        db=db,
        password=password,
        default_ttl=default_ttl
    )
    
    await cache_manager.connect()
    
    return cache_manager
