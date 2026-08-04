"""
比赛记录与复盘模块
- 左侧：比赛列表（按日期倒序）
- 右侧：比赛详情 + 复盘笔记
- 支持手动录入和从 CF/AtCoder 导入
"""

import json
import re
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timezone

from config import Config
from db.database import get_connection
from components.markdown_view import MarkdownView

PLATFORMS = ['Codeforces', 'AtCoder', '洛谷', '其他']


class ContestModule:

    def __init__(self, app, parent_frame):
        self.app = app
        self.config = Config()
        self.parent = parent_frame
        for w in parent_frame.winfo_children():
            w.destroy()

        self._current_id = None
        self._mode = 'view'
        self._dirty = False
        self._search_after_id = None
        self._build_ui()
        self._refresh_list()

    # ============================================================
    # UI 框架
    # ============================================================

    def _build_ui(self):
        colors = self.config.get_colors()

        # 顶部栏
        top = tk.Frame(self.parent, bg=colors['bg_sidebar'], height=42)
        top.pack(fill=tk.X)
        top.pack_propagate(False)

        tk.Label(top, text='比赛记录', font=(self.config.get('font_family'), 12, 'bold'),
                 bg=colors['bg_sidebar'], fg=colors['fg_primary']).pack(side=tk.LEFT, padx=12)

        tk.Frame(top, bg=colors['bg_sidebar']).pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Button(top, text='+ 手动录入', font=(self.config.get('font_family'), 10),
                  bg=colors['fg_accent'], fg='#ffffff', relief=tk.FLAT,
                  padx=12, pady=4, cursor='hand2',
                  command=self._start_add).pack(side=tk.RIGHT, padx=4, pady=8)
        tk.Button(top, text='从 CF 导入', font=(self.config.get('font_family'), 10),
                  bg=colors['bg_sidebar'], fg=colors['fg_accent'], relief=tk.FLAT,
                  padx=12, pady=4, cursor='hand2',
                  command=self._import_cf).pack(side=tk.RIGHT, padx=4, pady=8)
        tk.Button(top, text='从 AtCoder 导入', font=(self.config.get('font_family'), 10),
                  bg=colors['bg_sidebar'], fg=colors['fg_accent'], relief=tk.FLAT,
                  padx=12, pady=4, cursor='hand2',
                  command=self._import_atcoder).pack(side=tk.RIGHT, padx=4, pady=8)

        # 主区域
        main = tk.Frame(self.parent, bg=colors['bg_main'])
        main.pack(fill=tk.BOTH, expand=True)

        self._build_left(main)
        self._build_right(main)

    # ============================================================
    # 左侧列表
    # ============================================================

    def _build_left(self, parent):
        colors = self.config.get_colors()
        left = tk.Frame(parent, bg=colors['bg_sidebar'], width=300)
        left.pack(side=tk.LEFT, fill=tk.Y)
        left.pack_propagate(False)

        # 搜索/筛选
        search_frame = tk.Frame(left, bg=colors['bg_sidebar'])
        search_frame.pack(fill=tk.X, padx=8, pady=(6, 4))

        self.search_var = tk.StringVar()
        self._search_after_id = None
        def _debounced_refresh(*args):
            if self._search_after_id:
                self.parent.after_cancel(self._search_after_id)
            self._search_after_id = self.parent.after(250, self._refresh_list)
        self.search_var.trace_add('write', _debounced_refresh)
        tk.Entry(search_frame, textvariable=self.search_var,
                 font=(self.config.get('font_family'), 10),
                 bg=colors['bg_input'], fg=colors['fg_primary'],
                 relief=tk.FLAT).pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=2)

        # 平台筛选
        self.filter_platform = tk.StringVar(value='全部')
        ttk.Combobox(search_frame, textvariable=self.filter_platform,
                      values=['全部'] + PLATFORMS, state='readonly', width=10
                      ).pack(side=tk.RIGHT, padx=(4, 0))
        self.filter_platform.trace_add('write', lambda *a: self._refresh_list())

        # 列表
        self.listbox = tk.Listbox(left, font=(self.config.get('font_family'), 10),
                                   bg=colors['bg_input'], fg=colors['fg_primary'],
                                   selectbackground=colors['fg_accent'], selectforeground='#ffffff',
                                   relief=tk.FLAT, activestyle='none')
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=(0, 8))
        self.listbox.bind('<<ListboxSelect>>', self._on_select)

        sb = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.listbox.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y, pady=(0, 8), padx=(0, 8))
        self.listbox.configure(yscrollcommand=sb.set)

    def _refresh_list(self):
        self.listbox.delete(0, tk.END)
        self._contest_ids = []

        search = self.search_var.get().lower().strip()
        pf = self.filter_platform.get()

        try:
            conn = get_connection()
            query = "SELECT id, contest_name, platform, contest_date, rating_change, rank, solved_count, total_problems FROM contests WHERE 1=1"
            params = []
            if search:
                query += " AND (LOWER(contest_name) LIKE ? OR LOWER(contest_id) LIKE ?)"
                kw = f'%{search}%'
                params.extend([kw, kw])
            if pf != '全部':
                query += " AND platform = ?"
                params.append(pf)
            query += " ORDER BY contest_date DESC, id DESC"
            rows = conn.execute(query, params).fetchall()
            conn.close()
        except Exception:
            rows = []

        colors = self.config.get_colors()
        for row in rows:
            self._contest_ids.append(row['id'])
            date = row['contest_date'][:10] if row['contest_date'] else '??'
            rc = row['rating_change'] or 0
            rc_str = f' ({rc:+d})' if rc != 0 else ''
            solved = f' {row["solved_count"]}/{row["total_problems"]}' if row['total_problems'] else ''
            text = f'[{date}] {row["contest_name"][:25]}{rc_str}{solved}'
            self.listbox.insert(tk.END, text)

    # ============================================================
    # 右侧面板
    # ============================================================

    def _build_right(self, parent):
        colors = self.config.get_colors()
        self.right = tk.Frame(parent, bg=colors['bg_main'])
        self.right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 空状态
        self.empty_frame = tk.Frame(self.right, bg=colors['bg_main'])
        tk.Label(self.empty_frame, text='选择一场比赛查看详情\n或点击「+ 手动录入」添加记录',
                 font=(self.config.get('font_family'), 14),
                 bg=colors['bg_main'], fg=colors['fg_muted']
                 ).place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # 查看模式
        self.view_frame = tk.Frame(self.right, bg=colors['bg_main'])
        self._build_view_mode()

        # 编辑模式
        self.edit_frame = tk.Frame(self.right, bg=colors['bg_main'])
        self._build_edit_mode()

        self._show_frame('empty')

    def _show_frame(self, name):
        self._mode = name
        for n in ('view', 'edit', 'empty'):
            if hasattr(self, f'{n}_frame'):
                getattr(self, f'{n}_frame').pack_forget()
        f = getattr(self, f'{name}_frame')
        f.pack(fill=tk.BOTH, expand=True)

    # ============================================================
    # 查看模式
    # ============================================================

    def _build_view_mode(self):
        colors = self.config.get_colors()

        # 顶部元信息
        meta_bar = tk.Frame(self.view_frame, bg=colors['bg_sidebar'])
        meta_bar.pack(fill=tk.X, pady=(0, 4))

        self.view_rating_change = tk.Label(meta_bar, text='',
                                           font=(self.config.get('font_family'), 14, 'bold'),
                                           bg=colors['bg_sidebar'])
        self.view_rating_change.pack(side=tk.RIGHT, padx=16, pady=8)

        self.view_title = tk.Label(self.view_frame, text='',
                                    font=(self.config.get('font_family'), 18, 'bold'),
                                    bg=colors['bg_main'], fg=colors['fg_primary'], anchor=tk.W)
        self.view_title.pack(fill=tk.X, padx=20, pady=(16, 4))

        # 元信息行
        meta = tk.Frame(self.view_frame, bg=colors['bg_main'])
        meta.pack(fill=tk.X, padx=20, pady=(0, 8))

        self.view_meta = tk.Label(meta, text='', font=(self.config.get('font_family'), 10),
                                   bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.W,
                                   wraplength=600, justify=tk.LEFT)
        self.view_meta.pack(side=tk.LEFT)

        # 统计卡片行
        stats_row = tk.Frame(self.view_frame, bg=colors['bg_main'])
        stats_row.pack(fill=tk.X, padx=16, pady=(4, 8))

        self.stat_rank = self._make_stat_card(stats_row, '排名', '-')
        self.stat_solved = self._make_stat_card(stats_row, '通过', '-')
        self.stat_rating = self._make_stat_card(stats_row, 'Rating', '-')
        self.stat_perf = self._make_stat_card(stats_row, '表现分', '-')

        # 复盘笔记
        review_label = tk.Label(self.view_frame, text='复盘笔记', font=(self.config.get('font_family'), 12, 'bold'),
                                 bg=colors['bg_main'], fg=colors['fg_primary'], anchor=tk.W)
        review_label.pack(fill=tk.X, padx=20, pady=(8, 0))

        self.view_md = MarkdownView(self.view_frame)
        self.view_md.pack(fill=tk.BOTH, expand=True, padx=20, pady=(4, 4))

        # 底部操作栏
        bar = tk.Frame(self.view_frame, bg=colors['bg_sidebar'], height=40)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        bar.pack_propagate(False)
        tk.Button(bar, text='删除', font=(self.config.get('font_family'), 10),
                  bg=colors['bg_sidebar'], fg=colors['danger'], relief=tk.FLAT,
                  padx=12, pady=4, cursor='hand2',
                  command=self._delete_current).pack(side=tk.RIGHT, padx=8)
        tk.Button(bar, text='编辑复盘', font=(self.config.get('font_family'), 10),
                  bg=colors['fg_accent'], fg='#ffffff', relief=tk.FLAT,
                  padx=16, pady=4, cursor='hand2',
                  command=lambda: self._edit_contest(self._current_id)).pack(side=tk.RIGHT, padx=4)

    def _make_stat_card(self, parent, label, value):
        colors = self.config.get_colors()
        card = tk.Frame(parent, bg=colors['bg_card'],
                         relief=tk.RIDGE, bd=1, highlightthickness=0,
                         width=150, height=70)
        card.pack(side=tk.LEFT, padx=(0, 8))
        card.pack_propagate(False)

        tk.Label(card, text=label, font=(self.config.get('font_family'), 9),
                 bg=colors['bg_card'], fg=colors['fg_muted']
                 ).pack(anchor=tk.W, padx=12, pady=(8, 0))
        val_label = tk.Label(card, text=value, font=(self.config.get('font_family'), 18, 'bold'),
                              bg=colors['bg_card'], fg=colors['fg_accent'])
        val_label.pack(anchor=tk.W, padx=12, pady=(0, 4))
        return val_label

    def _load_view(self):
        if not self._current_id:
            return
        try:
            conn = get_connection()
            row = conn.execute("SELECT * FROM contests WHERE id=?", (self._current_id,)).fetchone()
            conn.close()
            if not row:
                return
            row = dict(row)

            self.view_title.config(text=row['contest_name'] or '未命名比赛')

            # Rating变化
            rc = row.get('rating_change', 0) or 0
            if rc > 0:
                self.view_rating_change.config(text=f'+{rc}', fg=self.config.get_colors()['success'])
            elif rc < 0:
                self.view_rating_change.config(text=f'{rc}', fg=self.config.get_colors()['danger'])
            else:
                self.view_rating_change.config(text=f'{rc}', fg=self.config.get_colors()['fg_muted'])

            # 元信息
            parts = [f'平台: {row["platform"]}']
            if row.get('contest_id'):
                parts.append(f'编号: {row["contest_id"]}')
            if row.get('contest_date'):
                parts.append(f'日期: {row["contest_date"][:10]}')
            if row.get('contest_type'):
                parts.append(f'类型: {row["contest_type"]}')
            if row.get('duration_min'):
                parts.append(f'时长: {row["duration_min"]}min')
            self.view_meta.config(text='  |  '.join(parts))

            # 统计卡片
            rank = row.get('rank', 0) or 0
            total = row.get('total_participants', 0) or 0
            if total > 0:
                pct = rank / total * 100
                self.stat_rank.config(text=f'{rank}/{total} (top {pct:.1f}%)')
            else:
                self.stat_rank.config(text=str(rank) if rank else '-')

            sc = row.get('solved_count', 0) or 0
            tp = row.get('total_problems', 0) or 0
            self.stat_solved.config(text=f'{sc}/{tp}' if tp else str(sc))

            rb = row.get('rating_before', 0) or 0
            ra = row.get('rating_after', 0) or 0
            self.stat_rating.config(text=f'{rb} → {ra}' if ra else str(rb))

            perf = row.get('performance', 0) or 0
            self.stat_perf.config(text=str(perf) if perf else '-')

            # 复盘笔记
            review = row.get('review', '') or ''
            if review:
                self.view_md.render(review)
            else:
                self.view_md.render('*暂无复盘笔记*')

        except Exception as e:
            self.app.set_status(f'加载失败: {e}')

    # ============================================================
    # 编辑/录入模式
    # ============================================================

    def _build_edit_mode(self):
        colors = self.config.get_colors()
        pad = 20

        # 提示
        self.edit_hint = tk.Label(self.edit_frame, text='',
                                   font=(self.config.get('font_family'), 9),
                                   bg=colors['bg_main'], fg=colors['fg_muted'], anchor=tk.W,
                                   padx=pad)
        self.edit_hint.pack(fill=tk.X, pady=(8, 0))

        # 第一行：平台 + 比赛编号
        row1 = tk.Frame(self.edit_frame, bg=colors['bg_main'])
        row1.pack(fill=tk.X, padx=pad, pady=(8, 0))

        left1 = tk.Frame(row1, bg=colors['bg_main'])
        left1.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 16))

        tk.Label(left1, text='平台 *', font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(anchor=tk.W)
        self.e_platform = ttk.Combobox(left1, values=PLATFORMS, state='readonly')
        self.e_platform.set('Codeforces')
        self.e_platform.pack(fill=tk.X, pady=(2, 0), ipady=2)

        right1 = tk.Frame(row1, bg=colors['bg_main'])
        right1.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(right1, text='比赛编号', font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(anchor=tk.W)
        self.e_contest_id = tk.Entry(right1, font=(self.config.get('font_family'), 12),
                                      bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT)
        self.e_contest_id.pack(fill=tk.X, pady=(2, 0), ipady=4)

        # 第二行：比赛名称 + 类型
        row2 = tk.Frame(self.edit_frame, bg=colors['bg_main'])
        row2.pack(fill=tk.X, padx=pad, pady=(12, 0))

        left2 = tk.Frame(row2, bg=colors['bg_main'])
        left2.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 16))

        tk.Label(left2, text='比赛名称 *', font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(anchor=tk.W)
        self.e_name = tk.Entry(left2, font=(self.config.get('font_family'), 12),
                                bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT)
        self.e_name.pack(fill=tk.X, pady=(2, 0), ipady=4)

        right2 = tk.Frame(row2, bg=colors['bg_main'])
        right2.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(right2, text='类型', font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(anchor=tk.W)
        self.e_type = ttk.Combobox(right2, values=['rated', 'unrated', 'virtual'], state='readonly')
        self.e_type.set('rated')
        self.e_type.pack(fill=tk.X, pady=(2, 0), ipady=2)

        # 第三行：日期 + 时长
        row3 = tk.Frame(self.edit_frame, bg=colors['bg_main'])
        row3.pack(fill=tk.X, padx=pad, pady=(12, 0))

        left3 = tk.Frame(row3, bg=colors['bg_main'])
        left3.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 16))

        tk.Label(left3, text='比赛日期', font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(anchor=tk.W)
        self.e_date = tk.Entry(left3, font=(self.config.get('font_family'), 12),
                                bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT)
        self.e_date.pack(fill=tk.X, pady=(2, 0), ipady=4)
        self.e_date.insert(0, 'YYYY-MM-DD')

        right3 = tk.Frame(row3, bg=colors['bg_main'])
        right3.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(right3, text='时长(分钟)', font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(anchor=tk.W)
        self.e_duration = tk.Entry(right3, font=(self.config.get('font_family'), 12),
                                    bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT)
        self.e_duration.pack(fill=tk.X, pady=(2, 0), ipady=4)

        # 第四行：排名 + 参赛人数
        row4 = tk.Frame(self.edit_frame, bg=colors['bg_main'])
        row4.pack(fill=tk.X, padx=pad, pady=(12, 0))

        left4 = tk.Frame(row4, bg=colors['bg_main'])
        left4.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 16))

        tk.Label(left4, text='排名', font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(anchor=tk.W)
        self.e_rank = tk.Entry(left4, font=(self.config.get('font_family'), 12),
                                bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT)
        self.e_rank.pack(fill=tk.X, pady=(2, 0), ipady=4)

        right4 = tk.Frame(row4, bg=colors['bg_main'])
        right4.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(right4, text='参赛人数', font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(anchor=tk.W)
        self.e_total = tk.Entry(right4, font=(self.config.get('font_family'), 12),
                                 bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT)
        self.e_total.pack(fill=tk.X, pady=(2, 0), ipady=4)

        # 第五行：Rating + 题数
        row5 = tk.Frame(self.edit_frame, bg=colors['bg_main'])
        row5.pack(fill=tk.X, padx=pad, pady=(12, 0))

        left5 = tk.Frame(row5, bg=colors['bg_main'])
        left5.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 16))

        tk.Label(left5, text='Rating (赛前)', font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(anchor=tk.W)
        self.e_rating_before = tk.Entry(left5, font=(self.config.get('font_family'), 12),
                                         bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT)
        self.e_rating_before.pack(fill=tk.X, pady=(2, 0), ipady=4)

        mid5 = tk.Frame(row5, bg=colors['bg_main'])
        mid5.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 16))

        tk.Label(mid5, text='Rating (赛后)', font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(anchor=tk.W)
        self.e_rating_after = tk.Entry(mid5, font=(self.config.get('font_family'), 12),
                                        bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT)
        self.e_rating_after.pack(fill=tk.X, pady=(2, 0), ipady=4)

        right5 = tk.Frame(row5, bg=colors['bg_main'])
        right5.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(right5, text='表现分', font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(anchor=tk.W)
        self.e_perf = tk.Entry(right5, font=(self.config.get('font_family'), 12),
                                bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT)
        self.e_perf.pack(fill=tk.X, pady=(2, 0), ipady=4)

        # 第六行：通过/总题数
        row6 = tk.Frame(self.edit_frame, bg=colors['bg_main'])
        row6.pack(fill=tk.X, padx=pad, pady=(12, 0))

        left6 = tk.Frame(row6, bg=colors['bg_main'])
        left6.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 16))

        tk.Label(left6, text='通过题数', font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(anchor=tk.W)
        self.e_solved = tk.Entry(left6, font=(self.config.get('font_family'), 12),
                                  bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT)
        self.e_solved.pack(fill=tk.X, pady=(2, 0), ipady=4)

        right6 = tk.Frame(row6, bg=colors['bg_main'])
        right6.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(right6, text='总题数', font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(anchor=tk.W)
        self.e_total_problems = tk.Entry(right6, font=(self.config.get('font_family'), 12),
                                          bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT)
        self.e_total_problems.pack(fill=tk.X, pady=(2, 0), ipady=4)

        # 复盘笔记
        tk.Label(self.edit_frame, text='复盘笔记（Markdown）',
                 font=(self.config.get('font_family'), 11, 'bold'),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(anchor=tk.W, padx=pad, pady=(12, 4))
        self.e_review = tk.Text(self.edit_frame, font=(self.config.get('font_family'), 11),
                                 bg=colors['bg_input'], fg=colors['fg_primary'],
                                 relief=tk.FLAT, wrap=tk.WORD, height=8)
        self.e_review.pack(fill=tk.BOTH, expand=True, padx=pad, pady=(0, 4))

        # 底部按钮
        bar = tk.Frame(self.edit_frame, bg=colors['bg_sidebar'], height=40)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        bar.pack_propagate(False)
        tk.Button(bar, text='取消', font=(self.config.get('font_family'), 10),
                  bg=colors['bg_sidebar'], fg=colors['fg_primary'], relief=tk.FLAT,
                  padx=16, pady=4, cursor='hand2',
                  command=self._cancel_edit).pack(side=tk.RIGHT, padx=8)
        tk.Button(bar, text='保存', font=(self.config.get('font_family'), 11, 'bold'),
                  bg=colors['fg_accent'], fg='#ffffff', relief=tk.FLAT,
                  padx=20, pady=4, cursor='hand2',
                  command=self._save_contest).pack(side=tk.RIGHT, padx=4)

        # 编辑字段变化时标记 dirty
        for w in [self.e_contest_id, self.e_name, self.e_date, self.e_duration,
                  self.e_rank, self.e_total, self.e_rating_before, self.e_rating_after,
                  self.e_perf, self.e_solved, self.e_total_problems]:
            w.bind('<KeyRelease>', self._mark_dirty)
        self.e_review.bind('<KeyRelease>', self._mark_dirty)
        self.e_platform.bind('<<ComboboxSelected>>', self._mark_dirty)
        self.e_type.bind('<<ComboboxSelected>>', self._mark_dirty)

    # ============================================================
    # 表单操作
    # ============================================================

    def _clear_form(self):
        self.e_contest_id.delete(0, tk.END)
        self.e_name.delete(0, tk.END)
        self.e_date.delete(0, tk.END)
        self.e_date.insert(0, 'YYYY-MM-DD')
        self.e_duration.delete(0, tk.END)
        self.e_rank.delete(0, tk.END)
        self.e_total.delete(0, tk.END)
        self.e_rating_before.delete(0, tk.END)
        self.e_rating_after.delete(0, tk.END)
        self.e_perf.delete(0, tk.END)
        self.e_solved.delete(0, tk.END)
        self.e_total_problems.delete(0, tk.END)
        self.e_review.delete('1.0', tk.END)
        try:
            self.e_platform.set('Codeforces')
            self.e_type.set('rated')
        except Exception:
            pass

    def _fill_form(self, row):
        self._clear_form()
        self.e_contest_id.insert(0, row.get('contest_id', ''))
        self.e_name.insert(0, row.get('contest_name', ''))
        self.e_date.delete(0, tk.END)
        self.e_date.insert(0, (row.get('contest_date', '') or '')[:10])
        if row.get('duration_min'):
            self.e_duration.insert(0, str(row['duration_min']))
        if row.get('rank'):
            self.e_rank.insert(0, str(row['rank']))
        if row.get('total_participants'):
            self.e_total.insert(0, str(row['total_participants']))
        if row.get('rating_before'):
            self.e_rating_before.insert(0, str(row['rating_before']))
        if row.get('rating_after'):
            self.e_rating_after.insert(0, str(row['rating_after']))
        if row.get('performance'):
            self.e_perf.insert(0, str(row['performance']))
        if row.get('solved_count'):
            self.e_solved.insert(0, str(row['solved_count']))
        if row.get('total_problems'):
            self.e_total_problems.insert(0, str(row['total_problems']))
        try:
            platform = row.get('platform', 'Codeforces')
            self.e_platform.set(platform if platform in PLATFORMS else '其他')
        except Exception:
            pass
        try:
            self.e_type.set(row.get('contest_type', 'rated'))
        except Exception:
            pass
        self.e_review.insert('1.0', row.get('review', ''))

    # ============================================================
    # 交互
    # ============================================================

    def _on_select(self, event):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx < len(self._contest_ids):
            if self._mode == 'edit' and self._dirty:
                self._save_contest()
            self._current_id = self._contest_ids[idx]
            self._show_frame('view')
            self._load_view()

    def _start_add(self):
        self._current_id = None
        self._clear_form()
        self.edit_hint.config(text='录入完成后点击保存')
        self._show_frame('edit')

    def _edit_contest(self, contest_id):
        self._current_id = contest_id
        try:
            conn = get_connection()
            row = conn.execute("SELECT * FROM contests WHERE id=?", (contest_id,)).fetchone()
            conn.close()
            if row:
                self._fill_form(dict(row))
                self.edit_hint.config(text='编辑完成后点击保存')
                self._show_frame('edit')
        except Exception as e:
            self.app.set_status(f'加载失败: {e}')

    def _cancel_edit(self):
        if self._current_id:
            self._show_frame('view')
            self._load_view()
        else:
            self._show_frame('empty')

    def _save_contest(self):
        name = self.e_name.get().strip()
        if not name:
            messagebox.showwarning('提示', '请输入比赛名称')
            return

        try:
            platform = self.e_platform.get()
            contest_id = self.e_contest_id.get().strip()
            contest_type = self.e_type.get()
            date = self.e_date.get().strip()
            if date == 'YYYY-MM-DD' or not date:
                date = ''
            dur = self._int_or_zero(self.e_duration.get())
            rank = self._int_or_zero(self.e_rank.get())
            total = self._int_or_zero(self.e_total.get())
            rating_before = self._int_or_zero(self.e_rating_before.get())
            rating_after = self._int_or_zero(self.e_rating_after.get())
            perf = self._int_or_zero(self.e_perf.get())
            solved = self._int_or_zero(self.e_solved.get())
            total_problems = self._int_or_zero(self.e_total_problems.get())
            review = self.e_review.get('1.0', tk.END).strip()
            rating_change = rating_after - rating_before if rating_after and rating_before else 0

            conn = get_connection()
            if self._current_id:
                conn.execute(
                    """UPDATE contests SET platform=?, contest_id=?, contest_name=?, contest_type=?,
                       contest_date=?, duration_min=?, rank=?, total_participants=?,
                       rating_before=?, rating_after=?, rating_change=?,
                       solved_count=?, total_problems=?, performance=?, review=?,
                       updated_at=datetime('now','localtime') WHERE id=?""",
                    (platform, contest_id, name, contest_type, date, dur, rank, total,
                     rating_before, rating_after, rating_change, solved, total_problems,
                     perf, review, self._current_id))
            else:
                cursor = conn.execute(
                    """INSERT INTO contests (platform, contest_id, contest_name, contest_type,
                       contest_date, duration_min, rank, total_participants,
                       rating_before, rating_after, rating_change, solved_count,
                       total_problems, performance, review)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (platform, contest_id, name, contest_type, date, dur, rank, total,
                     rating_before, rating_after, rating_change, solved, total_problems,
                     perf, review))
                self._current_id = cursor.lastrowid
            conn.commit()
            conn.close()

            self._refresh_list()
            self._show_frame('view')
            self._load_view()
            self.app.set_status(f'比赛「{name}」已保存')
        except Exception as e:
            self.app.set_status(f'保存失败: {e}')

    def _int_or_zero(self, val):
        try:
            return int(val)
        except (ValueError, TypeError):
            return 0

    def _mark_dirty(self, event=None):
        self._dirty = True

    # ============================================================
    # 导入 CF/AtCoder
    # ============================================================

    def _import_cf(self):
        """从 Codeforces API 导入用户比赛记录"""
        dialog = tk.Toplevel(self.parent)
        dialog.title('从 Codeforces 导入')
        dialog.geometry('400x200')
        dialog.transient(self.parent)
        colors = self.config.get_colors()
        dialog.configure(bg=colors['bg_main'])

        tk.Label(dialog, text='输入 Codeforces 用户名', font=(self.config.get('font_family'), 13, 'bold'),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(pady=(16, 8))

        handle_var = tk.StringVar()
        tk.Entry(dialog, textvariable=handle_var, font=(self.config.get('font_family'), 14),
                 bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT,
                 justify=tk.CENTER).pack(fill=tk.X, padx=30, pady=4, ipady=4)

        status_label = tk.Label(dialog, text='', font=(self.config.get('font_family'), 10),
                                 bg=colors['bg_main'], fg=colors['fg_muted'])
        status_label.pack(pady=4)

        def _do_import():
            handle = handle_var.get().strip()
            if not handle:
                return
            status_label.config(text='正在获取...')
            dialog.update()

            def _fetch():
                try:
                    import requests
                    resp = requests.get(
                        f'https://codeforces.com/api/user.rating?handle={handle}',
                        timeout=15
                    )
                    data = resp.json()
                    if data.get('status') != 'OK':
                        self.parent.after(0, lambda: status_label.config(text=f'API 错误: {data.get("comment", "未知")}'))
                        return

                    contests = data.get('result', [])
                    if not contests:
                        self.parent.after(0, lambda: status_label.config(text='没有找到比赛记录'))
                        return

                    # 再获取用户信息（当前 rating）
                    user_resp = requests.get(
                        f'https://codeforces.com/api/user.info?handles={handle}',
                        timeout=10
                    )
                    user_data = user_resp.json()
                    # 获取题目完成情况
                    solved_resp = requests.get(
                        f'https://codeforces.com/api/user.status?handle={handle}&from=1&count=10000',
                        timeout=15
                    )
                    solved_data = solved_resp.json()
                    # 按 contestId 分组建立倒排索引
                    solved_by_contest = {}
                    if solved_data.get('status') == 'OK':
                        for sub in solved_data['result']:
                            if sub.get('verdict') == 'OK':
                                cid = sub.get('problem', {}).get('contestId', '')
                                idx = sub.get('problem', {}).get('index', '')
                                key = f'{cid}{idx}'
                                m = re.match(r'(\d+)(\w+)', key)
                                if m:
                                    scid = m.group(1)
                                    solved_by_contest.setdefault(scid, 0)
                                    solved_by_contest[scid] += 1

                    # 获取题目列表（用于知道每题 rating）
                    prob_resp = requests.get(
                        'https://codeforces.com/api/problemset.problems',
                        timeout=10
                    )
                    # 按 contestId 分组建立倒排索引
                    total_by_contest = {}
                    if prob_resp.json().get('status') == 'OK':
                        for p in prob_resp.json()['result']['problems']:
                            pid = f'{p["contestId"]}{p["index"]}'
                            m = re.match(r'(\d+)(\w+)', pid)
                            if m:
                                scid = m.group(1)
                                total_by_contest.setdefault(scid, 0)
                                total_by_contest[scid] += 1

                    imported = 0
                    conn = get_connection()
                    for c in contests:
                        cid = c.get('contestId', 0)
                        # 检查是否已存在
                        existing = conn.execute(
                            "SELECT id FROM contests WHERE platform='Codeforces' AND contest_id=?",
                            (str(cid),)).fetchone()
                        if existing:
                            continue

                        contest_name = c.get('contestName', '')
                        rank = c.get('rank', 0) or 0
                        old_rating = c.get('oldRating', 0) or 0
                        new_rating = c.get('newRating', 0) or 0

                        # 从倒排索引中查询
                        solved = solved_by_contest.get(str(cid), 0)
                        total_probs = total_by_contest.get(str(cid), 0)

                        conn.execute(
                            """INSERT INTO contests (platform, contest_id, contest_name, contest_type,
                               contest_date, rank, rating_before, rating_after, rating_change,
                               solved_count, total_problems, performance)
                               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                            ('Codeforces', str(cid), contest_name, 'rated',
                             datetime.fromtimestamp(c.get('ratingUpdateTimeSeconds', 0), tz=timezone.utc).strftime('%Y-%m-%d') if c.get('ratingUpdateTimeSeconds') else '', rank,
                             old_rating, new_rating, new_rating - old_rating,
                             solved, total_probs, 0))
                        imported += 1

                    conn.commit()
                    conn.close()

                    self.parent.after(0, lambda: [
                        status_label.config(text=f'成功导入 {imported} 场比赛记录'),
                        self._refresh_list()
                    ])
                    if imported > 0:
                        self.parent.after(1000, dialog.destroy)
                except Exception as e:
                    self.parent.after(0, lambda: status_label.config(text=f'导入失败: {e}'))

            threading.Thread(target=_fetch, daemon=True).start()

        tk.Button(dialog, text='导入', font=(self.config.get('font_family'), 11, 'bold'),
                  bg=colors['fg_accent'], fg='#ffffff', padx=24, pady=6,
                  command=_do_import).pack(pady=8)

    def _import_atcoder(self):
        """从 AtCoder (kenkoooo API) 导入用户比赛记录"""
        dialog = tk.Toplevel(self.parent)
        dialog.title('从 AtCoder 导入')
        dialog.geometry('400x200')
        dialog.transient(self.parent)
        colors = self.config.get_colors()
        dialog.configure(bg=colors['bg_main'])

        tk.Label(dialog, text='输入 AtCoder 用户名', font=(self.config.get('font_family'), 13, 'bold'),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(pady=(16, 8))

        handle_var = tk.StringVar()
        tk.Entry(dialog, textvariable=handle_var, font=(self.config.get('font_family'), 14),
                 bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT,
                 justify=tk.CENTER).pack(fill=tk.X, padx=30, pady=4, ipady=4)

        status_label = tk.Label(dialog, text='', font=(self.config.get('font_family'), 10),
                                 bg=colors['bg_main'], fg=colors['fg_muted'])
        status_label.pack(pady=4)

        def _do_import():
            handle = handle_var.get().strip()
            if not handle:
                return
            status_label.config(text='正在获取...')
            dialog.update()

            def _fetch():
                try:
                    import requests
                    # 获取用户比赛记录
                    resp = requests.get(
                        f'https://kenkoooo.com/atcoder/ratings/history/{handle}',
                        timeout=15
                    )
                    if resp.status_code != 200:
                        self.parent.after(0, lambda: status_label.config(text='获取失败，请检查用户名'))
                        return

                    data = resp.json()
                    if not isinstance(data, list) or not data:
                        self.parent.after(0, lambda: status_label.config(text='没有找到比赛记录'))
                        return

                    # 获取题目完成情况（kenkoooo submissions API）
                    ac_resp = requests.get(
                        f'https://kenkoooo.com/atcoder/atcoder-api/v3/user/submissions?user={handle}&from_second=0',
                        timeout=15
                    )
                    ac_by_contest = {}
                    if ac_resp.status_code == 200:
                        submissions = ac_resp.json()
                        for sub in submissions:
                            if sub.get('result') == 'AC':
                                cid = sub.get('contest_id', '')
                                pid = sub.get('problem_id', '')
                                if cid:
                                    ac_by_contest.setdefault(cid, set())
                                    ac_by_contest[cid].add(pid)

                    # 获取每场比赛的题目总数
                    cp_resp = requests.get(
                        'https://kenkoooo.com/atcoder/resources/contest-problem.json',
                        timeout=10
                    )
                    total_by_contest = {}
                    if cp_resp.status_code == 200:
                        for entry in cp_resp.json():
                            cid = entry.get('contest_id', '')
                            if cid:
                                total_by_contest.setdefault(cid, 0)
                                total_by_contest[cid] += 1

                    imported = 0
                    conn = get_connection()
                    for c in data:
                        contest_id = c.get('contest_id', '') or c.get('ContestID', '') or ''
                        contest_name = c.get('contest_name', '') or c.get('ContestName', '') or ''
                        rank = c.get('Place', 0) or c.get('rank', 0) or 0
                        old_rating = c.get('OldRating', 0) or c.get('old_rating', 0) or 0
                        new_rating = c.get('NewRating', 0) or c.get('new_rating', 0) or 0
                        end_time = c.get('EndTime', '') or c.get('end_time', '') or ''
                        performance = c.get('Performance', 0) or c.get('performance', 0) or 0
                        is_rated = c.get('IsRated', False) or c.get('is_rated', False)

                        if not contest_id:
                            continue

                        existing = conn.execute(
                            "SELECT id FROM contests WHERE platform='AtCoder' AND contest_id=?",
                            (str(contest_id),)).fetchone()
                        if existing:
                            continue

                        # 提取日期
                        date_str = str(end_time)[:10] if end_time else ''

                        # 计算通过题数和总题数
                        solved_count = len(ac_by_contest.get(str(contest_id), set()))
                        total_problems = total_by_contest.get(str(contest_id), 0)

                        conn.execute(
                            """INSERT INTO contests (platform, contest_id, contest_name, contest_type,
                               contest_date, rank, rating_before, rating_after, rating_change, performance,
                               solved_count, total_problems)
                               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                            ('AtCoder', str(contest_id), contest_name,
                             'rated' if is_rated else 'unrated',
                             date_str, rank, old_rating, new_rating,
                             new_rating - old_rating, performance,
                             solved_count, total_problems))
                        imported += 1

                    conn.commit()
                    conn.close()

                    self.parent.after(0, lambda: [
                        status_label.config(text=f'成功导入 {imported} 场比赛记录'),
                        self._refresh_list()
                    ])
                    if imported > 0:
                        self.parent.after(1000, dialog.destroy)
                except Exception as e:
                    self.parent.after(0, lambda: status_label.config(text=f'导入失败: {e}'))

            threading.Thread(target=_fetch, daemon=True).start()

        tk.Button(dialog, text='导入', font=(self.config.get('font_family'), 11, 'bold'),
                  bg=colors['fg_accent'], fg='#ffffff', padx=24, pady=6,
                  command=_do_import).pack(pady=8)

    # ============================================================
    # 删除
    # ============================================================

    def _delete_current(self):
        if not self._current_id:
            return
        if not messagebox.askyesno('确认删除', '确定要删除这条比赛记录吗？'):
            return
        try:
            conn = get_connection()
            conn.execute("DELETE FROM contests WHERE id=?", (self._current_id,))
            conn.commit()
            conn.close()
            self._current_id = None
            self._refresh_list()
            self._show_frame('empty')
            self.app.set_status('比赛记录已删除')
        except Exception as e:
            self.app.set_status(f'删除失败: {e}')

    # ============================================================
    # 生命周期
    # ============================================================

    def on_before_leave(self):
        pass

    def apply_theme(self):
        for w in self.parent.winfo_children():
            w.destroy()
        self._build_ui()
        self._refresh_list()