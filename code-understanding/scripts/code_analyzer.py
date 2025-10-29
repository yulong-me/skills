#!/usr/bin/env python3
"""
Code Understanding Tool - 代码理解工具

This script recursively analyzes a codebase and generates hierarchical README.md files
at each directory level with structured documentation content.
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re
import json
from datetime import datetime

class CodeAnalyzer:
    """代码分析器主类"""

    def __init__(self, root_path: str, output_format: str = "markdown"):
        self.root_path = Path(root_path).resolve()
        self.output_format = output_format
        self.supported_extensions = {
            '.py': 'python',
            '.js': 'javascript', '.ts': 'typescript', '.jsx': 'react', '.tsx': 'react',
            '.java': 'java', '.cpp': 'cpp', '.c': 'c', '.cs': 'csharp',
            '.go': 'go', '.rs': 'rust', '.php': 'php', '.rb': 'ruby',
            '.swift': 'swift', '.kt': 'kotlin', '.scala': 'scala',
            '.html': 'html', '.css': 'css', '.scss': 'scss', '.sass': 'sass',
            '.sql': 'sql', '.sh': 'shell', '.bash': 'shell',
            '.json': 'json', '.yaml': 'yaml', '.yml': 'yaml', '.xml': 'xml',
            '.md': 'markdown', '.txt': 'text', '.dockerfile': 'docker'
        }

    def is_binary_file(self, file_path: Path) -> bool:
        """检查是否为二进制文件"""
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                return b'\0' in chunk
        except:
            return True

    def get_file_language(self, file_path: Path) -> str:
        """根据文件扩展名获取编程语言"""
        suffix = file_path.suffix.lower()
        return self.supported_extensions.get(suffix, 'unknown')

    def analyze_file(self, file_path: Path) -> Dict:
        """分析单个文件"""
        try:
            if self.is_binary_file(file_path):
                return {
                    'name': file_path.name,
                    'type': 'binary',
                    'size': file_path.stat().st_size,
                    'language': 'binary'
                }

            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            language = self.get_file_language(file_path)
            lines = len(content.splitlines())

            # 基本代码分析
            analysis = {
                'name': file_path.name,
                'type': 'source',
                'language': language,
                'lines': lines,
                'size': file_path.stat().st_size,
                'functions': [],
                'classes': [],
                'imports': [],
                'description': self.extract_description(content, language)
            }

            # 根据语言进行特定分析
            if language == 'python':
                analysis.update(self.analyze_python_file(content))
            elif language in ['javascript', 'typescript']:
                analysis.update(self.analyze_js_file(content))
            elif language == 'java':
                analysis.update(self.analyze_java_file(content))

            return analysis

        except Exception as e:
            return {
                'name': file_path.name,
                'type': 'error',
                'error': str(e)
            }

    def extract_description(self, content: str, language: str) -> str:
        """提取文件描述"""
        lines = content.splitlines()[:20]  # 只检查前20行

        for line in lines:
            line = line.strip()
            # 寻找注释行
            if line.startswith('#') or line.startswith('//') or line.startswith('/*'):
                desc = re.sub(r'^[#/*\s]+', '', line).strip()
                if len(desc) > 10 and len(desc) < 200:
                    return desc
            # 寻找docstring
            if '"""' in line or "'''" in line:
                desc = re.sub(r'["\'\s]+', '', line).strip()
                if len(desc) > 10 and len(desc) < 200:
                    return desc

        return f"{language}源代码文件"

    def analyze_python_file(self, content: str) -> Dict:
        """分析Python文件"""
        functions = re.findall(r'def\s+(\w+)\s*\(', content)
        classes = re.findall(r'class\s+(\w+)', content)
        imports = re.findall(r'^(?:from|import)\s+(\S+)', content, re.MULTILINE)

        return {
            'functions': functions[:10],  # 限制显示数量
            'classes': classes[:10],
            'imports': imports[:10]
        }

    def analyze_js_file(self, content: str) -> Dict:
        """分析JavaScript/TypeScript文件"""
        functions = re.findall(r'(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s+)?\()', content)
        functions = [f[0] or f[1] for f in functions if f[0] or f[1]]
        classes = re.findall(r'class\s+(\w+)', content)
        imports = re.findall(r'^(?:import.*from\s+[\'"](\S+)[\'"]|const\s+.*=\s*require\([\'"](\S+)[\'"]\))', content, re.MULTILINE)
        imports = [imp[0] or imp[1] for imp in imports if imp[0] or imp[1]]

        return {
            'functions': functions[:10],
            'classes': classes[:10],
            'imports': imports[:10]
        }

    def analyze_java_file(self, content: str) -> Dict:
        """分析Java文件"""
        classes = re.findall(r'(?:public\s+)?class\s+(\w+)', content)
        methods = re.findall(r'(?:public|private|protected)?\s*(?:static)?\s*\w+\s+(\w+)\s*\(', content)
        imports = re.findall(r'import\s+([\w\.]+);', content)

        return {
            'classes': classes[:10],
            'functions': methods[:10],
            'imports': imports[:10]
        }

    def analyze_directory(self, dir_path: Path) -> Dict:
        """分析目录"""
        if not dir_path.exists():
            return {'error': f'Directory {dir_path} does not exist'}

        directories = []
        files = []

        try:
            for item in dir_path.iterdir():
                if item.name.startswith('.'):
                    continue

                if item.is_dir():
                    directories.append(item)
                else:
                    files.append(self.analyze_file(item))
        except PermissionError:
            return {'error': f'Permission denied accessing {dir_path}'}

        return {
            'name': dir_path.name,
            'path': str(dir_path.relative_to(self.root_path)),
            'directories': sorted(directories, key=lambda x: x.name.lower()),
            'files': sorted(files, key=lambda x: x['name'].lower()),
            'stats': {
                'total_files': len(files),
                'total_dirs': len(directories),
                'languages': self.count_languages(files)
            }
        }

    def count_languages(self, files: List[Dict]) -> Dict[str, int]:
        """统计编程语言"""
        lang_count = {}
        for file_info in files:
            lang = file_info.get('language', 'unknown')
            lang_count[lang] = lang_count.get(lang, 0) + 1
        return dict(sorted(lang_count.items(), key=lambda x: x[1], reverse=True))

    def generate_readme_content(self, dir_analysis: Dict, depth: int = 0) -> str:
        """生成README内容"""
        if 'error' in dir_analysis:
            return f"# 错误\n\n无法分析此目录: {dir_analysis['error']}"

        name = dir_analysis['name']
        path = dir_analysis['path']
        stats = dir_analysis['stats']

        content = f"""# {name}

## 模块概述

此模块包含 {stats['total_files']} 个文件和 {stats['total_dirs']} 个子目录。

**目录路径:** `{path}`
**生成时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**主要编程语言:**
"""

        # 添加语言统计
        for lang, count in list(stats['languages'].items())[:5]:
            content += f"- {lang}: {count} 个文件\n"

        content += f"\n## 模块讲解\n\n"

        # 添加子目录信息
        if dir_analysis['directories']:
            content += "### 子目录\n\n"
            for subdir in dir_analysis['directories']:
                content += f"- **{subdir.name}/** - 包含相关模块和文件\n"
            content += "\n"

        # 添加文件摘要
        if dir_analysis['files']:
            content += "### 文件摘要\n\n"

            # 按类型分组文件
            source_files = [f for f in dir_analysis['files'] if f['type'] == 'source']
            other_files = [f for f in dir_analysis['files'] if f['type'] != 'source']

            if source_files:
                content += "#### 源代码文件\n\n"
                for file_info in source_files:
                    content += self.format_file_summary(file_info, depth)

            if other_files:
                content += "#### 其他文件\n\n"
                for file_info in other_files:
                    content += f"- **{file_info['name']}** ({file_info['type']})\n"

        content += f"\n---\n*此文档由代码理解工具自动生成*"

        return content

    def format_file_summary(self, file_info: Dict, depth: int) -> str:
        """格式化文件摘要"""
        name = file_info['name']
        language = file_info['language']
        lines = file_info.get('lines', 'N/A')
        description = file_info.get('description', f'{language}源代码文件')

        summary = f"##### {name}\n\n"
        summary += f"**语言:** {language}  \n"
        summary += f"**行数:** {lines}  \n"
        summary += f"**描述:** {description}\n\n"

        # 添加函数/类信息
        if file_info.get('functions'):
            funcs = file_info['functions'][:5]  # 只显示前5个
            summary += f"**主要函数:** `{'`, `'.join(funcs)}`\n\n"

        if file_info.get('classes'):
            classes = file_info['classes'][:5]  # 只显示前5个
            summary += f"**主要类:** `{'`, `'.join(classes)}`\n\n"

        if file_info.get('imports'):
            imports = file_info['imports'][:3]  # 只显示前3个
            summary += f"**依赖项:** `{'`, `'.join(imports)}`\n\n"

        return summary

    def generate_hierarchical_readmes(self, dry_run: bool = False) -> None:
        """递归生成层级化README文件"""
        if not self.root_path.exists():
            print(f"错误: 路径 {self.root_path} 不存在")
            return

        print(f"开始分析代码库: {self.root_path}")

        def process_directory(dir_path: Path, relative_path: str = ""):
            """处理单个目录"""
            print(f"正在处理: {relative_path or '根目录'}")

            # 分析当前目录
            analysis = self.analyze_directory(dir_path)

            # 生成README内容
            readme_content = self.generate_readme_content(analysis, relative_path.count('/'))

            # 确定README文件路径
            readme_path = dir_path / 'README.md'

            if not dry_run:
                # 检查是否已存在README
                if readme_path.exists():
                    backup_path = readme_path.with_suffix('.md.backup')
                    print(f"  备份现有README: {backup_path}")
                    readme_path.rename(backup_path)

                # 写入新的README
                try:
                    with open(readme_path, 'w', encoding='utf-8') as f:
                        f.write(readme_content)
                    print(f"  ✓ 生成README: {readme_path}")
                except Exception as e:
                    print(f"  ✗ 写入失败: {e}")
            else:
                print(f"  [预览] 将生成README: {readme_path}")
                print(f"  [预览] 内容长度: {len(readme_content)} 字符")

            # 递归处理子目录
            for subdir in analysis.get('directories', []):
                process_directory(subdir, f"{relative_path}/{subdir.name}" if relative_path else subdir.name)

        process_directory(self.root_path)
        print("\n代码分析完成!")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='代码理解工具 - 生成层级化README文档')
    parser.add_argument('path', nargs='?', default='.', help='要分析的代码路径 (默认: 当前目录)')
    parser.add_argument('--dry-run', action='store_true', help='预览模式，不实际写入文件')
    parser.add_argument('--format', choices=['markdown', 'json'], default='markdown', help='输出格式')

    args = parser.parse_args()

    analyzer = CodeAnalyzer(args.path, args.format)
    analyzer.generate_hierarchical_readmes(dry_run=args.dry_run)

if __name__ == "__main__":
    main()