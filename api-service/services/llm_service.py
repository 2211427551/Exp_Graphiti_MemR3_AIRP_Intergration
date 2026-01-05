# ============================================
# LLM服务封装
# ============================================
from openai import AsyncOpenAI
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class LLMService:
    """LLM服务封装类"""
    
    def __init__(self, api_key: str, base_url: str, model: str = "deepseek-chat"):
        """
        初始化LLM服务
        
        参数:
            api_key: str
                DeepSeek API密钥
            base_url: str
                DeepSeek API基础URL
            model: str
                默认模型名称
        """
        # 创建OpenAI兼容客户端
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.model = model
        logger.info(f"LLM服务初始化完成 - 模型: {model}")
    
    async def generate_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = 0.7,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        生成聊天补全
        
        参数:
            model: str
                模型名称（如：deepseek-chat）
            messages: List[Dict[str, str]]
                消息列表
                格式：[{"role": "user", "content": "..."}]
            temperature: float = 0.7
                温度参数（0.0-2.0）
            max_tokens: int = None
                最大生成token数
        
        返回:
            Dict[str, Any]: 响应结果
                {
                    "content": str,
                    "finish_reason": str,
                    "prompt_tokens": int,
                    "completion_tokens": int,
                    "total_tokens": int
                }
        
        流程:
            1. 调用OpenAI客户端的chat.completions.create()
            2. 传入messages, model, temperature, max_tokens
            3. 提取响应内容
            4. 返回格式化结果
        
        异常:
            APIError: API调用失败
            RateLimitError: 速率限制
        """
        logger.debug(f"生成补全 - 模型: {model}, 消息数: {len(messages)}")
        
        try:
            # 调用DeepSeek API
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # 提取结果
            choice = response.choices[0]
            result = {
                "content": choice.message.content,
                "finish_reason": choice.finish_reason,
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
            
            logger.info(f"补全生成完成 - tokens: {result['total_tokens']}")
            return result
            
        except Exception as e:
            logger.error(f"LLM调用失败: {e}", exc_info=True)
            raise
    
    async def close(self) -> None:
        """
        关闭LLM服务
        
        清理资源
        """
        logger.info("关闭LLM服务")
        await self.client.close()
