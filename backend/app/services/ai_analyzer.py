import os
import json
import re
from typing import Dict, Any, List, Set
from collections import Counter
import httpx
from dotenv import load_dotenv

load_dotenv()

# DeepSeek 模型列表
DEEPSEEK_MODELS = {
    "deepseek-chat": "通用对话模型 (DeepSeek-V3)",
    "deepseek-coder": "代码专用模型",
    "deepseek-reasoner": "推理增强模型 (DeepSeek-R1)",
    "deepseek-v3": "DeepSeek-V3 最新版",
    "deepseek-r1": "DeepSeek-R1 推理模型",
    "deepseek-v4-flash": "DeepSeek-V4 Flash 快速模型",
}

# 配置参数
MAX_CONTENT_LENGTH = 80000  # 每批次最大内容长度（字符数）
OVERLAP_LENGTH = 8000      # 批次间重叠长度，增加上下文保留
MIN_SECTION_LENGTH = 500   # 最小段落长度，过短的段落会合并

class AIAnalyzer:
    """AI分析器，用于从文本中提取概念和关系"""

    def __init__(self):
        # 支持多种LLM服务（优先从数据库读取，fallback 到环境变量）
        self.llm_provider = os.getenv("LLM_PROVIDER", "deepseek")
        self.api_key = os.getenv("LLM_API_KEY", "")
        self.api_base = os.getenv("LLM_API_BASE", "")
        self.model = os.getenv("LLM_MODEL", "")

        # 尝试从数据库加载配置
        self._load_from_db_on_init()

        # 固定的系统提示词前缀（用于缓存命中）
        self._system_prompt = "你是一个专业的知识分析助手，擅长从文本中提取概念和关系。请用中文回复。请确保返回有效的JSON格式。"

        # 固定的分析指令前缀（用于缓存命中）
        self._analysis_instruction_prefix = """请分析以下文档内容，提取知识点并构建层级结构。

文档结构说明：
- 使用 # ## ### 等标题标记层级
- # 一级标题 = 核心主题（level 1）
- ## 二级标题 = 主要分类（level 2）
- ### 三级标题 = 子主题（level 3）
- 正文内容 = 详细解释（level 4）

**核心要求**：
1. **提取所有知识点**：必须提取文档中的每一个知识点、概念、主题，不要遗漏任何一个
2. **保留文档层级**：严格按照标题层级构建树结构
3. **完整描述**：保留每个知识点的完整解释内容，不要省略任何细节
4. **分类清晰**：确保每个节点有明确的父级分类

节点类型说明：
- concept: 核心概念/主题（level 1）
- topic: 分类/子主题（level 2）
- detail: 具体知识点（level 3）
- example: 示例/代码（level 4）

请以JSON格式返回：
{
    "title": "文档主题",
    "summary": "内容摘要（200-500字）",
    "concepts": [
        {
            "name": "知识点名称",
            "description": "该知识点的完整解释（保留原文所有内容）",
            "type": "concept/topic/detail/example",
            "level": 1-4
        }
    ],
    "relations": [
        {
            "source": "父概念",
            "target": "子概念",
            "label": "包含",
            "type": "contains"
        }
    ]
}

**重要提示**：
- 必须提取文档中的【所有】知识点，不能只提取部分
- 每个独立的概念、主题、知识点都要作为一个单独的节点
- 描述要完整保留原文内容，不要概括或省略
- 如果文档有 10 个知识点，就必须返回 10 个节点
- 节点数量应该与文档中的知识点数量一致

文档内容：
"""

        # 固定的问答分析指令前缀（用于缓存命中）
        self._qa_instruction_prefix = """请分析以下问答格式的文本内容。

**核心要求**：
1. 识别主题（第一个非问/答的内容通常是主题）
2. 将【每一个】"问：xxx"作为一个节点，节点名称就是问题内容
3. 将对应的"答：xxx"作为该节点的详细描述
4. 如果问题之间有逻辑关系，建立相应的关联

请以JSON格式返回结果，格式如下：
{
    "title": "主题名称",
    "summary": "内容摘要",
    "concepts": [
        {
            "name": "问题内容（去掉问：前缀）",
            "description": "完整的答案内容（去掉答：前缀，保留所有细节）",
            "type": "concept",
            "level": 1
        }
    ],
    "relations": [
        {
            "source": "问题1",
            "target": "问题2",
            "label": "相关",
            "type": "relates"
        }
    ]
}

**重要提示**：
- 必须提取【所有】问题，不能只提取部分
- 节点名称只保留问题内容，不要包含"问："前缀
- 描述要完整保留答案的所有内容，不要省略
- 如果文档有 12 个问题，就必须返回 12 个节点
- 如果问题之间有逻辑顺序或关联，建立相应的关系

文本内容：
"""

    def _load_from_db_on_init(self):
        """初始化时尝试从数据库加载配置"""
        try:
            from app.core.database import SessionLocal
            from app.models.db_models import AIConfigDB
            from app.core.security import mask_api_key

            db = SessionLocal()
            try:
                config = db.query(AIConfigDB).first()
                if config and config.api_key:
                    self.llm_provider = config.provider
                    self.api_key = config.api_key
                    self.api_base = config.api_base or ""
                    self.model = config.model or ""
                    print(f"[AIAnalyzer] 从数据库加载配置: provider={config.provider}, "
                          f"key={mask_api_key(config.api_key)}, model={config.model}")
                else:
                    print("[AIAnalyzer] 数据库无配置，使用环境变量")
            finally:
                db.close()
        except Exception as e:
            print(f"[AIAnalyzer] 从数据库加载配置失败，使用环境变量: {e}")

    def reload_config_from_db(self, db):
        """从数据库重新加载配置（热更新）"""
        from app.models.db_models import AIConfigDB
        from app.core.security import mask_api_key

        config = db.query(AIConfigDB).first()
        if config:
            self.llm_provider = config.provider
            self.api_key = config.api_key
            self.api_base = config.api_base or ""
            self.model = config.model or ""
            print(f"[AIAnalyzer] 配置已热更新: provider={config.provider}, "
                  f"key={mask_api_key(config.api_key)}, model={config.model}")
            return True
        return False

    def get_model(self, default: str = "deepseek-chat") -> str:
        """获取模型名称"""
        return self.model or default

    async def analyze(self, content: str) -> Dict[str, Any]:
        """分析文本内容，提取概念和关系"""
        # 如果内容太长，进行分段处理
        if len(content) > MAX_CONTENT_LENGTH:
            return await self._analyze_long_content(content)

        prompt = self._build_analysis_prompt(content)

        try:
            response = await self._call_llm(prompt)
            return self._parse_analysis_response(response)
        except Exception as e:
            # 如果AI调用失败，返回简单的结构化结果
            return self._fallback_analysis(content)

    async def _analyze_long_content(self, content: str) -> Dict[str, Any]:
        """分析长文本内容 - 智能分段 + 滑动窗口 + 分批分析"""
        # 第一步：提取文档目录结构（如果有）
        toc = self._extract_toc(content)

        # 第二步：智能分段
        sections = self._smart_split(content)

        if len(sections) <= 1:
            # 如果无法有效分割，直接处理
            truncated = content[:MAX_CONTENT_LENGTH]
            prompt = self._build_analysis_prompt(truncated)
            try:
                response = await self._call_llm(prompt)
                return self._parse_analysis_response(response)
            except Exception as e:
                return self._fallback_analysis(content)

        # 第三步：构建批次（带滑动窗口）
        batches = self._create_batches_with_overlap(sections)

        # 第四步：分批分析
        all_results = []

        # 先分析目录（如果有）
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
                part_info = f"这是第 {i+1}/{len(batches)} 部分"
                prompt = self._build_analysis_prompt(batch, is_part=True, part_info=part_info)
                response = await self._call_llm(prompt)
                result = self._parse_analysis_response(response)
                all_results.append(result)
                print(f"批次 {i+1}/{len(batches)} 分析完成")
            except Exception as e:
                print(f"批次 {i+1} 分析失败: {e}")

        if not all_results:
            return self._fallback_analysis(content)

        # 第五步：合并所有分析结果
        return self._merge_analysis_results(all_results)

    def _extract_toc(self, content: str) -> str:
        """提取文档目录结构"""
        lines = content.split('\n')
        toc_lines = []
        in_toc = False

        for line in lines:
            stripped = line.strip()

            # 检测目录开始
            if any(kw in stripped.lower() for kw in ['目录', 'table of contents', 'toc', 'contents']):
                in_toc = True
                toc_lines.append(stripped)
                continue

            # 检测目录项
            if in_toc:
                # 目录项通常包含页码或缩进
                if re.match(r'^[\d\.\)]+\s+.+\s*[\.\.]+\s*\d+$', stripped):
                    toc_lines.append(stripped)
                elif re.match(r'^\s{2,}.+', stripped):
                    toc_lines.append(stripped)
                elif stripped == '':
                    continue
                else:
                    # 目录结束
                    break

        # 如果没有找到目录，提取所有标题作为伪目录
        if len(toc_lines) < 3:
            toc_lines = ["# 文档标题结构"]
            for line in lines:
                stripped = line.strip()
                if stripped.startswith('#'):
                    toc_lines.append(stripped)

        return '\n'.join(toc_lines) if len(toc_lines) > 3 else ''

    def _smart_split(self, content: str) -> List[str]:
        """智能分段 - 保留完整的语义单元"""
        lines = content.split('\n')
        sections = []
        current_section = []
        current_heading = ''

        for line in lines:
            stripped = line.strip()

            # 检测章节标题
            is_heading, heading_level = self._detect_heading(stripped)

            if is_heading:
                # 保存当前章节
                if current_section:
                    section_text = '\n'.join(current_section)
                    if len(section_text.strip()) >= MIN_SECTION_LENGTH:
                        sections.append(section_text)

                # 开始新章节
                current_heading = stripped
                current_section = [line]
            else:
                current_section.append(line)

                # 如果当前段落太长，按段落分割
                current_text = '\n'.join(current_section)
                if len(current_text) > MAX_CONTENT_LENGTH * 0.8:
                    # 按自然段落分割
                    paragraphs = current_text.split('\n\n')
                    if len(paragraphs) > 1:
                        # 保留最后一个段落继续
                        for para in paragraphs[:-1]:
                            if para.strip():
                                sections.append(para.strip())
                        current_section = [paragraphs[-1]]

        # 处理最后一个章节
        if current_section:
            section_text = '\n'.join(current_section)
            if len(section_text.strip()) >= MIN_SECTION_LENGTH:
                sections.append(section_text)

        # 合并过短的段落
        return self._merge_short_sections(sections)

    def _detect_heading(self, line: str) -> tuple:
        """检测标题，返回 (是否标题, 标题级别)"""
        if not line:
            return False, 0

        # Markdown 标题
        match = re.match(r'^(#{1,6})\s+', line)
        if match:
            return True, len(match.group(1))

        # 数字编号标题（如 1. 2.3. 1.2.3.）
        if re.match(r'^\d+(\.\d+)*[\.\)]\s+\S', line) and len(line) < 100:
            level = line.count('.') + 1
            return True, min(level, 6)

        # 中文章节标识
        chapter_patterns = [
            (r'^第[一二三四五六七八九十百千\d]+[章篇]', 1),
            (r'^第[一二三四五六七八九十百千\d]+[节部]', 2),
            (r'^[一二三四五六七八九十]+[、．.]', 2),
            (r'^[（\(][一二三四五六七八九十\d]+[）\)]', 3),
        ]
        for pattern, level in chapter_patterns:
            if re.match(pattern, line):
                return True, level

        # 全大写英文标题
        if line.isupper() and 5 < len(line) < 80:
            return True, 1

        # 特殊标记
        if line.startswith('【') and line.endswith('】'):
            return True, 2

        return False, 0

    def _merge_short_sections(self, sections: List[str]) -> List[str]:
        """合并过短的段落"""
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

        # 处理最后一个
        if current.strip():
            if len(current.strip()) < MIN_SECTION_LENGTH and merged:
                # 合并到前一个
                merged[-1] = merged[-1] + '\n\n' + current
            else:
                merged.append(current)

        return merged

    def _create_batches_with_overlap(self, sections: List[str]) -> List[str]:
        """创建批次，带滑动窗口重叠"""
        batches = []
        current_batch = []
        current_length = 0

        for i, section in enumerate(sections):
            section_len = len(section)

            # 如果添加当前段落会超出批次大小
            if current_length + section_len > MAX_CONTENT_LENGTH and current_batch:
                # 保存当前批次
                batch_content = '\n\n'.join(current_batch)
                batches.append(batch_content)

                # 计算重叠：从当前批次末尾取部分内容作为下一批次开头
                overlap_content = self._get_overlap_content(current_batch, OVERLAP_LENGTH)
                current_batch = [overlap_content] if overlap_content else []
                current_length = len(overlap_content) if overlap_content else 0

            current_batch.append(section)
            current_length += section_len

        # 处理最后一个批次
        if current_batch:
            batch_content = '\n\n'.join(current_batch)
            if batch_content.strip():
                batches.append(batch_content)

        return batches

    def _get_overlap_content(self, batch: List[str], overlap_length: int) -> str:
        """获取批次末尾的重叠内容"""
        if not batch:
            return ''

        # 从最后一个段落开始，向前取内容
        overlap_parts = []
        current_length = 0

        for section in reversed(batch):
            if current_length + len(section) > overlap_length:
                # 只取部分内容
                remaining = overlap_length - current_length
                if remaining > 100:  # 至少取100个字符
                    overlap_parts.append(section[-remaining:])
                break
            overlap_parts.append(section)
            current_length += len(section)

        return '\n\n'.join(reversed(overlap_parts)) if overlap_parts else ''

    def _merge_analysis_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """合并多个分析结果 - 保留所有节点"""
        if len(results) == 1:
            return results[0]

        # 合并标题和摘要
        title = results[0].get('title', '未命名思维树')
        summaries = [r.get('summary', '') for r in results if r.get('summary')]
        summary = '\n\n'.join(summaries) if summaries else ''

        # 合并所有概念节点 - 使用更宽松的去重策略
        all_concepts = []
        seen_names = {}  # 改用字典，记录名称和描述的组合
        for result in results:
            for concept in result.get('concepts', []):
                name = concept.get('name', '').strip()
                if not name:
                    continue

                # 创建唯一键：名称 + 描述前50个字符
                desc_prefix = concept.get('description', '')[:50].strip()
                unique_key = f"{name}|{desc_prefix}"

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

        # 如果有多个批次的结果，添加批次间的关联
        if len(results) > 1:
            # 将各批次的主题节点关联起来
            main_topics = []
            for result in results:
                concepts = result.get('concepts', [])
                if concepts:
                    # 取第一个概念作为该批次的主题
                    main_topics.append(concepts[0].get('name', ''))

            # 创建主题间的关联
            for i in range(len(main_topics) - 1):
                if main_topics[i] and main_topics[i + 1]:
                    all_relations.append({
                        "source": main_topics[i],
                        "target": main_topics[i + 1],
                        "label": "相关内容",
                        "type": "relates"
                    })

        print(f"合并结果：共 {len(all_concepts)} 个节点，{len(all_relations)} 条关系")

        return {
            "title": title,
            "summary": summary,
            "concepts": all_concepts,
            "relations": all_relations
        }

    def extract_keywords(self, content: str, analysis_result: Dict[str, Any] = None) -> List[str]:
        """
        从文本和分析结果中提取关键词

        Args:
            content: 原始文本内容
            analysis_result: AI 分析结果（可选）

        Returns:
            关键词列表
        """
        keywords = set()

        # 1. 从分析结果中提取关键词
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

        # 3. 过滤停用词和过短的词
        filtered_keywords = [w for w in keywords if len(w) > 1]

        # 4. 返回前20个关键词
        return filtered_keywords[:20]

    def _extract_words_from_text(self, text: str) -> List[str]:
        """从文本中提取词语"""
        # 移除标点符号
        text = re.sub(r'[^\w\s]', ' ', text)
        # 分词
        words = text.lower().split()
        # 过滤停用词
        stop_words = {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一',
            '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有',
            '看', '好', '自己', '这', '他', '她', '它', '们', '那', '被', '从', '把',
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'can', 'shall', 'to', 'of', 'in', 'for',
            'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'out', 'off', 'over',
            'under', 'again', 'further', 'then', 'once'
        }
        return [w for w in words if w not in stop_words and len(w) > 1]

    def _extract_high_freq_words(self, content: str, top_n: int = 20) -> List[str]:
        """提取高频词"""
        words = self._extract_words_from_text(content)
        # 统计词频
        word_counts = Counter(words)
        # 返回前 N 个高频词
        return [word for word, count in word_counts.most_common(top_n)]

    async def analyze_single_file(self, content: str, file_name: str) -> Dict[str, Any]:
        """
        单文件分析，提取结构化信息和关键词

        Args:
            content: 文件内容
            file_name: 文件名

        Returns:
            包含分析结果和关键词的字典
        """
        # 1. 进行 AI 分析
        analysis_result = await self.analyze(content)

        # 2. 提取关键词
        keywords = self.extract_keywords(content, analysis_result)

        # 3. 返回完整结果
        return {
            "title": analysis_result.get("title", file_name),
            "summary": analysis_result.get("summary", ""),
            "keywords": keywords,
            "concepts": analysis_result.get("concepts", []),
            "relations": analysis_result.get("relations", [])
        }

    async def refine(self, tree: Any, feedback: str) -> Dict[str, Any]:
        """根据反馈优化思维树"""
        prompt = self._build_refine_prompt(tree, feedback)

        try:
            response = await self._call_llm(prompt)
            return self._parse_analysis_response(response)
        except Exception as e:
            # 如果AI调用失败，返回原始树结构
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
        """构建分析提示词 - 使用固定前缀优化缓存命中"""
        # 检测是否是问答格式
        is_qa_format = "问：" in content and "答：" in content

        # 添加上下文说明
        context_prefix = ""
        if is_part:
            context_prefix = f"注意：以下是长文档的一部分内容。{part_info}\n请尽可能完整地提取本部分内容的知识点，不要遗漏任何重要信息。\n\n"

        # 使用固定的指令前缀（优化缓存命中）
        if is_qa_format:
            return f"{context_prefix}{self._qa_instruction_prefix}{content}\n\n请直接返回JSON格式的结果，不要添加其他说明。"
        else:
            return f"{context_prefix}{self._analysis_instruction_prefix}{content}\n\n请直接返回JSON格式的结果，不要添加其他说明。"

    def _build_refine_prompt(self, tree: Any, feedback: str) -> str:
        """构建优化提示词"""
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

        Args:
            file_analyses: 分组内文件的分析结果列表
            group_info: 分组信息

        Returns:
            综合分析结果
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
            response = await self._call_llm(prompt)
            result = self._parse_analysis_response(response)
            # 添加来源标记
            result["source_files"] = [f.get("file_id") for f in file_analyses]
            return result
        except Exception as e:
            print(f"分组分析失败: {e}")
            # 失败时合并各个文件的结果
            return self._merge_file_results(file_analyses)

    def _build_group_analysis_prompt(self, file_analyses: List[Dict[str, Any]],
                                     group_info: Dict[str, Any]) -> str:
        """构建分组综合分析提示词"""
        # 构建文件信息描述
        files_desc = []
        for i, fa in enumerate(file_analyses, 1):
            title = fa.get("title", "未命名")
            summary = fa.get("summary", "")
            concepts = [c.get("name", "") for c in fa.get("concepts", [])[:5]]
            files_desc.append(
                f"文件{i}: {title}\n"
                f"摘要: {summary[:200]}\n"
                f"主要概念: {', '.join(concepts)}"
            )

        files_text = "\n\n".join(files_desc)
        common_keywords = ", ".join(group_info.get("common_keywords", [])[:5])

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
        """合并多个文件的分析结果（作为备用方案）"""
        all_concepts = []
        all_relations = []
        seen_names = set()

        for fa in file_analyses:
            source_file = fa.get("file_name", "")

            for concept in fa.get("concepts", []):
                name = concept.get("name", "")
                if name and name not in seen_names:
                    seen_names.add(name)
                    concept_copy = concept.copy()
                    concept_copy["source_file"] = source_file
                    all_concepts.append(concept_copy)

            for relation in fa.get("relations", []):
                all_relations.append(relation)

        # 使用第一个文件的标题作为基础
        title = file_analyses[0].get("title", "综合分析")
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
        """调用LLM服务"""
        if not self.api_key:
            raise Exception("未配置LLM API密钥，请在 .env 文件中设置 LLM_API_KEY")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        # 根据不同的LLM服务构建请求
        if self.llm_provider == "deepseek":
            return await self._call_deepseek(prompt, headers)
        elif self.llm_provider == "openai":
            return await self._call_openai(prompt, headers)
        elif self.llm_provider == "claude":
            return await self._call_claude(prompt, headers)
        elif self.llm_provider == "zhipu":
            return await self._call_zhipu(prompt, headers)
        else:
            raise Exception(f"不支持的LLM服务: {self.llm_provider}")

    async def _call_deepseek(self, prompt: str, headers: Dict) -> str:
        """调用 DeepSeek API (OpenAI 兼容格式) - 支持 Prompt Caching"""
        api_base = self.api_base or "https://api.deepseek.com"
        model = self.get_model("deepseek-chat")

        # 验证模型名称
        if model not in DEEPSEEK_MODELS and not model.startswith("deepseek"):
            model = "deepseek-chat"

        # 构建消息列表，使用固定的系统提示词（优化缓存命中）
        messages = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": prompt}
        ]

        # DeepSeek 支持 prompt caching，通过保持相同的消息前缀
        # 系统提示词是固定的，分析指令前缀也是固定的
        # 只有文档内容会变化，这样可以最大化缓存命中率

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{api_base}/chat/completions",
                headers=headers,
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": 0.2,
                    "max_tokens": 16384,
                    # DeepSeek 的 prompt caching 默认开启
                    # 相同的前缀会自动命中缓存
                },
                timeout=300.0
            )

            if response.status_code != 200:
                error_msg = response.text
                raise Exception(f"DeepSeek API调用失败 (模型: {model}): {error_msg}")

            result = response.json()

            # 输出缓存使用情况（如果有）
            usage = result.get("usage", {})
            cache_hit = usage.get("prompt_cache_hit_tokens", 0)
            cache_miss = usage.get("prompt_cache_miss_tokens", 0)
            if cache_hit > 0 or cache_miss > 0:
                total = cache_hit + cache_miss
                hit_rate = (cache_hit / total * 100) if total > 0 else 0
                print(f"缓存命中: {cache_hit} tokens, 未命中: {cache_miss} tokens, 命中率: {hit_rate:.1f}%")

            return result["choices"][0]["message"]["content"]

    async def _call_openai(self, prompt: str, headers: Dict) -> str:
        """调用OpenAI API - 支持 Prompt Caching"""
        api_base = self.api_base or "https://api.openai.com/v1"
        model = self.get_model("gpt-3.5-turbo")

        # 构建消息列表，使用固定的系统提示词（优化缓存命中）
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

            # 输出缓存使用情况（如果有）
            usage = result.get("usage", {})
            cache_hit = usage.get("prompt_tokens_details", {}).get("cached_tokens", 0)
            if cache_hit > 0:
                total = usage.get("prompt_tokens", 0)
                hit_rate = (cache_hit / total * 100) if total > 0 else 0
                print(f"缓存命中: {cache_hit}/{total} tokens, 命中率: {hit_rate:.1f}%")

            return result["choices"][0]["message"]["content"]

    async def _call_claude(self, prompt: str, headers: Dict) -> str:
        """调用Claude API"""
        api_base = self.api_base or "https://api.anthropic.com/v1"
        model = self.get_model("claude-3-sonnet-20240229")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{api_base}/messages",
                headers={
                    **headers,
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01"
                },
                json={
                    "model": model,
                    "max_tokens": 16384,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ]
                },
                timeout=300.0
            )

            if response.status_code != 200:
                raise Exception(f"Claude API调用失败: {response.text}")

            result = response.json()
            return result["content"][0]["text"]

    async def _call_zhipu(self, prompt: str, headers: Dict) -> str:
        """调用智谱AI API"""
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

    def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
        """解析AI响应"""
        try:
            # 尝试提取JSON部分
            json_start = response.find("{")
            json_end = response.rfind("}") + 1

            if json_start != -1 and json_end != -1:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
            else:
                raise Exception("无法从响应中提取JSON")
        except json.JSONDecodeError as e:
            raise Exception(f"JSON解析失败: {str(e)}")

    def _fallback_analysis(self, content: str) -> Dict[str, Any]:
        """备用分析方法（当AI不可用时）"""
        # 简单的文本分析，提取可能的标题和关键词
        lines = content.split("\n")
        title = "未命名思维树"
        summary = content[:500] + "..." if len(content) > 500 else content

        # 尝试提取标题
        for line in lines[:20]:
            line = line.strip()
            if line and len(line) < 100:
                title = line
                break

        # 简单的关键词提取（基于词频）
        words = content.split()
        word_freq = {}
        for word in words:
            if len(word) > 3:  # 忽略太短的词
                word_freq[word] = word_freq.get(word, 0) + 1

        # 按词频排序，取前20个
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:20]

        concepts = [
            {
                "name": word,
                "description": f"在文本中出现 {count} 次",
                "type": "concept",
                "level": 1
            }
            for word, count in sorted_words
        ]

        # 创建简单的关联关系
        relations = []
        if len(concepts) > 1:
            for i in range(len(concepts) - 1):
                relations.append({
                    "source": concepts[i]["name"],
                    "target": concepts[i + 1]["name"],
                    "label": "相关",
                    "type": "relates"
                })

        return {
            "title": title,
            "summary": summary,
            "concepts": concepts,
            "relations": relations
        }
