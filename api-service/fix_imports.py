#!/usr/bin/env python3
"""
修复AIRP记忆系统导入问题
"""

import os
import sys
import re
from pathlib import Path

def add_sys_path_fix_to_file(file_path):
    """在文件开头添加sys.path修复代码"""
    print(f"处理文件: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否已经包含sys.path.insert
    if 'sys.path.insert' in content or 'sys.path.append' in content:
        print(f"  ⚠️  已包含sys.path相关代码，跳过")
        return False
    
    # 找到所有导入语句
    lines = content.split('\n')
    import_end_index = 0
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('import ') or stripped.startswith('from '):
            import_end_index = i
        elif stripped and not stripped.startswith('#') and not stripped.startswith('\"\"\"'):
            break
    
    # 添加sys.path修复代码
    sys_path_code = """import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
"""
    
    if import_end_index > 0:
        # 在导入语句后插入
        new_lines = lines[:import_end_index + 1] + [''] + sys_path_code.split('\n') + [''] + lines[import_end_index + 1:]
    else:
        # 在文件开头插入
        new_lines = sys_path_code.split('\n') + [''] + lines
    
    new_content = '\n'.join(new_lines)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"  ✅ 已添加sys.path修复代码")
    return True

def replace_relative_imports(file_path):
    """替换相对导入为绝对导入"""
    print(f"检查相对导入: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找相对导入模式
    patterns = [
        (r'from \.\.config\.settings import settings', 'from config.settings import settings'),
        (r'from \.\.services\.(\w+) import', r'from services.\1 import'),
        (r'from \.sillytavern_parser import', 'from services.sillytavern_parser import'),
        (r'from \.graphiti_service import', 'from services.graphiti_service import'),
        (r'from \.integration_service import', 'from services.integration_service import'),
    ]
    
    changes_made = False
    new_content = content
    
    for pattern, replacement in patterns:
        matches = re.findall(pattern, new_content)
        if matches:
            new_content = re.sub(pattern, replacement, new_content)
            print(f"  🔧 替换: {pattern} -> {replacement}")
            changes_made = True
    
    if changes_made:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"  ✅ 相对导入已替换")
    else:
        print(f"  ✅ 没有相对导入需要替换")
    
    return changes_made

def main():
    """主修复函数"""
    print("=" * 60)
    print("AIRP记忆系统导入问题修复工具")
    print("=" * 60)
    
    # 获取项目根目录
    current_dir = Path(__file__).parent
    services_dir = current_dir / 'services'
    
    # 需要处理的文件列表
    files_to_fix = [
        current_dir / 'services' / 'sillytavern_parser.py',
        current_dir / 'services' / 'integration_service.py',
        current_dir / 'services' / 'graphiti_service.py',
        current_dir / 'services' / 'llm_service.py',
        current_dir / 'services' / 'parser_service.py',
    ]
    
    # 确保这些文件存在
    existing_files = [f for f in files_to_fix if f.exists()]
    
    print(f"找到 {len(existing_files)} 个需要处理的服务文件:")
    for f in existing_files:
        print(f"  • {f.name}")
    
    print("\n" + "-" * 60)
    
    # 处理每个文件
    total_fixes = 0
    
    for file_path in existing_files:
        print(f"\n处理 {file_path.name}:")
        try:
            # 首先添加sys.path修复
            sys_path_fixed = add_sys_path_fix_to_file(file_path)
            
            # 然后替换相对导入
            imports_fixed = replace_relative_imports(file_path)
            
            if sys_path_fixed or imports_fixed:
                total_fixes += 1
                
        except Exception as e:
            print(f"  ❌ 处理失败: {str(e)}")
    
    print("\n" + "=" * 60)
    print(f"修复完成！总共处理了 {total_fixes} 个文件")
    print("\n修复内容:")
    print("1. 在文件开头添加sys.path.insert(0, project_root)")
    print("2. 替换相对导入为绝对导入 (from ..config -> from config)")
    print("3. 确保所有服务都可以作为顶层模块导入")
    print("\n建议:")
    print("1. 运行 'python api-service/test_imports.py' 测试导入")
    print("2. 运行 'python api-service/test_graphiti_simple.py' 测试Graphiti服务")
    print("3. 如果仍有问题，检查__init__.py文件和包结构")
    print("=" * 60)

if __name__ == "__main__":
    main()
