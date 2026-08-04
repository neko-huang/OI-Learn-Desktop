"""
数据库层 — SQLite 初始化、建表、连接管理、带版本追踪的迁移
数据库文件位于程序目录下的 data/info-learn.db
"""

import sqlite3
import os
import threading
from config import get_data_dir

DB_PATH = os.path.join(get_data_dir(), 'info-learn.db')

# 当前架构版本号（每次新增迁移 +1）
SCHEMA_VERSION = 6

# 备份写锁
_backup_lock = threading.Lock()


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
    # 0. 架构版本追踪表
    # ============================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            key     TEXT PRIMARY KEY,
            value   TEXT NOT NULL
        )
    """)

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
            mistake_note    TEXT    DEFAULT '',        -- 易错记录 Markdown（历史遗留，已迁移至 mistakes 表 reason 字段）
            url             TEXT    DEFAULT '',        -- OJ 题目链接
            solved_at       TEXT    DEFAULT NULL,
            created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
            updated_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_problems_status ON problems(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_problems_difficulty ON problems(difficulty)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_problems_platform ON problems(platform)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_problems_created_at ON problems(created_at)")

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
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mistakes_problem_id ON mistakes(problem_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mistakes_created_at ON mistakes(created_at)")

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
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_practice_plans_status ON practice_plans(status)")

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
            desc            TEXT    DEFAULT '',        -- Markdown 描述（保留字，后续迁移至 description）
            difficulty      INTEGER DEFAULT 1,         -- 难度 1-8
            level           TEXT    DEFAULT 'entry',   -- entry/improve/noi
            category_name   TEXT    DEFAULT '自定义',  -- 所属大类名
            created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
            updated_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    conn.commit()
    conn.close()


# ============================================================
# 版本迁移函数（每个版本独立为函数）
# ============================================================

def _migrate_v1_1(conn):
    """v1.1: 添加 description 字段"""
    try:
        conn.execute("ALTER TABLE problems ADD COLUMN description TEXT DEFAULT ''")
    except sqlite3.OperationalError as e:
        if 'duplicate column' not in str(e):
            raise


def _migrate_v1_2(conn):
    """v1.2: 添加练习模式字段"""
    try:
        conn.execute("ALTER TABLE practice_plans ADD COLUMN practice_mode TEXT DEFAULT 'free'")
    except sqlite3.OperationalError as e:
        if 'duplicate column' not in str(e):
            raise
    try:
        conn.execute("ALTER TABLE practice_plans ADD COLUMN duration INTEGER DEFAULT 0")
    except sqlite3.OperationalError as e:
        if 'duplicate column' not in str(e):
            raise


def _migrate_v1_3(conn):
    """v1.3: 比赛记录表"""
    conn.execute("""
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
    conn.execute("CREATE INDEX IF NOT EXISTS idx_contests_platform ON contests(platform)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_contests_date ON contests(contest_date)")


def _migrate_v1_4(conn):
    """v1.4: 练习状态持久化"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS practice_state (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id         INTEGER NOT NULL,
            started_at      TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            remaining_sec   INTEGER DEFAULT 0,
            last_updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (plan_id) REFERENCES practice_plans(id) ON DELETE CASCADE
        )
    """)


def _migrate_v1_5(conn):
    """v1.5: custom_topics.desc 改名 description（SQLite 3.25+ 支持 RENAME COLUMN）"""
    try:
        conn.execute("ALTER TABLE custom_topics RENAME COLUMN desc TO description")
    except sqlite3.OperationalError:
        # 列可能已改名或不存在，忽略
        pass


def _migrate_v1_6(conn):
    """v1.6: 为 mistakes 表补充外键约束和索引"""
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mistakes_problem_id ON mistakes(problem_id)")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mistakes_created_at ON mistakes(created_at)")
    except sqlite3.OperationalError:
        pass
    # 注意：SQLite 不支持通过 ALTER TABLE 添加外键约束，
    # 如需完整外键约束，需重建表（ALTER TABLE ... RENAME + CREATE + INSERT + DROP）。
    # 此处暂不处理，避免破坏现有数据。


# 迁移注册表：版本号 -> (描述, 迁移函数)
_MIGRATIONS = {
    1: ('v1.1: 添加 problems.description 字段', _migrate_v1_1),
    2: ('v1.2: 添加 practice_plans.practice_mode/duration', _migrate_v1_2),
    3: ('v1.3: 创建 contests 表', _migrate_v1_3),
    4: ('v1.4: 创建 practice_state 表', _migrate_v1_4),
    5: ('v1.5: custom_topics.desc 改名 description', _migrate_v1_5),
    6: ('v1.6: 补充 mistakes 表索引', _migrate_v1_6),
}


def _get_current_version(conn):
    """读取当前数据库架构版本，若 schema_version 表不存在则返回 0"""
    cursor = conn.execute("SELECT value FROM schema_version WHERE key='version'")
    row = cursor.fetchone()
    return int(row['value']) if row else 0


def _set_current_version(conn, version):
    """写入数据库架构版本"""
    conn.execute(
        "INSERT OR REPLACE INTO schema_version (key, value) VALUES ('version', ?)",
        (str(version),)
    )


def migrate():
    """
    数据库迁移入口——带版本追踪
    只执行尚未应用的迁移，避免重复执行
    """
    initialize_database()

    conn = get_connection()
    try:
        current_version = _get_current_version(conn)

        if current_version >= SCHEMA_VERSION:
            conn.close()
            # 启动后自动备份一次
            try:
                backup_database()
            except Exception:
                pass
            return

        # 按版本号顺序执行未应用的迁移
        for version in range(current_version + 1, SCHEMA_VERSION + 1):
            migration = _MIGRATIONS.get(version)
            if migration is None:
                print(f"[数据库] 跳过未知迁移版本 {version}")
                continue
            desc, func = migration
            print(f"[数据库] 执行迁移 {version} - {desc}")
            func(conn)
            conn.commit()

        _set_current_version(conn, SCHEMA_VERSION)
        conn.commit()
    except Exception as e:
        print(f"[数据库] 迁移失败: {e}")
        raise
    finally:
        conn.close()

    # 启动后自动备份一次
    try:
        backup_database()
    except Exception:
        pass


# ============================================================
# 数据库备份（带写锁保护）
# ============================================================

def backup_database():
    """自动备份数据库到 data/backup/ 目录，保留最近 7 份"""
    import shutil
    from datetime import datetime

    with _backup_lock:
        db_dir = os.path.dirname(DB_PATH)
        backup_dir = os.path.join(db_dir, 'backup')
        os.makedirs(backup_dir, exist_ok=True)

        now = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(backup_dir, f'info-learn_backup_{now}.db')

        try:
            # 使用 WAL 模式下的安全备份
            conn = get_connection()
            backup_conn = sqlite3.connect(backup_path)
            conn.backup(backup_conn)
            backup_conn.close()
            conn.close()
        except Exception:
            # 回退到文件复制
            try:
                shutil.copy2(DB_PATH, backup_path)
            except Exception:
                return

        # 清理旧备份，保留最近 7 份
        try:
            backups = sorted([
                os.path.join(backup_dir, f)
                for f in os.listdir(backup_dir)
                if f.startswith('info-learn_backup_') and f.endswith('.db')
            ])
            while len(backups) > 7:
                os.remove(backups.pop(0))
        except Exception:
            pass