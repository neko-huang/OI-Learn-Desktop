"""
数据统计模块
大纲进度、刷题分布、可视化图表（纯 Canvas，无外部依赖）
"""

import json
import tkinter as tk
from tkinter import ttk

from config import Config
from db.database import get_connection
from db.seed import get_categories, get_all_topic_ids


class StatsModule:

    def __init__(self, app, parent_frame):
        self.app = app
        self.config = Config()
        self.parent = parent_frame
        for w in parent_frame.winfo_children():
            w.destroy()

        self._build_ui()
        self._refresh()

    # ============================================================
    # UI
    # ============================================================

    def _build_ui(self):
        colors = self.config.get_colors()

        # 可滚动内容区
        canvas = tk.Canvas(self.parent, bg=colors['bg_main'], highlightthickness=0)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(self.parent, orient=tk.VERTICAL, command=canvas.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.configure(yscrollcommand=scroll.set)

        self.inner = tk.Frame(canvas, bg=colors['bg_main'])
        self._canvas_win = canvas.create_window((0, 0), window=self.inner, anchor=tk.NW)
        canvas.bind('<Configure>', lambda e: canvas.itemconfig(self._canvas_win, width=e.width))
        self.inner.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))

        # 标题
        tk.Label(self.inner, text='学习统计', font=(self.config.get('font_family'), 20, 'bold'),
                 bg=colors['bg_main'], fg=colors['fg_primary']
                 ).pack(anchor=tk.W, padx=20, pady=(16, 8))

        # 概览卡片行
        cards = tk.Frame(self.inner, bg=colors['bg_main'])
        cards.pack(fill=tk.X, padx=16, pady=(0, 12))

        self.card1 = self._make_card(cards, '大纲进度', '0/0')
        self.card2 = self._make_card(cards, '刷题总数', '0')
        self.card3 = self._make_card(cards, '已掌握算法', '0')
        self.card4 = self._make_card(cards, '易错记录', '0')

        # 图表区域
        self.charts_frame = tk.Frame(self.inner, bg=colors['bg_main'])
        self.charts_frame.pack(fill=tk.BOTH, expand=True, padx=16)

    def _make_card(self, parent, title, value):
        colors = self.config.get_colors()
        card = tk.Frame(parent, bg=colors['bg_card'], 
                         highlightbackground=colors['border_card'],
                         highlightthickness=1,
                         width=200, height=90)
        card.pack(side=tk.LEFT, padx=(0, 10), pady=4)
        card.pack_propagate(False)
        tk.Label(card, text=title, font=(self.config.get('font_family'), 10),
                 bg=colors['bg_card'], fg=colors['fg_secondary']
                 ).pack(anchor=tk.W, padx=14, pady=(14, 0))
        label = tk.Label(card, text=value, font=(self.config.get('font_family'), 26, 'bold'),
                          bg=colors['bg_card'], fg=colors['fg_accent'])
        label.pack(anchor=tk.W, padx=14, pady=(2, 0))
        return label

    def _refresh(self):
        self._refresh_cards()
        self._draw_charts()

    def _refresh_cards(self):
        try:
            conn = get_connection()
            try:
                # 大纲进度
                all_topics = get_all_topic_ids()
                total = len(all_topics)
                rows = conn.execute("SELECT COUNT(*) as c FROM outline_progress WHERE mastery != 'none'").fetchone()
                mastered = rows['c'] if rows else 0
                self.card1.config(text=f'{mastered}/{total}')

                # 刷题总数
                rows = conn.execute("SELECT COUNT(*) as c FROM problems").fetchone()
                self.card2.config(text=str(rows['c'] if rows else 0))

                # 已掌握
                rows = conn.execute("SELECT COUNT(*) as c FROM outline_progress WHERE mastery = 'mastered'").fetchone()
                self.card3.config(text=str(rows['c'] if rows else 0))

                # 易错记录
                rows = conn.execute("SELECT COUNT(*) as c FROM mistakes").fetchone()
                self.card4.config(text=str(rows['c'] if rows else 0))
            finally:
                conn.close()
        except Exception as e:
            self.app.set_status(f'数据加载失败: {e}')

    # ============================================================
    # 图表绘制
    # ============================================================

    def _draw_charts(self):
        for w in self.charts_frame.winfo_children():
            w.destroy()
        colors = self.config.get_colors()

        # 左半：大纲进度柱状图
        left = tk.Frame(self.charts_frame, bg=colors['bg_main'])
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        self._draw_outline_bars(left)

        # 右半：刷题难度分布 + 状态分布
        right = tk.Frame(self.charts_frame, bg=colors['bg_main'])
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))

        self._draw_problem_stats(right)

    def _draw_outline_bars(self, parent):
        colors = self.config.get_colors()

        tk.Label(parent, text='大纲掌握度（按大类）', font=(self.config.get('font_family'), 14, 'bold'),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(anchor=tk.W, pady=(0, 8))

        # 计算各大类掌握度
        cats = get_categories()
        try:
            conn = get_connection()
            try:
                rows = conn.execute("SELECT topic_id, mastery FROM outline_progress WHERE mastery != 'none'").fetchall()
                progress = {r['topic_id']: r['mastery'] for r in rows}
            finally:
                conn.close()
        except Exception as e:
            self.app.set_status(f'大纲数据加载失败: {e}')
            progress = {}

        all_topics = get_all_topic_ids()
        cat_data = {}
        for t in all_topics:
            cid = t['category_name']
            if cid not in cat_data:
                cat_data[cid] = {'total': 0, 'done': 0, 'mastered': 0}
            cat_data[cid]['total'] += 1
            m = progress.get(t['topic_id'], 'none')
            if m != 'none':
                cat_data[cid]['done'] += 1
            if m == 'mastered':
                cat_data[cid]['mastered'] += 1

        # 取前 10 个最多的
        sorted_cats = sorted(cat_data.items(), key=lambda x: x[1]['total'], reverse=True)[:10]

        canvas_w = 500
        bar_h = 24

        canvas = tk.Canvas(parent, bg=colors['bg_main'], height=len(sorted_cats) * (bar_h + 8) + 20,
                           highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)

        if not sorted_cats:
            canvas.create_text(canvas_w / 2, 20, text='暂无数据',
                               font=(self.config.get('font_family'), 10),
                               fill=colors['fg_muted'])
            return

        for i, (name, data) in enumerate(sorted_cats):
            y = i * (bar_h + 8) + 5
            label_w = 90
            bar_max_w = canvas_w - label_w - 60

            # 标签
            canvas.create_text(5, y + bar_h / 2, text=name[:6], anchor=tk.W,
                               font=(self.config.get('font_family'), 10),
                               fill=colors['fg_primary'])

            # 背景条
            canvas.create_rectangle(label_w, y, label_w + bar_max_w, y + bar_h,
                                     fill=colors['bg_sidebar'], outline='')

            # 已学条
            if data['done'] > 0:
                done_w = int(bar_max_w * data['done'] / data['total'])
                canvas.create_rectangle(label_w, y, label_w + done_w, y + bar_h,
                                         fill=colors['fg_accent'], outline='')

            # 数值标签（在柱子右端显示）
            pct = int(data['done'] / data['total'] * 100) if data['total'] > 0 else 0
            canvas.create_text(label_w + bar_max_w + 8, y + bar_h / 2,
                               text=f'{data["done"]}/{data["total"]} ({pct}%)', anchor=tk.W,
                               font=(self.config.get('font_family'), 9),
                               fill=colors['fg_secondary'])

    def _draw_problem_stats(self, parent):
        colors = self.config.get_colors()

        tk.Label(parent, text='刷题分布', font=(self.config.get('font_family'), 14, 'bold'),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(anchor=tk.W, pady=(0, 8))

        try:
            conn = get_connection()
            try:
                diff_rows = conn.execute(
                    "SELECT difficulty, COUNT(*) as c FROM problems WHERE difficulty != '' GROUP BY difficulty ORDER BY c DESC"
                ).fetchall()
                status_rows = conn.execute(
                    "SELECT status, COUNT(*) as c FROM problems GROUP BY status"
                ).fetchall()
            finally:
                conn.close()
        except Exception as e:
            self.app.set_status(f'刷题数据加载失败: {e}')
            diff_rows = []
            status_rows = []

        # 难度分布
        tk.Label(parent, text='按难度', font=(self.config.get('font_family'), 11, 'bold'),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(anchor=tk.W, pady=(8, 4))

        total_problems = sum(r['c'] for r in diff_rows) if diff_rows else 1
        bar_colors = ['#534AB7', '#7F77DD', '#AFA9EC', '#CECBF6', '#EEEDFE',
                       '#E1F5EE', '#9FE1CB', '#5DCAA5']

        canvas = tk.Canvas(parent, bg=colors['bg_main'],
                           height=min(len(diff_rows), 10) * 28 + 20,
                           highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)

        if not diff_rows:
            canvas.create_text(150, 20, text='暂无数据',
                               font=(self.config.get('font_family'), 10),
                               fill=colors['fg_muted'])

        for i, row in enumerate(diff_rows[:8]):
            y = i * 28 + 5
            pct = row['c'] / total_problems * 100
            bar_w = int(300 * pct / 100)

            # 标签
            diff_label = row['difficulty'][:8] if row['difficulty'] else '未评定'
            canvas.create_text(5, y + 12, text=diff_label, anchor=tk.W,
                               font=(self.config.get('font_family'), 9),
                               fill=colors['fg_primary'])

            # 条
            if bar_w > 0:
                canvas.create_rectangle(95, y + 3, 95 + bar_w, y + 21,
                                         fill=bar_colors[i % len(bar_colors)], outline='')

            canvas.create_text(100 + bar_w, y + 12, text=f'{row["c"]}题 ({pct:.0f}%)',
                               anchor=tk.W, font=(self.config.get('font_family'), 9),
                               fill=colors['fg_secondary'])

        # 状态分布
        tk.Label(parent, text='按状态', font=(self.config.get('font_family'), 11, 'bold'),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(anchor=tk.W, pady=(16, 4))

        status_names = {'todo': '待做', 'done': '已做', 'review': '复习'}
        status_colors = {'todo': '#888', 'done': '#3B6D11', 'review': '#185FA5'}

        status_fr = tk.Frame(parent, bg=colors['bg_main'])
        status_fr.pack(fill=tk.X, pady=(0, 8))
        for row in status_rows:
            name = status_names.get(row['status'], row['status'])
            color = status_colors.get(row['status'], '#888')
            tk.Label(status_fr, text=f'  {name}: {row["c"]} 题  ',
                     font=(self.config.get('font_family'), 10, 'bold'),
                     bg=colors['bg_main'], fg=color).pack(side=tk.LEFT, padx=4)

    def apply_theme(self):
        for w in self.parent.winfo_children():
            w.destroy()
        self._build_ui()
        self._refresh()
