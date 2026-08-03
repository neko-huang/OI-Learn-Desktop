"""
数据库层 — SQLite 初始化、建表、连接管理
数据库文件位于程序目录下的 data/info-learn.db
"""

import sqlite3
import os
from config import get_data_dir

DB_PATH = os.path.join(get_data_dir(), 'info-learn.db')


def dict_factory(cursor, row):
    """将 sqlite3 查询结果转为普通 dict（支持 .get() 方法）"""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def get_connection() -> sqlite3.Connection:
    """
    获取数据库连接
    每次调用返回新连接，保证线程安全
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = dict_factory       # 查询结果返回 dict（支持 .get()）
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def initialize_database():
    """
    首次运行时创建所有数据表
    使用 IF NOT EXISTS，可安全重复执行
    """
    conn = get_connection()
    cursor = conn.cursor()

    # ============================================================
    # 1. 大纲知识点掌握状态
    # ============================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS outline_progress (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id        TEXT    NOT NULL UNIQUE,   -- 知识点ID，如 'basic-sim'
            mastery         TEXT    NOT NULL DEFAULT 'none',  -- none/learning/familiar/mastered
            updated_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    # ============================================================
    # 2. 算法百科条目
    # ============================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS encyclopedia (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            title           TEXT    NOT NULL,          -- 百科标题
            content         TEXT    NOT NULL DEFAULT '', -- Markdown 正文
            category        TEXT    NOT NULL DEFAULT '', -- 所属分类
            tags            TEXT    DEFAULT '',        -- JSON 数组字符串
            topic_id        TEXT    DEFAULT '',        -- 关联的大纲知识点ID
            created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
            updated_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_encyclopedia_category ON encyclopedia(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_encyclopedia_topic_id ON encyclopedia(topic_id)")

    # ============================================================
    # 3. 刷题记录
    # ============================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS problems (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            title           TEXT    NOT NULL,          -- 题目名称
            platform        TEXT    NOT NULL DEFAULT '', -- OJ来源：CF/Luogu/AtCoder/Other
            platform_id     TEXT    DEFAULT '',        -- OJ 题目ID，如 CF 1500A
            difficulty      TEXT    DEFAULT '',        -- 难度等级
            tags            TEXT    DEFAULT '',        -- JSON 数组：算法标签
            description     TEXT    DEFAULT '',        -- 题意描述（Markdown）
            status          TEXT    NOT NULL DEFAULT 'todo',  -- todo/done/review
            solution        TEXT    DEFAULT '',        -- 题解 Markdown
            mistake_note    TEXT    DEFAULT '',        -- 易错记录 Markdown
            url             TEXT    DEFAULT '',        -- OJ 题目链接
            solved_at       TEXT    DEFAULT NULL,
            created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
            updated_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_problems_status ON problems(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_problems_difficulty ON problems(difficulty)")

    # ============================================================
    # 4. 算法模板库
    # ============================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS templates (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT    NOT NULL,          -- 模板名称
            category        TEXT    NOT NULL DEFAULT '', -- 分类：数据结构/图论/DP/数学/字符串/其他
            language        TEXT    NOT NULL DEFAULT 'cpp', -- cpp/python/java
            code            TEXT    NOT NULL DEFAULT '', -- 模板代码
            note            TEXT    DEFAULT '',        -- 备注/说明 Markdown
            is_starred      INTEGER NOT NULL DEFAULT 0, -- 是否收藏
            created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
            updated_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_templates_category ON templates(category)")

    # ============================================================
    # 5. 易错集
    # ============================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mistakes (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            problem_id      INTEGER DEFAULT NULL,     -- 关联的刷题记录ID
            title           TEXT    NOT NULL DEFAULT '', -- 易错描述标题
            wrong_code      TEXT    NOT NULL DEFAULT '', -- 错误代码
            correct_code    TEXT    NOT NULL DEFAULT '', -- 正确代码
            reason          TEXT    DEFAULT '',        -- 错误原因分析 Markdown
            tags            TEXT    DEFAULT '',        -- JSON 数组：关联标签
            created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
            updated_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    # ============================================================
    # 6. 练习计划
    # ============================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS practice_plans (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT    NOT NULL,          -- 计划名称
            description     TEXT    DEFAULT '',        -- 计划描述
            target_topics   TEXT    DEFAULT '',        -- 目标算法标签 JSON 数组
            status          TEXT    NOT NULL DEFAULT 'active', -- active/completed/paused
            created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
            updated_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    # ============================================================
    # 7. 计划内题目
    # ============================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS plan_problems (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id         INTEGER NOT NULL,         -- 关联计划
            problem_id      INTEGER DEFAULT NULL,     -- 关联本地刷题记录（可为空=外部题）
            platform        TEXT    DEFAULT '',        -- OJ来源
            platform_id     TEXT    DEFAULT '',        -- OJ 题目ID
            title           TEXT    NOT NULL DEFAULT '', -- 题目名称（外部题用这个显示）
            difficulty      TEXT    DEFAULT '',
            tags            TEXT    DEFAULT '',
            sort_order      INTEGER NOT NULL DEFAULT 0, -- 排序
            status          TEXT    NOT NULL DEFAULT 'todo', -- todo/done/skipped
            note            TEXT    DEFAULT '',        -- 练习笔记
            FOREIGN KEY (plan_id) REFERENCES practice_plans(id) ON DELETE CASCADE,
            FOREIGN KEY (problem_id) REFERENCES problems(id) ON DELETE SET NULL
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_plan_problems_plan ON plan_problems(plan_id)")

    # ============================================================
    # 8. 自定义大纲条目
    # ============================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS custom_topics (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id        TEXT    NOT NULL UNIQUE,   -- 唯一标识
            parent_id       TEXT    DEFAULT '',        -- 父节点ID（分类或主题ID）
            name            TEXT    NOT NULL,          -- 知识点名称
            desc            TEXT    DEFAULT '',        -- Markdown 描述
            difficulty      INTEGER DEFAULT 1,         -- 难度 1-8
            level           TEXT    DEFAULT 'entry',   -- entry/improve/noi
            category_name   TEXT    DEFAULT '自定义',  -- 所属大类名
            created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
            updated_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    conn.commit()
    conn.close()


def migrate():
    """
    数据库迁移入口（未来新增表/改结构时在此添加）
    """
    initialize_database()

    # v1.1: 添加 description 字段
    conn = get_connection()
    try:
        conn.execute("ALTER TABLE problems ADD COLUMN description TEXT DEFAULT ''")
        conn.commit()
    except Exception:
        pass  # 字段已存在，忽略
    conn.close()

    # v1.2: 添加练习模式字段
    conn2 = get_connection()
    try:
        conn2.execute("ALTER TABLE practice_plans ADD COLUMN practice_mode TEXT DEFAULT 'free'")
        conn2.commit()
    except Exception:
        pass
    try:
        conn2.execute("ALTER TABLE practice_plans ADD COLUMN duration INTEGER DEFAULT 0")
        conn2.commit()
    except Exception:
        pass
    conn2.close()

    # 自动初始化时也执行迁移
    _run_migrations = True


# ============================================================
# 注意：不再在 import 时自动建表
# 数据库初始化由 app.py 的 App.__init__ 显式调用
# ============================================================
# v1.3: 比赛记录表
    conn3 = get_connection()
    try:
        conn3.execute("""
            CREATE TABLE IF NOT EXISTS contests (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                platform        TEXT    NOT NULL,          -- Codeforces / AtCoder / 洛谷 / 其他
                contest_id      TEXT    DEFAULT '',        -- 比赛编号
                contest_name    TEXT    NOT NULL DEFAULT '',-- 比赛名称
                contest_type    TEXT    DEFAULT '',        -- 类型: rated/unrated/virtual
                contest_date    TEXT    NOT NULL DEFAULT '',-- 比赛日期 YYYY-MM-DD
                duration_min    INTEGER DEFAULT 0,        -- 时长(分钟)
                rank            INTEGER DEFAULT 0,        -- 排名
                total_participants INTEGER DEFAULT 0,     -- 参赛人数
                rating_before   INTEGER DEFAULT 0,        -- 赛前Rating
                rating_after    INTEGER DEFAULT 0,        -- 赛后Rating
                rating_change   INTEGER DEFAULT 0,        -- Rating变化
                solved_count    INTEGER DEFAULT 0,        -- 通过题数
                total_problems  INTEGER DEFAULT 0,        -- 总题数
                performance     INTEGER DEFAULT 0,        -- 表现分
                review          TEXT    DEFAULT '',        -- 复盘笔记 Markdown
                created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
                updated_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)
        conn3.execute("CREATE INDEX IF NOT EXISTS idx_contests_platform ON contests(platform)")
        conn3.execute("CREATE INDEX IF NOT EXISTS idx_contests_date ON contests(contest_date)")
        conn3.commit()
    except Exception:
        pass
    conn3.close()