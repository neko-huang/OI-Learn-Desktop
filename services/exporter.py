"""
数据导出服务
支持导出为 Markdown 文件，存放在程序目录下的 exports/ 文件夹
"""

import json
import os
from datetime import datetime

from config import get_app_dir


def get_export_dir() -> str:
    d = os.path.join(get_app_dir(), 'exports')
    os.makedirs(d, exist_ok=True)
    return d


def _timestamp() -> str:
    return datetime.now().strftime('%Y%m%d_%H%M%S')


def export_problems_to_md() -> str:
    """导出刷题记录为 Markdown"""
    from db.database import get_connection
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM problems ORDER BY updated_at DESC"
    ).fetchall()
    conn.close()

    if not rows:
        return None

    ts = _timestamp()
    path = os.path.join(get_export_dir(), f'刷题记录_{ts}.md')
    lines = [f'# 刷题记录导出\n\n> 导出时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n\n']

    for row in rows:
        row = dict(row)
        lines.append(f'## {row["title"]}\n\n')
        lines.append(f'- **平台**: {row["platform"]}')
        if row.get('platform_id'):
            lines.append(f'  | 编号: `{row["platform_id"]}`')
        lines.append(f'\n- **难度**: {row["difficulty"]}')
        try:
            tags = json.loads(row.get('tags') or '[]')
            if tags:
                lines.append(f'\n- **标签**: {", ".join(tags)}')
        except Exception:
            pass
        if row.get('url'):
            lines.append(f'\n- **链接**: [{row["url"]}]({row["url"]})')
        lines.append('\n')

        if row.get('description'):
            lines.append(f'### 题意\n\n{row["description"]}\n\n')
        if row.get('solution'):
            lines.append(f'### 题解\n\n{row["solution"]}\n\n')
        lines.append('\n---\n\n')

    with open(path, 'w', encoding='utf-8') as f:
        f.write(''.join(lines))
    return path


def export_templates_to_md() -> str:
    """导出模板库为 Markdown"""
    from db.database import get_connection
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM templates ORDER BY category, name"
    ).fetchall()
    conn.close()

    if not rows:
        return None

    ts = _timestamp()
    path = os.path.join(get_export_dir(), f'算法模板_{ts}.md')
    lines = [f'# 算法模板库导出\n\n> {datetime.now().strftime("%Y-%m-%d %H:%M")}\n\n']

    current_cat = ''
    for row in rows:
        row = dict(row)
        if row['category'] != current_cat:
            current_cat = row['category']
            lines.append(f'## {current_cat}\n\n')
        lines.append(f'### {row["name"]}\n\n')
        if row.get('note'):
            lines.append(f'{row["note"]}\n\n')
        lang = row.get('language', 'cpp')
        lines.append(f'```{lang}\n{row["code"]}\n```\n\n')

    with open(path, 'w', encoding='utf-8') as f:
        f.write(''.join(lines))
    return path


def export_encyclopedia_to_md() -> str:
    """导出百科为 Markdown"""
    from db.database import get_connection
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM encyclopedia ORDER BY category, title"
    ).fetchall()
    conn.close()

    if not rows:
        return None

    ts = _timestamp()
    path = os.path.join(get_export_dir(), f'算法百科_{ts}.md')
    lines = [f'# 算法百科导出\n\n> {datetime.now().strftime("%Y-%m-%d %H:%M")}\n\n']

    current_cat = ''
    for row in rows:
        row = dict(row)
        if row['category'] != current_cat:
            current_cat = row['category']
            lines.append(f'## {current_cat}\n\n')
        lines.append(f'### {row["title"]}\n\n')
        lines.append(f'{row.get("content", "")}\n\n')
        lines.append('---\n\n')

    with open(path, 'w', encoding='utf-8') as f:
        f.write(''.join(lines))
    return path


def export_mistakes_to_md() -> str:
    """导出易错集为 Markdown"""
    from db.database import get_connection
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM mistakes ORDER BY updated_at DESC"
    ).fetchall()
    conn.close()

    if not rows:
        return None

    ts = _timestamp()
    path = os.path.join(get_export_dir(), f'易错集_{ts}.md')
    lines = [f'# 易错集导出\n\n> {datetime.now().strftime("%Y-%m-%d %H:%M")}\n\n']

    for row in rows:
        row = dict(row)
        lines.append(f'## {row.get("title", "(未命名)")}\n\n')
        if row.get('reason'):
            lines.append(f'### 错误原因\n\n{row["reason"]}\n\n')
        if row.get('wrong_code'):
            lines.append(f'### 错误代码\n\n```cpp\n{row["wrong_code"]}\n```\n\n')
        if row.get('correct_code'):
            lines.append(f'### 正确代码\n\n```cpp\n{row["correct_code"]}\n```\n\n')
        lines.append('---\n\n')

    with open(path, 'w', encoding='utf-8') as f:
        f.write(''.join(lines))
    return path


def export_outline_progress_to_json() -> str:
    """导出大纲掌握度为 JSON"""
    from db.database import get_connection
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM outline_progress WHERE mastery != 'none'"
    ).fetchall()
    conn.close()

    if not rows:
        return None

    ts = _timestamp()
    path = os.path.join(get_export_dir(), f'大纲进度_{ts}.json')
    data = [{'topic_id': r['topic_id'], 'mastery': r['mastery']} for r in rows]
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path
