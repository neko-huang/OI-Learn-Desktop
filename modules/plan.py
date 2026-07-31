"""
练习模块（题单 + VP 合并）
- 两种模式：自由练习 / 定时模拟
- 题目来源：本地题库 / 外部搜索（洛谷+CF API）/ 手动输入
- 智能生成：选择算法标签 → 搜索 → 选数量加入
- 模拟赛倒计时器
- 进度追踪
"""

import json
import threading
import tkinter as tk
from datetime import date, timedelta
from tkinter import ttk, messagebox

from config import Config
from db.database import get_connection
from modules.problem_meta import DIFFICULTIES, STATUS_SYMBOLS


def get_upcoming_contests():
    """
    返回近期赛事信息（公开赛估算 + NOI 系列年度赛事）。
    公开赛按月估算实际场次，NOI 系列使用 2026 年度已知日期。
    """
    today = date.today()
    year = today.year
    contests = []

    # NOI 系列年度赛事（使用近似日期，实际以官方公告为准）
    annual_events = [
        ('NOI 冬令营', f'{year}-02-05'),
        ('WC WCCT', f'{year}-02-10'),
        ('CTS 比赛', f'{year}-02-15'),
        ('APIO', f'{year}-05-08'),
        ('NOI 省选', f'{year}-04-15'),
        ('NOI 国赛', f'{year}-07-15'),
        ('NOI 决赛', f'{year}-07-20'),
        ('NOI 集训队', f'{year}-08-01'),
        ('NOIP 提高组', f'{year}-11-15'),
        ('NOIP 普及组', f'{year}-10-18'),
        ('NOI 模拟赛 Round 1', f'{year}-09-15'),
    ]

    for name, date_str in annual_events:
        try:
            d = date.fromisoformat(date_str)
            contests.append({'name': name, 'date': d, 'type': 'NOI 系列'})
        except Exception:
            pass

    # 公开赛（按月估算）
    months_ahead = 6
    cur = date(today.year, today.month, 1)
    for i in range(months_ahead):
        m = cur.month + i
        y = cur.year + (m - 1) // 12
        m = ((m - 1) % 12) + 1
        contests.append({'name': f'Codeforces Round ≈6-8 场', 'date': date(y, m, 15), 'type': 'CF'})
        contests.append({'name': f'AtCoder 常规赛 ≈4 场', 'date': date(y, m, 20), 'type': 'AT'})
        contests.append({'name': f'洛谷周赛 ≈4 场', 'date': date(y, m, 25), 'type': '洛谷'})

    contests.sort(key=lambda c: c['date'])
    return contests


class PlanModule:

    def __init__(self, app, parent_frame):
        self.app = app
        self.config = Config()
        self.parent = parent_frame
        for w in parent_frame.winfo_children():
            w.destroy()

        self._current_id = None
        self._mode = 'view'         # 'view' | 'active' | 'empty'
        self._timer_id = None       # 计时器 after id
        self._remaining_sec = 0     # 模拟赛剩余秒数

        self._build_ui()
        self._refresh_list()

    # ============================================================
    # UI
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

    def _build_left(self, parent):
        colors = self.config.get_colors()
        left = tk.Frame(parent, bg=colors['bg_sidebar'], width=240)
        left.pack(side=tk.LEFT, fill=tk.Y)
        left.pack_propagate(False)

        tk.Label(left, text='练习列表', font=(self.config.get('font_family'), 12, 'bold'),
                 bg=colors['bg_sidebar'], fg=colors['fg_primary']
                 ).pack(anchor=tk.W, padx=12, pady=(6, 4))

        self.listbox = tk.Listbox(left, font=(self.config.get('font_family'), 10),
                                   bg=colors['bg_input'], fg=colors['fg_primary'],
                                   selectbackground=colors['fg_accent'], selectforeground='#ffffff',
                                   relief=tk.FLAT, activestyle='none')
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=(0, 8))
        self.listbox.bind('<<ListboxSelect>>', self._on_select)

        sb = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.listbox.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y, pady=(0, 8), padx=(0, 8))
        self.listbox.configure(yscrollcommand=sb.set)

    def _build_right(self, parent):
        colors = self.config.get_colors()
        self.right = tk.Frame(parent, bg=colors['bg_main'])
        self.right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 空状态 —— 签到 + 赛事 + 提示
        self.empty_frame = tk.Frame(self.right, bg=colors['bg_main'])
        self._build_empty_content()

        # 新建模式
        self._build_new_frame()
        # 查看模式
        self.view_frame = tk.Frame(self.right, bg=colors['bg_main'])

        # 标题行
        header = tk.Frame(self.view_frame, bg=colors['bg_main'])
        header.pack(fill=tk.X, padx=16, pady=(12, 2))
        self.practice_title = tk.Label(header, text='', font=(self.config.get('font_family'), 18, 'bold'),
                                        bg=colors['bg_main'], fg=colors['fg_primary'])
        self.practice_title.pack(side=tk.LEFT)

        # 模式标签
        self.mode_label = tk.Label(header, text='', font=(self.config.get('font_family'), 10),
                                    bg=colors['bg_main'], fg=colors['fg_muted'])
        self.mode_label.pack(side=tk.LEFT, padx=(12, 0))

        # 进度条
        self.progress_bar = ttk.Progressbar(self.view_frame, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=16, pady=(4, 0))
        self.progress_label = tk.Label(self.view_frame, text='', font=(self.config.get('font_family'), 9),
                                        bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.E)
        self.progress_label.pack(fill=tk.X, padx=16)

        # 题目列表 Canvas
        self.prob_canvas = tk.Canvas(self.view_frame, bg=colors['bg_main'], highlightthickness=0)
        psb = ttk.Scrollbar(self.view_frame, orient=tk.VERTICAL, command=self.prob_canvas.yview)
        self.prob_inner = tk.Frame(self.prob_canvas, bg=colors['bg_main'])
        self._prob_win = self.prob_canvas.create_window((0, 0), window=self.prob_inner, anchor=tk.NW)
        self.prob_canvas.configure(yscrollcommand=psb.set)
        self.prob_canvas.bind('<Configure>', lambda e: self.prob_canvas.itemconfig(self._prob_win, width=e.width-4))
        self.prob_inner.bind('<Configure>', lambda e: self.prob_canvas.configure(scrollregion=self.prob_canvas.bbox('all')))

        # 底部按钮（查看模式）—— 必须先 pack BOTTOM 才能给 expand widgets 留出空间
        vbar = tk.Frame(self.view_frame, bg=colors['bg_sidebar'], height=44)
        vbar.pack(side=tk.BOTTOM, fill=tk.X)
        vbar.pack_propagate(False)
        tk.Button(vbar, text='删除', font=(self.config.get('font_family'), 10),
                  bg=colors['bg_sidebar'], fg=colors['danger'], relief=tk.FLAT,
                  cursor='hand2', command=self._delete_practice).pack(side=tk.RIGHT, padx=8)
        tk.Button(vbar, text='智能生成', font=(self.config.get('font_family'), 10),
                  bg=colors['bg_sidebar'], fg=colors['fg_accent'], relief=tk.FLAT,
                  cursor='hand2', command=self._smart_gen_dialog).pack(side=tk.RIGHT, padx=8)
        tk.Button(vbar, text='+ 添加题目', font=(self.config.get('font_family'), 10),
                  bg=colors['fg_accent'], fg='#ffffff', relief=tk.FLAT,
                  cursor='hand2', command=self._add_problem_dialog).pack(side=tk.RIGHT, padx=8)
        tk.Button(vbar, text='开始练习', font=(self.config.get('font_family'), 10, 'bold'),
                  bg=colors['success'], fg='#ffffff', relief=tk.FLAT,
                  padx=20, cursor='hand2', command=self._start_practice).pack(side=tk.RIGHT, padx=8)

        # 然后再 pack expand widgets
        self.prob_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8)
        psb.pack(side=tk.RIGHT, fill=tk.Y)

        # 练习中模式
        self.active_frame = tk.Frame(self.right, bg=colors['bg_main'])

        # 计时器 + 进度
        self.timer_frame = tk.Frame(self.active_frame, bg=colors['bg_sidebar'])
        self.timer_frame.pack(fill=tk.X)

        self.timer_label = tk.Label(self.timer_frame, text='', font=(self.config.get('font_family'), 28, 'bold'),
                                     bg=colors['bg_sidebar'], fg=colors['fg_accent'])
        self.timer_label.pack(side=tk.LEFT, padx=16, pady=8)

        self.active_progress = tk.Label(self.timer_frame, text='', font=(self.config.get('font_family'), 11),
                                         bg=colors['bg_sidebar'], fg=colors['fg_secondary'])
        self.active_progress.pack(side=tk.RIGHT, padx=16)

        # 练习中题目列表
        self.active_canvas = tk.Canvas(self.active_frame, bg=colors['bg_main'], highlightthickness=0)
        self.active_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8)
        asb = ttk.Scrollbar(self.active_frame, orient=tk.VERTICAL, command=self.active_canvas.yview)
        asb.pack(side=tk.RIGHT, fill=tk.Y)
        self.active_canvas.configure(yscrollcommand=asb.set)
        self.active_inner = tk.Frame(self.active_canvas, bg=colors['bg_main'])
        self._active_win = self.active_canvas.create_window((0, 0), window=self.active_inner, anchor=tk.NW)
        self.active_canvas.bind('<Configure>', lambda e: self.active_canvas.itemconfig(self._active_win, width=e.width-4))
        self.active_inner.bind('<Configure>', lambda e: self.active_canvas.configure(scrollregion=self.active_canvas.bbox('all')))

        # 练习中底部按钮
        abar = tk.Frame(self.active_frame, bg=colors['bg_sidebar'], height=40)
        abar.pack(fill=tk.X, side=tk.BOTTOM)
        abar.pack_propagate(False)
        tk.Button(abar, text='结束练习', font=(self.config.get('font_family'), 10, 'bold'),
                  bg=colors['danger'], fg='#ffffff', relief=tk.FLAT,
                  padx=20, cursor='hand2', command=self._finish_practice).pack(side=tk.RIGHT, padx=8)

        self._show_frame('empty')

    def _show_frame(self, name):
        self._mode = name
        for n in ('view', 'active', 'empty', 'new'):
            if hasattr(self, f'{n}_frame'):
                getattr(self, f'{n}_frame').pack_forget()
        getattr(self, f'{name}_frame').pack(fill=tk.BOTH, expand=True)

    def _build_new_frame(self):
        colors = self.config.get_colors()
        self.new_frame = tk.Frame(self.right, bg=colors['bg_main'])
        pad = 16

        tk.Label(self.new_frame, text='新建完成后切换将自动保存', font=(self.config.get('font_family'), 9),
                 bg=colors['bg_main'], fg=colors['fg_muted'], anchor=tk.W).pack(fill=tk.X, padx=pad, pady=(6, 0))

        tk.Label(self.new_frame, text='练习名称 *', font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.W).pack(fill=tk.X, padx=pad, pady=(12, 0))
        self.n_name = tk.Entry(self.new_frame, font=(self.config.get('font_family'), 13, 'bold'),
                                bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT)
        self.n_name.pack(fill=tk.X, padx=pad, pady=(2, 8), ipady=4)

        tk.Label(self.new_frame, text='练习模式', font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.W).pack(fill=tk.X, padx=pad)
        self.n_mode = tk.StringVar(value='free')
        for val, txt in [('free', '自由练习'), ('timed', '定时模拟')]:
            tk.Radiobutton(self.new_frame, text=txt, variable=self.n_mode, value=val,
                           font=(self.config.get('font_family'), 10),
                           bg=colors['bg_main'], fg=colors['fg_primary'],
                           selectcolor=colors['bg_sidebar']).pack(anchor=tk.W, padx=pad+20)

        dur_row = tk.Frame(self.new_frame, bg=colors['bg_main'])
        dur_row.pack(fill=tk.X, padx=pad, pady=(8, 8))
        tk.Label(dur_row, text='时长(分钟):', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(side=tk.LEFT)
        self.n_dur = ttk.Combobox(dur_row, values=['60', '90', '120', '150', '180', '240', '300'],
                                   state='readonly', width=8)
        self.n_dur.pack(side=tk.LEFT, padx=4)
        self.n_dur.set('120')

        tk.Label(self.new_frame, text='描述（可选）', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.W).pack(fill=tk.X, padx=pad)
        self.n_desc = tk.Text(self.new_frame, font=(self.config.get('font_family'), 10),
                               bg=colors['bg_input'], fg=colors['fg_primary'],
                               relief=tk.FLAT, wrap=tk.WORD, height=3)
        self.n_desc.pack(fill=tk.X, padx=pad, pady=(2, 8))

        btn_row = tk.Frame(self.new_frame, bg=colors['bg_main'])
        btn_row.pack(fill=tk.X, padx=pad)
        tk.Button(btn_row, text='创建', font=(self.config.get('font_family'), 11, 'bold'),
                  bg=colors['fg_accent'], fg='#ffffff', relief=tk.FLAT,
                  padx=20, pady=6, command=self._do_create_inline).pack(side=tk.LEFT)

    def _start_new(self):
        self.n_name.delete(0, tk.END)
        self.n_mode.set('free')
        self.n_dur.set('120')
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
            conn.commit()
            conn.close()
            self._refresh_list()
            # 自动选中新练习并切换到查看模式
            self._current_id = new_id
            self._show_frame('view')
            self._load_view()
            self.app.set_status(f'练习「{name}」已创建')
        except Exception as e:
            self.app.set_status(f'创建失败: {e}')

    # ============================================================
    # 空状态内容：签到 + 赛事
    # ============================================================

    def _build_empty_content(self):
        colors = self.config.get_colors()
        pad = 16

        # 顶部标题
        tk.Label(self.empty_frame, text='练习模块',
                 font=(self.config.get('font_family'), 20, 'bold'),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(anchor=tk.W, padx=pad, pady=(16, 8))

        tk.Label(self.empty_frame, text='点击「+ 新建练习」创建你的第一个练习，或从下方查看近期赛事。',
                 font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_muted']).pack(anchor=tk.W, padx=pad)

        # 主体内容（左右）
        body = tk.Frame(self.empty_frame, bg=colors['bg_main'])
        body.pack(fill=tk.BOTH, expand=True, padx=pad, pady=12)

        # 左：每日签到
        self._build_checkin_panel(body)

        # 右：赛事日历
        self._build_contests_panel(body)

    def _build_checkin_panel(self, parent):
        colors = self.config.get_colors()
        from datetime import date

        panel = tk.Frame(parent, bg=colors['bg_sidebar'], bd=1)
        panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))

        tk.Label(panel, text='每日签到', font=(self.config.get('font_family'), 13, 'bold'),
                 bg=colors['bg_sidebar'], fg=colors['fg_primary']).pack(anchor=tk.W, padx=14, pady=(12, 8))

        # 显示最近签到
        streak = self._get_streak()
        last_date = self.config.get('last_checkin_date', '')
        today = str(date.today())

        info_row = tk.Frame(panel, bg=colors['bg_sidebar'])
        info_row.pack(fill=tk.X, padx=14)
        tk.Label(info_row, text=f'连续签到', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_sidebar'], fg=colors['fg_secondary']).pack(side=tk.LEFT)
        tk.Label(info_row, text=f'{streak} 天', font=(self.config.get('font_family'), 14, 'bold'),
                 bg=colors['bg_sidebar'], fg=colors['fg_accent']).pack(side=tk.LEFT, padx=4)

        tk.Label(panel, text=f'上次签到: {last_date or "尚未签到"}',
                 font=(self.config.get('font_family'), 9),
                 bg=colors['bg_sidebar'], fg=colors['fg_muted']).pack(anchor=tk.W, padx=14, pady=(2, 8))

        # 签到按钮
        self.checkin_btn = tk.Button(panel, text='', font=(self.config.get('font_family'), 11, 'bold'),
                                       bg=colors['fg_accent'], fg='#ffffff', relief=tk.FLAT,
                                       padx=24, pady=8, cursor='hand2',
                                       command=self._do_checkin)
        self.checkin_btn.pack(padx=14, pady=(0, 14))
        self._update_checkin_btn(today)

    def _update_checkin_btn(self, today: str):
        last_date = self.config.get('last_checkin_date', '')
        if last_date == today:
            self.checkin_btn.config(text='✓ 今日已签到', state=tk.DISABLED,
                                     bg=self.config.get_colors()['bg_sidebar'])
        else:
            self.checkin_btn.config(text='📅 点击签到', state=tk.NORMAL)

    def _do_checkin(self):
        from datetime import date, timedelta
        colors = self.config.get_colors()
        today = str(date.today())
        last = self.config.get('last_checkin_date', '')

        if last == today:
            self.app.set_status('今日已签到')
            return

        # 更新连续天数
        if last:
            try:
                last_d = date.fromisoformat(last)
                if (date.today() - last_d).days == 1:
                    streak = self.config.get('checkin_streak', 0) + 1
                else:
                    streak = 1  # 中断了，重新开始
            except Exception:
                streak = 1
        else:
            streak = 1

        self.config.set('last_checkin_date', today)
        self.config.set('checkin_streak', streak)
        self._update_checkin_btn(today)
        self.app.set_status(f'✓ 签到成功！连续 {streak} 天')

    def _get_streak(self):
        return self.config.get('checkin_streak', 0)

    def _build_contests_panel(self, parent):
        colors = self.config.get_colors()

        panel = tk.Frame(parent, bg=colors['bg_sidebar'], bd=1)
        panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 0))

        tk.Label(panel, text='近期赛事', font=(self.config.get('font_family'), 13, 'bold'),
                 bg=colors['bg_sidebar'], fg=colors['fg_primary']).pack(anchor=tk.W, padx=14, pady=(12, 4))

        # 可滚动
        canvas = tk.Canvas(panel, bg=colors['bg_sidebar'], highlightthickness=0)
        scroll = ttk.Scrollbar(panel, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=14, pady=(0, 8))
        scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=(0, 8))
        inner = tk.Frame(canvas, bg=colors['bg_sidebar'])
        win = canvas.create_window((0, 0), window=inner, anchor=tk.NW)
        canvas.bind('<Configure>', lambda e: canvas.itemconfig(win, width=e.width-4))
        inner.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))

        contests = get_upcoming_contests()
        from datetime import date
        today = date.today()

        for c in contests:
            if c['date'] < today:
                continue
            days_left = (c['date'] - today).days
            rf = tk.Frame(inner, bg=colors['bg_sidebar'])
            rf.pack(fill=tk.X, pady=2)
            # 日期
            tk.Label(rf, text=c['date'].strftime('%m-%d'),
                     font=(self.config.get('font_family'), 10, 'bold'),
                     bg=colors['bg_sidebar'],
                     fg=colors['fg_accent' if days_left <= 7 else 'fg_secondary']
                     ).pack(side=tk.LEFT, padx=(0, 8))
            # 名称
            tk.Label(rf, text=c['name'], font=(self.config.get('font_family'), 10),
                     bg=colors['bg_sidebar'], fg=colors['fg_primary']
                     ).pack(side=tk.LEFT, fill=tk.X, expand=True)
            # 倒计时
            tk.Label(rf, text=f'{days_left} 天', font=(self.config.get('font_family'), 9),
                     bg=colors['bg_sidebar'],
                     fg=colors['danger' if days_left <= 7 else 'fg_muted']
                     ).pack(side=tk.RIGHT)

    # ============================================================
    # 练习列表
    # ============================================================

    def _refresh_list(self):
        self.listbox.delete(0, tk.END)
        self._ids = []
        try:
            conn = get_connection()
            rows = conn.execute(
                "SELECT id, name, practice_mode, status FROM practice_plans ORDER BY created_at DESC"
            ).fetchall()
            conn.close()
            for row in rows:
                mode_icon = '⏱ ' if row['practice_mode'] == 'timed' else '📝 '
                status_icon = '✓ ' if row['status'] == 'completed' else ''
                self.listbox.insert(tk.END, f'{status_icon}{mode_icon}{row["name"]}')
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

            # 题目列表
            for w in self.prob_inner.winfo_children():
                w.destroy()

            for i, item in enumerate(items):
                item = dict(item)
                rf = tk.Frame(self.prob_inner, bg=colors['bg_main'])
                rf.pack(fill=tk.X, padx=12, pady=1)

                sym = STATUS_SYMBOLS.get(item['status'], '○')
                title = item['title'] or f'题目 #{i+1}'
                platform = item.get('platform', '')

                tk.Label(rf, text=f'{i+1}.', font=(self.config.get('font_family'), 10),
                         bg=colors['bg_main'], fg=colors['fg_muted']).pack(side=tk.LEFT, padx=(0, 8))

                tk.Label(rf, text=title, font=(self.config.get('font_family'), 11),
                         bg=colors['bg_main'], fg=colors['fg_primary'], anchor=tk.W
                         ).pack(side=tk.LEFT, fill=tk.X, expand=True)

                if platform:
                    tk.Label(rf, text=f'[{platform}]', font=(self.config.get('font_family'), 9),
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
    # 智能生成题单
    # ============================================================

    def _smart_gen_dialog(self):
        if not self._current_id:
            return
        from modules.problem_meta import get_all_subtopic_tags, PROBLEM_CATEGORIES

        dialog = tk.Toplevel(self.parent)
        dialog.title('题单生成器')
        dialog.geometry('720x720')
        dialog.transient(self.parent)
        dialog.resizable(False, False)
        colors = self.config.get_colors()
        dialog.configure(bg=colors['bg_main'])

        # 顶部 Tabs（仅展示，单页）
        tabs = tk.Frame(dialog, bg=colors['bg_main'])
        tabs.pack(fill=tk.X, padx=20, pady=(16, 4))

        active_tab = tk.Label(tabs, text='✦ 题单生成器', font=(self.config.get('font_family'), 13, 'bold'),
                               bg=colors['bg_main'], fg=colors['fg_accent'])
        active_tab.pack(side=tk.LEFT, padx=(0, 20))
        for txt in ['按标签归类', '已保存']:
            tk.Label(tabs, text=txt, font=(self.config.get('font_family'), 11),
                     bg=colors['bg_main'], fg=colors['fg_muted']).pack(side=tk.LEFT, padx=(0, 20))

        # 标题
        tk.Label(dialog, text='题单生成器', font=(self.config.get('font_family'), 18, 'bold'),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(anchor=tk.W, padx=20, pady=(8, 8))

        # 知识点区
        tk.Label(dialog, text='知识点（可多选）', font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.W).pack(fill=tk.X, padx=20)

        tag_frame = tk.Frame(dialog, bg=colors['bg_main'])
        tag_frame.pack(fill=tk.X, padx=20, pady=(4, 8))

        all_tags = get_all_subtopic_tags()

        # 按 18 大类分组展示
        row_frame = None
        col_count = 9
        tag_vars = {}
        widget_idx = 0
        for cat in PROBLEM_CATEGORIES:
            cat_tags = [t for t in all_tags if t['category'] == cat]
            if not cat_tags:
                continue
            if widget_idx % col_count == 0:
                row_frame = tk.Frame(tag_frame, bg=colors['bg_main'])
                row_frame.pack(fill=tk.X)
            tag_lbl = tk.Label(row_frame, text=cat,
                               font=(self.config.get('font_family'), 10, 'bold'),
                               bg=colors['bg_tag'], fg=colors['fg_link'],
                               relief=tk.FLAT, padx=10, pady=3, cursor='hand2')
            tag_lbl.pack(side=tk.LEFT, padx=2, pady=2)
            var = tk.BooleanVar()
            tag_vars[cat] = var

            def _toggle(c=cat, v=var, w=tag_lbl):
                v.set(not v.get())
                w.configure(fg='#ffffff' if v.get() else colors['fg_link'],
                            bg=colors['fg_accent'] if v.get() else colors['bg_tag'])

            tag_lbl.bind('<Button-1>', lambda e: _toggle())
            widget_idx += 1

        # 难度范围
        tk.Label(dialog, text='难度范围', font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.W).pack(fill=tk.X, padx=20, pady=(8, 0))

        diff_frame = tk.Frame(dialog, bg=colors['bg_main'])
        diff_frame.pack(fill=tk.X, padx=20, pady=(4, 8))

        DIFF_OPTS = ['入门', '普及−', '普及', '普及+/提高−', '提高', '提高+/省选−', '省选/NOI−', 'NOI/NOI+/CTS']
        diff_vars = {}
        for i, d in enumerate(DIFF_OPTS):
            var = tk.BooleanVar(value=d in ('普及+/提高−',))
            diff_vars[d] = var
            lbl = tk.Label(diff_frame, text=d, font=(self.config.get('font_family'), 9),
                           bg=colors['bg_sidebar'], fg=colors['fg_primary'],
                           relief=tk.FLAT, padx=8, pady=4, cursor='hand2')
            lbl.pack(side=tk.LEFT, padx=2, pady=2)

            def _toggle_diff(d=d, v=var, w=lbl):
                v.set(not v.get())
                w.configure(fg='#ffffff' if v.get() else colors['fg_primary'],
                            bg=colors['fg_accent'] if v.get() else colors['bg_sidebar'])

            lbl.bind('<Button-1>', lambda e: _toggle_diff())
            if i == 2 and len(DIFF_OPTS) > 4:
                diff_frame2 = tk.Frame(dialog, bg=colors['bg_main'])
                diff_frame2.pack(fill=tk.X, padx=20, pady=(0, 8))
                diff_frame = diff_frame2

        # 题目数
        count_row = tk.Frame(dialog, bg=colors['bg_main'])
        count_row.pack(fill=tk.X, padx=20, pady=(4, 4))
        tk.Label(count_row, text='题目数', font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(side=tk.LEFT)
        count_var = tk.StringVar(value='12 题')
        ttk.Combobox(count_row, textvariable=count_var,
                      values=['5 题', '8 题', '10 题', '12 题', '15 题', '20 题', '30 题'],
                      state='readonly', width=10).pack(side=tk.LEFT, padx=8)

        # 来源
        tk.Label(count_row, text='来源', font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(side=tk.LEFT, padx=(20, 4))
        source_var = tk.StringVar(value='洛谷')
        ttk.Combobox(count_row, textvariable=source_var,
                      values=['洛谷', 'Codeforces', '本地题库'],
                      state='readonly', width=14).pack(side=tk.LEFT, padx=4)

        # 结果区（占位）
        result_label = tk.Label(dialog, text='', font=(self.config.get('font_family'), 10),
                                 bg=colors['bg_main'], fg=colors['fg_muted'])
        result_label.pack(anchor=tk.W, padx=20)

        # 生成按钮
        btn_row = tk.Frame(dialog, bg=colors['bg_main'])
        btn_row.pack(fill=tk.X, padx=20, pady=(16, 8))
        tk.Button(btn_row, text='生成题单', font=(self.config.get('font_family'), 12, 'bold'),
                  bg=colors['fg_accent'], fg='#ffffff', relief=tk.FLAT,
                  padx=40, pady=8, cursor='hand2',
                  command=lambda: self._do_smart_search(
                      [n for n, v in tag_vars.items() if v.get()],
                      self._source_map(source_var.get()),
                      self._count_map(count_var.get()),
                      result_label, dialog)
                  ).pack(fill=tk.X)

        # 已选标签显示
        if tag_vars:
            pass

    def _source_map(self, txt):
        m = {'洛谷': 'luogu', 'Codeforces': 'codeforces', '本地题库': 'local'}
        return m.get(txt, 'luogu')

    def _count_map(self, txt):
        try:
            return int(txt.replace(' 题', ''))
        except Exception:
            return 10

    def _do_smart_search(self, tags, source, count, result_label, dialog):
        """搜索题目并将结果加入当前练习"""
        if not tags:
            self.app.set_status('请先选择至少一个知识点')
            result_label.config(text='请选择知识点')
            return

        result_label.config(text='正在搜索题目...')

        def _search():
            results = []
            if source == 'luogu':
                from services.fetcher import search_luogu
                for tag in tags[:3]:
                    r = search_luogu(keyword=tag, limit=count)
                    results.extend(r)
                seen = set()
                unique = []
                for r in results:
                    if r['platform_id'] not in seen:
                        seen.add(r['platform_id'])
                        unique.append(r)
                results = unique[:count]
            elif source == 'codeforces':
                from services.fetcher import search_codeforces
                results = search_codeforces(tags=tags[:3], limit=count)
            else:
                from services.fetcher import search_local
                for tag in tags[:3]:
                    r = search_local(keyword=tag)
                    results.extend(r)
                results = results[:count]

            self.parent.after(0, lambda: self._on_search_done(results, dialog, result_label))

        threading.Thread(target=_search, daemon=True).start()

    def _on_search_done(self, results, dialog, result_label):
        if results:
            result_label.config(text=f'找到 {len(results)} 道题目，已加入练习')
            self._add_selected_to_practice(results, dialog)
        else:
            result_label.config(text='未找到题目，请尝试其他知识点或来源')
        dialog.after(2500, dialog.destroy)

    def _add_selected_to_practice(self, problems, dialog):
        if not problems:
            return
        try:
            conn = get_connection()
            max_order = conn.execute(
                "SELECT MAX(sort_order) as m FROM plan_problems WHERE plan_id=?",
                (self._current_id,)).fetchone()
            next_order = (max_order['m'] or 0) + 1

            for p in problems:
                conn.execute(
                    """INSERT INTO plan_problems
                       (plan_id, platform, platform_id, title, difficulty, sort_order)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (self._current_id, p.get('platform', ''),
                     p.get('platform_id', ''), p.get('title', ''),
                     p.get('difficulty', ''), next_order))
                next_order += 1
            conn.commit()
            conn.close()
            dialog.destroy()
            self._load_view()
            self.app.set_status(f'已添加 {len(problems)} 道题目')
        except Exception as e:
            self.app.set_status(f'添加失败: {e}')

    # ============================================================
    # 手动添加题目
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
                  command=lambda: self._add_manual(title_var.get().strip(), dialog)
                  ).pack(side=tk.RIGHT)

    def _add_manual(self, title, dialog):
        if not title:
            messagebox.showwarning('提示', '请输入题目标题')
            return
        try:
            conn = get_connection()
            max_order = conn.execute(
                "SELECT MAX(sort_order) FROM plan_problems WHERE plan_id=?",
                (self._current_id,)).fetchone()
            conn.execute(
                "INSERT INTO plan_problems (plan_id, title, sort_order) VALUES (?, ?, ?)",
                (self._current_id, title, (max_order[0] or 0) + 1))
            conn.commit()
            conn.close()
            dialog.destroy()
            self._load_view()
        except Exception as e:
            self.app.set_status(f'添加失败: {e}')

    # ============================================================
    # 练习模式
    # ============================================================

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
                self.app.set_status('练习中没有题目')
                return

            self._show_frame('active')
            self._active_items = [dict(it) for it in items]

            # 计时器
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
            # 大按钮：切换状态
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

    def apply_theme(self):
        for w in self.parent.winfo_children():
            w.destroy()
        self._build_ui()
        self._refresh_list()
