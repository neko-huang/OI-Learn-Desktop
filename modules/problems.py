"""
刷题记录模块
- 左侧栏：可折叠、可搜索的题目列表（每题含 [编辑] [删除]）
- 右侧：查看模式（Markdown 渲染） / 编辑模式（按截图布局）
- 录入内嵌、自动保存
- 难度 8 级、标签=大纲子知识点
"""

import json
import tkinter as tk
from tkinter import ttk, messagebox

from config import Config
from db.database import get_connection
from components.markdown_view import MarkdownView
from modules.problem_meta import (
    DIFFICULTIES, PROBLEM_CATEGORIES, PLATFORMS, STATUSES, STATUS_SYMBOLS,
    get_all_subtopic_tags,
)


class ProblemsModule:

    def __init__(self, app, parent_frame):
        self.app = app
        self.config = Config()
        self.parent = parent_frame
        for w in parent_frame.winfo_children():
            w.destroy()

        self._current_id = None
        self._mode = 'view'      # 'view' | 'edit' | 'empty'
        self._dirty = False
        self._left_visible = True

        self._all_tags = get_all_subtopic_tags()

        self._build_ui()
        self._refresh_list()

    # ============================================================
    # UI 总框架
    # ============================================================

    def _build_ui(self):
        colors = self.config.get_colors()

        # 顶部栏
        top = tk.Frame(self.parent, bg=colors['bg_sidebar'], height=42)
        top.pack(fill=tk.X)
        top.pack_propagate(False)

        # 折叠按钮
        self.toggle_btn = tk.Label(top, text='◀',
                                    font=(self.config.get('font_family'), 12),
                                    bg=colors['bg_sidebar'], fg=colors['fg_secondary'],
                                    cursor='hand2', padx=10, pady=8)
        self.toggle_btn.pack(side=tk.LEFT)
        self.toggle_btn.bind('<Button-1>', lambda e: self._toggle_left_panel())

        # 搜索
        tk.Label(top, text='搜索:', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_sidebar'], fg=colors['fg_secondary']).pack(side=tk.LEFT, padx=(4, 4))
        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', lambda *a: self._refresh_list())
        tk.Entry(top, textvariable=self.search_var, font=(self.config.get('font_family'), 10),
                 bg=colors['bg_input'], fg=colors['fg_primary'],
                 relief=tk.FLAT, width=20).pack(side=tk.LEFT, padx=(0, 12))

        tk.Label(top, text='状态:', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_sidebar'], fg=colors['fg_secondary']).pack(side=tk.LEFT)
        self.filter_status = tk.StringVar(value='全部')
        ttk.Combobox(top, textvariable=self.filter_status,
                      values=['全部', '待做', '已做', '复习'], state='readonly', width=6
                      ).pack(side=tk.LEFT, padx=(4, 12))
        self.filter_status.trace_add('write', lambda *a: self._refresh_list())

        tk.Label(top, text='难度:', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_sidebar'], fg=colors['fg_secondary']).pack(side=tk.LEFT)
        self.filter_diff = tk.StringVar(value='全部')
        ttk.Combobox(top, textvariable=self.filter_diff,
                      values=['全部'] + DIFFICULTIES, state='readonly', width=14
                      ).pack(side=tk.LEFT, padx=(4, 12))
        self.filter_diff.trace_add('write', lambda *a: self._refresh_list())

        tk.Frame(top, bg=colors['bg_sidebar']).pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Button(top, text='+ 新建题目', font=(self.config.get('font_family'), 10),
                  bg=colors['fg_accent'], fg='#ffffff', relief=tk.FLAT,
                  padx=16, pady=4, cursor='hand2',
                  command=self._start_add).pack(side=tk.RIGHT, padx=8, pady=8)

        self.main_area = tk.Frame(self.parent, bg=colors['bg_main'])
        self.main_area.pack(fill=tk.BOTH, expand=True)

        self._build_left()
        self._build_right()

    # ============================================================
    # 左侧栏
    # ============================================================

    def _build_left(self):
        colors = self.config.get_colors()
        self.left_wrapper = tk.Frame(self.main_area, bg=colors['bg_sidebar'], width=320)
        self.left_wrapper.pack(side=tk.LEFT, fill=tk.Y)
        self.left_wrapper.pack_propagate(False)

        tk.Label(self.left_wrapper, text='题目列表',
                 font=(self.config.get('font_family'), 12, 'bold'),
                 bg=colors['bg_sidebar'], fg=colors['fg_primary']
                 ).pack(anchor=tk.W, padx=12, pady=(6, 2))

        self.list_canvas = tk.Canvas(self.left_wrapper, bg=colors['bg_sidebar'], highlightthickness=0)
        self.list_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(self.left_wrapper, orient=tk.VERTICAL, command=self.list_canvas.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.list_canvas.configure(yscrollcommand=scroll.set)

        self.list_inner = tk.Frame(self.list_canvas, bg=colors['bg_sidebar'])
        self._list_win = self.list_canvas.create_window((0, 0), window=self.list_inner, anchor=tk.NW)
        self.list_canvas.bind('<Configure>', lambda e: self.list_canvas.itemconfig(self._list_win, width=e.width))
        self.list_inner.bind('<Configure>', lambda e: self.list_canvas.configure(scrollregion=self.list_canvas.bbox('all')))

    def _toggle_left_panel(self):
        if self._left_visible:
            self.left_wrapper.pack_forget()
            self.toggle_btn.config(text='▶')
        else:
            self.left_wrapper.pack(side=tk.LEFT, fill=tk.Y, before=self.right_wrapper)
            self.toggle_btn.config(text='◀')
        self._left_visible = not self._left_visible

    def _refresh_list(self):
        for w in self.list_inner.winfo_children():
            w.destroy()

        search = self.search_var.get().lower().strip()
        sf = self.filter_status.get()
        df = self.filter_diff.get()

        try:
            conn = get_connection()
            rows = conn.execute(
                "SELECT id, title, platform, platform_id, difficulty, status FROM problems ORDER BY updated_at DESC"
            ).fetchall()
            conn.close()
        except Exception:
            rows = []

        colors = self.config.get_colors()
        count = 0

        for row in rows:
            row = dict(row)
            status_cn = STATUSES.get(row['status'], row['status'])
            if sf != '全部' and status_cn != sf:
                continue
            if df != '全部' and row['difficulty'] != df:
                continue
            if search:
                title_low = row['title'].lower()
                pid_low = (row.get('platform_id') or '').lower()
                if search not in title_low and search not in pid_low:
                    continue

            count += 1
            rf = tk.Frame(self.list_inner, bg=colors['bg_sidebar'])
            rf.pack(fill=tk.X, padx=8, pady=1)

            # 第一行：标题（点击查看）+ 状态符号
            sym = STATUS_SYMBOLS.get(row['status'], '○')
            pid_str = f' [{row["platform_id"]}]' if row.get('platform_id') else ''
            lb = tk.Label(rf, text=f'{sym} {row["title"]}{pid_str}',
                          font=(self.config.get('font_family'), 10),
                          bg=colors['bg_sidebar'], fg=colors['fg_primary'],
                          anchor=tk.W, cursor='hand2')
            lb.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))
            lb.bind('<Button-1>', lambda e, pid=row['id']: self._view_problem(pid))
            lb.bind('<Enter>', lambda e, l=lb: l.configure(fg=colors['fg_accent']))
            lb.bind('<Leave>', lambda e, l=lb: l.configure(fg=colors['fg_primary']))

            # 第二行：平台 + [编辑] [删除]
            bottom_row = tk.Frame(rf, bg=colors['bg_sidebar'])
            bottom_row.pack(fill=tk.X, padx=(20, 0))
            tk.Label(bottom_row, text=row['platform'], font=(self.config.get('font_family'), 9),
                     bg=colors['bg_sidebar'], fg=colors['fg_muted']).pack(side=tk.LEFT, padx=(0, 8))

            edit_lbl = tk.Label(bottom_row, text='编辑', font=(self.config.get('font_family'), 9),
                                bg=colors['bg_sidebar'], fg=colors['fg_accent'],
                                cursor='hand2', padx=6)
            edit_lbl.pack(side=tk.RIGHT)
            edit_lbl.bind('<Button-1>', lambda e, pid=row['id']: self._edit_problem(pid))

            del_lbl = tk.Label(bottom_row, text='删除', font=(self.config.get('font_family'), 9),
                               bg=colors['bg_sidebar'], fg=colors['danger'],
                               cursor='hand2', padx=6)
            del_lbl.pack(side=tk.RIGHT)
            del_lbl.bind('<Button-1>', lambda e, pid=row['id']: self._delete_problem(pid))

        if count == 0:
            tk.Label(self.list_inner, text='(暂无题目)',
                     font=(self.config.get('font_family'), 10),
                     bg=colors['bg_sidebar'], fg=colors['fg_muted']).pack(pady=20)

    # ============================================================
    # 右侧面板
    # ============================================================

    def _build_right(self):
        colors = self.config.get_colors()
        self.right_wrapper = tk.Frame(self.main_area, bg=colors['bg_main'])
        self.right_wrapper.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.view_frame = tk.Frame(self.right_wrapper, bg=colors['bg_main'])
        self._build_view_mode()
        self.edit_frame = tk.Frame(self.right_wrapper, bg=colors['bg_main'])
        # Canvas + 滚动条包装编辑内容
        self.edit_canvas = tk.Canvas(self.edit_frame, bg=colors['bg_main'], highlightthickness=0)
        self.edit_scroll = ttk.Scrollbar(self.edit_frame, orient=tk.VERTICAL, command=self.edit_canvas.yview)
        self.edit_inner = tk.Frame(self.edit_canvas, bg=colors['bg_main'])
        self.edit_canvas.create_window((0, 0), window=self.edit_inner, anchor=tk.NW)
        self.edit_canvas.configure(yscrollcommand=self.edit_scroll.set)
        self.edit_inner.bind('<Configure>', lambda e: self.edit_canvas.configure(scrollregion=self.edit_canvas.bbox('all')))
        self.edit_canvas.bind('<Configure>', lambda e: self.edit_canvas.itemconfig(self.edit_canvas.find_withtag('all')[0] if self.edit_canvas.find_all() else None, width=e.width))
        self._build_edit_mode()
        self.empty_frame = tk.Frame(self.right_wrapper, bg=colors['bg_main'])
        tk.Label(self.empty_frame, text='选择一个题目查看\n或点击「+ 新建题目」录入',
                 font=(self.config.get('font_family'), 14),
                 bg=colors['bg_main'], fg=colors['fg_muted']
                 ).place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        self._show_frame('empty')

    def _show_frame(self, name: str):
        self._mode = name
        for n in ('view', 'edit', 'empty'):
            getattr(self, f'{n}_frame').pack_forget()
        getattr(self, f'{name}_frame').pack(fill=tk.BOTH, expand=True)
        if name == 'edit':
            self.edit_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.edit_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        else:
            self.edit_canvas.pack_forget()
            self.edit_scroll.pack_forget()

    # ============================================================
    # 查看模式
    # ============================================================

    def _build_view_mode(self):
        colors = self.config.get_colors()

        self.view_title = tk.Label(self.view_frame, text='',
                                    font=(self.config.get('font_family'), 18, 'bold'),
                                    bg=colors['bg_main'], fg=colors['fg_primary'], anchor=tk.W)
        self.view_title.pack(fill=tk.X, padx=20, pady=(16, 4))

        meta = tk.Frame(self.view_frame, bg=colors['bg_main'])
        meta.pack(fill=tk.X, padx=20, pady=(0, 4))

        self.view_meta = tk.Label(meta, text='', font=(self.config.get('font_family'), 10),
                                   bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.W)
        self.view_meta.pack(side=tk.LEFT)

        self.view_status_var = tk.StringVar()
        status_fr = tk.Frame(meta, bg=colors['bg_main'])
        status_fr.pack(side=tk.RIGHT)
        for val, txt in STATUSES.items():
            tk.Radiobutton(status_fr, text=txt, variable=self.view_status_var, value=val,
                           font=(self.config.get('font_family'), 9),
                           bg=colors['bg_main'], fg=colors['fg_primary'],
                           selectcolor=colors['bg_sidebar'],
                           command=self._on_view_status_change).pack(side=tk.LEFT, padx=(4, 0))

        self.view_md = MarkdownView(self.view_frame)
        self.view_md.pack(fill=tk.BOTH, expand=True, padx=20, pady=(4, 4))

        bar = tk.Frame(self.view_frame, bg=colors['bg_sidebar'], height=40)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        bar.pack_propagate(False)
        tk.Button(bar, text='删除', font=(self.config.get('font_family'), 10),
                  bg=colors['bg_sidebar'], fg=colors['danger'], relief=tk.FLAT,
                  padx=12, pady=4, cursor='hand2',
                  command=self._delete_current).pack(side=tk.RIGHT, padx=8)
        tk.Button(bar, text='编辑', font=(self.config.get('font_family'), 10),
                  bg=colors['fg_accent'], fg='#ffffff', relief=tk.FLAT,
                  padx=16, pady=4, cursor='hand2',
                  command=lambda: self._edit_problem(self._current_id)).pack(side=tk.RIGHT, padx=4)

    def _load_view(self):
        if not self._current_id:
            return
        try:
            conn = get_connection()
            row = conn.execute("SELECT * FROM problems WHERE id=?", (self._current_id,)).fetchone()
            conn.close()
            if not row:
                return
            row = dict(row)

            self.view_title.config(text=row['title'])
            self.view_status_var.set(row['status'])

            parts = [f'平台: {row["platform"]}']
            if row.get('platform_id'):
                parts.append(f'编号: {row["platform_id"]}')
            parts.append(f'难度: {row["difficulty"]}')
            if row.get('url'):
                parts.append(f'链接: {row["url"]}')
            try:
                tags = json.loads(row.get('tags') or '[]')
                if tags:
                    parts.append(f'标签: {", ".join(tags[:5])}{"..." if len(tags)>5 else ""}')
            except Exception:
                pass
            self.view_meta.config(text='  |  '.join(parts))

            md = ''
            desc = row.get('description', '')
            sol = row.get('solution', '')
            if desc:
                md += f'## 题意\n\n{desc}\n\n'
            if sol:
                md += f'## 题解\n\n{sol}\n'
            if not md:
                md = '*暂无题意和题解*'
            self.view_md.render(md)

        except Exception as e:
            self.app.set_status(f'加载失败: {e}')

    def _on_view_status_change(self):
        if not self._current_id:
            return
        try:
            conn = get_connection()
            conn.execute(
                "UPDATE problems SET status=?, updated_at=datetime('now','localtime') WHERE id=?",
                (self.view_status_var.get(), self._current_id))
            conn.commit()
            conn.close()
            self._refresh_list()
            self.app.set_status('状态已更新')
        except Exception as e:
            self.app.set_status(f'更新失败: {e}')

    # ============================================================
    # 编辑模式 — 按截图布局
    # ============================================================

    def _build_edit_mode(self):
        """按截图布局：
        - 第一行：题号(*) + 难度    标题(*) + 状态
        - OJ链接
        - 知识点标签
        - 题意（Markdown 编辑器）
        - 题解（Markdown 编辑器）
        """
        colors = self.config.get_colors()
        pad_x = 20

        # 提示
        self.edit_hint = tk.Label(self.edit_inner,
                                   text='',
                                   font=(self.config.get('font_family'), 9),
                                   bg=colors['bg_main'], fg=colors['fg_muted'], anchor=tk.W,
                                   padx=pad_x)
        self.edit_hint.pack(fill=tk.X, pady=(8, 0))

        # 第一行：题号 (*) + 难度 | 标题 (*) + 状态
        row1 = tk.Frame(self.edit_inner, bg=colors['bg_main'])
        row1.pack(fill=tk.X, padx=pad_x, pady=(8, 0))

        # 左侧：题号
        left1 = tk.Frame(row1, bg=colors['bg_main'])
        left1.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 16))

        tk.Label(left1, text='题号 *', font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(anchor=tk.W)
        self.e_pid = tk.Entry(left1, font=(self.config.get('font_family'), 12),
                               bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT)
        self.e_pid.pack(fill=tk.X, pady=(2, 0), ipady=4)
        self.e_pid.bind('<KeyRelease>', lambda e: self._mark_dirty())

        # 右侧：难度
        right1 = tk.Frame(row1, bg=colors['bg_main'])
        right1.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(right1, text='难度', font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(anchor=tk.W)
        self.e_difficulty = ttk.Combobox(right1, values=DIFFICULTIES, state='readonly')
        self.e_difficulty.pack(fill=tk.X, pady=(2, 0), ipady=2)
        self.e_difficulty.bind('<<ComboboxSelected>>', lambda e: self._mark_dirty())

        # 第二行：标题 + 状态
        row2 = tk.Frame(self.edit_inner, bg=colors['bg_main'])
        row2.pack(fill=tk.X, padx=pad_x, pady=(12, 0))

        left2 = tk.Frame(row2, bg=colors['bg_main'])
        left2.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 16))

        tk.Label(left2, text='标题 *', font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(anchor=tk.W)
        self.e_title = tk.Entry(left2, font=(self.config.get('font_family'), 12),
                                 bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT)
        self.e_title.pack(fill=tk.X, pady=(2, 0), ipady=4)
        self.e_title.bind('<KeyRelease>', lambda e: self._mark_dirty())

        right2 = tk.Frame(row2, bg=colors['bg_main'])
        right2.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(right2, text='状态', font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(anchor=tk.W)
        self.e_status = ttk.Combobox(right2,
                                      values=['进行中', '待做', '已做', '复习'],
                                      state='readonly')
        self.e_status.set('待做')
        self.e_status.pack(fill=tk.X, pady=(2, 0), ipady=2)
        self.e_status.bind('<<ComboboxSelected>>', lambda e: self._mark_dirty())

        # 第三行：OJ链接
        row3 = tk.Frame(self.edit_inner, bg=colors['bg_main'])
        row3.pack(fill=tk.X, padx=pad_x, pady=(12, 0))
        tk.Label(row3, text='OJ链接', font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(anchor=tk.W)
        self.e_url = tk.Entry(row3, font=(self.config.get('font_family'), 11),
                               bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT)
        self.e_url.pack(fill=tk.X, pady=(2, 0), ipady=4)
        self.e_url.bind('<KeyRelease>', lambda e: self._mark_dirty())

        # 第四行：知识点标签
        row4 = tk.Frame(self.edit_inner, bg=colors['bg_main'])
        row4.pack(fill=tk.X, padx=pad_x, pady=(12, 0))
        tk.Label(row4, text='知识点标签', font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(anchor=tk.W)

        tags_row = tk.Frame(row4, bg=colors['bg_main'])
        tags_row.pack(fill=tk.X, pady=(4, 0))

        # 已选标签展示
        self.tags_chips_frame = tk.Frame(tags_row, bg=colors['bg_main'])
        self.tags_chips_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # + 按钮：弹出标签选择对话框
        plus_btn = tk.Label(tags_row, text='+',
                            font=(self.config.get('font_family'), 14, 'bold'),
                            bg=colors['bg_main'], fg=colors['fg_accent'],
                            cursor='hand2', padx=8)
        plus_btn.pack(side=tk.LEFT)
        plus_btn.bind('<Button-1>', lambda e: self._open_tag_picker())
        plus_btn.bind('<Enter>', lambda e, b=plus_btn: b.configure(fg=colors['fg_link']))
        plus_btn.bind('<Leave>', lambda e, b=plus_btn: b.configure(fg=colors['fg_accent']))

        self.e_selected_tags = []  # 当前已选标签列表（顺序保持）
        self._render_tag_chips()

        # 题意 - 分屏编辑器
        self._build_md_editor(self.edit_inner, '题目描述（题意）', 'e_desc')

        # 题解 - 分屏编辑器
        self._build_md_editor(self.edit_inner, '题解', 'e_sol')

        # 底部按钮
        bar = tk.Frame(self.edit_inner, bg=colors['bg_sidebar'], height=40)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        bar.pack_propagate(False)
        tk.Button(bar, text='返回查看', font=(self.config.get('font_family'), 10),
                  bg=colors['bg_sidebar'], fg=colors['fg_primary'], relief=tk.FLAT,
                  padx=16, pady=4, cursor='hand2',
                  command=self._exit_edit).pack(side=tk.RIGHT, padx=8)

    def _build_md_editor(self, parent, label_text: str, key: str):
        """构建分屏 Markdown 编辑器（编辑 / 分屏 / 预览）"""
        colors = self.config.get_colors()
        pad_x = 20

        wrapper = tk.Frame(parent, bg=colors['bg_main'])
        wrapper.pack(fill=tk.BOTH, expand=True, padx=pad_x, pady=(12, 0))

        # 标题 + 模式切换
        header = tk.Frame(wrapper, bg=colors['bg_main'])
        header.pack(fill=tk.X)
        tk.Label(header, text=label_text, font=(self.config.get('font_family'), 11, 'bold'),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(side=tk.LEFT)

        mode_frame = tk.Frame(header, bg=colors['bg_main'])
        mode_frame.pack(side=tk.RIGHT)
        # 模式切换变量
        self.__dict__[f'{key}_mode'] = tk.StringVar(value='edit')

        for mode, text in [('edit', '编辑'), ('split', '分屏'), ('preview', '预览')]:
            rb = tk.Radiobutton(mode_frame, text=text,
                                variable=self.__dict__[f'{key}_mode'], value=mode,
                                font=(self.config.get('font_family'), 9),
                                bg=colors['bg_main'], fg=colors['fg_secondary'],
                                selectcolor=colors['bg_sidebar'],
                                indicatoron=False, padx=8, pady=2,
                                command=lambda k=key: self._refresh_md_editor(k))
            rb.pack(side=tk.LEFT, padx=1)

        # 编辑器 + 预览容器
        content = tk.Frame(wrapper, bg=colors['bg_main'])
        content.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        setattr(self, f'{key}_container', content)

        # 编辑器（Text）
        text = tk.Text(content, font=(self.config.get('code_font_family'), 11),
                       bg=colors['bg_input'], fg=colors['fg_primary'],
                       relief=tk.FLAT, wrap=tk.WORD, undo=True)
        text.bind('<KeyRelease>', lambda e, k=key: self._on_md_text_change(k))
        setattr(self, f'{key}_text', text)

        # 预览（MarkdownView）
        md_view = MarkdownView(content)
        setattr(self, f'{key}_preview', md_view)

        self._refresh_md_editor(key)

    def _refresh_md_editor(self, key: str):
        """根据当前模式刷新编辑器显示"""
        mode = self.__dict__[f'{key}_mode'].get()
        text = getattr(self, f'{key}_text')
        preview = getattr(self, f'{key}_preview')
        container = getattr(self, f'{key}_container')

        for w in container.winfo_children():
            w.pack_forget()

        if mode == 'edit':
            text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        elif mode == 'preview':
            preview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            content = text.get('1.0', tk.END).strip()
            if content:
                from services.markdown_engine import render_markdown
                preview.load_html(render_markdown(content))
        else:  # split
            text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            preview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 0))
            content = text.get('1.0', tk.END).strip()
            if content:
                from services.markdown_engine import render_markdown
                preview.load_html(render_markdown(content))

    def _on_md_text_change(self, key: str):
        """编辑内容变化时，若处于分屏/预览模式则更新预览"""
        self._mark_dirty()
        mode = self.__dict__[f'{key}_mode'].get()
        if mode in ('split', 'preview'):
            self._refresh_md_editor(key)

    # ============================================================
    # 标签选择
    # ============================================================

    def _render_tag_chips(self):
        """渲染已选标签为 chip 块"""
        colors = self.config.get_colors()
        for w in self.tags_chips_frame.winfo_children():
            w.destroy()

        for tag in self.e_selected_tags:
            chip = tk.Frame(self.tags_chips_frame, bg=colors['bg_tag'])
            chip.pack(side=tk.LEFT, padx=(0, 4), pady=2)

            tk.Label(chip, text=tag, font=(self.config.get('font_family'), 10),
                     bg=colors['bg_tag'], fg=colors['fg_link']).pack(side=tk.LEFT, padx=(8, 2), pady=2)

            # X 删除按钮
            x = tk.Label(chip, text='×', font=(self.config.get('font_family'), 11, 'bold'),
                         bg=colors['bg_tag'], fg=colors['fg_link'],
                         cursor='hand2', padx=4)
            x.pack(side=tk.LEFT, pady=2)
            x.bind('<Button-1>', lambda e, t=tag: self._remove_tag(t))
            x.bind('<Enter>', lambda e, b=x: b.configure(fg=colors['danger']))
            x.bind('<Leave>', lambda e, b=x: b.configure(fg=colors['fg_link']))

    def _remove_tag(self, tag: str):
        if tag in self.e_selected_tags:
            self.e_selected_tags.remove(tag)
            self._render_tag_chips()
            self._mark_dirty()

    def _open_tag_picker(self):
        """弹出标签选择对话框"""
        dialog = tk.Toplevel(self.parent)
        dialog.title('选择标签')
        dialog.geometry('700x500')
        dialog.transient(self.parent)
        colors = self.config.get_colors()
        dialog.configure(bg=colors['bg_main'])

        # 搜索
        search_fr = tk.Frame(dialog, bg=colors['bg_sidebar'])
        search_fr.pack(fill=tk.X)
        tk.Label(search_fr, text='搜索:', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_sidebar'], fg=colors['fg_secondary']).pack(side=tk.LEFT, padx=8, pady=8)
        search_var = tk.StringVar()
        search_var.trace_add('write', lambda *a: _refresh_tags_list())
        tk.Entry(search_fr, textvariable=search_var, font=(self.config.get('font_family'), 11),
                 bg=colors['bg_input'], fg=colors['fg_primary'],
                 relief=tk.FLAT).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8), pady=8)

        # 标签列表（按大类分组）
        canvas = tk.Canvas(dialog, bg=colors['bg_main'], highlightthickness=0)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        scroll = ttk.Scrollbar(dialog, orient=tk.VERTICAL, command=canvas.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=(0, 8))
        canvas.configure(yscrollcommand=scroll.set)

        inner = tk.Frame(canvas, bg=colors['bg_main'])
        canvas.create_window((0, 0), window=inner, anchor=tk.NW)
        inner.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))

        def _refresh_tags_list():
            for w in inner.winfo_children():
                w.destroy()
            s = search_var.get().lower().strip()
            for cat in PROBLEM_CATEGORIES:
                cat_tags = [t for t in self._all_tags if t['category'] == cat]
                if s:
                    cat_tags = [t for t in cat_tags if s in t['name'].lower()]
                if not cat_tags:
                    continue
                # 大类标题
                tk.Label(inner, text=cat,
                         font=(self.config.get('font_family'), 11, 'bold'),
                         bg=colors['bg_main'], fg=colors['fg_accent']
                         ).pack(anchor=tk.W, pady=(6, 4))
                # 标签按钮
                row = tk.Frame(inner, bg=colors['bg_main'])
                row.pack(fill=tk.X)
                col_count = 5
                for i, tag_info in enumerate(cat_tags):
                    is_selected = tag_info['name'] in self.e_selected_tags
                    color_bg = colors['bg_tag'] if is_selected else colors['bg_main']
                    color_fg = colors['fg_link'] if is_selected else colors['fg_primary']
                    btn = tk.Label(row, text=tag_info['name'],
                                   font=(self.config.get('font_family'), 10),
                                   bg=color_bg, fg=color_fg,
                                   relief=tk.FLAT, bd=1, padx=8, pady=2,
                                   cursor='hand2')
                    btn.grid(row=i // col_count, column=i % col_count,
                             sticky=tk.W, padx=2, pady=2)
                    btn.bind('<Button-1>', lambda e, n=tag_info['name']: self._toggle_tag(n))
                    btn.bind('<Enter>', lambda e, b=btn: b.configure(bg=colors['bg_tag'], fg=colors['fg_link']))
                    btn.bind('<Leave>', lambda e, b=btn, sel=is_selected: b.configure(
                        bg=colors['bg_tag'] if sel else colors['bg_main'],
                        fg=colors['fg_link'] if sel else colors['fg_primary']))

        def _on_close():
            dialog.destroy()
            self._render_tag_chips()

        def _on_ok():
            _on_close()

        # 按钮
        btn_fr = tk.Frame(dialog, bg=colors['bg_main'])
        btn_fr.pack(fill=tk.X, padx=8, pady=(0, 8))
        tk.Button(btn_fr, text='关闭', font=(self.config.get('font_family'), 11),
                  bg=colors['bg_sidebar'], fg=colors['fg_primary'],
                  relief=tk.FLAT, padx=20, pady=6,
                  command=_on_ok).pack(side=tk.RIGHT)

        _refresh_tags_list()

    def _toggle_tag(self, tag_name: str):
        if tag_name in self.e_selected_tags:
            self.e_selected_tags.remove(tag_name)
        else:
            self.e_selected_tags.append(tag_name)
        self._mark_dirty()
        # 刷新当前对话框
        for child in self.parent.winfo_children():
            if isinstance(child, tk.Toplevel) and child.title() == '选择标签':
                # 重新渲染：调用 _open_tag_picker 不合适，简单刷新
                break
        self._render_tag_chips()

    # ============================================================
    # 编辑表单填充/清空
    # ============================================================

    def _clear_edit_form(self):
        self.e_pid.delete(0, tk.END)
        self.e_title.delete(0, tk.END)
        self.e_url.delete(0, tk.END)
        try:
            self.e_difficulty.set('入门')
        except Exception:
            pass
        self.e_status.set('待做')
        self.e_selected_tags = []
        self._render_tag_chips()
        self.e_desc_text.delete('1.0', tk.END)
        self.e_sol_text.delete('1.0', tk.END)
        self._dirty = False

    def _fill_edit_form(self, row: dict):
        self.e_pid.delete(0, tk.END)
        self.e_pid.insert(0, row.get('platform_id', ''))
        self.e_title.delete(0, tk.END)
        self.e_title.insert(0, row.get('title', ''))
        self.e_url.delete(0, tk.END)
        self.e_url.insert(0, row.get('url', ''))
        try:
            self.e_difficulty.set(row.get('difficulty', '入门'))
        except Exception:
            pass
        try:
            self.e_status.set(STATUSES.get(row.get('status', 'todo'), '待做'))
        except Exception:
            pass
        try:
            tags = json.loads(row.get('tags') or '[]')
        except Exception:
            tags = []
        self.e_selected_tags = tags
        self._render_tag_chips()
        self.e_desc_text.delete('1.0', tk.END)
        self.e_desc_text.insert('1.0', row.get('description', ''))
        self.e_sol_text.delete('1.0', tk.END)
        self.e_sol_text.insert('1.0', row.get('solution', ''))
        self._dirty = False

    def _mark_dirty(self):
        self._dirty = True

    # ============================================================
    # 交互
    # ============================================================

    def _view_problem(self, problem_id: int):
        self._auto_save()
        self._current_id = problem_id
        self._show_frame('view')
        self._load_view()

    def _edit_problem(self, problem_id: int):
        self._auto_save()
        self._current_id = problem_id
        try:
            conn = get_connection()
            row = conn.execute("SELECT * FROM problems WHERE id=?", (problem_id,)).fetchone()
            conn.close()
            if row:
                self.edit_hint.config(text='编辑完成后切换题目或模块将自动保存')
                self._fill_edit_form(dict(row))
                self._show_frame('edit')
        except Exception as e:
            self.app.set_status(f'加载失败: {e}')

    def _start_add(self):
        self._auto_save()
        self._current_id = None
        self.edit_hint.config(text='录入完成后切换题目或模块将自动保存')
        self._clear_edit_form()
        try:
            self.e_difficulty.set('入门')
            self.e_status.set('待做')
        except Exception:
            pass
        self._show_frame('edit')

    def _exit_edit(self):
        self._auto_save()
        if self._current_id:
            self._show_frame('view')
            self._load_view()
        else:
            self._show_frame('empty')

    # ============================================================
    # 自动保存
    # ============================================================

    def _auto_save(self):
        if self._mode != 'edit' or not self._dirty:
            return
        title = self.e_title.get().strip()
        if not title and not self._current_id:
            return

        try:
            difficulty = self.e_difficulty.get()
        except Exception:
            difficulty = '入门'
        try:
            status_cn = self.e_status.get()
            status_en = {v: k for k, v in STATUSES.items()}.get(status_cn, 'todo')
        except Exception:
            status_en = 'todo'

        pid = self.e_pid.get().strip()
        url = self.e_url.get().strip()
        tags = json.dumps(self.e_selected_tags, ensure_ascii=False)
        desc = self.e_desc_text.get('1.0', tk.END).strip()
        sol = self.e_sol_text.get('1.0', tk.END).strip()

        try:
            conn = get_connection()
            if self._current_id:
                conn.execute(
                    """UPDATE problems SET title=?, platform_id=?, difficulty=?,
                       tags=?, description=?, solution=?, url=?, status=?,
                       updated_at=datetime('now','localtime')
                       WHERE id=?""",
                    (title, pid, difficulty, tags, desc, sol, url, status_en, self._current_id))
            else:
                cursor = conn.execute(
                    """INSERT INTO problems (title, platform, platform_id, difficulty, tags,
                       description, solution, url, status)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (title, '洛谷', pid, difficulty, tags, desc, sol, url, status_en))
                self._current_id = cursor.lastrowid
            conn.commit()
            conn.close()
        except Exception as e:
            self.app.set_status(f'保存失败: {e}')
            return

        self._dirty = False
        self._refresh_list()
        self.app.set_status(f'已自动保存「{title}」')

    # ============================================================
    # 删除
    # ============================================================

    def _delete_problem(self, problem_id: int):
        if not messagebox.askyesno('确认删除', '确定要删除这个题目吗？'):
            return
        try:
            conn = get_connection()
            conn.execute("DELETE FROM problems WHERE id=?", (problem_id,))
            conn.commit()
            conn.close()
            if problem_id == self._current_id:
                self._current_id = None
                self._show_frame('empty')
            self._refresh_list()
            self.app.set_status('题目已删除')
        except Exception as e:
            self.app.set_status(f'删除失败: {e}')

    def _delete_current(self):
        if self._current_id:
            self._delete_problem(self._current_id)

    # ============================================================
    # 生命周期
    # ============================================================

    def on_before_leave(self):
        self._auto_save()

    def on_new(self):
        self._start_add()

    def on_export(self):
        from services.exporter import export_problems_to_md
        path = export_problems_to_md()
        if path:
            self.app.set_status(f'已导出: {path}')
        else:
            self.app.set_status('暂无数据可导出')

    def apply_theme(self):
        self._auto_save()
        for w in self.parent.winfo_children():
            w.destroy()
        self._build_ui()
        self._refresh_list()