#!/usr/bin/env python3
"""
OpenAI兼容API配置验证脚本

用于验证graphiti_core所需的OpenAI API配置是否正确
"""

import os
import sys

def check_env_var(name, description, required=True):
    """检查环境变量"""
    value = os.environ.get(name, "")
    status = "✅" if value else "❌"
    
    if required and not value:
        print(f"{status} {name} - {description}")
        print(f"   状态: 未设置（必需）")
        return False
    elif not value:
        print(f"{status} {name} - {description}")
        print(f"   状态: 未设置（可选）")
        return True
    else:
        print(f"{status} {name} - {description}")
        print(f"   值: {value[:20]}..." if len(value) > 20 else f"   值: {value}")
        return True

def check_graphiti_core():
    """测试graphiti_core初始化"""
    print("\n" + "="*60)
    print("测试graphiti_core初始化")
    print("="*60)
    
    try:
        from graphiti_core import Graphiti
        
        # 从环境变量获取Neo4j配置
        neo4j_uri = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
        neo4j_user = os.environ.get('NEO4J_USER', 'neo4j')
        neo4j_password = os.environ.get('NEO4J_PASSWORD', 'password')
        
        print(f"尝试连接Neo4j: {neo4j_uri}")
        
        # 初始化graphiti_core
        graphiti = Graphiti(neo4j_uri, neo4j_user, neo4j_password)
        print("✅ graphiti_core初始化成功！")
        
        return True
        
    except ImportError as e:
        print(f"❌ 无法导入graphiti_core: {e}")
        return False
    except Exception as e:
        print(f"❌ graphiti_core初始化失败: {e}")
        return False

def check_openai_api():
    """测试OpenAI API连接"""
    print("\n" + "="*60)
    print("测试OpenAI API连接")
    print("="*60)
    
    try:
        from openai import OpenAI
        
        api_key = os.environ.get('OPENAI_API_KEY')
        base_url = os.environ.get('OPENAI_BASE_URL')
        embedding_model = os.environ.get('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')
        
        if not api_key:
            print("❌ OPENAI_API_KEY未设置，无法测试API")
            return False
        
        print(f"使用模型: {embedding_model}")
        if base_url:
            print(f"自定义API端点: {base_url}")
        else:
            print(f"使用OpenAI官方API")
        
        # 创建客户端
        client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        # 测试embedding
        print("\n测试embedding API...")
        response = client.embeddings.create(
            model=embedding_model,
            input="测试文本"
        )
        
        embedding = response.data[0].embedding
        embedding_dim = len(embedding)
        
        print(f"✅ Embedding API测试成功！")
        print(f"   向量维度: {embedding_dim}")
        print(f"   前5个值: {embedding[:5]}")
        
        # 特别提示Qwen3-Embedding-4B
        if embedding_dim == 2560:
            print(f"\n📌 检测到Qwen3-Embedding-4B (2560维)")
            print(f"   提示: Neo4j向量索引支持任意维度，无需特殊配置")
        
        return True
        
    except ImportError:
        print("❌ openai库未安装")
        return False
    except Exception as e:
        print(f"❌ OpenAI API测试失败: {e}")
        return False

def main():
    """主函数"""
    print("="*60)
    print("OpenAI兼容API配置验证")
    print("="*60)
    
    # 检查环境变量
    all_ok = True
    all_ok &= check_env_var("OPENAI_API_KEY", "OpenAI API密钥（或兼容API密钥）")
    all_ok &= check_env_var("OPENAI_BASE_URL", "自定义API端点（可选）", required=False)
    all_ok &= check_env_var("OPENAI_EMBEDDING_MODEL", "Embedding模型名称", required=False)
    all_ok &= check_env_var("NEO4J_URI", "Neo4j连接URI", required=True)
    all_ok &= check_env_var("NEO4J_USER", "Neo4j用户名", required=True)
    all_ok &= check_env_var("NEO4J_PASSWORD", "Neo4j密码", required=True)
    
    # 检查graphiti_core
    graphiti_ok = check_graphiti_core()
    
    # 检查OpenAI API
    api_ok = check_openai_api()
    
    # 总结
    print("\n" + "="*60)
    print("总结")
    print("="*60)
    
    if all_ok and graphiti_ok and api_ok:
        print("✅ 所有配置正确，可以运行测试！")
        print("\n运行测试命令:")
        print("  python -m pytest tests/ -v")
        return 0
    else:
        print("❌ 配置不完整或有问题，请检查上述错误")
        
        if not all_ok:
            print("\n请设置环境变量:")
            print("  export OPENAI_API_KEY='你的密钥'")
            print("  export OPENAI_BASE_URL='https://api.siliconflow.cn/v1'")
            print("  export OPENAI_EMBEDDING_MODEL='qwen3embedding'")
        
        if not api_ok:
            print("\nAPI连接失败，请检查:")
            print("  1. API密钥是否正确")
            print("  2. BASE_URL是否正确")
            print("  3. 网络连接是否正常")
            print("  4. API服务是否可用")
        
        return 1

if __name__ == "__main__":
    sys.exit(main())
