import io
import os
import re
from typing import Optional, List
import PyPDF2
from docx import Document

# 尝试导入 pymupdf
try:
    import fitz
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False


class FileConverter:
    """文件转换器 - 将各种格式转换为 Markdown"""

    async def convert_to_markdown(self, filename: str, content: bytes) -> str:
        """将文件转换为 Markdown 格式"""
        ext = os.path.splitext(filename)[1].lower()

        if ext == ".pdf":
            return self._convert_pdf_to_markdown(content)
        elif ext == ".docx":
            return self._convert_docx_to_markdown(content)
        elif ext == ".txt":
            return self._convert_txt_to_markdown(content, filename)
        elif ext in (".md", ".markdown"):
            return content.decode('utf-8', errors='ignore')
        else:
            raise ValueError(f"不支持的文件格式: {ext}")

    def _convert_pdf_to_markdown(self, content: bytes) -> str:
        """将 PDF 转换为 Markdown"""
        # 优先使用 pymupdf
        if HAS_PYMUPDF:
            try:
                return self._convert_pdf_with_pymupdf(content)
            except Exception as e:
                print(f"pymupdf 转换失败，尝试 PyPDF2: {e}")

        # 回退到 PyPDF2
        try:
            return self._convert_pdf_with_pypdf2(content)
        except Exception as e:
            raise Exception(f"PDF 转换失败: {str(e)}")

    def _convert_pdf_with_pymupdf(self, content: bytes) -> str:
        """使用 pymupdf 将 PDF 转换为 Markdown"""
        doc = fitz.open(stream=content, filetype="pdf")
        markdown_parts = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            # 获取文本块，包含字体信息
            blocks = page.get_text("dict")["blocks"]

            page_lines = []
            for block in blocks:
                if block["type"] == 0:  # 文本块
                    for line in block["lines"]:
                        text = ""
                        max_size = 0
                        for span in line["spans"]:
                            text += span["text"]
                            max_size = max(max_size, span["size"])

                        text = text.strip()
                        if not text:
                            continue

                        # 根据字体大小判断标题
                        if max_size >= 18:  # 大字体
                            page_lines.append(f"\n# {text}\n")
                        elif max_size >= 16:
                            page_lines.append(f"\n## {text}\n")
                        elif max_size >= 14:
                            page_lines.append(f"\n### {text}\n")
                        else:
                            page_lines.append(text)

            if page_lines:
                markdown_parts.append('\n'.join(page_lines))

        doc.close()
        result = '\n\n'.join(markdown_parts)

        # 清理多余空行
        result = re.sub(r'\n{3,}', '\n\n', result)

        if not result:
            return "# PDF文件\n\n*无法提取文本内容*"
        return result

    def _convert_pdf_with_pypdf2(self, content: bytes) -> str:
        """使用 PyPDF2 将 PDF 转换为 Markdown"""
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
        markdown_parts = []

        for i, page in enumerate(pdf_reader.pages):
            try:
                text = page.extract_text()
                if text and text.strip():
                    # 清理文本
                    cleaned_text = self._clean_text(text)
                    # 尝试识别标题
                    lines = cleaned_text.split('\n')
                    formatted_lines = []

                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue

                        # 检测可能的标题（全大写、短行、数字开头等）
                        if self._is_likely_heading(line):
                            formatted_lines.append(f"\n## {line}\n")
                        else:
                            formatted_lines.append(line)

                    markdown_parts.append('\n'.join(formatted_lines))
            except Exception as e:
                print(f"警告: 解析PDF页面 {i+1} 失败: {e}")
                continue

        result = '\n\n'.join(markdown_parts)
        if not result:
            return "# PDF文件\n\n*无法提取文本内容*"
        return result

    def _convert_docx_to_markdown(self, content: bytes) -> str:
        """将 DOCX 转换为 Markdown"""
        try:
            doc = Document(io.BytesIO(content))
            markdown_parts = []

            for paragraph in doc.paragraphs:
                text = paragraph.text.strip()
                if not text:
                    markdown_parts.append('')
                    continue

                # 根据 Word 样式转换为 Markdown
                style_name = paragraph.style.name.lower() if paragraph.style else ''

                if 'heading 1' in style_name or '标题 1' in style_name:
                    markdown_parts.append(f'\n# {text}\n')
                elif 'heading 2' in style_name or '标题 2' in style_name:
                    markdown_parts.append(f'\n## {text}\n')
                elif 'heading 3' in style_name or '标题 3' in style_name:
                    markdown_parts.append(f'\n### {text}\n')
                elif 'heading 4' in style_name or '标题 4' in style_name:
                    markdown_parts.append(f'\n#### {text}\n')
                elif 'list' in style_name or '列表' in style_name:
                    markdown_parts.append(f'- {text}')
                else:
                    # 检测是否是数字列表
                    if re.match(r'^\d+[\.\)]\s', text):
                        markdown_parts.append(text)
                    # 检测是否是项目符号
                    elif text.startswith('•') or text.startswith('·') or text.startswith('-'):
                        markdown_parts.append(f'- {text[1:].strip()}')
                    else:
                        markdown_parts.append(text)

            result = '\n'.join(markdown_parts)
            # 清理多余的空行
            result = re.sub(r'\n{3,}', '\n\n', result)
            return result if result else '# DOCX文件\n\n*文档内容为空*'
        except Exception as e:
            raise Exception(f"DOCX 转换失败: {str(e)}")

    def _convert_txt_to_markdown(self, content: bytes, filename: str) -> str:
        """将 TXT 转换为 Markdown - 支持所有格式"""
        try:
            # 尝试多种编码
            text = None
            for encoding in ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'gb18030', 'latin-1']:
                try:
                    text = content.decode(encoding)
                    if text and text.strip():
                        break
                except (UnicodeDecodeError, LookupError):
                    continue

            if not text or not text.strip():
                return f'# {filename}\n\n*文件内容为空*'

            # 检测文本格式类型
            text_format = self._detect_text_format(text)
            print(f"检测到文本格式: {text_format}")

            # 使用文件名作为标题
            name_without_ext = os.path.splitext(filename)[0]

            # 根据格式类型选择转换策略
            if text_format == 'qa':
                return self._convert_qa_format(text, name_without_ext)
            elif text_format == 'dialogue':
                return self._convert_dialogue_format(text, name_without_ext)
            elif text_format == 'hierarchical':
                return self._convert_hierarchical_format(text, name_without_ext, filename)
            elif text_format == 'list':
                return self._convert_list_format(text, name_without_ext)
            elif text_format == 'code':
                return self._convert_code_format(text, name_without_ext, filename)
            else:
                return self._convert_plain_format(text, name_without_ext)
        except Exception as e:
            raise Exception(f"TXT 转换失败: {str(e)}")

    def _detect_text_format(self, text: str) -> str:
        """检测文本格式类型"""
        lines = text.split('\n')
        total_lines = len(lines)

        # 统计各种格式特征
        qa_count = 0          # 问答对数量
        dialogue_count = 0    # 对话数量
        heading_count = 0     # 标题数量
        list_count = 0        # 列表项数量

        qa_patterns = [
            r'^问[：:]\s*',
            r'^Q[：:]\s*',
            r'^问题[：:]\s*',
            r'^Question[：:]\s*',
        ]
        answer_patterns = [
            r'^答[：:]\s*',
            r'^A[：:]\s*',
            r'^回答[：:]\s*',
            r'^Answer[：:]\s*',
        ]
        dialogue_patterns = [
            r'^甲[：:]\s*',
            r'^乙[：:]\s*',
            r'^丙[：:]\s*',
            r'^丁[：:]\s*',
            r'^A[：:]\s*',
            r'^B[：:]\s*',
            r'^C[：:]\s*',
            r'^D[：:]\s*',
            r'^张三[：:]\s*',
            r'^李四[：:]\s*',
            r'^王五[：:]\s*',
            r'^老师[：:]\s*',
            r'^学生[：:]\s*',
            r'^ interviewer[：:]\s*',
            r'^ interviewee[：:]\s*',
        ]
        list_patterns = [
            r'^\d+[\.\)]\s+',
            r'^[•·□■◆◇○●]\s*',
            r'^[-*]\s+',
            r'^[一二三四五六七八九十]+[、．.]\s*',
        ]

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # 检测问答格式
            for pattern in qa_patterns:
                if re.match(pattern, stripped, re.IGNORECASE):
                    qa_count += 1
                    break

            # 检测对话格式
            for pattern in dialogue_patterns:
                if re.match(pattern, stripped):
                    dialogue_count += 1
                    break

            # 检测标题
            if self._detect_heading_level(stripped, 0, lines) > 0:
                heading_count += 1

            # 检测列表
            for pattern in list_patterns:
                if re.match(pattern, stripped):
                    list_count += 1
                    break

        # 判断格式类型
        # 如果问答对超过总行数的 20%，认为是问答格式
        if qa_count >= max(3, total_lines * 0.15):
            return 'qa'

        # 如果对话超过总行数的 20%，认为是对话格式
        if dialogue_count >= max(3, total_lines * 0.15):
            return 'dialogue'

        # 如果标题超过 3 个，认为是有层级结构的
        if heading_count >= 3:
            return 'hierarchical'

        # 如果列表项超过 30%，认为是列表格式
        if list_count >= total_lines * 0.3:
            return 'list'

        # 检测是否是代码文件
        if self._is_code_content(text):
            return 'code'

        # 默认为纯文本格式
        return 'plain'

    def _convert_qa_format(self, text: str, title: str) -> str:
        """转换问答格式的文本"""
        lines = text.split('\n')
        markdown_parts = [f'# {title}\n']

        current_question = None
        current_answer = []
        in_answer = False

        qa_patterns = [
            r'^问[：:]\s*(.*)',
            r'^Q[：:]\s*(.*)',
            r'^问题[：:]\s*(.*)',
            r'^Question[：:]\s*(.*)',
        ]
        answer_patterns = [
            r'^答[：:]\s*(.*)',
            r'^A[：:]\s*(.*)',
            r'^回答[：:]\s*(.*)',
            r'^Answer[：:]\s*(.*)',
        ]

        for line in lines:
            stripped = line.strip()
            if not stripped:
                if in_answer:
                    current_answer.append('')
                continue

            # 检测问题
            is_question = False
            for pattern in qa_patterns:
                match = re.match(pattern, stripped, re.IGNORECASE)
                if match:
                    # 保存上一个问答对
                    if current_question and current_answer:
                        answer_text = '\n'.join(current_answer).strip()
                        markdown_parts.append(f'\n## {current_question}\n')
                        markdown_parts.append(f'\n{answer_text}\n')

                    current_question = match.group(1).strip() or stripped
                    current_answer = []
                    in_answer = True
                    is_question = True
                    break

            if is_question:
                continue

            # 检测答案
            is_answer = False
            for pattern in answer_patterns:
                match = re.match(pattern, stripped, re.IGNORECASE)
                if match:
                    answer_content = match.group(1).strip()
                    if answer_content:
                        current_answer.append(answer_content)
                    in_answer = True
                    is_answer = True
                    break

            if is_answer:
                continue

            # 答案内容
            if in_answer:
                current_answer.append(stripped)

        # 保存最后一个问答对
        if current_question and current_answer:
            answer_text = '\n'.join(current_answer).strip()
            markdown_parts.append(f'\n## {current_question}\n')
            markdown_parts.append(f'\n{answer_text}\n')

        result = '\n'.join(markdown_parts)
        result = re.sub(r'\n{3,}', '\n\n', result)
        return result

    def _convert_dialogue_format(self, text: str, title: str) -> str:
        """转换对话格式的文本"""
        lines = text.split('\n')
        markdown_parts = [f'# {title}\n']

        dialogue_patterns = [
            r'^(甲|乙|丙|丁|A|B|C|D|张三|李四|王五|老师|学生|interviewer|interviewee)[：:]\s*(.*)',
        ]

        for line in lines:
            stripped = line.strip()
            if not stripped:
                markdown_parts.append('')
                continue

            matched = False
            for pattern in dialogue_patterns:
                match = re.match(pattern, stripped, re.IGNORECASE)
                if match:
                    speaker = match.group(1)
                    content = match.group(2).strip()
                    markdown_parts.append(f'\n**{speaker}**：{content}\n')
                    matched = True
                    break

            if not matched:
                markdown_parts.append(stripped)

        result = '\n'.join(markdown_parts)
        result = re.sub(r'\n{3,}', '\n\n', result)
        return result

    def _convert_hierarchical_format(self, text: str, title: str, filename: str) -> str:
        """转换有层级结构的文本"""
        lines = text.split('\n')
        markdown_parts = [f'# {title}\n']

        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                markdown_parts.append('')
                continue

            heading_level = self._detect_heading_level(stripped, i, lines)
            if heading_level > 0:
                prefix = '#' * heading_level
                markdown_parts.append(f'\n{prefix} {stripped}\n')
            else:
                markdown_parts.append(stripped)

        result = '\n'.join(markdown_parts)
        result = re.sub(r'\n{3,}', '\n\n', result)
        return result

    def _convert_list_format(self, text: str, title: str) -> str:
        """转换列表格式的文本"""
        lines = text.split('\n')
        markdown_parts = [f'# {title}\n']

        for line in lines:
            stripped = line.strip()
            if not stripped:
                markdown_parts.append('')
                continue

            # 数字列表
            if re.match(r'^\d+[\.\)]\s+', stripped):
                markdown_parts.append(stripped)
                continue

            # 符号列表
            if stripped.startswith(('•', '·', '□', '■', '◆', '◇', '○', '●')):
                markdown_parts.append(f'- {stripped[1:].strip()}')
                continue

            # - 或 * 列表
            if re.match(r'^[-*]\s+', stripped):
                markdown_parts.append(stripped)
                continue

            # 中文数字列表
            if re.match(r'^[一二三四五六七八九十]+[、．.]\s*', stripped):
                markdown_parts.append(f'\n## {stripped}\n')
                continue

            markdown_parts.append(stripped)

        result = '\n'.join(markdown_parts)
        result = re.sub(r'\n{3,}', '\n\n', result)
        return result

    def _convert_code_format(self, text: str, title: str, filename: str) -> str:
        """转换代码格式的文本"""
        lang = self._detect_code_language(filename)
        return f'# {title}\n\n```{lang}\n{text}\n```'

    def _convert_plain_format(self, text: str, title: str) -> str:
        """转换纯文本格式 - 尝试提取结构"""
        lines = text.split('\n')
        markdown_parts = [f'# {title}\n']

        # 尝试按段落分割（空行分隔）
        paragraphs = []
        current_para = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                if current_para:
                    paragraphs.append('\n'.join(current_para))
                    current_para = []
            else:
                current_para.append(stripped)

        if current_para:
            paragraphs.append('\n'.join(current_para))

        # 如果段落很少，直接返回
        if len(paragraphs) <= 3:
            for para in paragraphs:
                markdown_parts.append(f'\n{para}\n')
            result = '\n'.join(markdown_parts)
            return re.sub(r'\n{3,}', '\n\n', result)

        # 尝试提取关键词作为节点
        # 每个段落作为一个知识点
        for i, para in enumerate(paragraphs):
            if not para.strip():
                continue

            # 尝试从段落第一句提取标题
            first_sentence = para.split('。')[0].split('！')[0].split('？')[0].split('.')[0]
            if len(first_sentence) < 50 and len(first_sentence) > 5:
                markdown_parts.append(f'\n## {first_sentence}\n')
                # 剩余内容作为描述
                remaining = para[len(first_sentence):].strip()
                if remaining:
                    markdown_parts.append(remaining)
            else:
                markdown_parts.append(f'\n{para}\n')

        result = '\n'.join(markdown_parts)
        result = re.sub(r'\n{3,}', '\n\n', result)
        return result

    def _is_code_content(self, text: str) -> bool:
        """检测是否是代码内容"""
        code_indicators = [
            'def ', 'class ', 'import ', 'from ', 'function ',
            'var ', 'let ', 'const ', 'public ', 'private ',
            '#include', 'using namespace', 'print(', 'console.log',
            'if __name__', 'async ', 'await ', 'return ',
        ]
        # 如果包含多个代码特征，认为是代码文件
        count = sum(1 for indicator in code_indicators if indicator in text)
        return count >= 3

    def _detect_code_language(self, filename: str) -> str:
        """根据文件名检测代码语言"""
        ext = os.path.splitext(filename)[1].lower()
        lang_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java',
            '.c': 'c',
            '.cpp': 'cpp',
            '.h': 'c',
            '.hpp': 'cpp',
            '.cs': 'csharp',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.r': 'r',
            '.m': 'matlab',
            '.sql': 'sql',
            '.sh': 'bash',
            '.bash': 'bash',
            '.ps1': 'powershell',
            '.html': 'html',
            '.css': 'css',
            '.xml': 'xml',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.md': 'markdown',
        }
        return lang_map.get(ext, '')

    def _detect_heading_level(self, line: str, line_index: int, all_lines: List[str]) -> int:
        """检测标题级别，返回 0 表示不是标题"""
        # 空行不是标题
        if not line:
            return 0

        # 过长的行不是标题
        if len(line) > 100:
            return 0

        # 以标点结尾的行通常不是标题
        if line.endswith(('。', '，', '；', '！', '？', '.', ',', ';', '!', '?', '：', ':')):
            return 0

        # Markdown 标题格式
        match = re.match(r'^(#{1,6})\s+', line)
        if match:
            return len(match.group(1))

        # 全大写短行可能是标题
        if line.isupper() and 5 < len(line) < 60:
            return 1

        # 数字编号标题
        if re.match(r'^\d+[\.\)]\s*$', line) or re.match(r'^\d+\s*$', line):
            # 单独的数字可能是序号
            return 0

        # 带编号的标题（如 "1. 引言"）
        if re.match(r'^\d+[\.\)]\s+\S', line) and len(line) < 80:
            level = line.count('.') + 1
            return min(level, 4)

        # 中文章节标识
        chapter_patterns = [
            (r'^第[一二三四五六七八九十百千\d]+[章篇]', 1),
            (r'^第[一二三四五六七八九十百千\d]+[节部]', 2),
            (r'^[一二三四五六七八九十]+[、．.]', 2),
            (r'^[（\(][一二三四五六七八九十\d]+[）\)]', 3),
        ]
        for pattern, level in chapter_patterns:
            if re.match(pattern, line):
                return level

        # 特殊标记
        if line.startswith('【') and line.endswith('】'):
            return 2

        # 短行且下一行是分隔线
        if line_index + 1 < len(all_lines):
            next_line = all_lines[line_index + 1].strip()
            if re.match(r'^[-*=]{3,}\s*$', next_line):
                return 1

        return 0

    def _clean_text(self, text: str) -> str:
        """清理文本"""
        # 移除多余的空白字符
        text = re.sub(r'[ \t]+', ' ', text)
        # 移除页眉页脚常见模式
        text = re.sub(r'第\s*\d+\s*页', '', text)
        text = re.sub(r'Page\s*\d+', '', text, flags=re.IGNORECASE)
        # 清理特殊字符
        text = text.replace('\x00', '')
        return text.strip()

    def _is_likely_heading(self, line: str) -> bool:
        """判断是否可能是标题"""
        # 短行（少于50字符）且不以标点结尾
        if len(line) < 50 and not line.endswith(('。', '，', '；', '！', '？', '.', ',', ';', '!', '?')):
            # 全大写或首字母大写
            if line.isupper() or (line and line[0].isupper() and len(line) < 30):
                return True
            # 数字开头的标题
            if re.match(r'^\d+[\.\)]\s*\S', line):
                return True
            # 包含关键词
            heading_keywords = ['第一章', '第二章', '第三章', '第四章', '第五章',
                               '一、', '二、', '三、', '四、', '五、',
                               'Chapter', 'Section', 'Part']
            if any(keyword in line for keyword in heading_keywords):
                return True
        return False
