"""
测试包初始化

使api_service可以作为包导入，修复测试导入路径问题
"""

import sys
import os

# 将项目根目录添加到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print(f"测试包初始化完成，项目根目录：{project_root}")
