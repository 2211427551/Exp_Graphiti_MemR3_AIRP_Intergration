#!/usr/bin/env python3
"""
测试报告生成脚本

从pytest测试结果生成详细的HTML和Markdown报告
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import argparse


class TestReportGenerator:
    """测试报告生成器"""
    
    def __init__(self, results_dir: Path = None):
        if results_dir is None:
            results_dir = Path(__file__).parent / "test-results"
        self.results_dir = Path(results_dir)
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
    def load_coverage_data(self) -> Dict[str, Any]:
        """加载覆盖率数据"""
        coverage_path = self.results_dir.parent / "test-coverage" / "coverage.json"
        
        if not coverage_path.exists():
            print(f"警告: 覆盖率文件不存在: {coverage_path}")
            return None
        
        with open(coverage_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def generate_markdown_report(self) -> str:
        """生成Markdown格式的报告"""
        report_lines = [
            "# AIRP记忆系统测试报告",
            "",
            f"**生成时间**: {self.timestamp}",
            "",
            "---",
            "",
            "## 测试概览",
            "",
            "本报告包含第一阶段（Week 1-6）功能的完整测试结果。",
            "",
        ]
        
        # 添加覆盖率信息
        coverage_data = self.load_coverage_data()
        if coverage_data:
            totals = coverage_data.get('totals', {})
            report_lines.extend([
                "### 代码覆盖率",
                "",
                f"- **总体覆盖率**: {totals.get('percent_covered', 0):.2f}%",
                f"- **覆盖行数**: {totals.get('covered_lines', 0)} / {totals.get('num_statements', 0)}",
                f"- **缺失行数**: {totals.get('missing_lines', 0)}",
                "",
            ])
            
            # 按模块显示覆盖率
            files = coverage_data.get('files', {})
            if files:
                report_lines.append("### 模块覆盖率详情")
                report_lines.append("")
                report_lines.append("| 模块 | 覆盖率 | 覆盖行数 | 总行数 |")
                report_lines.append("|------|--------|----------|--------|")
                
                # 按文件分组
                module_stats = {}
                for file_path, data in files.items():
                    module_name = Path(file_path).name
                    if module_name == '__init__.py':
                        continue
                    
                    percent = data.get('summary', {}).get('percent_covered', 0)
                    covered = data.get('summary', {}).get('covered_lines', 0)
                    total = data.get('summary', {}).get('num_statements', 0)
                    
                    # 高亮显示低覆盖率
                    status = ""
                    if percent < 50:
                        status = " 🔴"
                    elif percent < 80:
                        status = " 🟡"
                    else:
                        status = " 🟢"
                    
                    module_stats[module_name] = (percent, covered, total, status)
                
                # 排序
                for module_name in sorted(module_stats.keys()):
                    percent, covered, total, status = module_stats[module_name]
                    report_lines.append(
                        f"| {module_name} | {percent:.1f}%{status} | {covered} | {total} |"
                    )
                
                report_lines.append("")
        
        report_lines.extend([
            "## 测试范围",
            "",
            "### 单元测试",
            "",
            "- **SillyTavern解析器服务** (`test_parser_service.py`)",
            "  - 标签检测（正则表达式）",
            "  - 内容分类（指令性/叙事性）",
            "  - World Info解析",
            "  - Chat History解析",
            "  - 对话模式识别",
            "",
            "- **变化检测** (`test_change_detection.py`)",
            "  - World Info变化检测",
            "  - Chat History变化检测",
            "  - 状态更新",
            "  - 哈希计算",
            "",
            "### 集成测试",
            "",
            "- **API端点** (`test_api_endpoints.py`)",
            "  - 健康检查端点",
            "  - OpenAI兼容的Chat Completions端点",
            "  - 完整请求处理流程",
            "  - 响应格式验证",
            "",
            "## 测试环境",
            "",
            "- **Python版本**: 3.11+",
            "- **测试框架**: pytest 7.4.3",
            "- **容器化**: Docker (neo4j, redis, test-runner)",
            "",
            "## 运行测试",
            "",
            "### 使用Docker（推荐）",
            "",
            "```bash",
            "# 运行所有测试",
            "./tests/run_tests.sh",
            "",
            "# 只运行单元测试",
            "./tests/run_tests.sh -u",
            "",
            "# 只运行集成测试",
            "./tests/run_tests.sh -i",
            "",
            "# 生成覆盖率报告",
            "./tests/run_tests.sh -c",
            "",
            "# 详细输出",
            "./tests/run_tests.sh -v",
            "```",
            "",
            "### 在本地运行",
            "",
            "```bash",
            "# 运行所有测试",
            "./tests/run_tests.sh -l",
            "",
            "# 使用Python脚本",
            "python tests/run_tests.py -l -c",
            "```",
            "",
            "## 测试说明",
            "",
            "### 标记说明",
            "",
            "- `@pytest.mark.unit`: 单元测试",
            "- `@pytest.mark.integration`: 集成测试",
            "- `@pytest.mark.parser`: 解析器相关测试",
            "- `@pytest.mark.change_detection`: 变化检测相关测试",
            "- `@pytest.mark.api`: API端点测试",
            "",
            "### 运行特定标记的测试",
            "",
            "```bash",
            # 只运行单元测试
            "pytest -m unit",
            "",
            # 只运行解析器测试
            "pytest -m parser",
            "",
            # 运行所有API测试
            "pytest -m api",
            "```",
            "",
            "## 报告文件",
            "",
            "- **HTML覆盖率报告**: `tests/test-coverage/html/index.html`",
            "- **JSON覆盖率数据**: `tests/test-coverage/coverage.json`",
            "- **Markdown报告**: `tests/test-results/TEST_REPORT.md` (本文件)",
            "",
            "## 下一步",
            "",
            "1. 查看HTML覆盖率报告了解详细覆盖情况",
            "2. 针对低覆盖率的模块补充测试用例",
            "3. 确保所有测试通过后再部署到生产环境",
            "",
            "---",
            "",
            f"*报告生成于 {self.timestamp}*",
        ])
        
        return "\n".join(report_lines)
    
    def generate_html_report(self, coverage_data: Dict[str, Any]) -> str:
        """生成HTML格式的报告"""
        html_template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AIRP记忆系统测试报告</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
        }}
        h3 {{
            color: #555;
        }}
        .timestamp {{
            color: #7f8c8d;
            font-style: italic;
        }}
        .summary {{
            background-color: #ecf0f1;
            padding: 15px;
            border-left: 4px solid #3498db;
            margin: 20px 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #3498db;
            color: white;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
        }}
        .badge-high {{
            background-color: #2ecc71;
            color: white;
        }}
        .badge-medium {{
            background-color: #f39c12;
            color: white;
        }}
        .badge-low {{
            background-color: #e74c3c;
            color: white;
        }}
        .code {{
            background-color: #f4f4f4;
            padding: 15px;
            border-radius: 4px;
            overflow-x: auto;
            font-family: 'Courier New', monospace;
        }}
        footer {{
            margin-top: 40px;
            text-align: center;
            color: #7f8c8d;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 AIRP记忆系统测试报告</h1>
        <p class="timestamp">生成时间: {timestamp}</p>
        
        <div class="summary">
            <h2>📋 测试概览</h2>
            <p>本报告包含第一阶段（Week 1-6）功能的完整测试结果。</p>
        </div>
        
        {coverage_section}
        
        <h2>🧪 测试范围</h2>
        
        <h3>单元测试</h3>
        <ul>
            <li><strong>SillyTavern解析器服务</strong> (<code>test_parser_service.py</code>)
                <ul>
                    <li>标签检测（正则表达式）</li>
                    <li>内容分类（指令性/叙事性）</li>
                    <li>World Info解析</li>
                    <li>Chat History解析</li>
                    <li>对话模式识别</li>
                </ul>
            </li>
            <li><strong>变化检测</strong> (<code>test_change_detection.py</code>)
                <ul>
                    <li>World Info变化检测</li>
                    <li>Chat History变化检测</li>
                    <li>状态更新</li>
                    <li>哈希计算</li>
                </ul>
            </li>
        </ul>
        
        <h3>集成测试</h3>
        <ul>
            <li><strong>API端点</strong> (<code>test_api_endpoints.py</code>)
                <ul>
                    <li>健康检查端点</li>
                    <li>OpenAI兼容的Chat Completions端点</li>
                    <li>完整请求处理流程</li>
                    <li>响应格式验证</li>
                </ul>
            </li>
        </ul>
        
        <h2>🔧 测试环境</h2>
        <ul>
            <li><strong>Python版本</strong>: 3.11+</li>
            <li><strong>测试框架</strong>: pytest 7.4.3</li>
            <li><strong>容器化</strong>: Docker (neo4j, redis, test-runner)</li>
        </ul>
        
        <h2>🚀 运行测试</h2>
        
        <h3>使用Docker（推荐）</h3>
        <div class="code">
<pre># 运行所有测试
./tests/run_tests.sh

# 只运行单元测试
./tests/run_tests.sh -u

# 只运行集成测试
./tests/run_tests.sh -i

# 生成覆盖率报告
./tests/run_tests.sh -c

# 详细输出
./tests/run_tests.sh -v</pre>
        </div>
        
        <h3>在本地运行</h3>
        <div class="code">
<pre># 运行所有测试
./tests/run_tests.sh -l

# 使用Python脚本
python tests/run_tests.py -l -c</pre>
        </div>
        
        <h2>📝 测试说明</h2>
        
        <h3>标记说明</h3>
        <ul>
            <li><code>@pytest.mark.unit</code>: 单元测试</li>
            <li><code>@pytest.mark.integration</code>: 集成测试</li>
            <li><code>@pytest.mark.parser</code>: 解析器相关测试</li>
            <li><code>@pytest.mark.change_detection</code>: 变化检测相关测试</li>
            <li><code>@pytest.mark.api</code>: API端点测试</li>
        </ul>
        
        <h3>运行特定标记的测试</h3>
        <div class="code">
<pre># 只运行单元测试
pytest -m unit

# 只运行解析器测试
pytest -m parser

# 运行所有API测试
pytest -m api</pre>
        </div>
        
        <h2>📄 报告文件</h2>
        <ul>
            <li><strong>HTML覆盖率报告</strong>: <code>tests/test-coverage/html/index.html</code></li>
            <li><strong>JSON覆盖率数据</strong>: <code>tests/test-coverage/coverage.json</code></li>
            <li><strong>Markdown报告</strong>: <code>tests/test-results/TEST_REPORT.md</code></li>
        </ul>
        
        <h2>📌 下一步</h2>
        <ol>
            <li>查看HTML覆盖率报告了解详细覆盖情况</li>
            <li>针对低覆盖率的模块补充测试用例</li>
            <li>确保所有测试通过后再部署到生产环境</li>
        </ol>
        
        <footer>
            <p>报告生成于 {timestamp} | AIRP记忆系统测试套件 v1.0</p>
        </footer>
    </div>
</body>
</html>
        """
        
        # 生成覆盖率部分
        coverage_section = ""
        if coverage_data:
            totals = coverage_data.get('totals', {})
            overall_coverage = totals.get('percent_covered', 0)
            
            # 确定覆盖率等级
            if overall_coverage >= 80:
                badge_class = "badge-high"
                badge_text = "优秀"
            elif overall_coverage >= 50:
                badge_class = "badge-medium"
                badge_text = "良好"
            else:
                badge_class = "badge-low"
                badge_text = "需改进"
            
            coverage_section = f"""
        <div class="summary">
            <h2>📈 代码覆盖率</h2>
            <p>
                <strong>总体覆盖率:</strong> 
                <span class="badge {badge_class}">{overall_coverage:.2f}% ({badge_text})</span>
            </p>
            <ul>
                <li><strong>覆盖行数:</strong> {totals.get('covered_lines', 0)} / {totals.get('num_statements', 0)}</li>
                <li><strong>缺失行数:</strong> {totals.get('missing_lines', 0)}</li>
            </ul>
        </div>
        
        <h2>📊 模块覆盖率详情</h2>
        <table>
            <thead>
                <tr>
                    <th>模块</th>
                    <th>覆盖率</th>
                    <th>覆盖行数</th>
                    <th>总行数</th>
                    <th>状态</th>
                </tr>
            </thead>
            <tbody>
            """
            
            # 添加模块数据
            files = coverage_data.get('files', {})
            module_stats = {}
            
            for file_path, data in files.items():
                module_name = Path(file_path).name
                if module_name == '__init__.py':
                    continue
                
                percent = data.get('summary', {}).get('percent_covered', 0)
                covered = data.get('summary', {}).get('covered_lines', 0)
                total = data.get('summary', {}).get('num_statements', 0)
                module_stats[module_name] = (percent, covered, total)
            
            # 排序
            for module_name in sorted(module_stats.keys()):
                percent, covered, total = module_stats[module_name]
                
                # 确定状态
                if percent >= 80:
                    badge = '<span class="badge badge-high">优秀</span>'
                elif percent >= 50:
                    badge = '<span class="badge badge-medium">良好</span>'
                else:
                    badge = '<span class="badge badge-low">需改进</span>'
                
                coverage_section += f"""
                <tr>
                    <td><code>{module_name}</code></td>
                    <td>{percent:.1f}%</td>
                    <td>{covered}</td>
                    <td>{total}</td>
                    <td>{badge}</td>
                </tr>
                """
            
            coverage_section += """
            </tbody>
        </table>
            """
        else:
            coverage_section = """
        <div class="summary">
            <h2>⚠️ 代码覆盖率</h2>
            <p>未找到覆盖率数据。请运行带覆盖率选项的测试：<code>./tests/run_tests.sh -c</code></p>
        </div>
            """
        
        return html_template.format(
            timestamp=self.timestamp,
            coverage_section=coverage_section
        )
    
    def save_reports(self):
        """保存所有报告"""
        # 创建结果目录
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载覆盖率数据
        coverage_data = self.load_coverage_data()
        
        # 生成并保存Markdown报告
        print("生成Markdown报告...")
        md_content = self.generate_markdown_report()
        md_path = self.results_dir / "TEST_REPORT.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        print(f"✓ Markdown报告已保存: {md_path}")
        
        # 生成并保存HTML报告
        print("生成HTML报告...")
        html_content = self.generate_html_report(coverage_data)
        html_path = self.results_dir / "TEST_REPORT.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"✓ HTML报告已保存: {html_path}")
        
        print("\n所有报告生成完成！")
        print(f"查看报告: {html_path}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="生成AIRP记忆系统测试报告"
    )
    parser.add_argument(
        "--results-dir",
        type=str,
        default=None,
        help="测试结果目录（默认: tests/test-results）"
    )
    
    args = parser.parse_args()
    
    # 创建报告生成器
    generator = TestReportGenerator(
        results_dir=args.results_dir
    )
    
    # 生成报告
    generator.save_reports()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
