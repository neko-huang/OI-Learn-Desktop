"""
种子数据 — 从旧 info-learn 项目导出的算法大纲、百科、模板
首次运行时自动填充数据库
"""

from db.database import get_connection

# ============================================================
# 14 大类算法大纲（类别 → 主题 → 子知识点）
# 数据结构：
#   每个类别有 id, name, desc
#   每个类别下有多个 topic（主题）
#   每个 topic 下有多个 subtopic（子知识点）
# ============================================================

ALGORITHM_CATEGORIES = [
    {
        'id': 'lang', 'name': '语言入门',
        'desc': 'C++基础语法与程序设计入门',
        'topics': [
            {
                'id': 'lang-base', 'name': '程序基础',
                'desc': '顺序/分支/循环结构与基本语法',
                'subtopics': [
                    ('lang-seq', '顺序结构', '程序从上到下逐行执行', 1, 'entry'),
                    ('lang-if', '分支结构', 'if/else/switch条件判断', 1, 'entry'),
                    ('lang-loop', '循环结构', 'for/while循环与嵌套', 2, 'entry'),
                    ('lang-array', '数组', '一维/二维数组的定义与使用', 3, 'entry'),
                    ('lang-string-basic', '字符串入门', 'C风格字符数组与string类基础', 2, 'entry'),
                    ('lang-struct', '结构体', 'struct定义与使用', 3, 'entry'),
                    ('lang-func', '函数与递归', '函数定义、参数传递、递归调用', 2, 'entry'),
                ]
            },
            {
                'id': 'lang-stl', 'name': 'STL入门',
                'desc': '标准模板库常用容器和算法',
                'subtopics': [
                    ('stl-vector', 'vector向量', '动态数组', 4, 'entry'),
                    ('stl-pair', 'pair对组', '键值对基础', 3, 'entry'),
                    ('stl-string', 'string类', '字符串操作封装', 3, 'entry'),
                    ('stl-sort', 'STL排序', 'sort函数与自定义比较', 3, 'entry'),
                    ('stl-map', 'map映射', '键值对存储', 5, 'improve'),
                    ('stl-set', 'set集合', '有序集合与去重', 5, 'improve'),
                    ('stl-stack', 'stack栈', 'STL栈容器适配器', 3, 'entry'),
                    ('stl-queue', 'queue队列', 'STL队列容器适配器', 3, 'entry'),
                    ('stl-deque', 'deque双端队列', '双端操作', 5, 'improve'),
                    ('stl-priority-queue', 'priority_queue优先队列', '堆的STL实现', 4, 'entry'),
                    ('stl-algorithm', 'STL算法', '常用算法库函数', 4, 'entry'),
                ]
            },
        ]
    },
    {
        'id': 'basics', 'name': '基础算法',
        'desc': '模拟、贪心、递推、二分、枚举、分治、排序、前缀和',
        'topics': [
            {
                'id': 'basic-core', 'name': '核心算法',
                'desc': '入门级基础算法',
                'subtopics': [
                    ('basic-sim', '模拟', '按题意逐步实现', 1, 'entry'),
                    ('basic-greedy', '贪心', '局部最优→全局最优', 3, 'entry'),
                    ('basic-rec', '递推', '逐步推导，从小到大', 3, 'entry'),
                    ('basic-binary', '二分', '有序序列O(logN)定位', 4, 'entry'),
                    ('basic-enum', '枚举', '穷举验证', 2, 'entry'),
                    ('basic-divide', '分治', '分解→解决→合并', 6, 'improve'),
                    ('basic-binary-lifting', '倍增法', '二进制拆分加速递推', 5, 'improve'),
                    ('basic-amortized', '均摊分析', '势能分析时间复杂度', 7, 'improve'),
                ]
            },
            {
                'id': 'basic-sort', 'name': '排序算法',
                'desc': '各种排序算法原理与实现',
                'subtopics': [
                    ('basic-sort-intro', '排序基础', '排序算法分类与稳定性', 3, 'entry'),
                    ('basic-sort-bubble', '冒泡排序', '相邻交换O(N²)', 2, 'entry'),
                    ('basic-sort-select', '选择排序', '每轮选最小O(N²)', 2, 'entry'),
                    ('basic-sort-insert', '插入排序', '已排序区间插入O(N²)', 2, 'entry'),
                    ('basic-sort-count', '计数排序', '值域O(N+K)', 4, 'entry'),
                    ('basic-sort-radix', '基数排序', '按位排序O(NK)', 5, 'improve'),
                    ('basic-sort-bucket', '桶排序', '分桶排序O(N+K)', 5, 'improve'),
                    ('basic-sort-merge', '归并排序', '分治合并O(NlogN)', 4, 'entry'),
                    ('basic-sort-quick', '快速排序', '分治划分O(NlogN)', 4, 'entry'),
                    ('basic-sort-heap', '堆排序', '堆选择O(NlogN)', 5, 'improve'),
                    ('basic-sort-shell', '希尔排序', '间隔分组插入', 5, 'improve'),
                    ('basic-sort-tim', 'TimSort', '混合归并+插入', 6, 'improve'),
                    ('basic-sort-stl', 'STL排序', 'sort/stable_sort/nth_element', 3, 'entry'),
                ]
            },
            {
                'id': 'basic-prefix', 'name': '前缀和与差分',
                'desc': '区间统计与修改的预处理技术',
                'subtopics': [
                    ('basic-prefix-sum', '前缀和', 'O(1)区间和查询', 3, 'entry'),
                    ('basic-diff', '差分', 'O(1)区间修改', 4, 'entry'),
                    ('basic-prefix-2d', '二维前缀和', '矩阵区间和O(1)查询', 5, 'improve'),
                    ('basic-diff-2d', '二维差分', '矩阵区间修改', 6, 'improve'),
                ]
            },
        ]
    },
    {
        'id': 'ds', 'name': '数据结构',
        'desc': '线性结构、树形结构、堆、哈希、可持久化结构',
        'topics': [
            {
                'id': 'ds-linear', 'name': '线性结构',
                'desc': '基础线性数据结构',
                'subtopics': [
                    ('lin-stack', '栈', 'LIFO后进先出', 4, 'entry'),
                    ('lin-queue', '队列', 'FIFO先进先出', 4, 'entry'),
                    ('lin-linked-list', '链表', '动态增删O(1)', 4, 'entry'),
                    ('lin-monotonic-stack', '单调栈', '下一个更大/更小元素', 3, 'entry'),
                    ('lin-monotonic-queue', '单调队列', '滑动窗口极值', 5, 'improve'),
                ]
            },
            {
                'id': 'ds-prefix', 'name': '前缀与区间查询',
                'desc': '区间查询与维护',
                'subtopics': [
                    ('lin-prefix', '前缀和', 'O(1)区间和', 3, 'entry'),
                    ('lin-diff', '差分', 'O(1)区间修改', 4, 'entry'),
                    ('lin-sparse-table', 'ST表(RMQ)', 'O(NlogN)预处理O(1)查询', 6, 'improve'),
                    ('lin-block', '分块', '√N优雅暴力', 7, 'improve'),
                    ('lin-cat-tree', '猫树', '静态区间查询O(1)', 8, 'noi'),
                    ('lin-sqrt-tree', 'Sqrt Tree', 'O(loglogN)区间查询', 9, 'noi'),
                ]
            },
            {
                'id': 'ds-tree-core', 'name': '核心树结构',
                'desc': '竞赛最常用的树形数据结构',
                'subtopics': [
                    ('tree-dsu', '并查集(DSU)', '近乎O(1)合并查询', 6, 'improve'),
                    ('tree-dsu-complex', '并查集复杂度', '路径压缩+按秩合并证明', 8, 'noi'),
                    ('tree-bit', '树状数组(BIT)', 'O(logN)单点改/区间查', 6, 'improve'),
                    ('tree-seg', '线段树', '区间操作瑞士军刀', 6, 'improve'),
                    ('tree-seg-beats', '吉司机线段树', 'Segment Tree Beats', 10, 'noi'),
                    ('tree-li-chao', '李超线段树', '维护直线/线段最值', 8, 'noi'),
                    ('tree-merge', '线段树合并', '启发式合并O(NlogN)', 8, 'noi'),
                    ('tree-trie', 'Trie字典树', '前缀检索', 6, 'improve'),
                    ('tree-persistent-trie', '可持久化Trie', '历史版本Trie', 8, 'noi'),
                ]
            },
            {
                'id': 'ds-heap', 'name': '堆与优先队列',
                'desc': '各种堆的实现与应用',
                'subtopics': [
                    ('tree-heap', '二叉堆', '数组实现优先队列', 5, 'improve'),
                    ('tree-leftist', '左偏树', '可并堆', 8, 'noi'),
                    ('tree-pairing-heap', '配对堆', '均摊O(1)插入', 8, 'noi'),
                    ('tree-huffman', '哈夫曼树', '最优前缀编码', 6, 'improve'),
                ]
            },
            {
                'id': 'ds-balanced', 'name': '平衡树',
                'desc': '自平衡二叉搜索树',
                'subtopics': [
                    ('tree-bst', '二叉搜索树', 'BST定义与操作', 5, 'improve'),
                    ('tree-treap', 'Treap', '树堆(随机优先级)', 8, 'noi'),
                    ('tree-splay', 'Splay', '伸展树', 8, 'noi'),
                    ('tree-avl', 'AVL树', '严格平衡二叉搜索树', 8, 'noi'),
                    ('tree-rbtree', '红黑树', '近似平衡树', 9, 'noi'),
                    ('tree-sbt', 'Size Balanced Tree', '按大小平衡', 8, 'noi'),
                    ('tree-skip', '跳表', '随机化多层链表', 8, 'noi'),
                    ('tree-cartesian', '笛卡尔树', 'Treap的变种', 8, 'noi'),
                ]
            },
            {
                'id': 'ds-persistent', 'name': '可持久化数据结构',
                'desc': '历史版本查询与维护',
                'subtopics': [
                    ('tree-persistent', '可持久化概述', '可持久化思想与实现', 7, 'improve'),
                    ('tree-pst', '可持久化线段树', '主席树，历史版本查询', 8, 'noi'),
                    ('tree-persistent-heap', '可持久化堆', '可持久化可并堆', 9, 'noi'),
                    ('tree-persistent-block', '可持久化块状数组', '分块的可持久化', 9, 'noi'),
                    ('tree-persistent-balanced', '可持久化平衡树', '可持久化Treap/Splay', 9, 'noi'),
                ]
            },
            {
                'id': 'ds-advanced', 'name': '高级数据结构',
                'desc': '竞赛进阶数据结构',
                'subtopics': [
                    ('tree-kdt', 'K-D Tree', '多维空间索引', 9, 'noi'),
                    ('tree-lct', '动态树(LCT)', 'Link-Cut Tree', 10, 'noi'),
                    ('tree-top-tree', 'Top Tree', '树链动态维护', 10, 'noi'),
                    ('tree-ett', 'Euler Tour Tree', '欧拉游览树', 10, 'noi'),
                    ('tree-global-bst', '全局平衡二叉树', '静态树上的LCT替代', 9, 'noi'),
                    ('tree-cdq', 'CDQ分治', '离线处理偏序问题', 8, 'noi'),
                    ('tree-divide-combine', '树分治合并', '按秩合并+线段树', 9, 'noi'),
                    ('tree-ktt', 'Kinetic Tournament Tree', '动态凸包维护', 10, 'noi'),
                ]
            },
            {
                'id': 'ds-hash', 'name': '哈希与映射',
                'desc': '哈希表及其应用',
                'subtopics': [
                    ('lin-hash', '哈希表', 'O(1)查找/插入', 5, 'improve'),
                    ('hash-string', '字符串哈希', 'Rolling Hash', 5, 'improve'),
                    ('hash-bloom', '布隆过滤器', '概率性存在判断', 7, 'improve'),
                ]
            },
            {
                'id': 'ds-other', 'name': '其他数据结构',
                'desc': '特殊用途的数据结构',
                'subtopics': [
                    ('tree-fenwick-in-block', '块状树状数组', '分块+BIT', 8, 'noi'),
                    ('tree-seg-in-bit', '树状数组套线段树', 'BIT套线段树', 9, 'noi'),
                    ('tree-seg-in-balanced', '平衡树套线段树', '动态区间第K大', 9, 'noi'),
                    ('tree-bit-in-block', '分块套树状数组', '二次离线分块', 9, 'noi'),
                    ('tree-balanced-in-seg', '线段树套平衡树', '树套树', 9, 'noi'),
                    ('tree-odt', '珂朵莉树(ODT)', '区间推平操作', 7, 'improve'),
                    ('tree-divide-combine-seg', '线段树分治', '时间维度的分治', 8, 'noi'),
                ]
            },
        ]
    },
    {
        'id': 'tree', 'name': '树',
        'desc': 'LCA、树链剖分、点分治、虚树、基环树、树哈希',
        'topics': [
            {
                'id': 'tree-basic', 'name': '树的基础',
                'desc': '树的定义与基本性质',
                'subtopics': [
                    ('tree-basic-concept', '树的基本概念', '树/森林/有根树/无根树', 3, 'entry'),
                    ('tree-center', '树的中心', '树的中心与重心', 5, 'improve'),
                    ('tree-diameter', '树的直径', '两次DFS或DP求直径', 6, 'improve'),
                    ('tree-centroid', '树的重心', '重心分解与性质', 6, 'improve'),
                ]
            },
            {
                'id': 'tree-adv', 'name': '树上高级算法',
                'desc': '树上的各种经典算法',
                'subtopics': [
                    ('tree-lca', '最近公共祖先(LCA)', '倍增/欧拉序/Tarjan', 6, 'improve'),
                    ('tree-hld', '树链剖分(HLD)', '重链剖分/长链剖分', 8, 'noi'),
                    ('tree-cent', '点分治', '树重心+分治', 8, 'noi'),
                    ('tree-virt', '虚树', '稀疏关键点压缩', 8, 'noi'),
                    ('tree-dsu-on', '树上启发式合并', 'DSU on Tree', 7, 'improve'),
                    ('tree-base', '基环树', '树上加一条边', 8, 'noi'),
                    ('tree-divide-dynamic', '动态点分治', '点分树', 9, 'noi'),
                    ('tree-hash', '树哈希', '树同构判定', 8, 'noi'),
                    ('tree-ahu', '树同构(AHU)', 'AHU算法判定有根树同构', 9, 'noi'),
                    ('tree-random-walk', '树上随机游走', '树上期望问题', 8, 'noi'),
                ]
            },
        ]
    },
    {
        'id': 'graph', 'name': '图论',
        'desc': 'BFS/DFS、最短路、MST、拓扑排序、连通性、网络流、匹配',
        'topics': [
            {
                'id': 'graph-basic', 'name': '基础图论',
                'desc': '图的遍历、最短路、MST、欧拉路',
                'subtopics': [
                    ('g-bfs', 'BFS广度优先搜索', '队列层序遍历', 7, 'improve'),
                    ('g-dfs', 'DFS深度优先搜索', '递归+回溯', 5, 'entry'),
                    ('g-topo', '拓扑排序', 'DAG顶点线性序', 6, 'improve'),
                    ('g-dij', 'Dijkstra最短路', '非负权单源O((V+E)logV)', 6, 'improve'),
                    ('g-floyd', 'Floyd-Warshall', '全源最短路O(V^3)', 6, 'improve'),
                    ('g-bellman', 'Bellman-Ford/SPFA', '含负权O(VE)', 6, 'improve'),
                    ('g-kruskal', 'Kruskal MST', '并查集+贪心选边', 6, 'improve'),
                    ('g-prim', 'Prim MST', '点扩散，适合稠密图', 6, 'improve'),
                    ('g-euler', '欧拉回路', '一笔画问题', 6, 'improve'),
                    ('g-hamilton', '哈密顿路径', 'NP完全问题', 9, 'noi'),
                ]
            },
            {
                'id': 'graph-adv', 'name': '进阶图论',
                'desc': '连通性、网络流、匹配、特殊图',
                'subtopics': [
                    ('g-scc', '强连通分量(Tarjan)', 'SCC缩点→DAG', 7, 'improve'),
                    ('g-bcc', '点双连通分量', '无向图点双连通', 7, 'improve'),
                    ('g-bridge', '桥(割边)', '割边判定', 7, 'improve'),
                    ('g-cut', '割点', '关节点判定', 7, 'improve'),
                    ('g-block-forest', '圆方树', 'Block Forest', 8, 'noi'),
                    ('g-sat', '2-SAT', '布尔可满足问题', 8, 'noi'),
                    ('g-flow', '网络流(Dinic)', '最大流O(V^2E)', 8, 'noi'),
                    ('g-mcmf', '最小费用最大流', 'SPFA/Dijkstra增广', 8, 'noi'),
                    ('g-bip', '二分图匹配', '匈牙利/KM算法', 8, 'noi'),
                    ('g-general-match', '一般图匹配', '带花树算法', 10, 'noi'),
                    ('g-stable-match', '稳定婚姻匹配', 'Gale-Shapley算法', 8, 'noi'),
                    ('g-diff', '差分约束', '不等式组→图论', 4, 'entry'),
                    ('g-min-cut', '最小割', '最大流最小割定理', 8, 'noi'),
                    ('g-bound-flow', '上下界网络流', '带容量上下界的网络流', 9, 'noi'),
                    ('g-chord', '弦图', '弦图与完美消除序列', 9, 'noi'),
                    ('g-planar', '平面图', '平面图性质与判定', 9, 'noi'),
                ]
            },
            {
                'id': 'graph-mst-adv', 'name': '最小生成树进阶',
                'desc': 'MST的扩展问题',
                'subtopics': [
                    ('g-mst-2nd', '次小生成树', '严格/非严格次小MST', 8, 'noi'),
                    ('g-dmst', '最小树形图', '有向图最小生成树', 9, 'noi'),
                    ('g-mdst', '最小直径生成树', '最小化树的直径', 9, 'noi'),
                    ('g-steiner-tree', '斯坦纳树', '最小连通子图包含指定点集', 9, 'noi'),
                ]
            },
            {
                'id': 'graph-tree', 'name': '图论中的树',
                'desc': '图论中的树相关算法',
                'subtopics': [
                    ('g-matrix-tree', '矩阵树定理', 'Kirchhoff定理', 9, 'noi'),
                    ('g-prufer', 'Prufer序列', '生成树计数', 9, 'noi'),
                    ('g-tree-ahu', '树同构AHU', '有根树同构判定', 9, 'noi'),
                ]
            },
            {
                'id': 'graph-path', 'name': '路径问题',
                'desc': '特殊路径与图上的路径问题',
                'subtopics': [
                    ('g-kth-path', 'K短路', '次短路及第K短路', 8, 'noi'),
                    ('g-mod-shortest-path', '同余最短路', '建图解决同余问题', 8, 'noi'),
                    ('g-min-cycle', '最小环', '无向图最小环', 8, 'noi'),
                    ('g-dom-tree', '支配树', '必经点树', 9, 'noi'),
                ]
            },
            {
                'id': 'graph-special', 'name': '特殊图论',
                'desc': '特殊图结构与算法',
                'subtopics': [
                    ('g-max-clique', '最大团问题', 'Bron-Kerbosch算法', 10, 'noi'),
                    ('g-color', '图染色', '顶点染色/边染色', 8, 'noi'),
                    ('g-graph-random-walk', '图随机游走', '图上期望问题', 9, 'noi'),
                    ('g-rings-count', '环计数', '简单环计数', 10, 'noi'),
                    ('g-lgv', 'LGV引理', '路径不交方案数', 10, 'noi'),
                    ('g-stoer-wagner', 'Stoer-Wagner算法', '全局最小割', 9, 'noi'),
                ]
            },
        ]
    },
    {
        'id': 'search', 'name': '搜索',
        'desc': 'BFS/DFS、剪枝、启发式、模拟退火、DLX',
        'topics': [
            {
                'id': 'search-all', 'name': '搜索策略',
                'desc': '各种搜索算法和优化',
                'subtopics': [
                    ('s-bfs', 'BFS', '广度优先搜索', 5, 'entry'),
                    ('s-dfs', 'DFS', '深度优先搜索', 5, 'entry'),
                    ('s-backtrack', '回溯', '递归+状态恢复', 5, 'entry'),
                    ('s-prune', '剪枝', '减少搜索空间', 6, 'improve'),
                    ('s-memo', '记忆化搜索', '缓存递归结果', 6, 'improve'),
                    ('s-heur', '启发式搜索', '估价函数引导', 7, 'improve'),
                    ('s-iter', '迭代加深搜索', '深度逐层增加', 7, 'improve'),
                    ('s-ida', 'IDA*', '迭代加深+启发式', 7, 'improve'),
                    ('s-dlx', 'Dancing Links', '精确覆盖问题/数独', 8, 'noi'),
                    ('s-bi', '双向BFS', '起点+终点同时BFS', 7, 'improve'),
                    ('s-astar', 'A*算法', 'f=g+h估价搜索', 7, 'improve'),
                    ('s-mim', '折半搜索', 'Meet in the Middle', 7, 'improve'),
                    ('s-sa', '模拟退火', '概率接受较差解', 8, 'noi'),
                    ('s-alpha-beta', 'Alpha-Beta剪枝', '博弈树搜索剪枝', 8, 'noi'),
                    ('s-hill', '爬山算法', '局部最优搜索', 7, 'improve'),
                ]
            },
        ]
    },
    {
        'id': 'dp', 'name': '动态规划',
        'desc': '背包/区间/树形/状压/数位/计数/DP优化',
        'topics': [
            {
                'id': 'dp-models', 'name': 'DP模型',
                'desc': '经典DP模型',
                'subtopics': [
                    ('dp-knap', '背包DP', '0-1/完全/多重/分组背包', 5, 'entry'),
                    ('dp-interval', '区间DP', '小区间→大区间', 5, 'entry'),
                    ('dp-tree2', '树形DP', '树上递推', 6, 'improve'),
                    ('dp-linear', '线性DP', '序列递推(LIS/LCS等)', 6, 'improve'),
                    ('dp-bitmask', '状压DP', '二进制表示状态', 6, 'improve'),
                    ('dp-digit', '数位DP', '按位递推统计', 4, 'entry'),
                    ('dp-dag', 'DAG上的DP', '有向无环图上递推', 6, 'improve'),
                    ('dp-probability', '概率DP', '状态转移概率', 6, 'improve'),
                    ('dp-dynamic', '动态DP', '带修改的DP', 10, 'noi'),
                    ('dp-dp-of-dp', 'DP自动机(DP of DP)', 'DP套DP', 10, 'noi'),
                ]
            },
            {
                'id': 'dp-count', 'name': '计数DP',
                'desc': '组合计数类动态规划',
                'subtopics': [
                    ('dp-count-basic', '计数DP基础', '排列组合计数递推', 6, 'improve'),
                    ('dp-number', '数论计数DP', '整除/质因数相关计数', 8, 'noi'),
                    ('dp-misc-count', '杂项计数DP', '各种计数DP技巧', 8, 'noi'),
                ]
            },
            {
                'id': 'dp-opt', 'name': 'DP优化',
                'desc': '加速DP转移的高级技巧',
                'subtopics': [
                    ('dp-pq', '优先队列优化DP', '维护转移最优值', 8, 'improve'),
                    ('dp-matrix', '矩阵加速DP', '常系数线性递推O(K^3 logN)', 4, 'entry'),
                    ('dp-slope', '斜率优化', '凸包维护决策', 8, 'improve'),
                    ('dp-wqs', 'WQS二分', '二分惩罚项凸优化', 9, 'noi'),
                    ('dp-quad', '四边形不等式', '决策单调性加速', 8, 'improve'),
                    ('dp-monotonic-queue', '单调队列优化DP', '滑动窗口最优转移', 7, 'improve'),
                    ('dp-slope-trick', 'Slope Trick', '凸函数斜率DP优化', 9, 'noi'),
                ]
            },
            {
                'id': 'dp-special', 'name': '特殊DP',
                'desc': '特殊类型DP',
                'subtopics': [
                    ('dp-plug', '插头DP', '轮廓线状态压缩DP', 10, 'noi'),
                    ('dp-contour', '轮廓线DP', '逐格转移', 8, 'noi'),
                ]
            },
        ]
    },
    {
        'id': 'string', 'name': '字符串',
        'desc': 'KMP/Trie/AC自动机/后缀数组/SAM/Manacher',
        'topics': [
            {
                'id': 'str-all', 'name': '字符串算法',
                'desc': '从匹配到后缀数据结构',
                'subtopics': [
                    ('str-hash', '字符串哈希', 'Rolling Hash/O(1)子串比较', 5, 'improve'),
                    ('str-kmp', 'KMP算法', '单模式串O(N+M)', 6, 'improve'),
                    ('str-z', 'Z函数(扩展KMP)', '字符串与自身匹配', 7, 'improve'),
                    ('str-trie2', 'Trie字典树', '前缀检索+01-Trie', 6, 'improve'),
                    ('str-ac', 'AC自动机', '多模式串=Trie+KMP', 8, 'noi'),
                    ('str-sa', '后缀数组(SA)', 'SA-IS/Doubling O(N)', 8, 'noi'),
                    ('str-sam', '后缀自动机(SAM)', '处理所有子串', 10, 'noi'),
                    ('str-general-sam', '广义SAM', '多串的后缀自动机', 10, 'noi'),
                    ('str-manacher', 'Manacher算法', 'O(N)最长回文', 7, 'improve'),
                    ('str-pam', '回文自动机(PAM)', '回文串结构', 9, 'noi'),
                    ('str-bm', 'BM算法', 'Boyer-Moore字符串匹配', 8, 'noi'),
                    ('str-lyndon', 'Lyndon分解', '字典序最小循环移位', 8, 'noi'),
                    ('str-minimal', '最小表示法', '字符串的最小循环表示', 6, 'improve'),
                    ('str-main-lorentz', 'Main-Lorentz算法', '求所有重复子串', 9, 'noi'),
                    ('str-seq-automaton', '序列自动机', '子序列快速判定', 8, 'noi'),
                    ('str-suffix-bst', '后缀平衡树', '动态维护后缀数组', 10, 'noi'),
                    ('str-suffix-tree', '后缀树', '后缀树结构与应用', 10, 'noi'),
                ]
            },
        ]
    },
    {
        'id': 'math', 'name': '数学',
        'desc': '数论/组合/线性代数/概率/博弈/多项式/数值方法',
        'topics': [
            {
                'id': 'math-number', 'name': '数论',
                'desc': '素数、同余、逆元、筛法、数论函数',
                'subtopics': [
                    ('m-prime', '素数判定与筛法', '埃氏筛/欧拉筛/米勒-拉宾', 4, 'entry'),
                    ('m-gcd', 'GCD与LCM', '欧几里得算法与扩展欧几里得', 3, 'entry'),
                    ('m-mod', '模运算与逆元', '费马小定理/扩展欧几里得求逆', 7, 'improve'),
                    ('m-crt', '中国剩余定理(CRT)', '同余方程组', 7, 'improve'),
                    ('m-mobius', '莫比乌斯反演', '数论函数卷积', 9, 'noi'),
                    ('m-bsgs', 'BSGS算法', '离散对数', 8, 'noi'),
                    ('m-euler', '欧拉函数', 'phi(n)定义与性质', 5, 'improve'),
                    ('m-linear-sieve', '线性筛', '筛积性函数', 4, 'entry'),
                    ('m-du', '杜教筛', '数论函数前缀和', 9, 'noi'),
                    ('m-min-25', 'Min_25筛', '亚线性素数求和', 10, 'noi'),
                    ('m-powerful-number', 'Powerful Number筛', '亚线性积性函数求和', 10, 'noi'),
                    ('m-fermat', '费马小定理', '模素数幂运算', 5, 'improve'),
                    ('m-pollard-rho', 'Pollard-Rho', '大数质因数分解', 9, 'noi'),
                    ('m-quad-residue', '二次剩余', '模平方根', 9, 'noi'),
                    ('m-pell', '佩尔方程', '二次丢番图方程', 9, 'noi'),
                    ('m-sqrt-decomp', '数论分块', '整除分块加速求和', 6, 'improve'),
                    ('m-prime-dist', '素数计数', 'Meissel-Lehmer算法', 10, 'noi'),
                    ('m-lucas', 'Lucas定理', '大组合数取模', 8, 'noi'),
                    ('m-stern-brocot', 'Stern-Brocot树', '有理数近似', 9, 'noi'),
                ]
            },
            {
                'id': 'math-combi', 'name': '组合数学',
                'desc': '排列组合、容斥、卡特兰数、生成函数',
                'subtopics': [
                    ('m-combi-basic', '排列组合基础', '阶乘/组合数/二项式定理', 4, 'entry'),
                    ('m-catalan', '卡特兰数', '出栈序列/括号匹配', 7, 'improve'),
                    ('m-incl-excl', '容斥原理', '集合计数', 6, 'improve'),
                    ('m-stirling', '斯特林数', '第一/二类斯特林数', 9, 'noi'),
                    ('m-partition', '整数拆分', '分拆数', 8, 'noi'),
                    ('m-fibonacci', '斐波那契数列', '斐波那契数列性质', 4, 'entry'),
                    ('m-bell', '贝尔数', '集合划分方案数', 8, 'noi'),
                    ('m-eulerian', '欧拉数', '排列的上升数', 9, 'noi'),
                    ('m-derangement', '错排', '错位排列计数', 6, 'improve'),
                    ('m-bernoulli', '伯努利数', '幂和公式', 9, 'noi'),
                    ('m-drawer', '抽屉原理', '鸽巢原理', 3, 'entry'),
                    ('m-burnside', 'Burnside引理', '置换群计数', 9, 'noi'),
                    ('m-polya', 'Polya计数定理', '染色方案计数', 9, 'noi'),
                    ('m-cantor', '康托展开', '排列与序号的映射', 6, 'improve'),
                ]
            },
            {
                'id': 'math-linear-algebra', 'name': '线性代数',
                'desc': '矩阵、行列式、线性方程组、线性空间',
                'subtopics': [
                    ('m-matrix', '矩阵', '矩阵运算与性质', 5, 'improve'),
                    ('m-det', '行列式', '行列式定义与计算', 7, 'improve'),
                    ('m-gauss', '高斯消元', '线性方程组求解', 7, 'improve'),
                    ('m-linear-basis', '线性基', '异或空间的基', 6, 'improve'),
                    ('m-vector-space', '向量空间', '线性空间与子空间', 8, 'noi'),
                    ('m-linear-mapping', '线性映射', '线性变换与矩阵表示', 8, 'noi'),
                    ('m-char-poly', '特征多项式', '特征值与特征向量', 9, 'noi'),
                    ('m-diagonalization', '对角化', '矩阵可对角化条件', 9, 'noi'),
                    ('m-jordan', 'Jordan标准型', '若尔当标准形', 10, 'noi'),
                ]
            },
            {
                'id': 'math-poly', 'name': '多项式与生成函数',
                'desc': 'FFT/NTT/FWT/生成函数/多项式运算',
                'subtopics': [
                    ('poly-fft', 'FFT', '快速傅里叶变换', 10, 'noi'),
                    ('poly-ntt', 'NTT', '数论变换', 10, 'noi'),
                    ('poly-fwt', 'FWT', '快速沃尔什变换', 10, 'noi'),
                    ('poly-ogf', '普通生成函数(OGF)', '序列的普通生成函数', 9, 'noi'),
                    ('poly-egf', '指数型生成函数(EGF)', '序列的指数型生成函数', 9, 'noi'),
                    ('poly-elementary', '多项式基础运算', '加减乘除/取模/求逆', 9, 'noi'),
                    ('poly-sqrt', '多项式开方', '多项式平方根', 10, 'noi'),
                    ('poly-ln-exp', '多项式ln/exp', '对数/指数运算', 10, 'noi'),
                    ('poly-comp-rev', '多项式复合逆', '反函数与拉格朗日反演', 10, 'noi'),
                    ('poly-czt', 'Chirp Z变换', '任意点FFT', 10, 'noi'),
                    ('poly-multipoint', '多点求值与插值', '多项式多点求值', 10, 'noi'),
                    ('poly-berlekamp-massey', 'Berlekamp-Massey', '线性递推最小阶', 10, 'noi'),
                    ('poly-linear-rec', '常系数线性递推', '线性递推求解', 9, 'noi'),
                ]
            },
            {
                'id': 'math-game', 'name': '博弈论',
                'desc': '公平组合游戏、SG函数、博弈DP',
                'subtopics': [
                    ('game-nim', 'NIM游戏', '异或和判定', 9, 'noi'),
                    ('game-sg', 'SG函数', '有向图游戏', 9, 'noi'),
                    ('game-wythoff', '威佐夫博弈', '两堆石子', 7, 'improve'),
                    ('game-composite', '组合游戏', '博弈DP', 4, 'entry'),
                    ('game-impartial', '不平等博弈', 'Surreal Number', 10, 'noi'),
                    ('game-partizan', '部分博弈', 'partisan game', 10, 'noi'),
                    ('game-zero-sum', '零和博弈', '线性规划求解博弈', 9, 'noi'),
                ]
            },
            {
                'id': 'math-prob', 'name': '概率与期望',
                'desc': '概率DP、期望线性性、马尔可夫链、随机变量',
                'subtopics': [
                    ('prob-dp', '概率DP', '状态转移概率', 6, 'improve'),
                    ('prob-expect', '期望DP', '期望线性性', 7, 'improve'),
                    ('prob-markov', '马尔可夫链', '状态转移矩阵', 9, 'noi'),
                    ('prob-random-var', '随机变量', '期望/方差/矩', 8, 'noi'),
                    ('prob-concentration', '集中不等式', 'Chernoff/Hoeffding界', 9, 'noi'),
                    ('prob-conditional', '条件概率', '贝叶斯定理', 6, 'improve'),
                ]
            },
            {
                'id': 'math-algebra', 'name': '代数结构',
                'desc': '群、环、域论基础',
                'subtopics': [
                    ('m-group-theory', '群论', '群的基本结构与性质', 9, 'noi'),
                    ('m-ring-theory', '环论', '环的基本概念', 9, 'noi'),
                    ('m-field-theory', '域论', '域与有限域', 9, 'noi'),
                    ('m-finite-field', '有限域', 'GF(p)与GF(2^n)', 9, 'noi'),
                    ('m-permutation', '置换群', '置换与置换群', 8, 'noi'),
                    ('m-schreier-sims', 'Schreier-Sims算法', '置换群算法', 10, 'noi'),
                ]
            },
            {
                'id': 'math-numerical', 'name': '数值方法',
                'desc': '数值计算与近似算法',
                'subtopics': [
                    ('m-interp', '插值', '拉格朗日插值/牛顿插值', 8, 'noi'),
                    ('m-newton', '牛顿迭代', '方程求根', 8, 'noi'),
                    ('m-integral', '数值积分', '辛普森法则', 8, 'noi'),
                    ('m-bignum', '高精度', '大整数运算', 4, 'entry'),
                    ('m-binary-set', '二进制集合', '位运算集合操作', 5, 'improve'),
                    ('m-gray', '格雷码', '二进制反射格雷码', 5, 'improve'),
                    ('m-balanced-ternary', '平衡三进制', '对称三进制', 7, 'improve'),
                ]
            },
        ]
    },
    {
        'id': 'geometry', 'name': '计算几何',
        'desc': '点线面/凸包/半平面交/旋转卡壳/最近点对',
        'topics': [
            {
                'id': 'geo-all', 'name': '计算几何',
                'desc': '基础计算几何算法',
                'subtopics': [
                    ('geo-vector', '向量运算', '点积/叉积/旋转', 6, 'improve'),
                    ('geo-2d', '二维计算几何', '点线面基础操作', 6, 'improve'),
                    ('geo-3d', '三维计算几何', '三维点线面', 8, 'noi'),
                    ('geo-convex', '凸包', 'Graham/Andrew扫描', 8, 'noi'),
                    ('geo-inter', '线段相交', '判断与求交', 7, 'improve'),
                    ('geo-half', '半平面交', '求半平面交集', 9, 'noi'),
                    ('geo-triang', '三角剖分', 'Delaunay三角剖分', 9, 'noi'),
                    ('geo-rotating', '旋转卡壳', '凸包直径/最远点对', 8, 'noi'),
                    ('geo-scanning', '扫描线', '平面扫描算法', 8, 'noi'),
                    ('geo-nearest', '最近点对', '分治求最近点对', 8, 'noi'),
                    ('geo-random', '随机增量法', '最小圆覆盖', 8, 'noi'),
                    ('geo-pick', 'Pick定理', '格点多边形面积', 7, 'improve'),
                    ('geo-distance', '距离', '各种距离定义', 5, 'improve'),
                    ('geo-inverse', '反演变换', '几何反演', 9, 'noi'),
                    ('geo-misc', '计算几何杂项', '其他计算几何技巧', 8, 'noi'),
                ]
            },
        ]
    },
    {
        'id': 'misc', 'name': '杂项',
        'desc': '离线算法、双指针、位运算、随机化、构造、交互、表达式',
        'topics': [
            {
                'id': 'misc-offline', 'name': '离线算法',
                'desc': '离线处理查询的各类技巧',
                'subtopics': [
                    ('misc-cdq', 'CDQ分治', '离线处理三维偏序', 8, 'noi'),
                    ('misc-mo', '莫队算法', '区间查询离线排序', 7, 'improve'),
                    ('misc-mo-modifiable', '带修莫队', '支持修改的莫队', 8, 'noi'),
                    ('misc-mo-tree', '树上莫队', '树上的莫队算法', 8, 'noi'),
                    ('misc-mo-rollback', '回滚莫队', '只增/只删莫队', 8, 'noi'),
                    ('misc-mo-2d', '二维莫队', '二维区间查询', 9, 'noi'),
                    ('misc-parallel-binsearch', '整体二分', '批量二分答案', 8, 'noi'),
                    ('misc-mo-bitset', '莫队+bitset', '莫队配合bitset优化', 9, 'noi'),
                    ('misc-mo-secondary', '二次离线莫队', '莫队二次离线优化', 9, 'noi'),
                ]
            },
            {
                'id': 'misc-twoptr', 'name': '双指针',
                'desc': '对撞/快慢/滑动窗口',
                'subtopics': [
                    ('tp-opposite', '对撞指针', '两端向中间', 4, 'entry'),
                    ('tp-same', '快慢指针', '同向不同速', 4, 'entry'),
                    ('tp-slide', '滑动窗口', '动态区间', 4, 'entry'),
                ]
            },
            {
                'id': 'misc-bit', 'name': '位运算',
                'desc': '位运算技巧、bitset、lowbit',
                'subtopics': [
                    ('bit-basic', '基本位操作', '与或非异或移位', 3, 'entry'),
                    ('bit-lowbit', 'lowbit技巧', 'n & -n', 4, 'entry'),
                    ('bit-subset', '子集枚举', '二进制子集遍历', 5, 'improve'),
                    ('bit-bitset', 'bitset优化', '常数/64优化', 5, 'improve'),
                ]
            },
            {
                'id': 'misc-random', 'name': '随机化算法',
                'desc': '随机化方法与技巧',
                'subtopics': [
                    ('misc-random-basic', '随机化基础', '随机函数与概率分析', 6, 'improve'),
                    ('misc-rand-tech', '随机化技巧', '随机化哈希/随机增量', 7, 'improve'),
                    ('misc-frac-programming', '分数规划', '最大化比值', 8, 'noi'),
                ]
            },
            {
                'id': 'misc-other', 'name': '其他技巧',
                'desc': '竞赛中的各种实用技巧',
                'subtopics': [
                    ('misc-bigint', '高精度运算', '大整数加减乘除', 4, 'entry'),
                    ('misc-construct', '构造题', '设计符合条件的解', 6, 'improve'),
                    ('misc-interact', '交互题', '与评判系统交互', 7, 'improve'),
                    ('misc-fastio', '快读快写', '优化大量IO', 4, 'entry'),
                    ('misc-discrete', '离散化', '坐标压缩', 6, 'improve'),
                    ('misc-expression', '表达式求值', '中缀/后缀表达式', 5, 'improve'),
                    ('misc-main-element', '主元素问题', '摩尔投票算法', 5, 'improve'),
                    ('misc-garsia-wachs', 'Garsia-Wachs算法', '最优二叉搜索树构造', 9, 'noi'),
                    ('misc-josephus', '约瑟夫问题', '约瑟夫环', 5, 'improve'),
                    ('misc-job-order', '流水作业调度', 'Johnson法则', 7, 'improve'),
                    ('misc-kahan', 'Kahan求和', '浮点误差补偿', 6, 'improve'),
                    ('misc-15-puzzle', '15数码问题', '启发式搜索经典问题', 8, 'noi'),
                    ('misc-endian', '字节序', '大端与小端', 4, 'entry'),
                    ('misc-space-opt', '空间优化', '滚动数组/原地操作', 5, 'improve'),
                    ('misc-hoverline', '悬线法', '最大子矩阵', 6, 'improve'),
                    ('misc-fsm', '有限状态机', '状态机DP', 7, 'improve'),
                ]
            },
        ]
    },
    {
        'id': 'contest', 'name': '竞赛相关',
        'desc': '竞赛经验、常见错误、技巧、IO、学习路线',
        'topics': [
            {
                'id': 'contest-intro', 'name': '竞赛入门',
                'desc': 'OI/ICPC竞赛基础知识',
                'subtopics': [
                    ('contest-oi', 'OI竞赛', '全国青少年信息学奥林匹克竞赛', 1, 'entry'),
                    ('contest-icpc', 'ICPC竞赛', '国际大学生程序设计竞赛', 1, 'entry'),
                    ('contest-roadmap', '学习路线', 'OI/ICPC学习路径规划', 1, 'entry'),
                    ('contest-resources', '学习资源', 'OI/ICPC学习资源推荐', 1, 'entry'),
                ]
            },
            {
                'id': 'contest-skill', 'name': '竞赛技巧',
                'desc': '竞赛中的实用技巧与经验',
                'subtopics': [
                    ('contest-io', '输入输出', '竞赛输入输出处理', 2, 'entry'),
                    ('contest-common-mistakes', '常见错误', '竞赛中常见错误汇总', 2, 'entry'),
                    ('contest-common-tricks', '常用技巧', '竞赛常用技巧总结', 3, 'entry'),
                    ('contest-dictionary', '竞赛用语', 'OI/ICPC常用术语', 1, 'entry'),
                    ('contest-problemsetting', '出题', '竞赛题目设计与数据', 7, 'improve'),
                ]
            },
        ]
    },
    {
        'id': 'tools', 'name': '工具与技巧',
        'desc': '对拍、调试、复杂度分析、STL进阶、编辑器',
        'topics': [
            {
                'id': 'tool-all', 'name': '开发工具',
                'desc': '竞赛开发必备工具',
                'subtopics': [
                    ('tool-compare', '对拍', '暴力+随机+批处理验证', 5, 'improve'),
                    ('tool-debug', '调试技巧', 'gdb/assert/输出调试', 4, 'entry'),
                    ('tool-complex', '复杂度分析', '时间/空间复杂度', 6, 'improve'),
                    ('tool-compiler', '编译器', 'g++/Clang编译选项', 3, 'entry'),
                    ('tool-cmd', '命令行', 'Windows/Linux命令行基础', 2, 'entry'),
                    ('tool-git', '版本控制', 'Git基础操作', 3, 'entry'),
                    ('tool-latex', 'LaTeX', '科技排版基础', 5, 'improve'),
                    ('tool-oj', 'OJ工具', '常用OJ平台与工具', 2, 'entry'),
                ]
            },
        ]
    },
    {
        'id': 'adv', 'name': '高级专题',
        'desc': '拟阵、LGV引理、Prufer序列、Burnside、各种高级专题',
        'topics': [
            {
                'id': 'adv-all', 'name': '高级专题',
                'desc': 'NOI级别进阶内容',
                'subtopics': [
                    ('adv-matroid', '拟阵', '贪心理论基础', 10, 'noi'),
                    ('adv-lgv', 'LGV引理', '路径不交方案数', 10, 'noi'),
                    ('adv-prufer', 'Prufer序列', '生成树计数', 9, 'noi'),
                    ('adv-polya', 'Polya计数定理', '置换群计数', 9, 'noi'),
                    ('adv-burnside', 'Burnside引理', '置换群计数', 9, 'noi'),
                ]
            },
        ]
    },
]

# ============================================================
# 种子数据：示例算法模板
# ============================================================
SEED_TEMPLATES = [
    {
        'name': '快速读入（快读）',
        'category': '工具与技巧',
        'language': 'cpp',
        'code': '''inline int read() {
    int x = 0, f = 1;
    char ch = getchar();
    while (ch < '0' || ch > '9') {
        if (ch == '-') f = -1;
        ch = getchar();
    }
    while (ch >= '0' && ch <= '9') {
        x = x * 10 + ch - '0';
        ch = getchar();
    }
    return x * f;
}''',
        'note': '比 cin/cout 快很多，大数据输入必备。\n使用方法：`int n = read();`',
    },
    {
        'name': '并查集 (DSU)',
        'category': '数据结构',
        'language': 'cpp',
        'code': '''struct DSU {
    vector<int> fa, sz;
    DSU(int n) : fa(n + 1), sz(n + 1, 1) {
        iota(fa.begin(), fa.end(), 0);
    }
    int find(int x) {
        return fa[x] == x ? x : fa[x] = find(fa[x]);
    }
    void merge(int a, int b) {
        a = find(a), b = find(b);
        if (a != b) {
            if (sz[a] < sz[b]) swap(a, b);
            fa[b] = a; sz[a] += sz[b];
        }
    }
    bool same(int a, int b) {
        return find(a) == find(b);
    }
};''',
        'note': '带路径压缩和按大小合并，近乎 O(1) 操作。\n常用于：连通分量、Kruskal MST、判环。',
    },
    {
        'name': '树状数组 (BIT)',
        'category': '数据结构',
        'language': 'cpp',
        'code': '''template<typename T>
struct BIT {
    int n; vector<T> tr;
    BIT(int n) : n(n), tr(n + 1) {}
    void add(int i, T x) {
        for (; i <= n; i += i & -i) tr[i] += x;
    }
    T sum(int i) {
        T s = 0;
        for (; i; i -= i & -i) s += tr[i];
        return s;
    }
    T range(int l, int r) {
        return sum(r) - sum(l - 1);
    }
};''',
        'note': '单点修改+区间查询 O(logN)。\n可扩展：区间修改+单点查询(差分)、逆序对计数。',
    },
    {
        'name': 'Dijkstra 最短路',
        'category': '图论',
        'language': 'cpp',
        'code': '''vector<long long> dijkstra(int s, const vector<vector<pair<int,int>>> &g) {
    int n = g.size() - 1;
    vector<long long> dist(n + 1, 1e18);
    priority_queue<pair<long long,int>, vector<pair<long long,int>>, greater<>> pq;
    dist[s] = 0; pq.push({0, s});
    while (!pq.empty()) {
        auto [d, u] = pq.top(); pq.pop();
        if (d != dist[u]) continue;
        for (auto [v, w] : g[u])
            if (dist[v] > d + w) {
                dist[v] = d + w;
                pq.push({dist[v], v});
            }
    }
    return dist;
}''',
        'note': '非负权单源最短路 O((V+E)logV)。\n注意：需用 long long 防溢出；pair<距离, 节点> 的排序方式。',
    },
    {
        'name': '快速幂',
        'category': '数学',
        'language': 'cpp',
        'code': '''long long qpow(long long a, long long b, long long mod) {
    long long res = 1;
    a %= mod;
    while (b) {
        if (b & 1) res = res * a % mod;
        a = a * a % mod;
        b >>= 1;
    }
    return res;
}''',
        'note': 'O(log N) 计算 a^b mod m。\n应用：模逆元 `qpow(a, mod-2, mod)`（mod 为质数）、矩阵快速幂。',
    },
]

# ============================================================
# 种子数据导入函数
# ============================================================

def seed_database() -> str:
    """
    将种子数据导入数据库（仅当表为空时执行）
    返回状态消息，供 GUI 状态栏显示
    """
    conn = get_connection()
    cursor = conn.cursor()
    messages = []

    # --- 导入模板（仅首次） ---
    cursor.execute("SELECT COUNT(*) as cnt FROM templates")
    if cursor.fetchone()['cnt'] == 0:
        for tmpl in SEED_TEMPLATES:
            cursor.execute(
                """INSERT INTO templates (name, category, language, code, note)
                   VALUES (?, ?, ?, ?, ?)""",
                (tmpl['name'], tmpl['category'], tmpl['language'],
                 tmpl['code'], tmpl['note'])
            )
        conn.commit()
        messages.append(f'已导入 {len(SEED_TEMPLATES)} 个算法模板')

    conn.close()
    return '；'.join(messages) if messages else ''


# ============================================================
# 辅助函数：获取大纲数据（供 outline 模块使用）
# ============================================================

def get_categories():
    """返回 22 大类算法大纲数据"""
    return ALGORITHM_CATEGORIES


def get_all_topic_ids():
    """返回所有子知识点的 ID 列表及其层级信息"""
    result = []
    for cat in ALGORITHM_CATEGORIES:
        for topic in cat['topics']:
            for sub in topic['subtopics']:
                result.append({
                    'topic_id': sub[0],
                    'name': sub[1],
                    'desc': sub[2],
                    'difficulty': sub[3],
                    'level': sub[4],
                    'category_id': cat['id'],
                    'category_name': cat['name'],
                    'topic_id_parent': topic['id'],
                    'topic_name': topic['name'],
                })
    return result
