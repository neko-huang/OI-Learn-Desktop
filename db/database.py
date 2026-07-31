"""
数据库层 — SQLite 初始化、建表、连接管理
数据库文件位于程序目录下的 data/info-learn.db
"""

import sqlite3
import os
from config import get_data_dir

DB_PATH = os.path.join(get_data_dir(), 'info-learn.db')


def get_connection() -> sqlite3.Connection:
    """
    获取数据库连接
    每次调用返回新连接，保证线程安全
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row          # 查询结果用字典访问
    conn.execute("PRAGMA journal_mode=WAL")  # WAL 模式：读不阻塞写
    conn.execute("PRAGMA foreign_keys=ON")   # 启用外键约束
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
        print("[迁移] 已添加 problems.description 字段")
    except Exception:
        pass  # 字段已存在，忽略
    conn.close()

    # v1.2: 添加练习模式字段
    conn2 = get_connection()
    try:
        conn2.execute("ALTER TABLE practice_plans ADD COLUMN practice_mode TEXT DEFAULT 'free'")
        conn2.commit()
        print("[迁移] 已添加 practice_plans.practice_mode 字段")
    except Exception:
        pass
    try:
        conn2.execute("ALTER TABLE practice_plans ADD COLUMN duration INTEGER DEFAULT 0")
        conn2.commit()
        print("[迁移] 已添加 practice_plans.duration 字段")
    except Exception:
        pass
    conn2.close()

    # 自动初始化时也执行迁移
    _run_migrations = True


# ============================================================
# 首次 import 时自动建表
# ============================================================
try:
    if not os.path.exists(DB_PATH):
        initialize_database()
except Exception as e:
    print(f"[数据库] 初始化失败: {e}")
