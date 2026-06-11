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
        """
        使用 pymupdf 将 PDF 转换为 Markdown

        改进的标题识别策略：
        1. 数字编号标题（1.、1.1、1.1.1 等）
        2. 中文章节标题（第一章、一、等）
        3. 字体大小差异（作为辅助判断）
        4. 加粗文本检测
        """
        doc = fitz.open(stream=content, filetype="pdf")
        markdown_parts = []

        # 收集所有字体大小，用于动态计算阈值
        all_font_sizes = []
        for page_num in range(min(5, len(doc))):  # 只分析前5页
            page = doc[page_num]
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if block["type"] == 0:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            if span["text"].strip():
                                all_font_sizes.append(round(span["size"], 1))

        # 计算字体大小阈值（使用统计方法）
        if all_font_sizes:
            avg_size = sum(all_font_sizes) / len(all_font_sizes)
            # 标题字体通常比正文大 20% 以上
            heading_threshold = avg_size * 1.2
        else:
            avg_size = 12
            heading_threshold = 14

        for page_num in range(len(doc)):
            page = doc[page_num]
            blocks = page.get_text("dict")["blocks"]

            page_lines = []
            for block in blocks:
                if block["type"] == 0:  # 文本块
                    for line in block["lines"]:
                        text = ""
                        max_size = 0
                        is_bold = False

                        for span in line["spans"]:
                            text += span["text"]
                            max_size = max(max_size, span["size"])
                            # 检测加粗（字体名称包含 Bold 或 weight >= 700）
                            font_name = span.get("font", "").lower()
                            if "bold" in font_name or span.get("weight", 0) >= 700:
                                is_bold = True

                        text = text.strip()
                        if not text:
                            continue

                        # 跳过页码、目录点号等
                        if re.match(r'^[\d.]+$', text) or re.match(r'^.{0,5}$', text):
                            continue
                        if '...' in text and len(text) < 20:
                            continue

                        # ============ 标题识别策略 ============

                        # 策略1：数字编号标题（最可靠）
                        # 匹配：1.、1.1、1.1.1、1.1.1.1 等
                        heading_level = self._detect_numbered_heading(text)
                        if heading_level > 0:
                            prefix = '#' * heading_level
                            page_lines.append(f"\n{prefix} {text}\n")
                            continue

                        # 策略2：中文章节标题
                        # 匹配：第一章、一、（一）等
                        heading_level = self._detect_chinese_heading(text)
                        if heading_level > 0:
                            prefix = '#' * heading_level
                            page_lines.append(f"\n{prefix} {text}\n")
                            continue

                        # 策略3：英文标题格式
                        # 匹配：Chapter 1、Section 1.1 等
                        heading_level = self._detect_english_heading(text)
                        if heading_level > 0:
                            prefix = '#' * heading_level
                            page_lines.append(f"\n{prefix} {text}\n")
                            continue

                        # 策略4：字体大小 + 加粗判断
                        if max_size >= heading_threshold:
                            # 根据字体大小差异判断级别
                            if max_size >= avg_size * 1.5:
                                page_lines.append(f"\n# {text}\n")
                            elif max_size >= avg_size * 1.3:
                                page_lines.append(f"\n## {text}\n")
                            elif max_size >= heading_threshold:
                                page_lines.append(f"\n### {text}\n")
                            continue

                        # 策略5：加粗短文本（可能是小标题）
                        if is_bold and len(text) < 50 and not text.endswith(('。', '，', '；')):
                            page_lines.append(f"\n### {text}\n")
                            continue

                        # 普通文本
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

    def _detect_numbered_heading(self, text: str) -> int:
        """
        检测数字编号标题的级别

        匹配规则：
        - "1 xxx" 或 "1." → 1级标题
        - "1.1 xxx" 或 "1.1." → 2级标题
        - "1.1.1 xxx" 或 "1.1.1." 或 "1.1.1、" → 3级标题
        - "1.1.1.1 xxx" → 4级标题

        Returns:
            int: 标题级别（1-4），0 表示不是标题
        """
        # 去除前导空格
        text = text.strip()

        # 首先尝试提取完整的编号部分（如 "2.3.1"）
        # 使用非贪婪匹配，确保能匹配到完整的编号
        match = re.match(r'^((?:\d+\.)+\d+)\s*(.+)', text)
        if match:
            number_part = match.group(1)  # 如 "2.3.1"
            rest = match.group(2)         # 如 "HashMap 的原理" 或 ". xxx"

            # 检查 rest 是否以分隔符开头
            rest_match = re.match(r'^[\.\)）、：:]\s*(.+)', rest)
            if rest_match:
                content = rest_match.group(1).strip()
            else:
                content = rest.strip()

            # 只有内容较短时才认为是标题
            if len(content) < 80 and content:
                # 计算级别（点号数量 + 1）
                level = number_part.count('.') + 1
                return min(level, 4)

        # 模式2：单级数字编号（如 "1 引言" 或 "1. 引言"）
        match = re.match(r'^(\d+)\s*[\.\)）、：:]\s*(.+)', text)
        if match:
            content = match.group(2).strip()
            if len(content) < 80 and content:
                return 1

        # 模式3：单级数字 + 空格 + 文本（无分隔符）
        match = re.match(r'^(\d+)\s+([^\d].+)', text)
        if match:
            content = match.group(2).strip()
            # 确保不是普通句子（检查内容是否像标题）
            if len(content) < 60 and not content.startswith(('的', '是', '在', '了')):
                return 1

        return 0

    def _detect_chinese_heading(self, text: str) -> int:
        """
        检测中文章节标题的级别

        匹配规则：
        - 第一章、第二章 → 1级标题
        - 第一节、第二节 → 2级标题
        - 一、二、三、 → 2级标题
        - （一）（二） → 3级标题

        Returns:
            int: 标题级别（1-3），0 表示不是标题
        """
        text = text.strip()

        # 第X章、第X篇 → 1级
        if re.match(r'^第[一二三四五六七八九十百千\d]+[章篇]', text):
            return 1

        # 第X节、第X部 → 2级
        if re.match(r'^第[一二三四五六七八九十百千\d]+[节部]', text):
            return 2

        # 一、二、三、 → 2级
        if re.match(r'^[一二三四五六七八九十]+[、．.\s]', text) and len(text) < 60:
            return 2

        # （一）（二） → 3级
        if re.match(r'^[（\(][一二三四五六七八九十\d]+[）\)]', text):
            return 3

        return 0

    def _detect_english_heading(self, text: str) -> int:
        """
        检测英文标题格式

        匹配规则：
        - Chapter 1、Chapter 1.1 → 1级标题
        - Section 1.1 → 2级标题
        - Part I → 1级标题

        Returns:
            int: 标题级别（1-2），0 表示不是标题
        """
        text = text.strip()

        # Chapter X → 1级
        if re.match(r'^Chapter\s+\d+', text, re.IGNORECASE):
            return 1

        # Part X → 1级
        if re.match(r'^Part\s+[IVX\d]+', text, re.IGNORECASE):
            return 1

        # Section X.X → 2级
        if re.match(r'^Section\s+\d+\.\d+', text, re.IGNORECASE):
            return 2

        # 全大写短文本 → 1级（可能是大标题）
        if text.isupper() and 5 < len(text) < 60:
            return 1

        return 0

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
        """转换有层级结构的文本 - 支持缩进格式"""
        # 先检测并移除目录部分
        text = self._remove_toc(text)

        lines = text.split('\n')
        markdown_parts = [f'# {title}\n']

        # 检测是否是缩进格式（使用制表符或空格缩进）
        has_indentation = self._detect_indentation_format(lines)

        if has_indentation:
            # 使用缩进格式转换
            return self._convert_indented_to_markdown(text, title)

        # 原有的标题检测逻辑
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

    def _remove_toc(self, text: str) -> str:
        """
        检测并移除目录部分

        目录特征：
        1. 以"目录"、"目 录"、"Table of Contents"等开头
        2. 包含大量页码引用（如 "......9"、"...10"）
        3. 通常在文档开头部分

        Args:
            text: 原始文本

        Returns:
            str: 移除目录后的文本
        """
        lines = text.split('\n')
        toc_end_index = 0
        in_toc = False

        # 目录标题的模式
        toc_title_patterns = [
            r'^目录\s*$',
            r'^目\s*录\s*$',
            r'^Table\s+of\s+Contents\s*$',
            r'^TOC\s*$',
            r'^CONTENTS\s*$',
        ]

        # 目录项的模式（包含页码引用）
        toc_item_patterns = [
            r'\.{3,}\s*\d+\s*$',  # ......9
            r'…+\s*\d+\s*$',      # ……9
            r'\s+\d+\s*$',        # 空格 + 数字（页码）
            r'^\d+[\.\)]\s+.*\.{3,}\s*\d+\s*$',  # 1.1 标题......9
            r'^\d+[\.\)]\s+.*\s+\d+\s*$',  # 1.1 标题 9
            r'^\d+\.\d+[\.\)]\s+.*\.{3,}\s*\d+\s*$',  # 1.1.1 标题......9
            r'^\d+\.\d+[\.\)]\s+.*\s+\d+\s*$',  # 1.1.1 标题 9
        ]

        for i, line in enumerate(lines):
            stripped = line.strip()

            # 检测目录标题
            if not in_toc:
                for pattern in toc_title_patterns:
                    if re.match(pattern, stripped, re.IGNORECASE):
                        in_toc = True
                        toc_end_index = i
                        break
                continue

            # 在目录中，检测目录结束
            if in_toc:
                # 如果行不为空，检查是否是目录项
                if stripped:
                    is_toc_item = False
                    for pattern in toc_item_patterns:
                        if re.match(pattern, stripped):
                            is_toc_item = True
                            break

                    # 如果不是目录项，可能是目录结束
                    if not is_toc_item:
                        # 检查是否是正文开始（有标题格式）
                        if re.match(r'^第[一二三四五六七八九十百千\d]+[章篇]', stripped):
                            toc_end_index = i
                            break
                        if re.match(r'^[一二三四五六七八九十]+[、．.]\s*', stripped):
                            toc_end_index = i
                            break
                        # 如果连续多行都不是目录项，认为目录结束
                        if i > toc_end_index + 5:
                            toc_end_index = i
                            break

        # 移除目录部分
        if in_toc and toc_end_index > 0:
            return '\n'.join(lines[toc_end_index:])

        return text

    def _detect_indentation_format(self, lines: List[str]) -> bool:
        """检测文本是否使用缩进格式表示层级"""
        indented_count = 0
        total_non_empty = 0

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            total_non_empty += 1

            # 检测是否有制表符缩进或多个空格缩进
            if line.startswith('\t') or (len(line) - len(line.lstrip()) >= 2):
                indented_count += 1

        # 如果超过 30% 的行有缩进，认为是缩进格式
        return total_non_empty > 0 and indented_count / total_non_empty > 0.3

    def _convert_indented_to_markdown(self, text: str, title: str) -> str:
        """将缩进格式的文本转换为 Markdown 标题层级"""
        lines = text.split('\n')
        markdown_parts = [f'# {title}\n']

        # 记录每个缩进级别对应的 Markdown 标题级别
        # 缩进级别 0 -> ## (level 2)
        # 缩进级别 1 -> ## (level 2)
        # 缩进级别 2 -> ### (level 3)
        # 缩进级别 3+ -> #### (level 4)
        indent_to_level = {}

        for line in lines:
            # 计算缩进级别
            indent_level = self._get_indent_level(line)
            stripped = line.strip()

            if not stripped:
                markdown_parts.append('')
                continue

            # 将缩进级别映射到 Markdown 标题级别
            # 缩进 0-1 -> ## (level 2)
            # 缩进 2 -> ### (level 3)
            # 缩进 3+ -> #### (level 4)
            if indent_level <= 1:
                md_level = 2
            elif indent_level == 2:
                md_level = 3
            else:
                md_level = 4

            # 生成 Markdown 标题
            prefix = '#' * md_level
            markdown_parts.append(f'\n{prefix} {stripped}\n')

        result = '\n'.join(markdown_parts)
        result = re.sub(r'\n{3,}', '\n\n', result)
        return result

    def _get_indent_level(self, line: str) -> int:
        """获取行的缩进级别"""
        if not line:
            return 0

        # 计算缩进级别
        indent_level = 0
        i = 0

        while i < len(line):
            if line[i] == '\t':
                indent_level += 1
                i += 1
            elif line[i] == ' ':
                # 连续的空格算作一个缩进级别（假设 2-4 个空格为一级）
                space_count = 0
                while i < len(line) and line[i] == ' ':
                    space_count += 1
                    i += 1
                # 每 2 个空格算作一个缩进级别
                indent_level += max(1, space_count // 2)
            else:
                break

        return indent_level

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
