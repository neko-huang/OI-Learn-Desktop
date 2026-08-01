"""
练习模块（题单 + VP）
- 自由练习 / 定时模拟
- 新建时内嵌智能生成（选知识点→搜索→加入）
- 进度追踪 + 模拟赛倒计时
"""

import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from config import Config
from db.database import get_connection
from modules.problem_meta import DIFFICULTIES, PROBLEM_CATEGORIES, PLATFORMS, STATUS_SYMBOLS


def _build_problem_url(platform: str, platform_id: str) -> str:
    """根据平台和题号构建题目链接"""
    if not platform or not platform_id:
        return ''
    p = platform.lower()
    if 'atcoder' in p:
        return f'https://atcoder.jp/contests/abc/tasks/{platform_id}'
    if 'codeforces' in p or 'cf' == p:
        cid, idx = '', ''
        for ch in platform_id:
            if ch.isdigit(): cid += ch
            else: idx += ch
        if cid and idx:
            return f'https://codeforces.com/problemset/problem/{cid}/{idx}'
        return 'https://codeforces.com/contests'
    if '洛谷' in p or 'luogu' in p:
        return f'https://www.luogu.com.cn/problem/{platform_id}'
    return ''


class PlanModule:

    def __init__(self, app, parent_frame):
        self.app = app
        self.config = Config()
        self.parent = parent_frame
        for w in parent_frame.winfo_children():
            w.destroy()

        self._current_id = None
        self._mode = 'view'
        self._timer_id = None
        self._remaining_sec = 0
        self._gen_results = []  # 智能生成的题目缓存

        self._build_ui()
        self._refresh_list()

    # ============================================================
    # UI 框架
    # ============================================================

    def _build_ui(self):
        colors = self.config.get_colors()

        top = tk.Frame(self.parent, bg=colors['bg_sidebar'], height=42)
        top.pack(fill=tk.X)
        top.pack_propagate(False)
        tk.Label(top, text='练习', font=(self.config.get('font_family'), 12, 'bold'),
                 bg=colors['bg_sidebar'], fg=colors['fg_primary']).pack(side=tk.LEFT, padx=12)

        tk.Frame(top, bg=colors['bg_sidebar']).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(top, text='+ 新建练习', font=(self.config.get('font_family'), 10),
                  bg=colors['fg_accent'], fg='#ffffff', relief=tk.FLAT,
                  padx=16, pady=4, cursor='hand2',
                  command=self._start_new).pack(side=tk.RIGHT, padx=8, pady=8)

        main = tk.Frame(self.parent, bg=colors['bg_main'])
        main.pack(fill=tk.BOTH, expand=True)

        self._build_left(main)
        self._build_right(main)

    # ============================================================
    # 左侧栏
    # ============================================================

    def _build_left(self, parent):
        colors = self.config.get_colors()
        left = tk.Frame(parent, bg=colors['bg_sidebar'], width=240)
        left.pack(side=tk.LEFT, fill=tk.Y)
        left.pack_propagate(False)

        tk.Label(left, text='练习列表', font=(self.config.get('font_family'), 12, 'bold'),
                 bg=colors['bg_sidebar'], fg=colors['fg_primary']).pack(anchor=tk.W, padx=12, pady=(6, 4))

        self.listbox = tk.Listbox(left, font=(self.config.get('font_family'), 10),
                                   bg=colors['bg_input'], fg=colors['fg_primary'],
                                   selectbackground=colors['fg_accent'], selectforeground='#ffffff',
                                   relief=tk.FLAT, activestyle='none')
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=(0, 8))
        self.listbox.bind('<<ListboxSelect>>', self._on_select)

        sb = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.listbox.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y, pady=(0, 8), padx=(0, 8))
        self.listbox.configure(yscrollcommand=sb.set)

    # ============================================================
    # 右侧 — 四种模式
    # ============================================================

    def _build_right(self, parent):
        colors = self.config.get_colors()
        self.right = tk.Frame(parent, bg=colors['bg_main'])
        self.right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 空状态
        self.empty_frame = tk.Frame(self.right, bg=colors['bg_main'])
        tk.Label(self.empty_frame, text='选择一个练习查看\n或点击「+ 新建练习」创建',
                 font=(self.config.get('font_family'), 14),
                 bg=colors['bg_main'], fg=colors['fg_muted']
                 ).place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # 新建模式
        self._build_new_frame()
        # 查看模式
        self._build_view_mode()
        # 练习中模式
        self._build_active_mode()

        self._show_frame('empty')

    def _show_frame(self, name):
        self._mode = name
        for n in ('view', 'active', 'empty', 'new'):
            if hasattr(self, f'{n}_frame'):
                getattr(self, f'{n}_frame').pack_forget()
        f = getattr(self, f'{name}_frame')
        f.pack(fill=tk.BOTH, expand=True)
        # show/hide sub-widgets for edit mode
        if name == 'new':
            self.n_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.n_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        else:
            if hasattr(self, 'n_canvas'):
                self.n_canvas.pack_forget()
                self.n_scroll.pack_forget()

    # ============================================================
    # 新建模式（含智能生成）
    # ============================================================

    def _build_new_frame(self):
        colors = self.config.get_colors()
        self.new_frame = tk.Frame(self.right, bg=colors['bg_main'])

        # Canvas 滚动
        self.n_canvas = tk.Canvas(self.new_frame, bg=colors['bg_main'], highlightthickness=0)
        self.n_scroll = ttk.Scrollbar(self.new_frame, orient=tk.VERTICAL, command=self.n_canvas.yview)
        self.n_canvas.configure(yscrollcommand=self.n_scroll.set)

        self.n_inner = tk.Frame(self.n_canvas, bg=colors['bg_main'])
        win = self.n_canvas.create_window((0, 0), window=self.n_inner, anchor=tk.NW)
        self.n_canvas.bind('<Configure>', lambda e: self.n_canvas.itemconfig(win, width=e.width - 4))
        self.n_inner.bind('<Configure>', lambda e: self.n_canvas.configure(scrollregion=self.n_canvas.bbox('all')))

        pad = 16

        # 标题
        tk.Label(self.n_inner, text='创建练习', font=(self.config.get('font_family'), 18, 'bold'),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(anchor=tk.W, padx=pad, pady=(12, 8))

        # 名称
        tk.Label(self.n_inner, text='练习名称 *', font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.W).pack(fill=tk.X, padx=pad)
        self.n_name = tk.Entry(self.n_inner, font=(self.config.get('font_family'), 13, 'bold'),
                                bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT)
        self.n_name.pack(fill=tk.X, padx=pad, pady=(2, 8), ipady=4)

        # 模式
        tk.Label(self.n_inner, text='练习模式', font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.W).pack(fill=tk.X, padx=pad)
        self.n_mode = tk.StringVar(value='free')
        for val, txt in [('free', '自由练习'), ('timed', '定时模拟')]:
            tk.Radiobutton(self.n_inner, text=txt, variable=self.n_mode, value=val,
                           font=(self.config.get('font_family'), 10),
                           bg=colors['bg_main'], fg=colors['fg_primary'],
                           selectcolor=colors['bg_sidebar']).pack(anchor=tk.W, padx=pad + 20)

        self._dur_row = tk.Frame(self.n_inner, bg=colors['bg_main'])
        self._dur_row.pack(fill=tk.X, padx=pad, pady=(8, 8))
        tk.Label(self._dur_row, text='时长(分钟):', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(side=tk.LEFT)
        self.n_dur = ttk.Combobox(self._dur_row, values=['60', '90', '120', '150', '180', '240', '300'],
                                   state='readonly', width=8)
        self.n_dur.pack(side=tk.LEFT, padx=4)
        self.n_dur.set('120')

        # 自由练习时隐藏时长选择
        self.n_mode.trace_add('write', lambda *a: (
            self._dur_row.pack_forget() if self.n_mode.get() == 'free'
            else self._dur_row.pack(fill=tk.X, padx=pad, pady=(8, 8))))

        # --- 智能生成区 ---
        sep = tk.Frame(self.n_inner, bg=colors['border'], height=1)
        sep.pack(fill=tk.X, padx=pad, pady=(10, 6))

        tk.Label(self.n_inner, text='题目来源',
                 font=(self.config.get('font_family'), 12, 'bold'),
                 bg=colors['bg_main'], fg=colors['fg_primary'], anchor=tk.W).pack(fill=tk.X, padx=pad)

        self.n_source = tk.StringVar(value='manual')
        for val, txt in [('manual', '手动添加'), ('smart', '智能生成')]:
            tk.Radiobutton(self.n_inner, text=txt, variable=self.n_source, value=val,
                           font=(self.config.get('font_family'), 10),
                           bg=colors['bg_main'], fg=colors['fg_primary'],
                           selectcolor=colors['bg_sidebar'],
                           command=self._toggle_gen_panel).pack(anchor=tk.W, padx=pad + 20)

        # 智能生成面板（默认隐藏）
        self.gen_panel = tk.Frame(self.n_inner, bg=colors['bg_main'])

        tk.Label(self.gen_panel, text='知识点（可多选）',
                 font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(anchor=tk.W, padx=8, pady=(4, 2))

        self.gen_tags_frame = tk.Frame(self.gen_panel, bg=colors['bg_main'])
        self.gen_tags_frame.pack(fill=tk.X, padx=8)
        self.gen_tag_vars = {}
        self._build_gen_tags()

        tk.Label(self.gen_panel, text='难度（可多选）',
                 font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(anchor=tk.W, padx=8, pady=(6, 2))

        self.gen_diff_frame = tk.Frame(self.gen_panel, bg=colors['bg_main'])
        self.gen_diff_frame.pack(fill=tk.X, padx=8)
        self.gen_diff_vars = {}
        self._build_gen_diffs()

        gen_ctrl = tk.Frame(self.gen_panel, bg=colors['bg_main'])
        gen_ctrl.pack(fill=tk.X, padx=8, pady=(8, 4))

        tk.Label(gen_ctrl, text='数量', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(side=tk.LEFT)
        self.gen_count = ttk.Combobox(gen_ctrl, values=['5', '8', '10', '12', '15', '20', '30'],
                                       state='readonly', width=6)
        self.gen_count.pack(side=tk.LEFT, padx=4)
        self.gen_count.set('10')

        tk.Label(gen_ctrl, text='来源', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(side=tk.LEFT, padx=(12, 4))
        self.gen_source_var = tk.StringVar(value='codeforces')
        ttk.Combobox(gen_ctrl, textvariable=self.gen_source_var,
                      values=['codeforces', 'atcoder', 'luogu', 'local'],
                      state='readonly', width=12).pack(side=tk.LEFT, padx=4)

        self.gen_status = tk.Label(self.gen_panel, text='',
                                    font=(self.config.get('font_family'), 10),
                                    bg=colors['bg_main'], fg=colors['fg_muted'])
        self.gen_status.pack(anchor=tk.W, padx=8, pady=(4, 0))

        tk.Button(self.gen_panel, text='搜索题目',
                  font=(self.config.get('font_family'), 11, 'bold'),
                  bg=colors['fg_accent'], fg='#ffffff', relief=tk.FLAT,
                  padx=20, pady=6, cursor='hand2',
                  command=self._do_gen_search).pack(anchor=tk.W, padx=8, pady=(8, 4))

        # 结果预览列表
        self.gen_result_label = tk.Label(self.gen_panel, text='',
                                          font=(self.config.get('font_family'), 10),
                                          bg=colors['bg_main'], fg=colors['fg_muted'])
        self.gen_result_label.pack(anchor=tk.W, padx=8)
        self.gen_result_frame = tk.Frame(self.gen_panel, bg=colors['bg_main'])
        self.gen_result_frame.pack(fill=tk.X, padx=8)

        # 描述
        tk.Label(self.n_inner, text='描述（可选）',
                 font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(anchor=tk.W, padx=pad, pady=(12, 2))
        self.n_desc = tk.Text(self.n_inner, font=(self.config.get('font_family'), 10),
                               bg=colors['bg_input'], fg=colors['fg_primary'],
                               relief=tk.FLAT, wrap=tk.WORD, height=2)
        self.n_desc.pack(fill=tk.X, padx=pad, pady=(0, 8))

        # 创建按钮
        tk.Button(self.n_inner, text='创建练习', font=(self.config.get('font_family'), 12, 'bold'),
                  bg=colors['fg_accent'], fg='#ffffff', relief=tk.FLAT,
                  padx=30, pady=8, cursor='hand2',
                  command=self._do_create_inline).pack(padx=pad, pady=12)

    def _build_gen_tags(self):
        """构建知识点 chip 选择器 — 使用种子数据原始分类"""
        from db.seed import ALGORITHM_CATEGORIES
        for w in self.gen_tags_frame.winfo_children():
            w.destroy()
        self.gen_tag_vars.clear()

        colors = self.config.get_colors()
        col_max = 7

        for cat in ALGORITHM_CATEGORIES:  # 直接使用种子的22个大类
            # 大类标题
            tk.Label(self.gen_tags_frame, text=f'▸ {cat["name"]}',
                     font=(self.config.get('font_family'), 9, 'bold'),
                     bg=colors['bg_main'], fg=colors['fg_accent']).pack(anchor=tk.W, padx=(4, 0), pady=(4, 0))

            row_frame = tk.Frame(self.gen_tags_frame, bg=colors['bg_main'])
            row_frame.pack(fill=tk.X, pady=(0, 4))
            col = 0

            for topic in cat['topics']:
                for sub in topic['subtopics']:
                    name = sub[1]
                    var = tk.BooleanVar()
                    self.gen_tag_vars[name] = var

                    lbl = tk.Label(row_frame, text=name,
                                   font=(self.config.get('font_family'), 9),
                                   bg=colors['bg_sidebar'], fg=colors['fg_primary'],
                                   relief=tk.FLAT, padx=6, pady=2, cursor='hand2')
                    lbl.pack(side=tk.LEFT, padx=1, pady=1)
                    lbl.bind('<Button-1>', self._make_tag_toggle(var, lbl))
                    col += 1
                    if col >= col_max:
                        row_frame = tk.Frame(self.gen_tags_frame, bg=colors['bg_main'])
                        row_frame.pack(fill=tk.X, pady=(0, 4))
                        col = 0

    def _make_tag_toggle(self, var, lbl):
        def handler(e):
            var.set(not var.get())
            colors = self.config.get_colors()
            if var.get():
                lbl.configure(bg=colors['fg_accent'], fg='#ffffff')
            else:
                lbl.configure(bg=colors['bg_sidebar'], fg=colors['fg_primary'])
        return handler

    def _build_gen_diffs(self):
        """构建难度 chip 选择器"""
        for w in self.gen_diff_frame.winfo_children():
            w.destroy()
        self.gen_diff_vars.clear()

        colors = self.config.get_colors()
        row_frame = tk.Frame(self.gen_diff_frame, bg=colors['bg_main'])
        row_frame.pack(fill=tk.X)

        for i, d in enumerate(DIFFICULTIES):
            var = tk.BooleanVar()
            self.gen_diff_vars[d] = var

            lbl = tk.Label(row_frame, text=d,
                           font=(self.config.get('font_family'), 9),
                           bg=colors['bg_sidebar'], fg=colors['fg_primary'],
                           relief=tk.FLAT, padx=8, pady=3, cursor='hand2')
            lbl.pack(side=tk.LEFT, padx=2, pady=2)
            lbl.bind('<Button-1>', self._make_tag_toggle(var, lbl))

    def _toggle_gen_panel(self):
        if self.n_source.get() == 'smart':
            self.gen_panel.pack(fill=tk.X, padx=16, pady=(4, 0), before=self.n_desc)
        else:
            self.gen_panel.pack_forget()

    # ============================================================
    # 智能生成搜索
    # ============================================================

    def _do_gen_search(self):
        tags = [n for n, v in self.gen_tag_vars.items() if v.get()]
        diffs = [d for d, v in self.gen_diff_vars.items() if v.get()]
        source = self.gen_source_var.get()

        # CF/AT 不需要标签也能搜
        if not tags and source in ('luogu', 'local'):
            self.gen_status.config(text='请选择至少一个知识点（CF/AT 可不选直接搜）')
            return

        try:
            count = int(self.gen_count.get())
        except Exception:
            count = 10

        self.gen_status.config(text='正在搜索题目...')

        def _search():
            results = []
            if source == 'luogu':
                from services.fetcher import search_luogu
                for tag in tags[:3]:
                    r = search_luogu(keyword=tag, limit=count)
                    results.extend(r)
            elif source == 'codeforces':
                from services.fetcher import search_codeforces
                results = search_codeforces(limit=count * 3)
            elif source == 'atcoder':
                from services.fetcher import search_atcoder
                results = search_atcoder(keyword='', limit=count * 3)
            else:
                from services.fetcher import search_local
                if tags:
                    for tag in tags[:3]:
                        r = search_local(keyword=tag)
                        results.extend(r)
                if not results:
                    r = search_local()
                    results = r
                results = results[:count * 2]

            # 去重 + 难度筛选（AT 不筛难度，其 difficulty 为空）
            seen = set()
            unique = []
            for r in results:
                rid = r.get('platform_id', '') or r.get('title', '')
                if rid in seen:
                    continue
                if source != 'atcoder' and diffs and r.get('difficulty', '') not in diffs:
                    continue
                seen.add(rid)
                unique.append(r)
            results = unique[:count]

            self.parent.after(0, lambda: self._on_gen_results(results))

        threading.Thread(target=_search, daemon=True).start()

    def _on_gen_results(self, results):
        if results:
            self._gen_results = results
            self.gen_status.config(text=f'找到 {len(results)} 道题目')
            self.gen_result_label.config(text='创建练习时将自动加入以下题目:')

            for w in self.gen_result_frame.winfo_children():
                w.destroy()
            colors = self.config.get_colors()
            for p in results:
                rf = tk.Frame(self.gen_result_frame, bg=colors['bg_main'])
                rf.pack(fill=tk.X, pady=1)
                tk.Label(rf, text=f'{p.get("platform_id","")[:12]}',
                         font=(self.config.get('font_family'), 9),
                         bg=colors['bg_main'], fg=colors['fg_muted']).pack(side=tk.LEFT, padx=(0, 8))
                tk.Label(rf, text=p['title'][:30],
                         font=(self.config.get('font_family'), 10),
                         bg=colors['bg_main'], fg=colors['fg_primary'], anchor=tk.W
                         ).pack(side=tk.LEFT, fill=tk.X, expand=True)
                tk.Label(rf, text=p.get('difficulty', '')[:10],
                         font=(self.config.get('font_family'), 9),
                         bg=colors['bg_main'], fg=colors['fg_muted']).pack(side=tk.LEFT, padx=4)
        else:
            self.gen_status.config(text='未找到题目，请尝试其他关键词')

    # ============================================================
    # 创建练习
    # ============================================================

    def _start_new(self):
        self.n_name.delete(0, tk.END)
        self.n_mode.set('free')
        self.n_dur.set('120')
        self.n_source.set('manual')
        self._gen_results = []
        self.gen_panel.pack_forget()
        self._gen_packed = False
        self.gen_status.config(text='')
        self.gen_result_label.config(text='')
        for w in self.gen_result_frame.winfo_children():
            w.destroy()
        self.n_desc.delete('1.0', tk.END)
        self._show_frame('new')

    def _do_create_inline(self):
        name = self.n_name.get().strip()
        if not name:
            messagebox.showwarning('提示', '请输入名称')
            return
        mode = self.n_mode.get()
        dur = int(self.n_dur.get()) if mode == 'timed' else 0
        desc = self.n_desc.get('1.0', tk.END).strip()

        try:
            conn = get_connection()
            cursor = conn.execute(
                "INSERT INTO practice_plans (name, description, practice_mode, duration) VALUES (?,?,?,?)",
                (name, desc, mode, dur))
            new_id = cursor.lastrowid

            # 插入智能生成的题目
            if self._gen_results:
                for i, p in enumerate(self._gen_results):
                    conn.execute(
                        """INSERT INTO plan_problems
                           (plan_id, platform, platform_id, title, difficulty, sort_order)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (new_id, p.get('platform', ''), p.get('platform_id', ''),
                         p.get('title', ''), p.get('difficulty', ''), i + 1))

            conn.commit()
            conn.close()

            self._refresh_list()
            self._current_id = new_id
            self._show_frame('view')
            self._load_view()
            self.app.set_status(f'练习「{name}」已创建')
        except Exception as e:
            self.app.set_status(f'创建失败: {e}')

    # ============================================================
    # 练习列表
    # ============================================================

    def _refresh_list(self):
        self.listbox.delete(0, tk.END)
        self._ids = []
        try:
            conn = get_connection()
            rows = conn.execute(
                """SELECT p.id, p.name, p.practice_mode, p.status,
                          (SELECT COUNT(*) FROM plan_problems WHERE plan_id=p.id) as cnt
                   FROM practice_plans p ORDER BY p.created_at DESC"""
            ).fetchall()
            conn.close()
            for row in rows:
                mode_icon = '⏱ ' if row['practice_mode'] == 'timed' else '📝 '
                status_icon = '✓ ' if row['status'] == 'completed' else ''
                cnt = row['cnt']
                self.listbox.insert(tk.END, f'{status_icon}{mode_icon}{row["name"]}  ({cnt})')
                self._ids.append(row['id'])
        except Exception:
            pass

    def _on_select(self, event):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self._ids):
            return
        self._stop_timer()
        self._current_id = self._ids[idx]
        self._show_frame('view')
        self._load_view()

    # ============================================================
    # 查看模式
    # ============================================================

    def _build_view_mode(self):
        colors = self.config.get_colors()
        self.view_frame = tk.Frame(self.right, bg=colors['bg_main'])

        header = tk.Frame(self.view_frame, bg=colors['bg_main'])
        header.pack(fill=tk.X, padx=16, pady=(12, 2))
        self.practice_title = tk.Label(header, text='', font=(self.config.get('font_family'), 18, 'bold'),
                                        bg=colors['bg_main'], fg=colors['fg_primary'])
        self.practice_title.pack(side=tk.LEFT)
        self.mode_label = tk.Label(header, text='', font=(self.config.get('font_family'), 10),
                                    bg=colors['bg_main'], fg=colors['fg_muted'])
        self.mode_label.pack(side=tk.LEFT, padx=(12, 0))

        self.progress_bar = ttk.Progressbar(self.view_frame, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=16, pady=(4, 0))
        self.progress_label = tk.Label(self.view_frame, text='', font=(self.config.get('font_family'), 9),
                                        bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.E)
        self.progress_label.pack(fill=tk.X, padx=16)

        # 底部按钮 — 先 pack 确保不被 expand widget 挤掉
        vbar = tk.Frame(self.view_frame, bg=colors['bg_sidebar'], height=44)
        vbar.pack(side=tk.BOTTOM, fill=tk.X)
        vbar.pack_propagate(False)
        tk.Button(vbar, text='删除', font=(self.config.get('font_family'), 10),
                  bg=colors['bg_sidebar'], fg=colors['danger'], relief=tk.FLAT,
                  cursor='hand2', command=self._delete_practice).pack(side=tk.RIGHT, padx=8)
        tk.Button(vbar, text='+ 添加题目', font=(self.config.get('font_family'), 10),
                  bg=colors['fg_accent'], fg='#ffffff', relief=tk.FLAT,
                  cursor='hand2', command=self._add_problem_dialog).pack(side=tk.RIGHT, padx=8)
        tk.Button(vbar, text='从本地添加', font=(self.config.get('font_family'), 10),
                  bg=colors['bg_sidebar'], fg=colors['fg_accent'], relief=tk.FLAT,
                  cursor='hand2', command=self._add_from_local_dialog).pack(side=tk.RIGHT, padx=8)
        tk.Button(vbar, text='导入题单', font=(self.config.get('font_family'), 10),
                  bg=colors['bg_sidebar'], fg=colors['fg_accent'], relief=tk.FLAT,
                  cursor='hand2', command=self._import_problemset_dialog).pack(side=tk.RIGHT, padx=8)
        tk.Button(vbar, text='开始练习', font=(self.config.get('font_family'), 10, 'bold'),
                  bg=colors['success'], fg='#ffffff', relief=tk.FLAT,
                  padx=20, cursor='hand2', command=self._start_practice).pack(side=tk.RIGHT, padx=8)

        # 题目列表
        self.prob_canvas = tk.Canvas(self.view_frame, bg=colors['bg_main'], highlightthickness=0)
        psb = ttk.Scrollbar(self.view_frame, orient=tk.VERTICAL, command=self.prob_canvas.yview)
        self.prob_inner = tk.Frame(self.prob_canvas, bg=colors['bg_main'])
        self._prob_win = self.prob_canvas.create_window((0, 0), window=self.prob_inner, anchor=tk.NW)
        self.prob_canvas.configure(yscrollcommand=psb.set)
        self.prob_canvas.bind('<Configure>', lambda e: self.prob_canvas.itemconfig(self._prob_win, width=e.width-4))
        self.prob_inner.bind('<Configure>', lambda e: self.prob_canvas.configure(scrollregion=self.prob_canvas.bbox('all')))

        self.prob_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8)
        psb.pack(side=tk.RIGHT, fill=tk.Y)

    def _load_view(self):
        if not self._current_id:
            return
        colors = self.config.get_colors()
        try:
            conn = get_connection()
            plan = conn.execute("SELECT * FROM practice_plans WHERE id=?", (self._current_id,)).fetchone()
            if not plan:
                conn.close()
                return
            plan = dict(plan)
            items = conn.execute(
                "SELECT * FROM plan_problems WHERE plan_id=? ORDER BY sort_order, id",
                (self._current_id,)).fetchall()
            conn.close()

            self.practice_title.config(text=plan['name'])
            mode_text = '定时模拟' if plan.get('practice_mode') == 'timed' else '自由练习'
            if plan.get('duration'):
                mode_text += f' ({plan["duration"]} 分钟)'
            self.mode_label.config(text=mode_text)

            total = len(items)
            done = sum(1 for it in items if it['status'] == 'done')
            pct = (done / total * 100) if total > 0 else 0
            self.progress_bar['value'] = pct
            self.progress_label.config(text=f'{done}/{total} 已完成' if total > 0 else '暂无题目')

            for w in self.prob_inner.winfo_children():
                w.destroy()
            for i, item in enumerate(items):
                item = dict(item)
                rf = tk.Frame(self.prob_inner, bg=colors['bg_main'])
                rf.pack(fill=tk.X, padx=12, pady=1)

                tk.Label(rf, text=f'{i+1}.', font=(self.config.get('font_family'), 10),
                         bg=colors['bg_main'], fg=colors['fg_muted']).pack(side=tk.LEFT, padx=(0, 8))

                # 标题可点击 → 跳转到平台题目页
                title_lbl = tk.Label(rf, text=item['title'] or f'题目 #{i+1}',
                         font=(self.config.get('font_family'), 11),
                         bg=colors['bg_main'], fg=colors['fg_primary'], anchor=tk.W,
                         cursor='hand2')
                title_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
                plat = item.get('platform', '')
                pid = item.get('platform_id', '')
                if pid:
                    url = _build_problem_url(plat, pid)
                    if url:
                        import webbrowser
                        title_lbl.bind('<Button-1>', lambda e, u=url: webbrowser.open(u))
                        title_lbl.bind('<Enter>', lambda e, l=title_lbl: l.configure(fg=colors['fg_link']))
                        title_lbl.bind('<Leave>', lambda e, l=title_lbl: l.configure(fg=colors['fg_primary']))

                if pid:
                    tk.Label(rf, text=pid, font=(self.config.get('font_family'), 9),
                             bg=colors['bg_main'], fg=colors['fg_muted']).pack(side=tk.LEFT, padx=4)
                if plat:
                    tk.Label(rf, text=f'[{plat}]', font=(self.config.get('font_family'), 9),
                             bg=colors['bg_main'], fg=colors['fg_muted']).pack(side=tk.LEFT, padx=4)
                del_btn = tk.Label(rf, text='×', font=(self.config.get('font_family'), 12),
                                    bg=colors['bg_main'], fg=colors['fg_muted'],
                                    cursor='hand2', padx=4)
                del_btn.pack(side=tk.RIGHT)
                del_btn.bind('<Button-1>', lambda e, it=item: self._remove_item(it['id']))
                del_btn.bind('<Enter>', lambda e, b=del_btn: b.configure(fg=colors['danger']))
                del_btn.bind('<Leave>', lambda e, b=del_btn: b.configure(fg=colors['fg_muted']))
        except Exception as e:
            self.app.set_status(f'加载失败: {e}')

    # ============================================================
    # 添加题目对话框
    # ============================================================

    def _add_problem_dialog(self):
        if not self._current_id:
            return
        dialog = tk.Toplevel(self.parent)
        dialog.title('添加题目')
        dialog.geometry('350x220')
        dialog.transient(self.parent)
        colors = self.config.get_colors()
        dialog.configure(bg=colors['bg_main'])

        tk.Label(dialog, text='手动添加题目', font=(self.config.get('font_family'), 13, 'bold'),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(pady=(12, 8))

        tk.Label(dialog, text='题目标题', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.W).pack(fill=tk.X, padx=20)
        title_var = tk.StringVar()
        tk.Entry(dialog, textvariable=title_var, font=(self.config.get('font_family'), 11),
                 bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT
                 ).pack(fill=tk.X, padx=20, pady=(2, 8), ipady=3)

        tk.Label(dialog, text='OJ链接（可选）', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.W).pack(fill=tk.X, padx=20)
        url_var = tk.StringVar()
        tk.Entry(dialog, textvariable=url_var, font=(self.config.get('font_family'), 10),
                 bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT
                 ).pack(fill=tk.X, padx=20, pady=(2, 8), ipady=3)

        btn_row = tk.Frame(dialog, bg=colors['bg_main'])
        btn_row.pack(fill=tk.X, padx=20, pady=(4, 12))
        tk.Button(btn_row, text='取消', font=(self.config.get('font_family'), 11),
                  bg=colors['bg_sidebar'], fg=colors['fg_primary'],
                  relief=tk.FLAT, padx=16, pady=6, command=dialog.destroy).pack(side=tk.RIGHT, padx=(8, 0))
        tk.Button(btn_row, text='添加', font=(self.config.get('font_family'), 11),
                  bg=colors['fg_accent'], fg='#ffffff', relief=tk.FLAT, padx=16, pady=6,
                  command=lambda: self._add_manual(title_var.get().strip(), dialog)).pack(side=tk.RIGHT)

    def _add_manual(self, title, dialog):
        if not title:
            messagebox.showwarning('提示', '请输入题目标题')
            return
        try:
            conn = get_connection()
            max_order = conn.execute("SELECT MAX(sort_order) FROM plan_problems WHERE plan_id=?",
                                      (self._current_id,)).fetchone()
            conn.execute("INSERT INTO plan_problems (plan_id, title, sort_order) VALUES (?,?,?)",
                          (self._current_id, title, (max_order[0] or 0) + 1))
            conn.commit()
            conn.close()
            dialog.destroy()
            self._load_view()
        except Exception as e:
            self.app.set_status(f'添加失败: {e}')

    def _add_from_local_dialog(self):
        """从本地刷题记录添加题目到当前练习"""
        if not self._current_id:
            return
        dialog = tk.Toplevel(self.parent)
        dialog.title('从刷题记录添加')
        dialog.geometry('600x500')
        dialog.transient(self.parent)
        colors = self.config.get_colors()
        dialog.configure(bg=colors['bg_main'])

        tk.Label(dialog, text='从刷题记录选择题目', font=(self.config.get('font_family'), 13, 'bold'),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(pady=(12, 4))

        search_var = tk.StringVar()
        tk.Entry(dialog, textvariable=search_var, font=(self.config.get('font_family'), 11),
                 bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT
                 ).pack(fill=tk.X, padx=16, pady=(0, 6))

        # 题目列表
        listbox = tk.Listbox(dialog, font=(self.config.get('font_family'), 10),
                             bg=colors['bg_input'], fg=colors['fg_primary'],
                             selectbackground=colors['fg_accent'],
                             selectmode=tk.EXTENDED)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(16, 0), pady=(0, 8))
        sb = ttk.Scrollbar(dialog, orient=tk.VERTICAL, command=listbox.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y, pady=(0, 8), padx=(0, 16))
        listbox.configure(yscrollcommand=sb.set)

        _local_ids = []

        def _refresh():
            listbox.delete(0, tk.END)
            _local_ids.clear()
            try:
                conn = get_connection()
                rows = conn.execute(
                    "SELECT id, title, platform, platform_id, difficulty FROM problems ORDER BY updated_at DESC"
                ).fetchall()
                conn.close()
                s = search_var.get().lower().strip()
                for row in rows:
                    title_low = row['title'].lower()
                    pid_low = (row['platform_id'] or '').lower()
                    if s and s not in title_low and s not in pid_low:
                        continue
                    listbox.insert(tk.END, f'{row["title"][:40]}  [{row["platform"]}]  {row["difficulty"] or ""}')
                    _local_ids.append(row['id'])
                if not rows:
                    listbox.insert(tk.END, '暂无刷题记录，请先在"刷题"模块添加题目')
            except Exception:
                pass

        search_var.trace_add('write', lambda *a: _refresh())
        _refresh()

        def _add_selected():
            sel = listbox.curselection()
            if not sel:
                return
            try:
                conn = get_connection()
                max_order = conn.execute("SELECT MAX(sort_order) FROM plan_problems WHERE plan_id=?",
                                          (self._current_id,)).fetchone()
                next_order = (max_order[0] or 0) + 1
                for idx in sel:
                    pid = _local_ids[idx]
                    row = conn.execute("SELECT * FROM problems WHERE id=?", (pid,)).fetchone()
                    if row:
                        conn.execute(
                            "INSERT INTO plan_problems (plan_id, problem_id, platform, platform_id, title, difficulty, sort_order) VALUES (?,?,?,?,?,?,?)",
                            (self._current_id, row['id'], row['platform'], row['platform_id'] or '',
                             row['title'], row['difficulty'] or '', next_order))
                        next_order += 1
                conn.commit()
                conn.close()
                self._load_view()
                self.app.set_status(f'已添加 {len(sel)} 道题目')
            except Exception as e:
                self.app.set_status(f'添加失败: {e}')
            dialog.destroy()

        tk.Button(dialog, text='添加选中题目', font=(self.config.get('font_family'), 11, 'bold'),
                  bg=colors['fg_accent'], fg='#ffffff', padx=16, pady=6,
                  command=_add_selected).pack(pady=8)

    # ============================================================
    # 导入题单（洛谷 training 链接）
    # ============================================================

    def _import_problemset_dialog(self):
        if not self._current_id:
            return
        dialog = tk.Toplevel(self.parent)
        dialog.title('导入题单')
        dialog.geometry('480x400')
        dialog.transient(self.parent)
        colors = self.config.get_colors()
        dialog.configure(bg=colors['bg_main'])

        tk.Label(dialog, text='导入洛谷题单',
                 font=(self.config.get('font_family'), 14, 'bold'),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(pady=(14, 4))

        tk.Label(dialog, text='粘贴洛谷训练题单链接或编号',
                 font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_muted']).pack()

        # 输入框
        entry_frame = tk.Frame(dialog, bg=colors['bg_main'])
        entry_frame.pack(fill=tk.X, padx=20, pady=(10, 4))

        self.import_url_var = tk.StringVar()
        tk.Entry(entry_frame, textvariable=self.import_url_var,
                 font=(self.config.get('font_family'), 12),
                 bg=colors['bg_input'], fg=colors['fg_primary'],
                 relief=tk.FLAT).pack(fill=tk.X, ipady=4)

        # 示例
        tk.Label(dialog, text='例如: https://www.luogu.com.cn/training/30300  或直接输入 30300',
                 font=(self.config.get('font_family'), 9),
                 bg=colors['bg_main'], fg=colors['fg_muted']).pack(pady=(0, 8))

        # 结果区
        self.import_result_label = tk.Label(dialog, text='',
                                             font=(self.config.get('font_family'), 10),
                                             bg=colors['bg_main'], fg=colors['fg_muted'])
        self.import_result_label.pack(anchor=tk.W, padx=20)

        self.import_result_frame = tk.Frame(dialog, bg=colors['bg_main'])
        self.import_result_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(4, 8))

        # 按钮行
        btn_row = tk.Frame(dialog, bg=colors['bg_main'])
        btn_row.pack(fill=tk.X, padx=20, pady=(0, 12))
        tk.Button(btn_row, text='关闭', font=(self.config.get('font_family'), 11),
                  bg=colors['bg_sidebar'], fg=colors['fg_primary'],
                  relief=tk.FLAT, padx=16, pady=6,
                  command=dialog.destroy).pack(side=tk.RIGHT, padx=(8, 0))
        tk.Button(btn_row, text='导入', font=(self.config.get('font_family'), 11, 'bold'),
                  bg=colors['fg_accent'], fg='#ffffff', relief=tk.FLAT,
                  padx=20, pady=6,
                  command=lambda: self._do_import(dialog)).pack(side=tk.RIGHT)

    def _do_import(self, dialog):
        url = self.import_url_var.get().strip()
        if not url:
            return

        # 提取 training ID
        import re
        m = re.search(r'training/(\d+)', url)
        if not m:
            # 尝试纯数字
            m = re.match(r'^(\d+)$', url)
            if not m:
                self.import_result_label.config(text='无法识别题单链接，请输入有效的洛谷训练链接')
                return

        tid = m.group(1)
        self.import_result_label.config(text=f'正在获取题单 #{tid} ...')

        def _fetch():
            try:
                import requests
                resp = requests.get(
                    f'https://www.luogu.com.cn/training/{tid}?_contentOnly=1',
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'},
                    timeout=15
                )
                data = resp.json()
                if data.get('code') != 200:
                    self.parent.after(0, lambda: self.import_result_label.config(text='获取失败，请检查题单编号是否正确'))
                    return

                probs = data.get('currentData', {}).get('training', {}).get('problems', [])
                results = []
                for p in probs:
                    prob = p.get('problem', {})
                    results.append({
                        'platform': '洛谷',
                        'platform_id': prob.get('pid', ''),
                        'title': prob.get('title', ''),
                        'difficulty': '',
                    })

                self.parent.after(0, lambda: self._show_import_results(results, dialog))
            except Exception as e:
                self.parent.after(0, lambda: self.import_result_label.config(text=f'网络请求失败: {e}'))

        threading.Thread(target=_fetch, daemon=True).start()

    def _show_import_results(self, results, dialog):
        if not results:
            self.import_result_label.config(text='未找到题目')
            return

        self.import_result_label.config(text=f'找到 {len(results)} 道题目，点击确认导入')
        for w in self.import_result_frame.winfo_children():
            w.destroy()

        colors = self.config.get_colors()
        for p in results:
            row = tk.Frame(self.import_result_frame, bg=colors['bg_main'])
            row.pack(fill=tk.X, pady=1)
            tk.Label(row, text=p['platform_id'],
                     font=(self.config.get('font_family'), 9),
                     bg=colors['bg_main'], fg=colors['fg_muted']).pack(side=tk.LEFT, padx=(0, 8))
            tk.Label(row, text=p['title'][:35],
                     font=(self.config.get('font_family'), 10),
                     bg=colors['bg_main'], fg=colors['fg_primary'], anchor=tk.W
                     ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 确认导入
        def do_bulk_import():
            try:
                conn = get_connection()
                max_order = conn.execute(
                    "SELECT MAX(sort_order) FROM plan_problems WHERE plan_id=?",
                    (self._current_id,)).fetchone()
                next_order = (max_order[0] or 0) + 1
                for p in results:
                    conn.execute(
                        "INSERT INTO plan_problems (plan_id, platform, platform_id, title, difficulty, sort_order) VALUES (?,?,?,?,?,?)",
                        (self._current_id, p['platform'], p['platform_id'], p['title'], p.get('difficulty', ''), next_order))
                    next_order += 1
                conn.commit()
                conn.close()
                self.app.set_status(f'已导入 {len(results)} 道题目')
                self._load_view()
            except Exception as e:
                self.app.set_status(f'导入失败: {e}')
            dialog.destroy()

        tk.Button(self.import_result_frame, text='确认导入全部',
                  font=(self.config.get('font_family'), 11, 'bold'),
                  bg=colors['success'], fg='#ffffff', relief=tk.FLAT,
                  padx=16, pady=6, command=do_bulk_import).pack(pady=8)

    # ============================================================
    # 练习中模式
    # ============================================================

    def _build_active_mode(self):
        colors = self.config.get_colors()
        self.active_frame = tk.Frame(self.right, bg=colors['bg_main'])

        self.timer_frame = tk.Frame(self.active_frame, bg=colors['bg_sidebar'])
        self.timer_frame.pack(fill=tk.X)
        self.timer_label = tk.Label(self.timer_frame, text='', font=(self.config.get('font_family'), 28, 'bold'),
                                     bg=colors['bg_sidebar'], fg=colors['fg_accent'])
        self.timer_label.pack(side=tk.LEFT, padx=16, pady=8)
        self.active_progress = tk.Label(self.timer_frame, text='', font=(self.config.get('font_family'), 11),
                                         bg=colors['bg_sidebar'], fg=colors['fg_secondary'])
        self.active_progress.pack(side=tk.RIGHT, padx=16)

        # 底部按钮 — 先 pack
        abar = tk.Frame(self.active_frame, bg=colors['bg_sidebar'], height=44)
        abar.pack(side=tk.BOTTOM, fill=tk.X)
        abar.pack_propagate(False)
        tk.Button(abar, text='结束练习', font=(self.config.get('font_family'), 10, 'bold'),
                  bg=colors['danger'], fg='#ffffff', relief=tk.FLAT,
                  padx=20, cursor='hand2', command=self._finish_practice).pack(side=tk.RIGHT, padx=8)

        # 题目列表
        self.active_canvas = tk.Canvas(self.active_frame, bg=colors['bg_main'], highlightthickness=0)
        asb = ttk.Scrollbar(self.active_frame, orient=tk.VERTICAL, command=self.active_canvas.yview)
        self.active_inner = tk.Frame(self.active_canvas, bg=colors['bg_main'])
        self._active_win = self.active_canvas.create_window((0, 0), window=self.active_inner, anchor=tk.NW)
        self.active_canvas.configure(yscrollcommand=asb.set)
        self.active_canvas.bind('<Configure>', lambda e: self.active_canvas.itemconfig(self._active_win, width=e.width-4))
        self.active_inner.bind('<Configure>', lambda e: self.active_canvas.configure(scrollregion=self.active_canvas.bbox('all')))

        self.active_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8)
        asb.pack(side=tk.RIGHT, fill=tk.Y)

    def _start_practice(self):
        if not self._current_id:
            return
        try:
            conn = get_connection()
            plan = conn.execute("SELECT * FROM practice_plans WHERE id=?", (self._current_id,)).fetchone()
            if not plan:
                conn.close()
                return
            plan = dict(plan)
            items = conn.execute(
                "SELECT * FROM plan_problems WHERE plan_id=? ORDER BY sort_order, id",
                (self._current_id,)).fetchall()
            conn.close()

            if not items:
                self.app.set_status('练习中没有题目，请先添加题目')
                return

            self._show_frame('active')
            self._active_items = [dict(it) for it in items]

            if plan.get('practice_mode') == 'timed' and plan.get('duration', 0) > 0:
                self._remaining_sec = plan['duration'] * 60
                self._update_timer()
            else:
                self._remaining_sec = 0
                self.timer_label.config(text='自由练习')

            self._refresh_active_list()
        except Exception as e:
            self.app.set_status(f'开始失败: {e}')

    def _update_timer(self):
        if self._remaining_sec > 0:
            h = self._remaining_sec // 3600
            m = (self._remaining_sec % 3600) // 60
            s = self._remaining_sec % 60
            self.timer_label.config(text=f'{h:02d}:{m:02d}:{s:02d}')
            self._remaining_sec -= 1
            self._timer_id = self.parent.after(1000, self._update_timer)
        else:
            self.timer_label.config(text='00:00:00')
            self._finish_practice()

    def _stop_timer(self):
        if self._timer_id:
            self.parent.after_cancel(self._timer_id)
            self._timer_id = None

    def _refresh_active_list(self):
        colors = self.config.get_colors()
        for w in self.active_inner.winfo_children():
            w.destroy()

        done = sum(1 for it in self._active_items if it['status'] == 'done')
        total = len(self._active_items)
        self.active_progress.config(text=f'{done}/{total}')

        for i, item in enumerate(self._active_items):
            rf = tk.Frame(self.active_inner, bg=colors['bg_main'])
            rf.pack(fill=tk.X, padx=16, pady=4)

            sym = STATUS_SYMBOLS.get(item['status'], '○')
            btn = tk.Label(rf, text=sym, font=(self.config.get('font_family'), 20),
                           bg=colors['bg_main'],
                           fg=colors['success'] if item['status'] == 'done' else colors['fg_muted'],
                           cursor='hand2', padx=8)
            btn.pack(side=tk.LEFT)
            btn.bind('<Button-1>', lambda e, idx=i: self._toggle_active(idx))

            tk.Label(rf, text=f'{i+1}. {item["title"]}',
                     font=(self.config.get('font_family'), 13),
                     bg=colors['bg_main'], fg=colors['fg_primary'], anchor=tk.W
                     ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)

            if item.get('platform_id'):
                tk.Label(rf, text=item['platform_id'], font=(self.config.get('font_family'), 10),
                         bg=colors['bg_main'], fg=colors['fg_muted']).pack(side=tk.LEFT, padx=4)

    def _toggle_active(self, idx):
        new_status = 'todo' if self._active_items[idx]['status'] == 'done' else 'done'
        self._active_items[idx]['status'] = new_status
        try:
            conn = get_connection()
            conn.execute("UPDATE plan_problems SET status=? WHERE id=?",
                          (new_status, self._active_items[idx]['id']))
            conn.commit()
            conn.close()
        except Exception:
            pass
        self._refresh_active_list()

    def _finish_practice(self):
        self._stop_timer()
        self._show_frame('view')
        self._load_view()
        self.app.set_status('练习已结束')

    def _remove_item(self, item_id):
        try:
            conn = get_connection()
            conn.execute("DELETE FROM plan_problems WHERE id=?", (item_id,))
            conn.commit()
            conn.close()
            self._load_view()
        except Exception:
            pass

    def _delete_practice(self):
        if not self._current_id:
            return
        if not messagebox.askyesno('确认删除', '确定要删除这个练习吗？'):
            return
        try:
            conn = get_connection()
            conn.execute("DELETE FROM plan_problems WHERE plan_id=?", (self._current_id,))
            conn.execute("DELETE FROM practice_plans WHERE id=?", (self._current_id,))
            conn.commit()
            conn.close()
            self._current_id = None
            self._refresh_list()
            self._show_frame('empty')
            self.app.set_status('已删除')
        except Exception as e:
            self.app.set_status(f'删除失败: {e}')

    def on_new(self):
        self._start_new()

    def on_before_leave(self):
        pass

    def apply_theme(self):
        for w in self.parent.winfo_children():
            w.destroy()
        self._build_ui()
        self._refresh_list()
