"""
业务逻辑服务层
"""
from typing import List, Dict, Optional, Tuple

# 预定义的分类关键词（根据实际业务场景）
CATEGORY_KEYWORDS = {
    "功能使用问题": ["怎么用", "如何", "使用", "操作", "不会", "找不到", "在哪", "怎么", "无法使用", "不能用", "用不了", "打不开", "进不去"],
    "网络连接异常": ["网络", "连接", "断开", "超时", "加载", "刷新", "联网", "网速", "掉线", "连不上", "服务器", "请求失败"],
    "校对功能缺陷": ["校对", "纠错", "错别字", "语法", "标点", "修改", "改错", "检测", "识别", "漏检", "误报", "不准", "准确率"],
    "会员权限问题": ["会员", "VIP", "权限", "付费", "订阅", "开通", "续费", "到期", "免费", "次数", "限制", "额度", "充值"],
    "功能建议与反馈": ["建议", "希望", "能否", "可以增加", "想要", "需要", "功能", "新增", "添加", "支持", "优化", "改进", "体验"],
    "其他": []
}


class FeedbackClassifier:
    """反馈分类器"""
    
    def __init__(self, category_keywords: Dict[str, List[str]] = None):
        self.category_keywords = category_keywords or CATEGORY_KEYWORDS
    
    def classify(self, content: str) -> str:
        """
        根据内容自动分类反馈
        使用关键词匹配进行分类
        """
        if not content:
            return "其他"
        
        content_lower = content.lower()
        
        # 统计每个分类的匹配分数
        scores = {}
        for category, keywords in self.category_keywords.items():
            if category == "其他":
                continue
            score = sum(1 for kw in keywords if kw.lower() in content_lower)
            if score > 0:
                scores[category] = score
        
        # 返回得分最高的分类
        if scores:
            return max(scores, key=scores.get)
        
        return "其他"
    
    def get_categories(self) -> List[str]:
        """获取所有分类"""
        return list(self.category_keywords.keys())


class UserTypeParser:
    """用户类型解析器"""
    
    MEMBER_KEYWORDS = ["会员", "vip", "premium", "付费", "pro"]
    NORMAL_KEYWORDS = ["普通", "免费", "free", "normal", "basic"]
    
    @classmethod
    def parse(cls, user_type_str: str) -> str:
        """解析用户类型"""
        if not user_type_str:
            return "未知"
        
        user_type_lower = str(user_type_str).lower()
        if any(kw in user_type_lower for kw in cls.MEMBER_KEYWORDS):
            return "会员"
        elif any(kw in user_type_lower for kw in cls.NORMAL_KEYWORDS):
            return "普通用户"
        else:
            return str(user_type_str)


class CSVColumnDetector:
    """CSV列检测器"""
    
    # 内容列关键词
    CONTENT_KEYWORDS = ["内容", "content", "feedback", "message", "描述", "意见", "评论", "反馈内容"]
    # 需要排除的列名关键词
    EXCLUDE_KEYWORDS = ["id", "编号", "序号", "时间", "日期", "date"]
    # 用户类型关键词
    USER_TYPE_KEYWORDS = ["用户类型", "会员", "user_type", "身份", "等级", "会员类型", "用户身份"]
    # 用户附件关键词（注意：要匹配"列表"而非"数量"）
    # 使用更短的关键词便于部分匹配
    ATTACHMENT_KEYWORDS = ["附件列表", "用户附件", "attachment", "附件链接", "文件链接"]
    # 需要排除的附件列关键词（避免匹配到"附件数量"）
    ATTACHMENT_EXCLUDE_KEYWORDS = ["数量", "count", "num", "个数", "数目"]
    
    @classmethod
    def detect(cls, headers: List[str]) -> Dict[str, Optional[int]]:
        """
        自动检测CSV列索引
        返回内容列、用户类型列和附件列的索引
        """
        content_col = None
        user_type_col = None
        attachment_col = None
        
        for i, header in enumerate(headers):
            header_lower = header.lower().strip()
            
            # 检查是否应该排除该列
            should_exclude = any(ex in header_lower for ex in cls.EXCLUDE_KEYWORDS)
            
            # 检测内容列（排除包含ID等关键词的列）
            if content_col is None and not should_exclude:
                for kw in cls.CONTENT_KEYWORDS:
                    if kw in header_lower:
                        content_col = i
                        break
            
            # 检测用户类型列
            if user_type_col is None:
                for kw in cls.USER_TYPE_KEYWORDS:
                    if kw in header_lower:
                        user_type_col = i
                        break
            
            # 检测附件列（排除"数量"等列）
            if attachment_col is None:
                # 去除所有空格和特殊字符后的列名
                header_clean = header.strip().replace(' ', '').replace('\u3000', '').replace('\t', '')
                # 先检查是否应该排除
                should_exclude_attachment = any(ex in header_clean for ex in cls.ATTACHMENT_EXCLUDE_KEYWORDS)
                if not should_exclude_attachment:
                    for kw in cls.ATTACHMENT_KEYWORDS:
                        # 检查清理后的列名是否包含关键词
                        if kw in header_clean or kw in header:
                            attachment_col = i
                            break
        
        return {"content": content_col, "user_type": user_type_col, "attachment": attachment_col}


class KanbanCategoryGenerator:
    """看板分类名称生成器"""
    
    # 关键词到分类名的映射
    KEYWORD_TO_CATEGORY = {
        # 问题类
        ("bug", "崩溃", "闪退", "卡死", "报错", "异常"): "技术问题",
        ("慢", "卡顿", "加载", "性能"): "性能问题",
        ("界面", "UI", "样式", "显示", "布局"): "界面问题",
        
        # 功能类
        ("功能", "新增", "添加", "支持", "希望", "建议"): "功能需求",
        ("优化", "改进", "提升", "增强"): "优化建议",
        
        # 体验类
        ("体验", "使用", "操作", "不方便", "麻烦"): "体验问题",
        ("满意", "好用", "不错", "赞"): "正面反馈",
        
        # 业务类
        ("会员", "VIP", "付费", "订阅", "价格"): "会员相关",
        ("校对", "纠错", "错别字", "语法"): "校对功能",
    }
    
    @classmethod
    def generate_category_name(cls, contents: List[str]) -> str:
        """
        根据一组反馈内容自动生成分类名称
        分析内容中的关键词，返回最匹配的分类名
        """
        if not contents:
            return "新分类"
        
        # 合并所有内容
        all_text = " ".join(contents).lower()
        
        # 统计各分类的匹配分数
        scores = {}
        for keywords, category_name in cls.KEYWORD_TO_CATEGORY.items():
            score = sum(1 for kw in keywords if kw.lower() in all_text)
            if score > 0:
                scores[category_name] = scores.get(category_name, 0) + score
        
        # 返回得分最高的分类名
        if scores:
            return max(scores, key=scores.get)
        
        # 如果没有匹配，尝试提取高频词作为分类名
        return cls._extract_key_phrase(contents)
    
    @classmethod
    def _extract_key_phrase(cls, contents: List[str]) -> str:
        """提取关键短语作为分类名"""
        # 简单的词频统计
        words = {}
        stop_words = {"的", "是", "了", "在", "我", "有", "和", "就", "不", "人", "都", 
                      "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", 
                      "会", "着", "没有", "看", "好", "自己", "这", "那", "怎么", "什么"}
        
        for content in contents:
            for word in content:
                if len(word) >= 2 and word not in stop_words:
                    # 简单的双字词提取
                    pass
        
        # 如果无法提取，返回默认名称
        return "重点反馈"
    
    @classmethod
    def suggest_category_for_feedback(cls, content: str) -> Optional[str]:
        """为单条反馈建议分类"""
        return cls.generate_category_name([content])


# 单例实例
feedback_classifier = FeedbackClassifier()
user_type_parser = UserTypeParser()
csv_column_detector = CSVColumnDetector()
kanban_category_generator = KanbanCategoryGenerator()

