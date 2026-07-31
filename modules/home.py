"""
首页模块（Dashboard）
- 每日签到 + 月度日历
- 近期赛事（NOI 系列 + 公开赛）
- 便签/草稿区
"""

import tkinter as tk
from tkinter import ttk
from datetime import date, timedelta
import calendar
import webbrowser

from config import Config


def get_upcoming_contests():
    """获取真实赛事数据（CF/AT 在线拉取 + NOI 系列配置文件）"""
    from services.contests import get_all_contests
    return get_all_contests()


class HomeModule:

    def __init__(self, app, parent_frame):
        self.app = app
        self.config = Config()
        self.parent = parent_frame
        for w in parent_frame.winfo_children():
            w.destroy()

        self._build_ui()

    # ============================================================
    # UI
    # ============================================================

    def _build_ui(self):
        colors = self.config.get_colors()

        # 顶部欢迎条
        top = tk.Frame(self.parent, bg=colors['bg_sidebar'], height=80)
        top.pack(fill=tk.X)
        top.pack_propagate(False)

        tk.Label(top, text=f'欢迎回来，猫先生',
                 font=(self.config.get('font_family'), 18, 'bold'),
                 bg=colors['bg_sidebar'], fg=colors['fg_primary']).pack(side=tk.LEFT, padx=20, pady=20)

        # 当前日期
        today = date.today()
        weekday_cn = ['一', '二', '三', '四', '五', '六', '日']
        date_text = f'{today.year}年{today.month}月{today.day}日 星期{weekday_cn[today.weekday()]}'
        tk.Label(top, text=date_text,
                 font=(self.config.get('font_family'), 11),
                 bg=colors['bg_sidebar'], fg=colors['fg_muted']).pack(side=tk.RIGHT, padx=20, pady=20)

        # 主体三栏
        main = tk.Frame(self.parent, bg=colors['bg_main'])
        main.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        self._build_checkin(main)
        self._build_contests(main)
        self._build_notes(main)

    # ============================================================
    # 签到面板
    # ============================================================

    def _build_checkin(self, parent):
        colors = self.config.get_colors()
        panel = tk.Frame(parent, bg=colors['bg_sidebar'])
        panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))

        # 标题行
        header = tk.Frame(panel, bg=colors['bg_sidebar'])
        header.pack(fill=tk.X, padx=14, pady=(10, 6))

        tk.Label(header, text='每日签到',
                 font=(self.config.get('font_family'), 13, 'bold'),
                 bg=colors['bg_sidebar'], fg=colors['fg_primary']).pack(side=tk.LEFT)

        streak = self.config.get('checkin_streak', 0)
        tk.Label(header, text=f'连续 {streak} 天',
                 font=(self.config.get('font_family'), 11),
                 bg=colors['bg_sidebar'], fg=colors['fg_accent']).pack(side=tk.RIGHT)

        # 签到按钮
        btn_frame = tk.Frame(panel, bg=colors['bg_sidebar'])
        btn_frame.pack(fill=tk.X, padx=14, pady=(0, 10))

        last_date = self.config.get('last_checkin_date', '')
        today_str = str(date.today())
        already = (last_date == today_str)

        self.checkin_btn = tk.Button(btn_frame, text='',
                                      font=(self.config.get('font_family'), 12, 'bold'),
                                      relief=tk.FLAT, padx=20, pady=8, cursor='hand2',
                                      command=self._do_checkin)
        self.checkin_btn.pack(side=tk.LEFT)
        self._update_checkin_btn()

        # 月历格子
        cal_frame = tk.Frame(panel, bg=colors['bg_sidebar'])
        cal_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 12))

        self._draw_calendar(cal_frame)

    def _update_checkin_btn(self):
        today_str = str(date.today())
        last_date = self.config.get('last_checkin_date', '')
        if last_date == today_str:
            self.checkin_btn.config(text='✓ 今日已签到', state=tk.DISABLED,
                                     bg=self.config.get_colors()['bg_sidebar'],
                                     fg=self.config.get_colors()['success'])
        else:
            self.checkin_btn.config(text='📅 点击签到', state=tk.NORMAL,
                                     bg=self.config.get_colors()['fg_accent'],
                                     fg='#ffffff')

    def _do_checkin(self):
        today_str = str(date.today())
        last = self.config.get('last_checkin_date', '')

        if last == today_str:
            self.app.set_status('今日已签到')
            return

        streak = self.config.get('checkin_streak', 0)
        if last:
            try:
                last_d = date.fromisoformat(last)
                if (date.today() - last_d).days == 1:
                    streak += 1
                else:
                    streak = 1
            except Exception:
                streak = 1
        else:
            streak = 1

        self.config.set('last_checkin_date', today_str)
        self.config.set('checkin_streak', streak)
        self._update_checkin_btn()
        self._draw_calendar(self.parent.winfo_children()[1].winfo_children()[0].winfo_children()[2])
        self.app.set_status(f'✓ 签到成功！连续 {streak} 天')

    def _draw_calendar(self, parent):
        """绘制月历"""
        for w in parent.winfo_children():
            w.destroy()

        colors = self.config.get_colors()
        today = date.today()
        last_date = self.config.get('last_checkin_date', '')

        # 月初、天数、月初星期
        first_day = date(today.year, today.month, 1)
        days_in_month = calendar.monthrange(today.year, today.month)[1]
        start_wd = first_day.weekday()  # 0=Mon

        HEADERS = ['一', '二', '三', '四', '五', '六', '日']
        for i, h in enumerate(HEADERS):
            fg = colors['fg_accent'] if h in ('六', '日') else colors['fg_muted']
            tk.Label(parent, text=h, font=(self.config.get('font_family'), 9, 'bold'),
                     bg=colors['bg_sidebar'], fg=fg, width=2).grid(row=0, column=i, padx=1, pady=1)

        for d in range(1, days_in_month + 1):
            row = (start_wd + d - 1) // 7 + 1
            col = (start_wd + d - 1) % 7
            dt = date(today.year, today.month, d)
            dt_str = str(dt)

            bg = colors['bg_sidebar']
            fg = colors['fg_primary']

            if dt == today:
                bg = colors['fg_accent']
                fg = '#ffffff'
            elif dt_str <= last_date:
                bg = '#AFA9EC'
                fg = '#ffffff'
            elif d > today.day:
                bg = colors['bg_sidebar']
                fg = colors['fg_muted']

            lbl = tk.Label(parent, text=str(d), font=(self.config.get('font_family'), 10),
                            bg=bg, fg=fg, width=2, padx=6, pady=3)
            lbl.grid(row=row, column=col, padx=1, pady=1)

    # ============================================================
    # 赛事面板
    # ============================================================

    def _build_contests(self, parent):
        colors = self.config.get_colors()
        panel = tk.Frame(parent, bg=colors['bg_sidebar'])
        panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

        header = tk.Frame(panel, bg=colors['bg_sidebar'])
        header.pack(fill=tk.X, padx=14, pady=(10, 6))
        tk.Label(header, text='近期赛事',
                 font=(self.config.get('font_family'), 13, 'bold'),
                 bg=colors['bg_sidebar'], fg=colors['fg_primary']).pack(side=tk.LEFT)
        refresh_btn = tk.Label(header, text='🔄', font=(self.config.get('font_family'), 12),
                               bg=colors['bg_sidebar'], fg=colors['fg_accent'],
                               cursor='hand2', padx=4)
        refresh_btn.pack(side=tk.RIGHT)
        refresh_btn.bind('<Button-1>', lambda e: self._refresh_contests())

        canvas = tk.Canvas(panel, bg=colors['bg_sidebar'], highlightthickness=0)
        scroll = ttk.Scrollbar(panel, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))
        scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=(0, 8))

        inner = tk.Frame(canvas, bg=colors['bg_sidebar'])
        win = canvas.create_window((0, 0), window=inner, anchor=tk.NW)
        canvas.bind('<Configure>', lambda e: canvas.itemconfig(win, width=e.width - 4))
        inner.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))

        contests = get_upcoming_contests()
        today = date.today()
        shown = 0
        for c in contests:
            if c['date'] < today:
                continue
            shown += 1
            days_left = (c['date'] - today).days
            rf = tk.Frame(inner, bg=colors['bg_sidebar'])
            rf.pack(fill=tk.X, pady=1)

            if days_left <= 7:
                fg = colors['danger']
            elif days_left <= 30:
                fg = colors['fg_accent']
            else:
                fg = colors['fg_muted']

            tk.Label(rf, text=c['date'].strftime('%m-%d'),
                     font=(self.config.get('font_family'), 10, 'bold'),
                     bg=colors['bg_sidebar'], fg=fg).pack(side=tk.LEFT, padx=(0, 8))

            name_lbl = tk.Label(rf, text=c['name'], font=(self.config.get('font_family'), 10),
                     bg=colors['bg_sidebar'], fg=colors['fg_primary'], anchor=tk.W,
                     cursor='hand2')
            name_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
            url = c.get('url', '')
            if url:
                import webbrowser
                name_lbl.bind('<Button-1>', lambda e, u=url: webbrowser.open(u))
                name_lbl.bind('<Enter>', lambda e, lb=name_lbl: lb.configure(fg=colors['fg_link']))
                name_lbl.bind('<Leave>', lambda e, lb=name_lbl: lb.configure(fg=colors['fg_primary']))

            countdown = f'{days_left} 天' if days_left > 0 else '今天'
            tk.Label(rf, text=countdown, font=(self.config.get('font_family'), 9),
                     bg=colors['bg_sidebar'], fg=fg).pack(side=tk.RIGHT)

        if shown == 0:
            tk.Label(inner, text='暂无近期赛事',
                     font=(self.config.get('font_family'), 10),
                     bg=colors['bg_sidebar'], fg=colors['fg_muted']).pack(pady=10)

    # ============================================================
    # 便签区
    # ============================================================

    def _build_notes(self, parent):
        colors = self.config.get_colors()
        panel = tk.Frame(parent, bg=colors['bg_sidebar'], width=260)
        panel.pack(side=tk.RIGHT, fill=tk.Y)
        panel.pack_propagate(False)

        tk.Label(panel, text='便签',
                 font=(self.config.get('font_family'), 13, 'bold'),
                 bg=colors['bg_sidebar'], fg=colors['fg_primary']).pack(anchor=tk.W, padx=14, pady=(10, 6))

        self.note_text = tk.Text(panel, font=(self.config.get('font_family'), 11),
                                  bg=colors['bg_input'], fg=colors['fg_primary'],
                                  relief=tk.FLAT, wrap=tk.WORD, undo=True)
        self.note_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # 加载保存的便签
        saved = self.config.get('home_note', '')
        if saved:
            self.note_text.insert('1.0', saved)
        self.note_text.bind('<KeyRelease>', lambda e: self._save_note())

    def _save_note(self):
        content = self.note_text.get('1.0', tk.END).strip()
        self.config.set('home_note', content)

    def on_before_leave(self):
        self._save_note()

    def _refresh_contests(self):
        """强制刷新赛事数据"""
        from services.contests import refresh_contests
        refresh_contests()
        self._build_ui()
        self.app.set_status('赛事数据已刷新')

    def apply_theme(self):
        for w in self.parent.winfo_children():
            w.destroy()
        self._build_ui()
