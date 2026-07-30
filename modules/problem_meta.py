"""
题目分类与标签数据
- 18 大类（一级分类）
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

# 18 大类（一级分类）—— 题目按此分类
PROBLEM_CATEGORIES = [
    '基础算法', '搜索', '动态规划', '字符串',
    '数学', '数据结构', '图论', '树论',
    '计算几何', '博弈论', '概率与期望', '多项式',
    '位运算', '构造', '杂项技巧', '语言基础',
    '随机化', '高级专题',
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