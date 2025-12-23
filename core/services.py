"""
业务逻辑服务层
"""
from typing import List, Dict, Optional

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
    
    @classmethod
    def detect(cls, headers: List[str]) -> Dict[str, Optional[int]]:
        """
        自动检测CSV列索引
        返回内容列和用户类型列的索引
        """
        content_col = None
        user_type_col = None
        
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
        
        return {"content": content_col, "user_type": user_type_col}


# 单例实例
feedback_classifier = FeedbackClassifier()
user_type_parser = UserTypeParser()
csv_column_detector = CSVColumnDetector()

