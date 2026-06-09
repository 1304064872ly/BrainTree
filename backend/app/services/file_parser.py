import io
import os
import re
from typing import Optional
import PyPDF2
from docx import Document

# 尝试导入 OCR 相关库
try:
    import fitz  # pymupdf
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    import pytesseract
    from pdf2image import convert_from_bytes
    HAS_OCR = True
except ImportError:
    HAS_OCR = False

class FileParser:
    """文件解析器，支持 PDF、DOCX、TXT 格式，支持 OCR"""

    async def parse(self, filename: str, content: bytes) -> str:
        """解析文件内容"""
        ext = os.path.splitext(filename)[1].lower()

        if ext == ".pdf":
            return self._parse_pdf(content)
        elif ext == ".docx":
            return self._parse_docx(content)
        elif ext == ".txt":
            return self._parse_txt(content)
        elif ext in (".md", ".markdown"):
            return self._parse_txt(content)  # Markdown 文件按文本解析
        else:
            raise ValueError(f"不支持的文件格式: {ext}")

    def _parse_pdf(self, content: bytes) -> str:
        """解析 PDF 文件，优先使用 pymupdf，支持 OCR"""
        # 方法1: 使用 pymupdf 提取文本（更好的文本提取能力）
        if HAS_PYMUPDF:
            try:
                return self._parse_pdf_with_pymupdf(content)
            except Exception as e:
                print(f"pymupdf 解析失败，尝试其他方法: {e}")

        # 方法2: 使用 PyPDF2 提取文本
        try:
            text = self._parse_pdf_with_pypdf2(content)
            if text and len(text.strip()) > 50:
                return text
        except Exception as e:
            print(f"PyPDF2 解析失败: {e}")

        # 方法3: 使用 OCR 提取文本（扫描版PDF）
        if HAS_OCR:
            try:
                return self._parse_pdf_with_ocr(content)
            except Exception as e:
                print(f"OCR 解析失败: {e}")

        # 如果所有方法都失败
        if not text:
            return "[PDF文件内容为空或无法提取文本，建议使用OCR工具预处理]"
        return text

    def _parse_pdf_with_pymupdf(self, content: bytes) -> str:
        """使用 pymupdf 解析 PDF"""
        import fitz
        doc = fitz.open(stream=content, filetype="pdf")
        text_content = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            # 尝试提取文本
            text = page.get_text("text")
            if text and text.strip():
                text_content.append(text.strip())
            else:
                # 如果文本提取失败，尝试提取文本块
                blocks = page.get_text("blocks")
                if blocks:
                    page_text = "\n".join([block[4] for block in blocks if block[4].strip()])
                    if page_text.strip():
                        text_content.append(page_text.strip())

        doc.close()
        result = "\n\n".join(text_content)

        if not result or len(result.strip()) < 50:
            raise Exception("pymupdf 提取的文本过少")

        return result

    def _parse_pdf_with_pypdf2(self, content: bytes) -> str:
        """使用 PyPDF2 解析 PDF"""
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
        text_content = []

        for page in pdf_reader.pages:
            try:
                text = page.extract_text()
                if text and text.strip():
                    text_content.append(text.strip())
            except Exception as e:
                print(f"警告: 解析PDF页面失败: {e}")
                continue

        return "\n\n".join(text_content)

    def _parse_pdf_with_ocr(self, content: bytes) -> str:
        """使用 OCR 解析扫描版 PDF"""
        print("正在使用 OCR 解析扫描版 PDF...")

        # 将 PDF 转换为图片
        images = convert_from_bytes(content, dpi=200)

        text_content = []
        for i, image in enumerate(images):
            try:
                # 使用 pytesseract 进行 OCR
                text = pytesseract.image_to_string(image, lang='chi_sim+eng')
                if text and text.strip():
                    text_content.append(text.strip())
                print(f"OCR 完成第 {i+1}/{len(images)} 页")
            except Exception as e:
                print(f"OCR 第 {i+1} 页失败: {e}")
                continue

        result = "\n\n".join(text_content)
        if not result:
            return "[OCR 未能提取到文本内容]"
        return result

    def _parse_docx(self, content: bytes) -> str:
        """解析 DOCX 文件"""
        try:
            doc = Document(io.BytesIO(content))
            text_content = []

            # 提取段落内容
            for paragraph in doc.paragraphs:
                if paragraph.text and paragraph.text.strip():
                    text_content.append(paragraph.text.strip())

            # 提取表格内容
            for table in doc.tables:
                for row in table.rows:
                    row_text = [cell.text.strip() for cell in row.cells if cell.text and cell.text.strip()]
                    if row_text:
                        text_content.append(" | ".join(row_text))

            result = "\n\n".join(text_content)
            if not result:
                return "[DOCX文件内容为空或无法提取文本]"
            return result
        except Exception as e:
            raise Exception(f"DOCX 解析失败: {str(e)}")

    def _parse_txt(self, content: bytes) -> str:
        """解析 TXT 文件"""
        try:
            # 尝试多种编码
            encodings = ["utf-8", "utf-8-sig", "gbk", "gb2312", "gb18030", "latin-1"]

            for encoding in encodings:
                try:
                    result = content.decode(encoding)
                    if result and result.strip():
                        return result
                except (UnicodeDecodeError, LookupError):
                    continue

            # 如果所有编码都失败，使用 utf-8 并忽略错误
            result = content.decode("utf-8", errors="ignore")
            if not result or not result.strip():
                return "[TXT文件内容为空]"
            return result
        except Exception as e:
            raise Exception(f"TXT 解析失败: {str(e)}")
