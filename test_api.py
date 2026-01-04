#!/usr/bin/env python3
"""
API测试脚本

测试AIRP Knowledge Graph API的基础功能
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api_service'))

import requests
import json
from datetime import datetime

# API基础URL
BASE_URL = "http://localhost:8000"


def test_health():
    """测试健康检查"""
    print("\n" + "="*60)
    print("测试1: 健康检查")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 状态: {data.get('status')}")
            print(f"✅ 版本: {data.get('version')}")
            print(f"✅ graphiti_core: {'已启用' if data.get('graphiti_core_enabled') else '未启用'}")
            return True
        else:
            print(f"❌ 失败: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        return False


def test_create_episode():
    """测试创建Episode"""
    print("\n" + "="*60)
    print("测试2: 创建Episode")
    print("="*60)
    
    try:
        episode_data = {
            "content": "测试内容：用户Alice今天访问了网站并购买了产品",
            "episode_type": "text",
            "name": "测试Episode",
            "metadata": {
                "user_id": "test_user",
                "action": "visit"
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/episodes/",
            json=episode_data
        )
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 成功创建Episode")
            print(f"   UUID: {data.get('data', {}).get('uuid')}")
            print(f"   名称: {data.get('data', {}).get('name')}")
            return data.get('data', {}).get('uuid')
        else:
            print(f"❌ 失败: {response.text}")
            return None
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        return None


def test_search_episodes():
    """测试搜索Episodes"""
    print("\n" + "="*60)
    print("测试3: 搜索Episodes")
    print("="*60)
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/search/episodes",
            params={
                "query": "Alice",
                "limit": 5
            }
        )
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 搜索成功")
            print(f"   查询: {data.get('query')}")
            print(f"   结果数: {data.get('total')}")
            
            for i, result in enumerate(data.get('results', [])[:3], 1):
                print(f"   结果{i}: {result.get('fact', 'N/A')[:50]}...")
            
            return True
        else:
            print(f"❌ 失败: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        return False


def test_search_nodes():
    """测试搜索节点"""
    print("\n" + "="*60)
    print("测试4: 搜索节点（混合搜索）")
    print("="*60)
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/search/nodes",
            params={
                "query": "用户",
                "limit": 3,
                "use_hybrid": True
            }
        )
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 搜索成功")
            print(f"   查询: {data.get('query')}")
            print(f"   搜索类型: {data.get('search_type')}")
            print(f"   节点数: {data.get('total')}")
            
            for i, node in enumerate(data.get('nodes', [])[:3], 1):
                print(f"   节点{i}: {node.get('name', 'N/A')}")
            
            return True
        else:
            print(f"❌ 失败: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        return False


def test_graph_state():
    """测试获取图状态（时间旅行）"""
    print("\n" + "="*60)
    print("测试5: 获取图状态（时间旅行）")
    print("="*60)
    
    try:
        query_time = datetime.now().isoformat()
        response = requests.get(
            f"{BASE_URL}/api/v1/search/graph-state",
            params={
                "query_time": query_time,
                "limit": 10
            }
        )
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 查询成功")
            print(f"   查询时间: {data.get('data', {}).get('query_time')}")
            print(f"   节点数: {data.get('data', {}).get('total_nodes')}")
            return True
        else:
            print(f"❌ 失败: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        return False


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("AIRP Knowledge Graph API 测试")
    print("="*60)
    print(f"API地址: {BASE_URL}")
    print(f"文档地址: {BASE_URL}/docs")
    
    results = {
        "健康检查": False,
        "创建Episode": False,
        "搜索Episodes": False,
        "搜索节点": False,
        "获取图状态": False
    }
    
    # 运行测试
    results["健康检查"] = test_health()
    
    if results["健康检查"]:
        results["创建Episode"] = test_create_episode()
        
        if results["创建Episode"]:
            results["搜索Episodes"] = test_search_episodes()
            results["搜索节点"] = test_search_nodes()
            results["获取图状态"] = test_graph_state()
    
    # 打印总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {test_name}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
