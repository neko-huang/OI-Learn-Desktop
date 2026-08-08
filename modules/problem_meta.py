"""
题目分类与标签数据
- 14 大类（一级分类）
- 子知识点标签（来自大纲）
"""

# 题目难度（8 级）
DIFFICULTIES = [
    '入门',
    '普及−',
    '普及',
    '普及+/提高−',
    '提高',
    '提高+/省选−',
    '省选/NOI−',
    'NOI/NOI+/CTS',
]

# 14 大类（一级分类）—— 题目按此分类
PROBLEM_CATEGORIES = [
    '语言入门', '基础算法', '数据结构', '树',
    '图论', '搜索', '动态规划', '字符串',
    '数学', '计算几何', '杂项', '竞赛相关',
    '工具与技巧', '高级专题',
]

# OJ 平台
PLATFORMS = ['Codeforces', '洛谷', 'AtCoder', 'USACO', 'POJ', 'HDU', 'VJudge', '其他']

# 状态
STATUSES = {'todo': '待做', 'done': '已做', 'review': '复习'}
STATUS_SYMBOLS = {'todo': '○', 'done': '●', 'review': '⟳'}


def get_all_subtopic_tags():
    """从大纲种子数据提取所有子知识点名称作为标签"""
    from db.seed import ALGORITHM_CATEGORIES
    tags = []
    for cat in ALGORITHM_CATEGORIES:
        for topic in cat['topics']:
            for sub in topic['subtopics']:
                tags.append({
                    'id': sub[0],
                    'name': sub[1],
                    'category': cat['name'],
                })
    return tags