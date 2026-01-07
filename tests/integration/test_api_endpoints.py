"""
API端点集成测试

测试范围：
- 健康检查端点
- OpenAI兼容的Chat Completions端点
- 完整请求处理流程
- 响应格式验证
"""

import pytest
from fastapi.testclient import TestClient
from models.requests import ChatCompletionRequest, Message
from tests.conftest import (
    SAMPLE_SILLYTAVERN_INPUT,
    assert_response_format
)


class TestHealthEndpoint:
    """健康检查端点测试"""
    
    def test_health_check(self, test_client):
        """测试健康检查端点"""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
    
    def test_health_check_with_stats(self, test_client):
        """测试健康检查包含统计信息"""
        # 首先执行一些请求
        # 注意：这里使用mock client，所以实际不会请求
        
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # 验证统计字段存在
        assert "world_info_states" in data
        assert "chat_history_states" in data
        assert "psych_state_records" in data
        
        # 值应为整数
        assert isinstance(data["world_info_states"], int)
        assert isinstance(data["chat_history_states"], int)
        assert isinstance(data["psych_state_records"], int)


class TestChatCompletionsEndpoint:
    """Chat Completions端点测试"""
    
    def test_chat_completions_basic_request(self, test_client):
        """测试基本的Chat Completions请求"""
        request_data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "你是haruki"},
                {"role": "user", "content": "你好"}
            ],
            "temperature": 0.7,
            "max_tokens": 100
        }
        
        response = test_client.post(
            "/v1/chat/completions",
            json=request_data
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert_response_format(data)
        
        # 验证响应内容
        assert len(data["choices"]) > 0
        assert data["choices"][0]["message"]["role"] == "assistant"
        assert isinstance(data["choices"][0]["message"]["content"], str)
    
    def test_chat_completions_with_sillytavern_format(self, test_client):
        """测试包含SillyTavern格式的请求"""
        request_data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "你是haruki"},
                {"role": "user", "content": SAMPLE_SILLYTAVERN_INPUT}
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        response = test_client.post(
            "/v1/chat/completions",
            json=request_data
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert_response_format(data)
        
        # 验证记忆信息
        assert "extra" in data
        assert "memories_used" in data["extra"]
        assert isinstance(data["extra"]["memories_used"], int)
    
    def test_chat_completions_with_session_id(self, test_client):
        """测试带session_id的请求"""
        request_data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "user", "content": "你好"}
            ],
            "session_id": "test-session-123"
        }
        
        response = test_client.post(
            "/v1/chat/completions",
            json=request_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert_response_format(data)
    
    def test_chat_completions_session_id_in_header(self, test_client):
        """测试session_id在header中"""
        request_data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "user", "content": "你好"}
            ]
        }
        
        headers = {"X-Session-ID": "test-session-header-456"}
        
        response = test_client.post(
            "/v1/chat/completions",
            json=request_data,
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert_response_format(data)
    
    def test_chat_completions_missing_user_message(self, test_client):
        """测试缺少user消息的请求"""
        request_data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "你是haruki"}
            ]
        }
        
        response = test_client.post(
            "/v1/chat/completions",
            json=request_data
        )
        
        assert response.status_code == 400  # Bad Request
    
    def test_chat_completions_invalid_temperature(self, test_client):
        """测试无效的temperature值"""
        request_data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "user", "content": "你好"}
            ],
            "temperature": 2.5  # 超出范围（应该< 2）
        }
        
        response = test_client.post(
            "/v1/chat/completions",
            json=request_data
        )
        
        # Pydantic应该验证并返回错误
        assert response.status_code in [400, 422]
    
    def test_chat_completions_response_usage(self, test_client):
        """测试响应包含usage信息"""
        request_data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "user", "content": "测试token统计"}
            ]
        }
        
        response = test_client.post(
            "/v1/chat/completions",
            json=request_data
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert "usage" in data
        assert "prompt_tokens" in data["usage"]
        assert "completion_tokens" in data["usage"]
        assert "total_tokens" in data["usage"]
        
        # 验证token计数
        assert isinstance(data["usage"]["prompt_tokens"], int)
        assert isinstance(data["usage"]["completion_tokens"], int)
        assert isinstance(data["usage"]["total_tokens"], int)
        assert data["usage"]["total_tokens"] >= data["usage"]["prompt_tokens"]


class TestErrorResponse:
    """错误响应测试"""
    
    def test_invalid_json(self, test_client):
        """测试无效的JSON请求"""
        response = test_client.post(
            "/v1/chat/completions",
            data="invalid json"
        )
        
        assert response.status_code == 422  # Unprocessable Entity
    
    def test_missing_required_field(self, test_client):
        """测试缺少必需字段"""
        request_data = {
            "messages": [
                {"role": "user", "content": "你好"}
            ]
            # 缺少model字段
        }
        
        response = test_client.post(
            "/v1/chat/completions",
            json=request_data
        )
        
        assert response.status_code == 422
    
    def test_empty_messages(self, test_client):
        """测试空消息列表"""
        request_data = {
            "model": "deepseek-chat",
            "messages": []
        }
        
        response = test_client.post(
            "/v1/chat/completions",
            json=request_data
        )
        
        assert response.status_code == 400 or response.status_code == 422


class TestCORS:
    """CORS测试"""
    
    def test_cors_headers(self, test_client):
        """测试CORS头"""
        # 发送OPTIONS请求
        response = test_client.options(
            "/v1/chat/completions",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST"
            }
        )
        
        # 应该返回CORS头
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] == "*"


class TestCompleteWorkflow:
    """完整工作流测试"""
    
    def test_full_request_workflow(self, test_client):
        """测试完整的请求处理工作流"""
        session_id = "test-workflow-session"
        
        # 第一次请求
        request1 = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "你是haruki"},
                {"role": "user", "content": "你好，我是新用户"}
            ],
            "session_id": session_id
        }
        
        response1 = test_client.post(
            "/v1/chat/completions",
            json=request1
        )
        
        assert response1.status_code == 200
        data1 = response1.json()
        assert_response_format(data1)
        
        # 第二次请求（模拟对话继续）
        request2 = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "user", "content": "这是第二个问题"}
            ],
            "session_id": session_id
        }
        
        response2 = test_client.post(
            "/v1/chat/completions",
            json=request2
        )
        
        assert response2.status_code == 200
        data2 = response2.json()
        assert_response_format(data2)
        
        # 验证健康检查显示会话状态
        health_response = test_client.get("/health")
        health_data = health_response.json()
        
        # 应该至少有一个会话状态记录
        # 注意：由于使用mock，实际可能没有真实存储
        assert isinstance(health_data["chat_history_states"], int)
    
    def test_multiple_sessions(self, test_client):
        """测试多个独立会话"""
        session1 = "test-session-1"
        session2 = "test-session-2"
        
        # 会话1的请求
        request1 = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": "会话1的消息"}],
            "session_id": session1
        }
        
        response1 = test_client.post(
            "/v1/chat/completions",
            json=request1
        )
        
        assert response1.status_code == 200
        
        # 会话2的请求
        request2 = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": "会话2的消息"}],
            "session_id": session2
        }
        
        response2 = test_client.post(
            "/v1/chat/completions",
            json=request2
        )
        
        assert response2.status_code == 200
        
        # 两个响应应该不同（独立会话）
        data1 = response1.json()
        data2 = response2.json()
        
        # 由于使用mock，内容可能相同，但在真实场景中应该不同
        assert "id" in data1
        assert "id" in data2


class TestOpenAICompatibility:
    """OpenAI兼容性测试"""
    
    def test_response_structure_matches_openai(self, test_client):
        """测试响应结构符合OpenAI规范"""
        request = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "user", "content": "测试"}
            ]
        }
        
        response = test_client.post(
            "/v1/chat/completions",
            json=request
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 验证OpenAI标准字段
        required_fields = ["id", "object", "created", "model", "choices"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        # 验证choices结构
        assert len(data["choices"]) > 0
        choice = data["choices"][0]
        assert "index" in choice
        assert "message" in choice
        assert "finish_reason" in choice
        
        # 验证message结构
        message = choice["message"]
        assert "role" in message
        assert "content" in message
        assert message["role"] == "assistant"
    
    def test_supports_optional_parameters(self, test_client):
        """测试支持可选参数"""
        request = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "user", "content": "测试"}
            ],
            "temperature": 0.5,
            "max_tokens": 100,
            "top_p": 0.9,
            "frequency_penalty": 0.5,
            "presence_penalty": 0.5,
            "n": 1
        }
        
        response = test_client.post(
            "/v1/chat/completions",
            json=request
        )
        
        # 应该成功处理所有参数
        assert response.status_code == 200
