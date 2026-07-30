"""
种子数据 — 从旧 info-learn 项目导出的算法大纲、百科、模板
首次运行时自动填充数据库
"""

from db.database import get_connection

# ============================================================
# 22 大类算法大纲（类别 → 主题 → 子知识点）
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
                    ('lang-array', '数组', '一维/二维数组的定义与使用', 2, 'entry'),
                    ('lang-string-basic', '字符串入门', 'C风格字符数组与string类基础', 2, 'entry'),
                    ('lang-struct', '结构体', 'struct定义与使用', 3, 'entry'),
                    ('lang-func', '函数与递归', '函数定义、参数传递、递归调用', 3, 'entry'),
                ]
            },
            {
                'id': 'lang-stl', 'name': 'STL入门',
                'desc': '标准模板库常用容器和算法',
                'subtopics': [
                    ('stl-vector', 'vector向量', '动态数组', 3, 'entry'),
                    ('stl-sort', 'STL排序', 'sort函数与自定义比较', 3, 'entry'),
                    ('stl-map', 'map映射', '键值对存储', 4, 'entry'),
                ]
            },
        ]
    },
    {
        'id': 'basics', 'name': '基础算法',
        'desc': '模拟、贪心、递推、二分、枚举、分治',
        'topics': [
            {
                'id': 'basic-core', 'name': '核心算法',
                'desc': '入门级基础算法',
                'subtopics': [
                    ('basic-sim', '模拟', '按题意逐步实现', 1, 'entry'),
                    ('basic-greedy', '贪心', '局部最优→全局最优', 3, 'entry'),
                    ('basic-rec', '递推', '逐步推导，从小到大', 3, 'entry'),
                    ('basic-binary', '二分', '有序序列O(logN)定位', 3, 'entry'),
                    ('basic-enum', '枚举', '穷举验证', 2, 'entry'),
                    ('basic-divide', '分治', '分解→解决→合并', 6, 'improve'),
                    ('basic-sort', '排序', '各类排序算法', 3, 'entry'),
                ]
            },
        ]
    },
    {
        'id': 'twoptr', 'name': '双指针',
        'desc': '对撞/快慢/滑动窗口',
        'topics': [
            {
                'id': 'twoptr-all', 'name': '双指针技巧',
                'desc': '四种经典模式',
                'subtopics': [
                    ('tp-opposite', '对撞指针', '两端向中间', 3, 'entry'),
                    ('tp-same', '快慢指针', '同向不同速', 3, 'entry'),
                    ('tp-slide', '滑动窗口', '动态区间', 4, 'entry'),
                ]
            },
        ]
    },
    {
        'id': 'ds-linear', 'name': '线性数据结构',
        'desc': '栈、队列、链表、哈希表、前缀和、差分、单调队列/栈、分块',
        'topics': [
            {
                'id': 'linear-core', 'name': '线性结构',
                'desc': '基础线性数据结构',
                'subtopics': [
                    ('lin-stack', '栈', 'LIFO后进先出', 3, 'entry'),
                    ('lin-queue', '队列', 'FIFO + 单调队列', 3, 'entry'),
                    ('lin-list', '链表', '动态增删O(1)', 3, 'entry'),
                    ('lin-hash', '哈希表', 'O(1)查找', 5, 'improve'),
                    ('lin-prefix', '前缀和', 'O(1)区间和', 3, 'entry'),
                    ('lin-diff', '差分', 'O(1)区间修改', 4, 'entry'),
                    ('lin-st', 'ST表(RMQ)', 'O(NlogN)预处理/O(1)查询', 6, 'improve'),
                    ('lin-block', '分块', '√N优雅暴力', 7, 'improve'),
                    ('lin-mono-queue', '单调队列', '区间极值', 5, 'improve'),
                    ('lin-mono-stack', '单调栈', '下一个更大/更小', 5, 'improve'),
                ]
            },
        ]
    },
    {
        'id': 'ds-tree', 'name': '树形数据结构',
        'desc': '线段树、树状数组、平衡树、LCT、主席树',
        'topics': [
            {
                'id': 'tree-core', 'name': '核心树结构',
                'desc': '竞赛最常用的树形结构',
                'subtopics': [
                    ('tree-dsu', '并查集(DSU)', '近乎O(1)合并查询', 6, 'improve'),
                    ('tree-bit', '树状数组(BIT)', 'O(logN)单点改/区间查', 6, 'improve'),
                    ('tree-seg', '线段树', '区间操作瑞士军刀', 6, 'improve'),
                    ('tree-heap', '堆/优先队列', '极值维护', 5, 'improve'),
                    ('tree-bal', '平衡树', 'Treap/Splay/AVL', 8, 'noi'),
                    ('tree-trie', 'Trie字典树', '前缀检索', 6, 'improve'),
                    ('tree-lct', '动态树(LCT)', 'Link-Cut Tree', 10, 'noi'),
                    ('tree-pst', '可持久化线段树', '历史版本查询', 8, 'noi'),
                    ('tree-kdt', 'K-D Tree', '多维空间索引', 9, 'noi'),
                    ('tree-seg-beats', '吉司机线段树', 'Segment Tree Beats', 10, 'noi'),
                    ('tree-merge', '线段树合并', '启发式合并O(NlogN)', 8, 'noi'),
                    ('tree-cdq', 'CDQ分治', '离线处理偏序', 8, 'noi'),
                    ('tree-li-chao', '李超线段树', '维护直线/线段', 8, 'noi'),
                ]
            },
        ]
    },
    {
        'id': 'tree-theory', 'name': '树论',
        'desc': 'LCA、树链剖分、点分治、虚树、基环树',
        'topics': [
            {
                'id': 'tree-adv', 'name': '树上高级算法',
                'desc': '树结构上的各种经典算法',
                'subtopics': [
                    ('tree-lca', '最近公共祖先(LCA)', '倍增/欧拉序/Tarjan', 6, 'improve'),
                    ('tree-hld', '树链剖分(HLD)', '重链剖分/长链剖分', 8, 'noi'),
                    ('tree-cent', '点分治', '树重心+分治', 8, 'noi'),
                    ('tree-virt', '虚树', '稀疏关键点压缩', 8, 'noi'),
                    ('tree-dsu-on', '树上启发式合并', 'DSU on Tree', 7, 'improve'),
                    ('tree-base', '基环树', '树上加一条边', 8, 'noi'),
                    ('tree-diam', '树的直径', '两次DFS或DP', 4, 'entry'),
                ]
            },
        ]
    },
    {
        'id': 'graph', 'name': '图论',
        'desc': 'BFS/DFS、最短路、MST、拓扑排���、连通性、网络流',
        'topics': [
            {
                'id': 'graph-basic', 'name': '基础图论',
                'desc': '图的遍历、最短路、MST',
                'subtopics': [
                    ('g-bfs', 'BFS广度优先搜索', '队列层序遍历', 5, 'entry'),
                    ('g-dfs', 'DFS深度优先搜索', '递归+回溯', 5, 'entry'),
                    ('g-topo', '拓扑排序', 'DAG顶点线性序', 6, 'improve'),
                    ('g-dij', 'Dijkstra最短路', '非负权单源O((V+E)logV)', 6, 'improve'),
                    ('g-floyd', 'Floyd-Warshall', '全源最短路O(V³)', 6, 'improve'),
                    ('g-bellman', 'Bellman-Ford/SPFA', '含负权O(VE)', 6, 'improve'),
                    ('g-kruskal', 'Kruskal MST', '并查集+贪心选边', 6, 'improve'),
                    ('g-prim', 'Prim MST', '点扩散，适合稠密图', 6, 'improve'),
                    ('g-euler', '欧拉回路', '一笔画问题', 6, 'improve'),
                ]
            },
            {
                'id': 'graph-adv', 'name': '进阶图论',
                'desc': '连通性、网络流、匹配',
                'subtopics': [
                    ('g-scc', '强连通分量(Tarjan)', 'SCC缩点→DAG', 7, 'improve'),
                    ('g-bridge', '桥', '割边判定', 7, 'improve'),
                    ('g-cut', '割点', '关节点判定', 7, 'improve'),
                    ('g-sat', '2-SAT', '布尔可满足问题', 8, 'noi'),
                    ('g-flow', '网络流(Dinic)', '最大流O(V²E)', 8, 'noi'),
                    ('g-mcmf', '最小费用最大流', 'SPFA/Dijkstra增广', 8, 'noi'),
                    ('g-bip', '二分图匹配', '匈牙利/KM算法', 8, 'noi'),
                    ('g-diff', '差分约束', '不��式组→图论', 7, 'improve'),
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
                    ('s-prune', '剪枝', '减少搜索空间', 6, 'improve'),
                    ('s-memo', '记忆化搜索', '缓存递归结果', 6, 'improve'),
                    ('s-heur', '启发式搜索', '估价函数引导', 7, 'improve'),
                    ('s-iter', '迭代加深搜索', '深度逐层增加', 7, 'improve'),
                    ('s-ida', 'IDA*', '迭代加深+启发式', 7, 'improve'),
                    ('s-dlx', 'Dancing Links', '精确覆盖/数独', 8, 'noi'),
                    ('s-bi', '双向BFS', '起点+终点同时BFS', 7, 'improve'),
                    ('s-astar', 'A*算法', 'f=g+h估价搜索', 7, 'improve'),
                    ('s-mim', '折半搜索', 'Meet in Middle', 7, 'improve'),
                    ('s-sa', '模拟退火', '概率接受较差解', 8, 'noi'),
                ]
            },
        ]
    },
    {
        'id': 'dp', 'name': '动态规划',
        'desc': '背包/区间/树形/状压/数位/DP优化',
        'topics': [
            {
                'id': 'dp-models', 'name': 'DP模型',
                'desc': '经典DP模型',
                'subtopics': [
                    ('dp-knap', '背包DP', '0-1/完全/多重', 5, 'entry'),
                    ('dp-interval', '区间DP', '小区间→大区间', 5, 'entry'),
                    ('dp-tree2', '树形DP', '树上递推', 6, 'improve'),
                    ('dp-linear', '线性DP', '序列递推', 4, 'entry'),
                    ('dp-bitmask', '状压DP', '二进制表示状态', 6, 'improve'),
                    ('dp-digit', '数位DP', '按位递推统计', 7, 'improve'),
                    ('dp-contour', '轮廓线DP', '逐格转移', 8, 'noi'),
                ]
            },
            {
                'id': 'dp-opt', 'name': 'DP优化',
                'desc': '加速DP转移的高级技巧',
                'subtopics': [
                    ('dp-pq', '优先队列优化DP', '维护转移最优值', 6, 'improve'),
                    ('dp-matrix', '矩阵加速DP', '常系数线性递推O(K³logN)', 6, 'improve'),
                    ('dp-slope', '斜率优化', '凸包维护决策', 8, 'noi'),
                    ('dp-wqs', 'WQS二分', '二分惩罚项', 9, 'noi'),
                    ('dp-quad', '四边形不等式', '决策单调性加速', 8, 'noi'),
                    ('dp-ddp', '动态DP', '带修改的DP', 10, 'noi'),
                ]
            },
        ]
    },
    {
        'id': 'string', 'name': '字符串',
        'desc': 'KMP/Trie/AC自动机/后缀数���/SAM/Manacher',
        'topics': [
            {
                'id': 'str-all', 'name': '字符串算法',
                'desc': '从匹配到后缀数据结构',
                'subtopics': [
                    ('str-kmp', 'KMP算法', '单模式串O(N+M)', 6, 'improve'),
                    ('str-trie2', 'Trie字典树', '前缀检索+01-Trie', 6, 'improve'),
                    ('str-ac', 'AC自动机', '多模式串=Trie+KMP', 8, 'noi'),
                    ('str-sa', '后缀数组(SA)', 'SA-IS O(N)', 8, 'noi'),
                    ('str-sam', '后缀自动机(SAM)', '处理所有子串', 10, 'noi'),
                    ('str-manacher', 'Manacher算法', 'O(N)最长回文', 7, 'improve'),
                    ('str-pam', '回文自动机(PAM)', '回文串结构', 9, 'noi'),
                    ('str-z', 'Z函数(扩展KMP)', 'Z函数模板', 7, 'improve'),
                ]
            },
        ]
    },
    {
        'id': 'math', 'name': '数学',
        'desc': '数论/组合/线性代数/概率/博弈/多项式',
        'topics': [
            {
                'id': 'math-number', 'name': '数论',
                'desc': '素数、同余、逆元、筛法',
                'subtopics': [
                    ('m-prime', '素数判定与筛法', '埃氏筛/欧拉筛', 5, 'improve'),
                    ('m-gcd', 'GCD与LCM', '欧几里得算法', 4, 'entry'),
                    ('m-mod', '模运算与逆元', '费马小定理/扩展欧几里得', 6, 'improve'),
                    ('m-crt', '中国剩余定理(CRT)', '同余方程组', 7, 'improve'),
                    ('m-mobius', '莫比乌斯反演', '数论函数卷积', 8, 'noi'),
                    ('m-bsgs', 'BSGS算法', '离散对数', 8, 'noi'),
                    ('m-euler', '欧拉函数', 'φ(n)定义与应用', 6, 'improve'),
                    ('m-linear-sieve', '线性筛', '筛积性函数', 7, 'improve'),
                ]
            },
            {
                'id': 'math-combi', 'name': '组合数学',
                'desc': '排列组合、容斥、卡特兰数',
                'subtopics': [
                    ('m-combi-basic', '排列组合基础', '阶乘/组合数', 5, 'entry'),
                    ('m-catalan', '卡特兰数', '出栈序列/括号匹配', 6, 'improve'),
                    ('m-incl-excl', '容斥原理', '集合计数', 7, 'improve'),
                    ('m-stirling', '斯特林数', '集合划分/轮换', 8, 'noi'),
                ]
            },
        ]
    },
    {
        'id': 'geometry', 'name': '计算几何',
        'desc': '点线面/凸包/半平面交/旋转卡壳',
        'topics': [
            {
                'id': 'geo-all', 'name': '计算几何',
                'desc': '基础计算几何算法',
                'subtopics': [
                    ('geo-vector', '向量运算', '点积/叉积/旋转', 5, 'improve'),
                    ('geo-convex', '凸包', 'Graham/Andrew扫描', 6, 'improve'),
                    ('geo-inter', '线段相交', '旋转卡壳', 7, 'improve'),
                    ('geo-half', '半平面交', '求半平面交集', 8, 'noi'),
                    ('geo-triang', '三角剖分', 'Delaunay三角剖分', 9, 'noi'),
                ]
            },
        ]
    },
    {
        'id': 'bitwise', 'name': '位运算',
        'desc': '位运算技巧、bitset、lowbit',
        'topics': [
            {
                'id': 'bit-all', 'name': '位运算技巧',
                'desc': '位运算加速和状态压缩',
                'subtopics': [
                    ('bit-basic', '基本位操作', '与或非异或移位', 3, 'entry'),
                    ('bit-lowbit', 'lowbit技巧', 'n & -n', 4, 'entry'),
                    ('bit-subset', '子集枚举', '二进制子集遍历', 5, 'improve'),
                    ('bit-bitset', 'bitset优化', '常数/64优化', 6, 'improve'),
                ]
            },
        ]
    },
    {
        'id': 'game', 'name': '博弈论',
        'desc': 'NIM/SG函数/威佐夫博弈',
        'topics': [
            {
                'id': 'game-all', 'name': '博弈论',
                'desc': '公平组合游戏',
                'subtopics': [
                    ('game-nim', 'NIM游戏', '异或和判定', 5, 'improve'),
                    ('game-sg', 'SG函数', '有向图游戏', 7, 'improve'),
                    ('game-wythoff', '威佐夫博弈', '两堆石子', 7, 'improve'),
                    ('game-composite', '组合游戏', '博弈DP', 8, 'noi'),
                ]
            },
        ]
    },
    {
        'id': 'prob', 'name': '概率与期望',
        'desc': '概率DP、期望线性性、马尔可夫链',
        'topics': [
            {
                'id': 'prob-all', 'name': '概率与期望',
                'desc': '竞赛中概率与期望的计算',
                'subtopics': [
                    ('prob-dp', '概率DP', '状态转移概率', 6, 'improve'),
                    ('prob-expect', '期望DP', '期望线性性', 7, 'improve'),
                    ('prob-markov', '马尔可夫链', '状态转移矩阵', 9, 'noi'),
                ]
            },
        ]
    },
    {
        'id': 'poly', 'name': '多项式与生成函数',
        'desc': 'FFT/NTT/FWT/生成函数',
        'topics': [
            {
                'id': 'poly-all', 'name': '多项式算法',
                'desc': '多项式运算与变换',
                'subtopics': [
                    ('poly-fft', 'FFT', '快速傅里叶变换', 8, 'noi'),
                    ('poly-ntt', 'NTT', '数论变换', 8, 'noi'),
                    ('poly-fwt', 'FWT', '快速沃尔什变换', 9, 'noi'),
                    ('poly-gf', '生成函数', '普通/指数型生成函数', 9, 'noi'),
                ]
            },
        ]
    },
    {
        'id': 'ml', 'name': '机器学习入门',
        'desc': '线性回归、决策树、神经网络基础',
        'topics': [
            {
                'id': 'ml-all', 'name': 'ML基础',
                'desc': '机器学习基础知识',
                'subtopics': [
                    ('ml-linear', '线性回归', '最小二乘法', 7, 'improve'),
                    ('ml-decision', '决策树', '信息增益', 7, 'improve'),
                    ('ml-nn', '神经网���基础', '感知器/反向传播', 8, 'noi'),
                ]
            },
        ]
    },
    {
        'id': 'parallel', 'name': '并行与并发',
        'desc': '多线程、OpenMP、GPU编程基础',
        'topics': [
            {
                'id': 'par-all', 'name': '并行编程',
                'desc': '竞赛中的并行优化',
                'subtopics': [
                    ('par-thread', '多线程基础', '线程创建与同步', 7, 'improve'),
                    ('par-openmp', 'OpenMP', '并行循环/归约', 7, 'improve'),
                ]
            },
        ]
    },
    {
        'id': 'misc', 'name': '杂项',
        'desc': '高精度/离线技巧/构造/交互/读入优化',
        'topics': [
            {
                'id': 'misc-all', 'name': '杂项技巧',
                'desc': '竞赛中的各种实用技巧',
                'subtopics': [
                    ('misc-bigint', '高精度运算', '大整数加减乘除', 5, 'improve'),
                    ('misc-offline', '离线查询', '莫队算法/整体二分', 8, 'noi'),
                    ('misc-construct', '构造题', '设计符合条件的解', 6, 'improve'),
                    ('misc-interact', '交互题', '与评判系统交互', 7, 'improve'),
                    ('misc-fastio', '快读快写', '优化大量IO', 4, 'entry'),
                    ('misc-discrete', '离散化', '坐标压缩', 4, 'entry'),
                ]
            },
        ]
    },
    {
        'id': 'tools', 'name': '工具与技巧',
        'desc': '对拍、调试、复杂度分析、STL进阶',
        'topics': [
            {
                'id': 'tool-all', 'name': '开发工具',
                'desc': '竞赛开发必备工具',
                'subtopics': [
                    ('tool-compare', '对拍', '暴力+随机+批处理', 5, 'improve'),
                    ('tool-debug', '调试技巧', 'gdb/assert/输出调试', 4, 'entry'),
                    ('tool-complex', '复杂度分析', '时间/空间复杂度', 3, 'entry'),
                ]
            },
        ]
    },
    {
        'id': 'adv', 'name': '高级专题',
        'desc': 'LGV引理/Burnside引理/prufer序列/拟阵',
        'topics': [
            {
                'id': 'adv-all', 'name': '高级专题',
                'desc': 'NOI级别进阶内容',
                'subtopics': [
                    ('adv-lgv', 'LGV引理', '路径不交方案数', 10, 'noi'),
                    ('adv-burnside', 'Burnside引理', '置换群计数', 10, 'noi'),
                    ('adv-prufer', 'Prufer序列', '生成树计数', 9, 'noi'),
                    ('adv-matroid', '拟阵', '贪心理论基础', 10, 'noi'),
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
    cursor.execute("SELECT COUNT(*) FROM templates")
    if cursor.fetchone()[0] == 0:
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
