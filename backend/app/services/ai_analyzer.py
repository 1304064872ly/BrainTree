"""
AI 分析器模块
============

本模块是 BrainTree 项目的核心服务，负责：
1. 调用 LLM（大语言模型）从文本中提取概念和关系
2. 支持多种 LLM 服务商（DeepSeek、OpenAI、Claude、智谱AI）
3. 长文本智能分段和滑动窗口分析
4. 多文件分组综合分析
5. 思维树优化（根据用户反馈调整）
6. 关键词提取
7. 配置热更新（支持运行时切换模型）

主要类：
    AIAnalyzer: AI 分析器，提供文本分析和思维树生成功能

使用示例：
    analyzer = AIAnalyzer()
    result = await analyzer.analyze("这是一段文本内容")
"""

# ============================================================
# 第一部分：导入依赖
# ============================================================
import os           # 读取环境变量
import json         # JSON 解析和序列化
import re           # 正则表达式，用于文本处理
from typing import Dict, Any, List, Set  # 类型注解
from collections import Counter           # 词频统计
import httpx        # 异步 HTTP 客户端，用于调用 LLM API
from dotenv import load_dotenv  # 加载 .env 环境变量文件

# 加载 .env 文件中的环境变量
load_dotenv()

# ============================================================
# 第二部分：常量定义
# ============================================================

# DeepSeek 模型列表
# 键：模型 ID（用于 API 调用）
# 值：模型描述（用于前端显示）
DEEPSEEK_MODELS = {
    "deepseek-chat": "通用对话模型 (DeepSeek-V3)",      # 默认模型，适合大多数场景
    "deepseek-coder": "代码专用模型",                    # 适合技术文档分析
    "deepseek-reasoner": "推理增强模型 (DeepSeek-R1)",   # 适合复杂逻辑分析
    "deepseek-v3": "DeepSeek-V3 最新版",                # 最新版本
    "deepseek-r1": "DeepSeek-R1 推理模型",              # 深度推理
    "deepseek-v4-flash": "DeepSeek-V4 Flash 快速模型",  # 快速响应
}

# 配置参数 - 控制长文本分析的行为
MAX_CONTENT_LENGTH = 120000  # 每批次最大内容长度（字符数）
                            # 超过此长度的文本会被分段处理
                            # 增大此值可以减少分段数量，保留更完整的语义单元
OVERLAP_LENGTH = 15000      # 批次间重叠长度（字符数）
                            # 滑动窗口重叠，确保上下文连贯性
                            # 增大此值可以保持更好的上下文连贯
MIN_SECTION_LENGTH = 500    # 最小段落长度（字符数）
                            # 过短的段落会被合并，避免碎片化

class AIAnalyzer:
    """
    AI 分析器类

    负责调用 LLM 从文本中提取概念和关系，生成思维树数据结构。

    主要功能：
    1. 文本分析：从单个文本中提取知识点和关系
    2. 长文本处理：智能分段 + 滑动窗口 + 分批分析
    3. 多文件分析：将多个相关文件合并分析
    4. 思维树优化：根据用户反馈调整思维树结构
    5. 关键词提取：从文本中提取关键词
    6. 配置热更新：支持运行时切换 AI 模型

    属性：
        llm_provider (str): LLM 服务商名称（deepseek/openai/claude/zhipu）
        api_key (str): API 密钥
        api_base (str): API 基础 URL（可选，留空使用默认）
        model (str): 模型名称
    """

    def __init__(self):
        """
        初始化 AI 分析器

        配置加载优先级：
        1. 数据库中的 ai_config 表（用户在前端设置页面配置）
        2. .env 环境变量文件
        3. 默认值
        """
        # 从环境变量读取默认配置（作为 fallback）
        self.llm_provider = os.getenv("LLM_PROVIDER", "deepseek")  # 默认使用 DeepSeek
        self.api_key = os.getenv("LLM_API_KEY", "")                # API 密钥
        self.api_base = os.getenv("LLM_API_BASE", "")              # 自定义 API 地址
        self.model = os.getenv("LLM_MODEL", "")                    # 模型名称

        # 尝试从数据库加载配置（优先级高于环境变量）
        self._load_from_db_on_init()

        # 尝试从数据库加载配置
        self._load_from_db_on_init()

        # ============================================================
        # 系统提示词（System Prompt）
        # ============================================================
        # 系统提示词用于设定 AI 的角色和行为规范
        # 使用固定的系统提示词可以提高 Prompt Caching 命中率
        # DeepSeek 和 OpenAI 都支持缓存相同的前缀内容
        self._system_prompt = "你是一个专业的知识分析助手，擅长从文本中提取概念和关系。请用中文回复。请确保返回有效的JSON格式。"

        # ============================================================
        # 分析指令前缀（用于 Prompt Caching）
        # ============================================================
        # 固定的分析指令前缀，与系统提示词一起构成缓存前缀
        # 只有文档内容会变化，这样可以最大化缓存命中率
        # 降低 API 调用成本并提高响应速度
        self._analysis_instruction_prefix = """请分析以下文档内容，提取知识点并构建知识图谱。

【任务说明】
1. 先扫描整个文档，忽略目录、页码、页眉页脚等非内容部分
2. 提取文档中的核心知识点，每个知识点作为一个独立的节点
3. 知识点之间如果有逻辑关系，建立相应的连接

【知识点提取规则】
- 每个知识点应该是文档中的一个独立概念、主题或要点
- 知识点名称应该简洁明了（10-30字）
- 知识点描述应该包含完整详细的解释内容
- 忽略目录、索引、参考文献等非核心内容

【输出格式】
{
    "title": "文档主题",
    "summary": "内容摘要（200-500字）",
    "nodes": [
        {
            "id": "node_1",
            "name": "知识点名称",
            "description": "该知识点的详细解释内容（保留原文所有细节）",
            "level": 1
        }
    ],
    "edges": [
        {
            "source": "node_1",
            "target": "node_2",
            "label": "包含/关联/依赖",
            "type": "contains"
        }
    ]
}

【level 说明】
- level 1：核心主题/大类
- level 2：主要知识点
- level 3：细分知识点
- level 4：具体细节/示例

【重要提示】
- 忽略目录、页码、页眉页脚等非内容部分
- 每个知识点的 description 必须包含完整的详细内容
- 知识点之间的关系要有意义（包含、关联、依赖等）
- 如果文档有 10 个核心知识点，就返回 10 个节点

请直接返回JSON格式的结果，不要添加其他说明。

文档内容：
"""

        # 固定的问答分析指令前缀（用于缓存命中）
        # 注意：结尾部分（"请直接返回JSON格式的结果"）已合并到此处
        self._qa_instruction_prefix = """请分析以下问答格式的文本内容，构建层级清晰的知识树。

【核心要求】
1. 识别主题（第一个非问/答的内容通常是主题）
2. 将【每一个】"问：xxx"作为一个节点，节点名称就是问题内容
3. 将对应的"答：xxx"作为该节点的详细描述
4. 如果问题之间有逻辑关系，建立相应的关联

【层级规则】
1. 一级节点（level 1）：主题或核心问题
2. 二级节点（level 2）：主要问题分类
3. 三级节点（level 3）：具体问题
4. 四级节点（level 4）：问题的细节或示例

【父子关系规则】
- 每个节点必须有且只有一个父节点（除了根节点）
- 父节点的 level 必须比子节点小 1
- 关系类型：只有 "contains"（包含）和 "relates"（关联）两种

【输出格式】
{
    "title": "主题名称（必填）",
    "summary": "内容摘要",
    "concepts": [
        {
            "name": "问题内容（去掉问：前缀）",
            "description": "完整的答案内容（去掉答：前缀，保留所有细节）",
            "type": "concept/topic/detail/example",
            "level": 1-4
        }
    ],
    "relations": [
        {
            "source": "父节点名称",
            "target": "子节点名称",
            "label": "包含",
            "type": "contains"
        }
    ]
}

【重要提示】
- 必须提取【所有】问题，不能只提取部分
- 节点名称只保留问题内容，不要包含"问："前缀
- 描述要完整保留答案的所有内容，不要省略
- 如果文档有 12 个问题，就必须返回 12 个节点
- 如果问题之间有逻辑顺序或关联，建立相应的关系
- 层级关系必须正确：父节点的 level 必须比子节点小 1
- 每个节点必须有且只有一个父节点（除了根节点）

请直接返回JSON格式的结果，不要添加其他说明。

文本内容：
"""

    def _load_from_db_on_init(self):
        """
        初始化时从数据库加载 AI 配置

        从 ai_config 表中读取用户在前端设置页面配置的 AI 模型参数。
        如果数据库中没有配置或加载失败，则使用环境变量作为 fallback。

        加载优先级：数据库配置 > 环境变量 > 默认值

        注意：
        - 使用独立的数据库会话，避免与请求级别的会话冲突
        - 加载完成后立即关闭会话，释放连接
        - 所有异常都会被捕获，确保不影响应用启动
        """
        try:
            # 延迟导入，避免循环依赖
            from app.core.database import SessionLocal
            from app.models.db_models import AIConfigDB
            from app.core.security import mask_api_key

            # 创建独立的数据库会话
            db = SessionLocal()
            try:
                # 查询第一条配置记录（系统只有一条配置）
                config = db.query(AIConfigDB).first()

                if config and config.api_key:
                    # 数据库中有有效配置，使用数据库配置
                    self.llm_provider = config.provider      # 服务商名称
                    self.api_key = config.api_key            # API 密钥
                    self.api_base = config.api_base or ""    # 自定义 API 地址
                    self.model = config.model or ""          # 模型名称
                    print(f"[AIAnalyzer] 从数据库加载配置: provider={config.provider}, "
                          f"key={mask_api_key(config.api_key)}, model={config.model}")
                else:
                    # 数据库中没有配置，使用环境变量
                    print("[AIAnalyzer] 数据库无配置，使用环境变量")
            finally:
                # 确保数据库会话被关闭，释放连接
                db.close()
        except Exception as e:
            # 数据库加载失败（可能是表不存在），使用环境变量
            print(f"[AIAnalyzer] 从数据库加载配置失败，使用环境变量: {e}")

    def reload_config_from_db(self, db):
        """
        从数据库重新加载配置（热更新）

        当用户在前端设置页面修改配置后，调用此方法热更新配置，
        无需重启后端服务。

        Args:
            db: SQLAlchemy 数据库会话（由调用方提供）

        Returns:
            bool: 配置更新成功返回 True，无配置返回 False

        使用场景：
            config.py 的 update_config 接口调用此方法实现配置热更新
        """
        from app.models.db_models import AIConfigDB
        from app.core.security import mask_api_key

        # 查询数据库中的配置
        config = db.query(AIConfigDB).first()

        if config:
            # 更新内存中的配置
            self.llm_provider = config.provider      # 服务商名称
            self.api_key = config.api_key            # API 密钥
            self.api_base = config.api_base or ""    # 自定义 API 地址
            self.model = config.model or ""          # 模型名称
            print(f"[AIAnalyzer] 配置已热更新: provider={config.provider}, "
                  f"key={mask_api_key(config.api_key)}, model={config.model}")
            return True
        return False

    def get_model(self, default: str = "deepseek-chat") -> str:
        """
        获取当前配置的模型名称

        Args:
            default: 默认模型名称，当未配置时使用

        Returns:
            str: 模型名称

        示例：
            analyzer.model = "deepseek-r1"
            analyzer.get_model()  # 返回 "deepseek-r1"

            analyzer.model = ""
            analyzer.get_model()  # 返回 "deepseek-chat"（默认值）
        """
        return self.model or default

    async def analyze(self, content: str) -> Dict[str, Any]:
        """
        分析文本内容，提取概念和关系

        这是 AI 分析的核心方法，负责：
        1. 判断文本长度，决定是否需要分段处理
        2. 构建分析提示词
        3. 调用 LLM API
        4. 解析 AI 响应，提取结构化数据

        Args:
            content: 待分析的文本内容

        Returns:
            Dict: 包含以下字段的字典
                - title (str): 文档主题
                - summary (str): 内容摘要
                - concepts (List[Dict]): 概念节点列表
                - relations (List[Dict]): 关系列表

        异常处理：
            如果 AI 调用失败，会调用 _fallback_analysis 返回简单的结构化结果
        """
        # 如果内容超过最大长度限制，使用长文本分析方法
        if len(content) > MAX_CONTENT_LENGTH:
            return await self._analyze_long_content(content)

        # 构建分析提示词
        prompt = self._build_analysis_prompt(content)

        try:
            # 调用 LLM API
            response = await self._call_llm(prompt)
            # 解析 AI 响应，提取 JSON 数据
            return self._parse_analysis_response(response)
        except Exception as e:
            # AI 调用失败时，使用备用分析方法
            print(f"[AIAnalyzer] AI 分析失败，使用备用方法: {e}")
            return self._fallback_analysis(content)

    async def _analyze_long_content(self, content: str) -> Dict[str, Any]:
        """
        分析长文本内容 - 智能分段 + 滑动窗口 + 分批分析

        处理流程：
        1. 提取文档目录结构（如果有）
        2. 智能分段（按章节标题分割）
        3. 构建批次（带滑动窗口重叠）
        4. 分批调用 LLM 分析
        5. 合并所有分析结果

        Args:
            content: 长文本内容（超过 MAX_CONTENT_LENGTH）

        Returns:
            Dict: 合并后的分析结果
        """
        # 第一步：提取文档目录结构（如果有）
        # 目录可以帮助 AI 理解文档的整体结构
        toc = self._extract_toc(content)

        # 第二步：智能分段
        # 按章节标题分割，保留完整的语义单元
        sections = self._smart_split(content)

        if len(sections) <= 1:
            # 如果无法有效分割（例如没有标题），直接截断处理
            truncated = content[:MAX_CONTENT_LENGTH]
            prompt = self._build_analysis_prompt(truncated)
            try:
                response = await self._call_llm(prompt)
                return self._parse_analysis_response(response)
            except Exception as e:
                return self._fallback_analysis(content)

        # 第三步：构建批次（带滑动窗口）
        # 滑动窗口确保相邻批次之间有重叠内容，保持上下文连贯
        batches = self._create_batches_with_overlap(sections)

        # 第四步：分批分析
        all_results = []

        # 先分析目录（如果有）
        # 目录分析可以帮助 AI 理解文档的整体结构
        if toc:
            try:
                toc_prompt = self._build_analysis_prompt(toc)
                toc_response = await self._call_llm(toc_prompt)
                toc_result = self._parse_analysis_response(toc_response)
                all_results.append(toc_result)
            except Exception as e:
                print(f"目录分析失败: {e}")

        # 分析每个批次
        for i, batch in enumerate(batches):
            try:
                # 添加批次信息，让 AI 知道这是长文档的一部分
                part_info = f"这是第 {i+1}/{len(batches)} 部分"
                prompt = self._build_analysis_prompt(batch, is_part=True, part_info=part_info)
                response = await self._call_llm(prompt)
                result = self._parse_analysis_response(response)
                all_results.append(result)
                print(f"批次 {i+1}/{len(batches)} 分析完成")
            except Exception as e:
                print(f"批次 {i+1} 分析失败: {e}")

        # 如果所有批次都分析失败，使用备用方法
        if not all_results:
            return self._fallback_analysis(content)

        # 第五步：合并所有分析结果
        # 去重、合并关系、添加批次间的关联
        return self._merge_analysis_results(all_results)

    def _extract_toc(self, content: str) -> str:
        """
        提取文档目录结构

        从文档中识别并提取目录部分，用于帮助 AI 理解文档结构。
        如果没有找到明确的目录，则提取所有标题作为伪目录。

        Args:
            content: 文档内容

        Returns:
            str: 目录文本，如果没有找到目录则返回空字符串

        目录检测策略：
        1. 查找包含"目录"、"table of contents"等关键词的行
        2. 识别目录项（包含页码或缩进的行）
        3. 如果没有明确目录，提取所有 Markdown 标题作为伪目录
        """
        lines = content.split('\n')
        toc_lines = []
        in_toc = False  # 标记是否在目录区域内

        for line in lines:
            stripped = line.strip()

            # 检测目录开始
            # 查找包含"目录"、"table of contents"等关键词的行
            if any(kw in stripped.lower() for kw in ['目录', 'table of contents', 'toc', 'contents']):
                in_toc = True
                toc_lines.append(stripped)
                continue

            # 检测目录项
            if in_toc:
                # 目录项通常包含页码或缩进
                # 格式1：数字编号 + 内容 + 页码（如 "1. 引言 ...... 5"）
                if re.match(r'^[\d\.\)]+\s+.+\s*[\.\.]+\s*\d+$', stripped):
                    toc_lines.append(stripped)
                # 格式2：缩进的行（目录项通常有缩进）
                elif re.match(r'^\s{2,}.+', stripped):
                    toc_lines.append(stripped)
                # 空行跳过
                elif stripped == '':
                    continue
                # 其他内容表示目录结束
                else:
                    break

        # 如果没有找到目录（少于3行），提取所有标题作为伪目录
        if len(toc_lines) < 3:
            toc_lines = ["# 文档标题结构"]  # 添加标题
            for line in lines:
                stripped = line.strip()
                # 提取所有 Markdown 标题
                if stripped.startswith('#'):
                    toc_lines.append(stripped)

        # 只有目录内容足够多时才返回
        return '\n'.join(toc_lines) if len(toc_lines) > 3 else ''

    def _smart_split(self, content: str) -> List[str]:
        """
        智能分段 - 按一级标题分割，保留完整的语义单元

        改进策略：只按一级标题（#）分割，而不是按所有标题分割。
        这样可以保留完整的章节结构，避免破坏跨章节的逻辑关系。

        分割策略：
        1. 只按一级标题（# 开头，不是 ##）分割
        2. 每个一级标题下的所有内容（包括子标题）作为一个完整段落
        3. 如果单个章节太长，按自然段落进一步分割
        4. 合并过短的段落，避免碎片化

        Args:
            content: 文档内容

        Returns:
            List[str]: 分段后的文本列表
        """
        lines = content.split('\n')
        sections = []           # 存储所有分段结果
        current_section = []    # 当前正在构建的段落

        for line in lines:
            stripped = line.strip()

            # 只按一级标题分割（# 开头，但不是 ## 或 ###）
            is_root_heading = stripped.startswith('# ') and not stripped.startswith('## ')

            if is_root_heading:
                # 遇到新的一级标题，保存当前章节
                if current_section:
                    section_text = '\n'.join(current_section)
                    # 只保存长度足够的段落
                    if len(section_text.strip()) >= MIN_SECTION_LENGTH:
                        sections.append(section_text)

                # 开始新章节
                current_section = [line]
            else:
                # 普通内容或子标题，添加到当前章节
                current_section.append(line)

        # 处理最后一个章节
        if current_section:
            section_text = '\n'.join(current_section)
            if len(section_text.strip()) >= MIN_SECTION_LENGTH:
                sections.append(section_text)

        # 如果没有一级标题，或者只有一个段落，按二级标题分割
        if len(sections) <= 1:
            sections = []
            current_section = []

            for line in lines:
                stripped = line.strip()

                # 按一级或二级标题分割
                is_heading = (stripped.startswith('# ') or stripped.startswith('## ')) and not stripped.startswith('### ')

                if is_heading:
                    if current_section:
                        section_text = '\n'.join(current_section)
                        if len(section_text.strip()) >= MIN_SECTION_LENGTH:
                            sections.append(section_text)
                    current_section = [line]
                else:
                    current_section.append(line)

            if current_section:
                section_text = '\n'.join(current_section)
                if len(section_text.strip()) >= MIN_SECTION_LENGTH:
                    sections.append(section_text)

        # 合并过短的段落
        return self._merge_short_sections(sections)

    def _detect_heading(self, line: str) -> tuple:
        """
        检测标题，返回 (是否标题, 标题级别)

        支持多种标题格式：
        1. Markdown 标题：# 一级标题、## 二级标题
        2. 数字编号标题：1. 一级标题、2.1 二级标题
        3. 中文章节标识：第一章、一、（一）
        4. 全大写英文标题
        5. 特殊标记：【标题】

        Args:
            line: 待检测的文本行

        Returns:
            tuple: (是否标题, 标题级别)
                - 是否标题：True/False
                - 标题级别：1-6（1=最高级，6=最低级）

        示例：
            _detect_heading("# 引言")      # 返回 (True, 1)
            _detect_heading("## 背景")     # 返回 (True, 2)
            _detect_heading("1. 概述")     # 返回 (True, 1)
            _detect_heading("这是正文")    # 返回 (False, 0)
        """
        if not line:
            return False, 0

        # Markdown 标题：# ## ### #### ##### ######
        # 正则匹配：以1-6个#开头，后跟空格
        match = re.match(r'^(#{1,6})\s+', line)
        if match:
            return True, len(match.group(1))  # #数量就是标题级别

        # 数字编号标题：1. 2.3. 1.2.3.
        # 正则匹配：数字.数字.数字. 的格式
        if re.match(r'^\d+(\.\d+)*[\.\)]\s+\S', line) and len(line) < 100:
            level = line.count('.') + 1  # 点号数量+1就是级别
            return True, min(level, 6)   # 最大6级

        # 中文章节标识
        chapter_patterns = [
            (r'^第[一二三四五六七八九十百千\d]+[章篇]', 1),  # 第X章/篇 = 1级
            (r'^第[一二三四五六七八九十百千\d]+[节部]', 2),  # 第X节/部 = 2级
            (r'^[一二三四五六七八九十]+[、．.]', 2),        # 一、二、 = 2级
            (r'^[（\(][一二三四五六七八九十\d]+[）\)]', 3),  # （一） = 3级
        ]
        for pattern, level in chapter_patterns:
            if re.match(pattern, line):
                return True, level

        # 全大写英文标题（长度在5-80之间）
        if line.isupper() and 5 < len(line) < 80:
            return True, 1

        # 特殊标记：【标题】
        if line.startswith('【') and line.endswith('】'):
            return True, 2

        return False, 0

    def _merge_short_sections(self, sections: List[str]) -> List[str]:
        """
        合并过短的段落

        将长度不足 MIN_SECTION_LENGTH 的段落与相邻段落合并，
        避免产生过多碎片化的短段落。

        Args:
            sections: 原始分段列表

        Returns:
            List[str]: 合并后的分段列表

        合并策略：
        1. 遍历所有段落
        2. 如果当前段落太短，与下一个段落合并
        3. 最后一个段落如果太短，与前一个段落合并
        """
        if not sections:
            return sections

        merged = []
        current = sections[0]

        for section in sections[1:]:
            # 如果当前段落太短，与下一个合并
            if len(current.strip()) < MIN_SECTION_LENGTH:
                current = current + '\n\n' + section
            else:
                merged.append(current)
                current = section

        # 处理最后一个段落
        if current.strip():
            if len(current.strip()) < MIN_SECTION_LENGTH and merged:
                # 太短，合并到前一个段落
                merged[-1] = merged[-1] + '\n\n' + current
            else:
                merged.append(current)

        return merged

    def _create_batches_with_overlap(self, sections: List[str]) -> List[str]:
        """
        创建批次，带滑动窗口重叠

        将分段后的内容组织成多个批次，每个批次的大小不超过 MAX_CONTENT_LENGTH。
        相邻批次之间有 OVERLAP_LENGTH 的重叠内容，确保上下文连贯。

        滑动窗口原理：
        - 批次1：[段落1, 段落2, 段落3]
        - 批次2：[段落3的末尾, 段落4, 段落5]
        - 批次3：[段落5的末尾, 段落6, 段落7]

        这样可以确保：
        1. 每个批次的内容都在长度限制内
        2. 相邻批次之间有重叠，保持上下文连贯
        3. AI 可以更好地理解跨批次的内容

        Args:
            sections: 分段后的内容列表

        Returns:
            List[str]: 批次列表，每个元素是一个批次的内容
        """
        batches = []
        current_batch = []      # 当前批次的段落列表
        current_length = 0      # 当前批次的总长度

        for i, section in enumerate(sections):
            section_len = len(section)

            # 如果添加当前段落会超出批次大小限制
            if current_length + section_len > MAX_CONTENT_LENGTH and current_batch:
                # 保存当前批次
                batch_content = '\n\n'.join(current_batch)
                batches.append(batch_content)

                # 计算重叠：从当前批次末尾取部分内容作为下一批次开头
                overlap_content = self._get_overlap_content(current_batch, OVERLAP_LENGTH)
                current_batch = [overlap_content] if overlap_content else []
                current_length = len(overlap_content) if overlap_content else 0

            # 添加当前段落到批次
            current_batch.append(section)
            current_length += section_len

        # 处理最后一个批次
        if current_batch:
            batch_content = '\n\n'.join(current_batch)
            if batch_content.strip():
                batches.append(batch_content)

        return batches

    def _get_overlap_content(self, batch: List[str], overlap_length: int) -> str:
        """
        获取批次末尾的重叠内容

        从批次的末尾向前取指定长度的内容，用于滑动窗口重叠。
        这样可以确保下一个批次的开头包含上一个批次的结尾内容，
        帮助 AI 理解上下文连贯性。

        Args:
            batch: 当前批次的段落列表
            overlap_length: 需要重叠的字符数

        Returns:
            str: 重叠内容文本

        示例：
            batch = ["段落1内容", "段落2内容", "段落3内容"]
            overlap_length = 100
            # 返回段落3的最后100个字符（或更多，如果段落较短）
        """
        if not batch:
            return ''

        # 从最后一个段落开始，向前取内容
        overlap_parts = []
        current_length = 0

        for section in reversed(batch):
            # 如果添加整个段落会超出重叠长度
            if current_length + len(section) > overlap_length:
                # 只取部分内容（段落的末尾部分）
                remaining = overlap_length - current_length
                if remaining > 100:  # 至少取100个字符才有意义
                    overlap_parts.append(section[-remaining:])
                break
            overlap_parts.append(section)
            current_length += len(section)

        # 反转并拼接（因为我们是从后向前遍历的）
        return '\n\n'.join(reversed(overlap_parts)) if overlap_parts else ''

    def _merge_analysis_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        合并多个分析结果 - 使用更智能的去重和关系重建

        改进策略：
        1. 使用更精确的去重策略：基于名称 + level，而不是名称 + 描述前50字符
        2. 重建批次间的层级关系：根据文档结构（标题层级）重建父子关系
        3. 不再简单添加"相关内容"关系，而是根据 level 值重建层级关系
        """
        if len(results) == 1:
            return results[0]

        # 合并标题和摘要
        title = results[0].get('title', '未命名思维树')
        summaries = [r.get('summary', '') for r in results if r.get('summary')]
        summary = '\n\n'.join(summaries) if summaries else ''

        # 合并所有概念节点 - 使用更精确的去重策略
        all_concepts = []
        seen_names = {}  # 记录名称和level的组合
        for result in results:
            for concept in result.get('concepts', []):
                name = concept.get('name', '').strip()
                if not name:
                    continue

                # 创建唯一键：名称 + level（更精确的去重）
                level = concept.get('level', 1)
                unique_key = f"{name}|{level}"

                if unique_key not in seen_names:
                    seen_names[unique_key] = concept
                    all_concepts.append(concept)
                else:
                    # 如果节点已存在，但描述更长，则更新描述
                    existing = seen_names[unique_key]
                    if len(concept.get('description', '')) > len(existing.get('description', '')):
                        existing['description'] = concept['description']

        # 合并所有关系
        all_relations = []
        seen_relations = set()
        for result in results:
            for relation in result.get('relations', []):
                source = relation.get('source', '').strip()
                target = relation.get('target', '').strip()
                label = relation.get('label', '').strip()

                if not source or not target:
                    continue

                # 创建唯一键
                relation_key = f"{source}|{target}|{label}"
                if relation_key not in seen_relations:
                    seen_relations.add(relation_key)
                    all_relations.append(relation)

        # 如果有多个批次的结果，重建层级关系
        if len(results) > 1:
            # 使用新的层级重建逻辑
            hierarchy_relations = self._rebuild_hierarchy(all_concepts)

            # 合并原有关系和新重建的关系
            for rel in hierarchy_relations:
                relation_key = f"{rel['source']}|{rel['target']}|{rel['label']}"
                if relation_key not in seen_relations:
                    seen_relations.add(relation_key)
                    all_relations.append(rel)

        print(f"合并结果：共 {len(all_concepts)} 个节点，{len(all_relations)} 条关系")

        return {
            "title": title,
            "summary": summary,
            "concepts": all_concepts,
            "relations": all_relations
        }

    def _rebuild_hierarchy(self, concepts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        根据 level 值重建层级关系

        当多个批次的分析结果合并时，原有的层级关系可能丢失或混乱。
        此方法根据节点的 level 值重新建立父子关系。

        算法：
        1. 按 level 分组
        2. 对于每个非一级节点，找到它应该属于的父节点
        3. 父节点选择规则：同批次中 level 比它小 1 的节点

        Args:
            concepts: 所有概念节点列表

        Returns:
            List[Dict]: 重建的层级关系列表
        """
        relations = []

        # 按 level 分组
        level_groups = {}
        for concept in concepts:
            level = concept.get('level', 1)
            if level not in level_groups:
                level_groups[level] = []
            level_groups[level].append(concept)

        # 获取所有存在的 level 值，排序
        sorted_levels = sorted(level_groups.keys())

        # 对于每个非一级节点，建立与上一层级节点的父子关系
        for i in range(1, len(sorted_levels)):
            current_level = sorted_levels[i]
            parent_level = sorted_levels[i - 1]

            # 检查 level 是否连续（跳过了某些 level）
            if current_level - parent_level > 1:
                # 尝试找到正确的父级 level
                expected_parent_level = current_level - 1
                if expected_parent_level in level_groups:
                    parent_level = expected_parent_level
                else:
                    # 如果找不到正确的父级，使用最近的上一层级
                    pass

            # 为当前层级的每个节点找到父节点
            for concept in level_groups[current_level]:
                # 找到同批次中 level 比它小 1 的节点作为父节点
                # 策略：选择第一个可用的父节点
                if level_groups[parent_level]:
                    parent = level_groups[parent_level][0]
                    relations.append({
                        "source": parent['name'],
                        "target": concept['name'],
                        "label": "包含",
                        "type": "contains"
                    })

        return relations

    def extract_keywords(self, content: str, analysis_result: Dict[str, Any] = None) -> List[str]:
        """
        从文本和分析结果中提取关键词

        通过两个维度提取关键词：
        1. 从 AI 分析结果中提取（标题、概念名称）
        2. 从原文中提取高频词

        Args:
            content: 原始文本内容
            analysis_result: AI 分析结果（可选）

        Returns:
            List[str]: 关键词列表（最多20个）

        提取策略：
        1. 从分析结果的标题和概念名称中提取词语
        2. 从原文中提取高频词（词频统计）
        3. 过滤停用词和过短的词
        4. 返回前20个关键词
        """
        keywords = set()  # 使用集合去重

        # 1. 从 AI 分析结果中提取关键词
        if analysis_result:
            # 从标题提取
            title = analysis_result.get("title", "")
            if title:
                keywords.update(self._extract_words_from_text(title))

            # 从概念名称提取
            for concept in analysis_result.get("concepts", []):
                name = concept.get("name", "")
                if name:
                    keywords.update(self._extract_words_from_text(name))

        # 2. 从原文中提取高频词
        text_keywords = self._extract_high_freq_words(content, top_n=20)
        keywords.update(text_keywords)

        # 3. 过滤停用词和过短的词（长度<=1的词通常是无意义的）
        filtered_keywords = [w for w in keywords if len(w) > 1]

        # 4. 返回前20个关键词
        return filtered_keywords[:20]

    def _extract_words_from_text(self, text: str) -> List[str]:
        """
        从文本中提取词语

        处理流程：
        1. 移除标点符号
        2. 转换为小写
        3. 按空格分词
        4. 过滤停用词

        Args:
            text: 输入文本

        Returns:
            List[str]: 提取的词语列表
        """
        # 移除标点符号，替换为空格
        text = re.sub(r'[^\w\s]', ' ', text)
        # 转换为小写并按空格分词
        words = text.lower().split()

        # 停用词列表（常见的无意义词语）
        stop_words = {
            # 中文停用词
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一',
            '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有',
            '看', '好', '自己', '这', '他', '她', '它', '们', '那', '被', '从', '把',
            # 英文停用词
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'can', 'shall', 'to', 'of', 'in', 'for',
            'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'out', 'off', 'over',
            'under', 'again', 'further', 'then', 'once'
        }
        # 过滤停用词和过短的词
        return [w for w in words if w not in stop_words and len(w) > 1]

    def _extract_high_freq_words(self, content: str, top_n: int = 20) -> List[str]:
        """
        提取高频词

        使用词频统计提取文本中出现频率最高的词语。
        高频词通常是文档的核心概念。

        Args:
            content: 文本内容
            top_n: 返回前 N 个高频词

        Returns:
            List[str]: 高频词列表
        """
        words = self._extract_words_from_text(content)
        # 使用 Counter 统计词频
        word_counts = Counter(words)
        # 返回前 N 个高频词（按词频降序）
        return [word for word, count in word_counts.most_common(top_n)]

    async def analyze_single_file(self, content: str, file_name: str) -> Dict[str, Any]:
        """
        单文件分析，提取结构化信息和关键词

        这是单文件分析的入口方法，负责：
        1. 调用 AI 分析提取概念和关系
        2. 提取关键词
        3. 组合返回完整结果

        Args:
            content: 文件内容
            file_name: 文件名（用于默认标题）

        Returns:
            Dict: 包含以下字段的字典
                - title (str): 文档标题
                - summary (str): 内容摘要
                - keywords (List[str]): 关键词列表
                - concepts (List[Dict]): 概念节点列表
                - relations (List[Dict]): 关系列表

        使用场景：
            analyze.py 中的 analyze_files 接口调用此方法
        """
        # 1. 进行 AI 分析
        analysis_result = await self.analyze(content)

        # 2. 提取关键词
        keywords = self.extract_keywords(content, analysis_result)

        # 3. 返回完整结果
        return {
            "title": analysis_result.get("title", file_name),  # 优先使用 AI 提取的标题
            "summary": analysis_result.get("summary", ""),     # 内容摘要
            "keywords": keywords,                               # 关键词列表
            "concepts": analysis_result.get("concepts", []),   # 概念节点
            "relations": analysis_result.get("relations", [])  # 关系列表
        }

    async def refine(self, tree: Any, feedback: str) -> Dict[str, Any]:
        """
        根据用户反馈优化思维树

        允许用户对生成的思维树提供反馈，AI 会根据反馈调整树结构。
        支持的反馈类型：
        - 添加/删除/修改概念
        - 调整概念之间的关系
        - 优化层级结构

        Args:
            tree: 当前思维树对象（包含节点和边）
            feedback: 用户反馈文本

        Returns:
            Dict: 优化后的思维树数据

        异常处理：
            如果 AI 调用失败，返回原始树结构（不做修改）
        """
        # 构建优化提示词
        prompt = self._build_refine_prompt(tree, feedback)

        try:
            # 调用 AI 进行优化
            response = await self._call_llm(prompt)
            return self._parse_analysis_response(response)
        except Exception as e:
            # AI 调用失败，返回原始树结构
            print(f"[AIAnalyzer] 思维树优化失败，返回原始结构: {e}")
            return {
                "title": tree.name,
                "summary": tree.description,
                "concepts": [
                    {
                        "name": node.label,
                        "description": node.description,
                        "type": node.type,
                        "level": node.level
                    }
                    for node in tree.nodes
                ],
                "relations": [
                    {
                        "source": next(
                            (n.label for n in tree.nodes if n.id == edge.source),
                            edge.source
                        ),
                        "target": next(
                            (n.label for n in tree.nodes if n.id == edge.target),
                            edge.target
                        ),
                        "label": edge.label,
                        "type": edge.type
                    }
                    for edge in tree.edges
                ]
            }

    def _build_analysis_prompt(self, content: str, is_part: bool = False, part_info: str = '') -> str:
        """
        构建分析提示词 - 使用固定前缀优化缓存命中

        根据文档内容自动选择合适的提示词模板：
        - 问答格式：使用问答专用模板
        - 普通文档：使用通用分析模板

        Args:
            content: 文档内容
            is_part: 是否是长文档的一部分（用于分批分析）
            part_info: 批次信息（如"这是第 1/3 部分"）

        Returns:
            str: 完整的提示词

        Prompt Caching 优化（改进版）：
        - 系统提示词是固定的
        - 分析指令前缀是固定的（放在最前面）
        - 文档内容放在中间（变化的部分）
        - 批次信息放在最后（如果有的话）
        - 这样可以最大化缓存命中率，降低 API 调用成本

        为什么批次信息放在最后？
        - DeepSeek/OpenAI 的 Prompt Caching 机制是基于前缀匹配的
        - 相同的前缀会自动被缓存
        - 如果批次信息放在中间，会导致前缀不一致，破坏缓存
        - 放在最后，前缀部分保持完全一致，只有文档内容和批次信息变化
        """
        # 检测是否是问答格式（包含"问："和"答："标记）
        is_qa_format = "问：" in content and "答：" in content

        # 构建批次上下文说明（放在文档内容后面，不破坏前缀缓存）
        context_suffix = ""
        if is_part:
            context_suffix = f"\n\n【注意：以上是长文档的一部分内容。{part_info}】\n请尽可能完整地提取本部分内容的知识点，不要遗漏任何重要信息。"

        # 使用固定的指令前缀（优化缓存命中）
        # 关键改动：指令前缀和结尾固定，批次信息放在文档内容后面
        # 这样可以最大化缓存命中率
        #
        # 优化后的结构：
        # [分析指令前缀] + [文档内容] + [批次信息]
        #
        # 为什么这样优化？
        # - DeepSeek/OpenAI 的 Prompt Caching 机制是基于前缀匹配的
        # - 相同的前缀会自动被缓存
        # - 批次信息放在文档内容后面，不会破坏前缀缓存
        # - 固定的结尾部分已经合并到前缀中
        #
        # 注意：末尾的"请直接返回JSON格式的结果"已经合并到前缀中
        if is_qa_format:
            # 问答格式：使用问答专用模板
            return f"{self._qa_instruction_prefix}{content}{context_suffix}"
        else:
            # 普通文档：使用通用分析模板
            return f"{self._analysis_instruction_prefix}{content}{context_suffix}"

    def _build_refine_prompt(self, tree: Any, feedback: str) -> str:
        """
        构建优化提示词

        将当前思维树转换为 JSON 格式，结合用户反馈，
        构建让 AI 优化思维树的提示词。

        Args:
            tree: 当前思维树对象
            feedback: 用户反馈文本

        Returns:
            str: 优化提示词

        提示词结构：
        1. 当前思维树的 JSON 表示
        2. 用户反馈内容
        3. 优化要求
        4. 输出格式说明
        """
        # 将思维树转换为 JSON 格式
        tree_json = json.dumps({
            "title": tree.name,
            "summary": tree.description,
            "concepts": [
                {
                    "name": node.label,
                    "description": node.description,
                    "type": node.type,
                    "level": node.level
                }
                for node in tree.nodes
            ],
            "relations": [
                {
                    "source": next(
                        (n.label for n in tree.nodes if n.id == edge.source),
                        edge.source
                    ),
                    "target": next(
                        (n.label for n in tree.nodes if n.id == edge.target),
                        edge.target
                    ),
                    "label": edge.label,
                    "type": edge.type
                }
                for edge in tree.edges
            ]
        }, ensure_ascii=False, indent=2)

        # 构建优化提示词
        return f"""请根据用户反馈优化以下思维树。

当前思维树：
{tree_json}

用户反馈：
{feedback}

要求：
1. 保持原有结构的合理性
2. 根据反馈添加、删除或修改概念
3. 调整概念之间的关系
4. 确保层级结构清晰

请以JSON格式返回优化后的思维树，格式与输入相同。

请直接返回JSON格式的结果，不要添加其他说明。"""

    async def analyze_group(self, file_analyses: List[Dict[str, Any]], group_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        对分组内的多个文件进行综合分析

        将多个相关文件的分析结果合并，生成统一的思维树。
        处理流程：
        1. 如果是单文件组，直接返回该文件的分析结果
        2. 如果是多文件组，调用 AI 进行综合分析
        3. 如果 AI 调用失败，使用简单的合并方法

        Args:
            file_analyses: 分组内文件的分析结果列表
                每个元素包含：title, summary, concepts, relations, file_id
            group_info: 分组信息
                包含：common_keywords（共同关键词）

        Returns:
            Dict: 综合分析结果
                包含：title, summary, concepts, relations, source_files

        使用场景：
            analyze.py 中的多文件分析功能调用此方法
        """
        # 如果是单文件组，直接返回该文件的分析结果
        if len(file_analyses) == 1:
            result = file_analyses[0].copy()
            result["source_files"] = [file_analyses[0].get("file_id")]
            return result

        # 多文件组，进行综合分析
        # 构建综合分析提示词
        prompt = self._build_group_analysis_prompt(file_analyses, group_info)

        try:
            # 调用 AI 进行综合分析
            response = await self._call_llm(prompt)
            result = self._parse_analysis_response(response)
            # 添加来源标记（记录每个概念来自哪个文件）
            result["source_files"] = [f.get("file_id") for f in file_analyses]
            return result
        except Exception as e:
            print(f"分组分析失败: {e}")
            # AI 调用失败，使用简单的合并方法
            return self._merge_file_results(file_analyses)

    def _build_group_analysis_prompt(self, file_analyses: List[Dict[str, Any]],
                                     group_info: Dict[str, Any]) -> str:
        """
        构建分组综合分析提示词

        将多个文件的分析结果整合成一个提示词，
        让 AI 综合分析这些相关文件，生成统一的思维树。

        Args:
            file_analyses: 文件分析结果列表
            group_info: 分组信息（包含共同关键词）

        Returns:
            str: 综合分析提示词

        提示词结构：
        1. 文件间的关联性说明（共同关键词）
        2. 每个文件的基本信息（标题、摘要、主要概念）
        3. 综合分析要求
        4. 输出格式说明
        """
        # 构建文件信息描述
        files_desc = []
        for i, fa in enumerate(file_analyses, 1):
            title = fa.get("title", "未命名")
            summary = fa.get("summary", "")
            # 只取前5个概念作为代表性概念
            concepts = [c.get("name", "") for c in fa.get("concepts", [])[:5]]
            files_desc.append(
                f"文件{i}: {title}\n"
                f"摘要: {summary[:200]}\n"  # 摘要最多200字
                f"主要概念: {', '.join(concepts)}"
            )

        # 将所有文件信息合并
        files_text = "\n\n".join(files_desc)
        # 获取共同关键词（最多5个）
        common_keywords = ", ".join(group_info.get("common_keywords", [])[:5])

        # 构建综合分析提示词
        return f"""请综合分析以下相关文件，构建统一的知识结构。

这些文件之间存在关联性（共同关键词：{common_keywords}）。

文件信息：
{files_text}

要求：
1. 识别所有文件中的知识点，不要遗漏
2. 相同概念合并，不同概念保留
3. 建立文件间的关联关系
4. 构建层级清晰的思维树
5. 保留每个知识点的来源文件信息

请以JSON格式返回结果，格式如下：
{{
    "title": "综合主题名称",
    "summary": "综合摘要（200-500字）",
    "concepts": [
        {{
            "name": "概念名称",
            "description": "概念描述",
            "type": "concept/topic/detail/example",
            "level": 1-4,
            "source_file": "来源文件名"
        }}
    ],
    "relations": [
        {{
            "source": "源概念",
            "target": "目标概念",
            "label": "关系描述",
            "type": "contains/relates/depends"
        }}
    ]
}}

请直接返回JSON格式的结果，不要添加其他说明。"""

    def _merge_file_results(self, file_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        合并多个文件的分析结果（作为备用方案）

        当 AI 综合分析失败时，使用简单的合并方法：
        1. 合并所有概念节点（去重）
        2. 合并所有关系
        3. 添加来源文件信息

        Args:
            file_analyses: 文件分析结果列表

        Returns:
            Dict: 合并后的分析结果

        注意：
        - 这是 AI 分析失败时的兜底方案
        - 合并结果质量不如 AI 综合分析
        - 使用简单的名称去重策略
        """
        all_concepts = []      # 所有概念节点
        all_relations = []     # 所有关系
        seen_names = set()     # 已处理的概念名称（用于去重）

        for fa in file_analyses:
            source_file = fa.get("file_name", "")  # 来源文件名

            # 合并概念节点（去重）
            for concept in fa.get("concepts", []):
                name = concept.get("name", "")
                if name and name not in seen_names:
                    seen_names.add(name)
                    concept_copy = concept.copy()
                    concept_copy["source_file"] = source_file  # 添加来源标记
                    all_concepts.append(concept_copy)

            # 合并关系
            for relation in fa.get("relations", []):
                all_relations.append(relation)

        # 使用第一个文件的标题作为基础
        title = file_analyses[0].get("title", "综合分析")
        # 合并摘要（最多3个文件的摘要）
        summaries = [fa.get("summary", "") for fa in file_analyses if fa.get("summary")]
        summary = "；".join(summaries[:3])

        return {
            "title": f"综合：{title}",
            "summary": summary,
            "concepts": all_concepts,
            "relations": all_relations,
            "source_files": [fa.get("file_id") for fa in file_analyses]
        }

    async def _call_llm(self, prompt: str) -> str:
        """
        调用 LLM 服务的统一入口

        根据配置的服务商（llm_provider）分发到对应的 API 调用方法。
        支持的服务商：DeepSeek、OpenAI、Claude、智谱AI、小米MiMo

        Args:
            prompt: 发送给 AI 的提示词

        Returns:
            str: AI 返回的文本内容

        Raises:
            Exception: 未配置 API 密钥或不支持的服务商

        流程：
        1. 检查 API 密钥是否配置
        2. 构建通用请求头（包含认证信息）
        3. 根据服务商分发到对应的调用方法
        """
        # 检查 API 密钥
        if not self.api_key:
            raise Exception("未配置LLM API密钥，请在设置页面或 .env 文件中配置")

        # 构建通用请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"  # Bearer Token 认证
        }

        # 根据服务商分发到对应的调用方法
        if self.llm_provider == "deepseek":
            return await self._call_deepseek(prompt, headers)
        elif self.llm_provider == "openai":
            return await self._call_openai(prompt, headers)
        elif self.llm_provider == "claude":
            return await self._call_claude(prompt, headers)
        elif self.llm_provider == "zhipu":
            return await self._call_zhipu(prompt, headers)
        elif self.llm_provider == "xiaomi":
            return await self._call_xiaomi(prompt, headers)
        else:
            raise Exception(f"不支持的LLM服务: {self.llm_provider}")

    async def _call_deepseek(self, prompt: str, headers: Dict) -> str:
        """
        调用 DeepSeek API（OpenAI 兼容格式）

        DeepSeek 使用与 OpenAI 兼容的 API 格式，支持 Prompt Caching。
        相同的系统提示词和指令前缀会自动命中缓存，降低 API 调用成本。

        Args:
            prompt: 提示词内容
            headers: 请求头（包含认证信息）

        Returns:
            str: AI 返回的文本内容

        API 参数说明：
        - model: 模型名称（deepseek-chat、deepseek-r1 等）
        - messages: 消息列表（系统提示词 + 用户提示词）
        - temperature: 温度参数（0.0-1.0），越低越确定性
        - max_tokens: 最大输出 token 数量
        - timeout: 请求超时时间（秒）
        """
        # 获取 API 基础地址（优先使用自定义地址）
        api_base = self.api_base or "https://api.deepseek.com"
        # 获取模型名称
        model = self.get_model("deepseek-chat")

        # 验证模型名称，如果无效则使用默认模型
        if model not in DEEPSEEK_MODELS and not model.startswith("deepseek"):
            model = "deepseek-chat"

        # 构建消息列表
        # 使用固定的系统提示词可以提高 Prompt Caching 命中率
        messages = [
            {"role": "system", "content": self._system_prompt},  # 系统提示词（固定）
            {"role": "user", "content": prompt}                  # 用户提示词（变化）
        ]

        # DeepSeek 支持 prompt caching，通过保持相同的消息前缀
        # 系统提示词是固定的，分析指令前缀也是固定的
        # 只有文档内容会变化，这样可以最大化缓存命中率

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{api_base}/chat/completions",  # API 端点
                headers=headers,
                json={
                    "model": model,           # 模型名称
                    "messages": messages,      # 消息列表
                    "temperature": 0.2,        # 低温度，结果更确定性
                    "max_tokens": 16384,       # 最大输出 16K tokens
                    # DeepSeek 的 prompt caching 默认开启
                    # 相同的前缀会自动命中缓存
                },
                timeout=300.0  # 5分钟超时（长文本分析需要较长时间）
            )

            # 检查响应状态
            if response.status_code != 200:
                error_msg = response.text
                raise Exception(f"DeepSeek API调用失败 (模型: {model}): {error_msg}")

            result = response.json()

            # 输出缓存使用情况（用于监控和调试）
            usage = result.get("usage", {})
            cache_hit = usage.get("prompt_cache_hit_tokens", 0)    # 缓存命中 token 数
            cache_miss = usage.get("prompt_cache_miss_tokens", 0)  # 缓存未命中 token 数
            if cache_hit > 0 or cache_miss > 0:
                total = cache_hit + cache_miss
                hit_rate = (cache_hit / total * 100) if total > 0 else 0
                print(f"缓存命中: {cache_hit} tokens, 未命中: {cache_miss} tokens, 命中率: {hit_rate:.1f}%")

            # 提取 AI 返回的文本内容
            return result["choices"][0]["message"]["content"]

    async def _call_openai(self, prompt: str, headers: Dict) -> str:
        """
        调用 OpenAI API

        OpenAI API 支持 Prompt Caching，相同的前缀内容会自动缓存。

        Args:
            prompt: 提示词内容
            headers: 请求头（包含认证信息）

        Returns:
            str: AI 返回的文本内容
        """
        api_base = self.api_base or "https://api.openai.com/v1"
        model = self.get_model("gpt-3.5-turbo")

        # 构建消息列表
        messages = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": prompt}
        ]

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{api_base}/chat/completions",
                headers=headers,
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": 0.2,
                    "max_tokens": 16384
                },
                timeout=300.0
            )

            if response.status_code != 200:
                raise Exception(f"OpenAI API调用失败: {response.text}")

            result = response.json()

            # 输出缓存使用情况
            usage = result.get("usage", {})
            cache_hit = usage.get("prompt_tokens_details", {}).get("cached_tokens", 0)
            if cache_hit > 0:
                total = usage.get("prompt_tokens", 0)
                hit_rate = (cache_hit / total * 100) if total > 0 else 0
                print(f"缓存命中: {cache_hit}/{total} tokens, 命中率: {hit_rate:.1f}%")

            return result["choices"][0]["message"]["content"]

    async def _call_claude(self, prompt: str, headers: Dict) -> str:
        """
        调用 Claude API

        Claude API 使用不同的消息格式和认证方式。
        需要额外的 anthropic-version 头部。

        Args:
            prompt: 提示词内容
            headers: 请求头（包含认证信息）

        Returns:
            str: AI 返回的文本内容

        注意：
        - Claude API 端点是 /messages，不是 /chat/completions
        - 认证使用 x-api-key 头部，不是 Authorization
        - 需要 anthropic-version 头部指定 API 版本
        """
        api_base = self.api_base or "https://api.anthropic.com/v1"
        model = self.get_model("claude-3-sonnet-20240229")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{api_base}/messages",  # Claude API 端点
                headers={
                    **headers,                                    # 通用头部
                    "x-api-key": self.api_key,                  # Claude 专用认证
                    "anthropic-version": "2023-06-01"           # API 版本
                },
                json={
                    "model": model,
                    "max_tokens": 16384,
                    "messages": [
                        {"role": "user", "content": prompt}  # Claude 不需要系统提示词
                    ]
                },
                timeout=300.0
            )

            if response.status_code != 200:
                raise Exception(f"Claude API调用失败: {response.text}")

            result = response.json()
            # Claude 返回格式：{"content": [{"text": "..."}]}
            return result["content"][0]["text"]

    async def _call_zhipu(self, prompt: str, headers: Dict) -> str:
        """
        调用智谱 AI API（GLM 系列模型）

        智谱 AI 使用与 OpenAI 兼容的 API 格式。

        Args:
            prompt: 提示词内容
            headers: 请求头（包含认证信息）

        Returns:
            str: AI 返回的文本内容
        """
        api_base = self.api_base or "https://open.bigmodel.cn/api/paas/v4"
        model = self.get_model("glm-4")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{api_base}/chat/completions",
                headers=headers,
                json={
                    "model": model,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 16384
                },
                timeout=300.0
            )

            if response.status_code != 200:
                raise Exception(f"智谱AI API调用失败: {response.text}")

            result = response.json()
            return result["choices"][0]["message"]["content"]

    async def _call_xiaomi(self, prompt: str, headers: Dict) -> str:
        """
        调用小米 MiMo API（OpenAI 兼容格式）

        小米 MiMo 使用 OpenAI 兼容的 API 格式。
        API 地址：https://token-plan-cn.xiaomimimo.com

        Args:
            prompt: 提示词内容
            headers: 请求头（包含认证信息）

        Returns:
            str: AI 返回的文本内容

        注意：
        - 小米 MiMo 使用 OpenAI 兼容格式，不是 Anthropic 格式
        - 需要 Authorization: Bearer 头部
        - 消息格式与 OpenAI API 一致
        """
        api_base = self.api_base or "https://token-plan-cn.xiaomimimo.com"
        model = self.get_model("mimo-v2.5-pro")

        # 小米 MiMo 使用 OpenAI 兼容格式
        xiaomi_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"     # OpenAI 认证方式
        }

        # 使用固定的系统提示词可以提高 Prompt Caching 命中率
        messages = [
            {"role": "system", "content": self._system_prompt},  # 系统提示词（固定）
            {"role": "user", "content": prompt}                  # 用户提示词（变化）
        ]

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{api_base}/v1/chat/completions",  # OpenAI 兼容格式的端点
                headers=xiaomi_headers,
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": 0.2,
                    "max_tokens": 16384
                },
                timeout=300.0
            )

            if response.status_code != 200:
                raise Exception(f"小米MiMo API调用失败 (模型: {model}): {response.text}")

            result = response.json()
            # OpenAI 格式返回：{"choices": [{"message": {"content": "..."}}]}
            return result["choices"][0]["message"]["content"]

    def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
        """
        解析 AI 响应，提取 JSON 数据并验证层级关系

        AI 返回的文本可能包含其他内容（如解释说明），
        需要从中提取 JSON 格式的分析结果。

        Args:
            response: AI 返回的原始文本

        Returns:
            Dict: 解析后的 JSON 数据（已验证层级关系）

        Raises:
            Exception: 无法提取 JSON 或 JSON 格式错误

        解析策略：
        1. 查找第一个 { 和最后一个 } 的位置
        2. 提取两者之间的内容
        3. 解析为 JSON 对象
        4. 验证并修复层级关系
        """
        try:
            # 查找 JSON 的起始位置（第一个 {）
            json_start = response.find("{")
            # 查找 JSON 的结束位置（最后一个 }）
            json_end = response.rfind("}") + 1

            if json_start != -1 and json_end != -1:
                # 提取 JSON 字符串
                json_str = response[json_start:json_end]
                data = json.loads(json_str)

                # 验证并修复层级关系
                data = self._validate_hierarchy(data)

                return data
            else:
                raise Exception("无法从响应中提取JSON")
        except json.JSONDecodeError as e:
            raise Exception(f"JSON解析失败: {str(e)}")

    def _validate_hierarchy(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证并修复层级关系

        检查 AI 返回的数据中，节点的 level 值是否与父子关系一致。
        如果不一致，自动修复 level 值。

        验证规则：
        1. 构建父子关系图
        2. 对于每个节点，如果它有父节点，它的 level 应该是父节点 level + 1
        3. 如果 level 不正确，自动修正
        4. 如果所有节点都是 level 1，但有 contains 关系，则根据关系自动推断层级

        Args:
            data: AI 返回的分析结果

        Returns:
            Dict: 修复后的分析结果
        """
        concepts = data.get('concepts', [])
        relations = data.get('relations', [])

        if not concepts:
            return data

        # 构建父子关系图：child_name -> parent_name
        parent_map = {}
        for rel in relations:
            if rel.get('type') == 'contains':
                parent_map[rel['target']] = rel['source']

        # 构建概念名称到概念的映射
        concept_map = {c.get('name', ''): c for c in concepts}

        # 检查是否所有节点都是 level 1
        all_level_1 = all(c.get('level', 1) == 1 for c in concepts)

        # 如果所有节点都是 level 1，但有 contains 关系，则根据关系自动推断层级
        if all_level_1 and parent_map:
            # 找到根节点（没有父节点的节点）
            child_names = set(parent_map.keys())
            parent_names = set(parent_map.values())
            root_names = parent_names - child_names

            # 为根节点设置 level 1
            for concept in concepts:
                if concept.get('name') in root_names:
                    concept['level'] = 1

            # BFS 遍历，为子节点设置正确的 level
            queue = list(root_names)
            visited = set(root_names)

            while queue:
                current_name = queue.pop(0)
                current_concept = concept_map.get(current_name)
                if not current_concept:
                    continue

                current_level = current_concept.get('level', 1)

                # 找到所有子节点
                for child_name, parent_name in parent_map.items():
                    if parent_name == current_name and child_name not in visited:
                        child_concept = concept_map.get(child_name)
                        if child_concept:
                            child_concept['level'] = current_level + 1
                            visited.add(child_name)
                            queue.append(child_name)

        # 如果没有 contains 关系，但有 relates 关系，尝试根据顺序推断层级
        elif not parent_map and relations:
            # 第一个节点作为根节点（level 1）
            if concepts:
                concepts[0]['level'] = 1

            # 根据 relates 关系的顺序，为后续节点设置递增的 level
            # 但这可能导致不准确，所以只在没有其他信息时使用
            pass

        # 验证每个节点的 level
        for concept in concepts:
            name = concept.get('name', '')
            level = concept.get('level', 1)

            # 如果有父节点，level 应该是父节点 level + 1
            if name in parent_map:
                parent_name = parent_map[name]
                parent_concept = concept_map.get(parent_name)

                if parent_concept:
                    expected_level = parent_concept.get('level', 1) + 1

                    # 如果 level 不正确，修正它
                    if level != expected_level:
                        concept['level'] = expected_level

        # 确保所有节点都有有效的 level（1-4）
        for concept in concepts:
            level = concept.get('level', 1)
            if level < 1:
                concept['level'] = 1
            elif level > 4:
                concept['level'] = 4

        return data

    def _fallback_analysis(self, content: str) -> Dict[str, Any]:
        """
        备用分析方法（当 AI 不可用时）

        当 LLM API 调用失败时，使用简单的文本分析作为兜底方案。
        基于词频统计提取关键词，生成简单的思维树结构。

        Args:
            content: 文本内容

        Returns:
            Dict: 简单的分析结果（质量不如 AI 分析）

        实现原理：
        1. 提取文档前20行作为标题候选
        2. 使用词频统计提取关键词
        3. 创建简单的关联关系
        """
        lines = content.split("\n")
        title = "未命名思维树"
        summary = content[:500] + "..." if len(content) > 500 else content

        # 尝试提取标题（取第一个非空行作为标题）
        for line in lines[:20]:
            line = line.strip()
            if line and len(line) < 100:  # 标题不应太长
                title = line
                break

        # 简单的关键词提取（基于词频统计）
        words = content.split()
        word_freq = {}
        for word in words:
            if len(word) > 3:  # 忽略太短的词（可能是停用词）
                word_freq[word] = word_freq.get(word, 0) + 1

        # 按词频排序，取前20个高频词作为概念节点
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:20]

        # 构建概念节点列表
        concepts = [
            {
                "name": word,
                "description": f"在文本中出现 {count} 次",  # 简单描述
                "type": "concept",  # 类型：概念
                "level": 1          # 层级：1（最高级）
            }
            for word, count in sorted_words
        ]

        # 创建简单的关联关系（按顺序关联）
        relations = []
        if len(concepts) > 1:
            for i in range(len(concepts) - 1):
                relations.append({
                    "source": concepts[i]["name"],      # 源节点
                    "target": concepts[i + 1]["name"],  # 目标节点
                    "label": "相关",                     # 关系标签
                    "type": "relates"                    # 关系类型
                })

        return {
            "title": title,
            "summary": summary,
            "concepts": concepts,
            "relations": relations
        }
