"""文件相关性检测服务"""
import re
from typing import List, Dict, Any, Set, Tuple
from collections import Counter


class RelationDetector:
    """检测多个文件之间的相关性"""

    def __init__(self, similarity_threshold: float = 0.3):
        """
        初始化相关性检测器

        Args:
            similarity_threshold: 相似度阈值，超过此值认为文件相关
        """
        self.similarity_threshold = similarity_threshold

    def detect_relations(self, file_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        检测多个文件分析结果之间的相关性

        Args:
            file_analyses: 单文件分析结果列表

        Returns:
            包含相似度矩阵和分组结果的字典
        """
        n = len(file_analyses)

        # 计算相似度矩阵
        similarity_matrix = self._calculate_similarity_matrix(file_analyses)

        # 进行分组
        groups = self._group_files(file_analyses, similarity_matrix)

        return {
            "similarity_matrix": similarity_matrix,
            "groups": groups,
            "total_files": n,
            "total_groups": len(groups)
        }

    def _calculate_similarity_matrix(self, file_analyses: List[Dict[str, Any]]) -> List[List[float]]:
        """计算文件间的相似度矩阵"""
        n = len(file_analyses)
        matrix = [[0.0] * n for _ in range(n)]

        for i in range(n):
            for j in range(i + 1, n):
                score = self._calculate_similarity(file_analyses[i], file_analyses[j])
                matrix[i][j] = score
                matrix[j][i] = score
            # 对角线为1（自己和自己完全相似）
            matrix[i][i] = 1.0

        return matrix

    def _calculate_similarity(self, file1: Dict[str, Any], file2: Dict[str, Any]) -> float:
        """计算两个文件的相似度"""
        # 1. 关键词重叠率（权重 0.4）
        keywords1 = set(file1.get("keywords", []))
        keywords2 = set(file2.get("keywords", []))
        keyword_score = self._jaccard_similarity(keywords1, keywords2)

        # 2. 概念名称重叠率（权重 0.3）
        concepts1 = set(c.get("name", "") for c in file1.get("concepts", []))
        concepts2 = set(c.get("name", "") for c in file2.get("concepts", []))
        concept_score = self._jaccard_similarity(concepts1, concepts2)

        # 3. 标题相似度（权重 0.3）
        title1 = file1.get("title", "")
        title2 = file2.get("title", "")
        title_score = self._title_similarity(title1, title2)

        # 综合评分
        total_score = (keyword_score * 0.4 +
                      concept_score * 0.3 +
                      title_score * 0.3)

        return round(total_score, 3)

    def _jaccard_similarity(self, set1: Set[str], set2: Set[str]) -> float:
        """计算 Jaccard 相似度"""
        if not set1 and not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0

    def _title_similarity(self, title1: str, title2: str) -> float:
        """计算标题相似度"""
        if not title1 or not title2:
            return 0.0

        # 提取标题中的关键词
        words1 = set(self._extract_words(title1))
        words2 = set(self._extract_words(title2))

        return self._jaccard_similarity(words1, words2)

    def _extract_words(self, text: str) -> List[str]:
        """从文本中提取关键词"""
        # 移除标点符号
        text = re.sub(r'[^\w\s]', ' ', text)
        # 分词（简单按空格分割）
        words = text.lower().split()
        # 过滤停用词
        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
        return [w for w in words if w not in stop_words and len(w) > 1]

    def _group_files(self, file_analyses: List[Dict[str, Any]],
                     similarity_matrix: List[List[float]]) -> List[Dict[str, Any]]:
        """根据相似度矩阵进行分组"""
        n = len(file_analyses)
        assigned = [False] * n
        groups = []

        for i in range(n):
            if assigned[i]:
                continue

            # 创建新分组
            group_files = [i]
            group_keywords = set(file_analyses[i].get("keywords", []))
            assigned[i] = True

            # 查找相似文件
            for j in range(i + 1, n):
                if assigned[j]:
                    continue

                if similarity_matrix[i][j] >= self.similarity_threshold:
                    group_files.append(j)
                    group_keywords |= set(file_analyses[j].get("keywords", []))
                    assigned[j] = True

            # 计算组内平均相似度
            avg_similarity = self._calculate_group_similarity(group_files, similarity_matrix)

            groups.append({
                "group_index": len(groups),
                "file_indices": group_files,
                "file_ids": [file_analyses[idx]["file_id"] for idx in group_files],
                "file_names": [file_analyses[idx]["file_name"] for idx in group_files],
                "common_keywords": list(group_keywords)[:10],  # 保留前10个关键词
                "avg_similarity": avg_similarity,
                "is_single": len(group_files) == 1
            })

        return groups

    def _calculate_group_similarity(self, file_indices: List[int],
                                    similarity_matrix: List[List[float]]) -> float:
        """计算组内文件的平均相似度"""
        if len(file_indices) <= 1:
            return 1.0

        total = 0.0
        count = 0
        for i in range(len(file_indices)):
            for j in range(i + 1, len(file_indices)):
                total += similarity_matrix[file_indices[i]][file_indices[j]]
                count += 1

        return round(total / count, 3) if count > 0 else 0.0

    def generate_group_name(self, group: Dict[str, Any], file_analyses: List[Dict[str, Any]]) -> str:
        """生成分组名称"""
        if group["is_single"]:
            # 单文件组，使用文件名
            idx = group["file_indices"][0]
            return file_analyses[idx].get("title", "未命名文档")

        # 多文件组，使用共同关键词
        keywords = group.get("common_keywords", [])
        if keywords:
            return f"相关文档：{'、'.join(keywords[:3])}"

        return f"文档组 {group['group_index'] + 1}"
