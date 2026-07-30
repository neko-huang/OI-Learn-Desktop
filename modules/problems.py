"""
刷题记录模块
- 左侧栏可折叠，含搜索筛选
- 点击题目 → 查看模式（可改状态）
- 点击编辑 → 右侧编辑模式（全字段）
- 录入内嵌，离开自动保存
"""

import json
import tkinter as tk
from tkinter import ttk, messagebox

from config import Config
from db.database import get_connection
from components.markdown_view import MarkdownView

DIFFICULTIES = ['暂未评定', '入门', '普及−', '普及', '普及+', '提高−', '提高', '提高+', '省选−', '省选', 'NOI−', 'NOI']
PLATFORMS = ['Codeforces', '洛谷', 'AtCoder', 'USACO', 'POJ', 'HDU', 'VJudge', '其他']
STATUSES = {'todo': '待做', 'done': '已做', 'review': '复习'}
STATUS_SYMBOLS = {'todo': '○', 'done': '●', 'review': '⟳'}
TAGS = [
    '模拟', '贪心', '二分', '枚举', '分治', '排序', '双指针', '滑动窗口',
    '栈', '队列', '链表', '哈希', '前缀和', '差分', 'ST表', '分块',
    '并查集', '树状数组', '线段树', '堆', '平衡树', 'Trie',
    'LCA', '树链剖分', '点分治', '基环树', 'BFS', 'DFS',
    '拓扑排序', 'Dijkstra', 'Floyd', 'MST', 'SCC', '网络流', '二分图', '2-SAT',
    '剪枝', '记忆化', 'A*', 'IDA*', '双向BFS', 'DLX',
    '背包DP', '区间DP', '树形DP', '状压DP', '数位DP',
    '斜率优化', '矩阵加速', 'WQS二分',
    'KMP', 'AC自动机', 'SA', 'SAM', 'Manacher',
    '数论', '组合数学', '博弈论', '概率期望',
    'FFT', 'NTT', '计算几何', '构造', '交互',
]


class ProblemsModule:

    def __init__(self, app, parent_frame):
        self.app = app
        self.config = Config()
        self.parent = parent_frame
        for w in parent_frame.winfo_children():
            w.destroy()

        self._current_id = None       # 正在查看/编辑的题目ID
        self._mode = 'view'           # 'view' | 'edit' | 'add' | 'empty'
        self._dirty = False           # 编辑内容未保存
        self._left_visible = True     # 左侧栏可见
        self._problems_cache = []

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
        self.toggle_btn = tk.Label(top, text='◀', font=(self.config.get('font_family'), 12),
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

        # 状态筛选
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
                      values=['全部'] + DIFFICULTIES, state='readonly', width=10
                      ).pack(side=tk.LEFT, padx=(4, 12))
        self.filter_diff.trace_add('write', lambda *a: self._refresh_list())

        tk.Frame(top, bg=colors['bg_sidebar']).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 录入按钮
        tk.Button(top, text='+ 新建', font=(self.config.get('font_family'), 10),
                  bg=colors['fg_accent'], fg='#ffffff', relief=tk.FLAT,
                  padx=16, pady=4, cursor='hand2',
                  command=self._start_add).pack(side=tk.RIGHT, padx=8, pady=8)

        # 主体区
        self.main_area = tk.Frame(self.parent, bg=colors['bg_main'])
        self.main_area.pack(fill=tk.BOTH, expand=True)

        self._build_left()
        self._build_right()

    # ============================================================
    # 左侧栏（可折叠）
    # ============================================================

    def _build_left(self):
        colors = self.config.get_colors()
        self.left_wrapper = tk.Frame(self.main_area, bg=colors['bg_sidebar'])
        self.left_wrapper.pack(side=tk.LEFT, fill=tk.Y)
        # 初始宽度在 _toggle 中设置

        self.left_panel = tk.Frame(self.left_wrapper, bg=colors['bg_sidebar'])
        self.left_panel.pack(fill=tk.BOTH, expand=True)

        tk.Label(self.left_panel, text='题目列表', font=(self.config.get('font_family'), 12, 'bold'),
                 bg=colors['bg_sidebar'], fg=colors['fg_primary']).pack(anchor=tk.W, padx=12, pady=(6, 2))

        self.list_canvas = tk.Canvas(self.left_panel, bg=colors['bg_sidebar'], highlightthickness=0)
        self.list_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(self.left_panel, orient=tk.VERTICAL, command=self.list_canvas.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.list_canvas.configure(yscrollcommand=scroll.set)

        self.list_inner = tk.Frame(self.list_canvas, bg=colors['bg_sidebar'])
        self._list_win = self.list_canvas.create_window((0, 0), window=self.list_inner, anchor=tk.NW)
        self.list_canvas.bind('<Configure>', lambda e: self.list_canvas.itemconfig(self._list_win, width=e.width))
        self.list_inner.bind('<Configure>', lambda e: self.list_canvas.configure(scrollregion=self.list_canvas.bbox('all')))

    def _toggle_left_panel(self):
        """折叠/展开左侧栏"""
        if self._left_visible:
            self.left_wrapper.pack_forget()
            self.toggle_btn.config(text='▶')
        else:
            self.left_wrapper.pack(side=tk.LEFT, fill=tk.Y, before=self.right_wrapper)
            self.toggle_btn.config(text='◀')
        self._left_visible = not self._left_visible

    def _refresh_list(self):
        """刷新左侧题目列表"""
        for w in self.list_inner.winfo_children():
            w.destroy()

        search = self.search_var.get().lower().strip()
        sf = self.filter_status.get()
        df = self.filter_diff.get()

        try:
            conn = get_connection()
            rows = conn.execute(
                "SELECT id, title, platform, platform_id, difficulty, tags, status FROM problems ORDER BY updated_at DESC"
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
            # 搜索：标题 或 题号
            if search:
                title_low = row['title'].lower()
                pid_low = (row.get('platform_id') or '').lower()
                if search not in title_low and search not in pid_low:
                    continue

            count += 1
            rf = tk.Frame(self.list_inner, bg=colors['bg_sidebar'])
            rf.pack(fill=tk.X, padx=8, pady=1)

            sym = STATUS_SYMBOLS.get(row['status'], '○')
            pid_str = f' [{row["platform_id"]}]' if row.get('platform_id') else ''

            # 标题（点击查看）
            lb = tk.Label(rf, text=f'{sym} {row["title"]}{pid_str}',
                          font=(self.config.get('font_family'), 10),
                          bg=colors['bg_sidebar'], fg=colors['fg_primary'],
                          anchor=tk.W, cursor='hand2')
            lb.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))
            lb.bind('<Button-1>', lambda e, pid=row['id']: self._view_problem(pid))
            lb.bind('<Enter>', lambda e, l=lb: l.configure(fg=colors['fg_accent']))
            lb.bind('<Leave>', lambda e, l=lb: l.configure(fg=colors['fg_primary']))

            # 编辑按钮
            eb = tk.Label(rf, text='编辑', font=(self.config.get('font_family'), 9),
                          bg=colors['bg_sidebar'], fg=colors['fg_accent'],
                          cursor='hand2', padx=6)
            eb.pack(side=tk.RIGHT, padx=(0, 4))
            eb.bind('<Button-1>', lambda e, pid=row['id']: self._edit_problem(pid))
            eb.bind('<Enter>', lambda e, b=eb: b.configure(fg=colors['fg_link']))
            eb.bind('<Leave>', lambda e, b=eb: b.configure(fg=colors['fg_accent']))

        if count == 0:
            tk.Label(self.list_inner, text='(暂无题目)', font=(self.config.get('font_family'), 10),
                     bg=colors['bg_sidebar'], fg=colors['fg_muted']).pack(pady=20)

    # ============================================================
    # 右侧 — 三种模式
    # ============================================================

    def _build_right(self):
        colors = self.config.get_colors()
        self.right_wrapper = tk.Frame(self.main_area, bg=colors['bg_main'])
        self.right_wrapper.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 查看模式
        self.view_frame = tk.Frame(self.right_wrapper, bg=colors['bg_main'])
        self._build_view_mode()
        # 编辑模式
        self.edit_frame = tk.Frame(self.right_wrapper, bg=colors['bg_main'])
        self._build_edit_mode()
        # 空状态
        self.empty_frame = tk.Frame(self.right_wrapper, bg=colors['bg_main'])
        self._build_empty()

        self._show_frame('empty')

    def _show_frame(self, name: str):
        self._mode = name
        for n in ('view', 'edit', 'empty'):
            getattr(self, f'{n}_frame').pack_forget()
        getattr(self, f'{name}_frame').pack(fill=tk.BOTH, expand=True)

    # ============================================================
    # 空状态
    # ============================================================

    def _build_empty(self):
        colors = self.config.get_colors()
        tk.Label(self.empty_frame, text='选择一个题目查看\n或点击「+ 新建」录入新题',
                 font=(self.config.get('font_family'), 14),
                 bg=colors['bg_main'], fg=colors['fg_muted']
                 ).place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    # ============================================================
    # 查看模式
    # ============================================================

    def _build_view_mode(self):
        colors = self.config.get_colors()

        # 标题行
        self.view_title = tk.Label(self.view_frame, text='',
                                    font=(self.config.get('font_family'), 18, 'bold'),
                                    bg=colors['bg_main'], fg=colors['fg_primary'], anchor=tk.W)
        self.view_title.pack(fill=tk.X, padx=16, pady=(12, 4))

        # 元信息 + 状态修改
        meta = tk.Frame(self.view_frame, bg=colors['bg_main'])
        meta.pack(fill=tk.X, padx=16, pady=(0, 4))
        self.view_meta = tk.Label(meta, text='', font=(self.config.get('font_family'), 10),
                                   bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.W)
        self.view_meta.pack(side=tk.LEFT)

        # 状态切换（直接改）
        self.view_status_var = tk.StringVar()
        status_fr = tk.Frame(meta, bg=colors['bg_main'])
        status_fr.pack(side=tk.RIGHT)
        for val, txt in STATUSES.items():
            tk.Radiobutton(status_fr, text=txt, variable=self.view_status_var, value=val,
                           font=(self.config.get('font_family'), 9),
                           bg=colors['bg_main'], fg=colors['fg_primary'],
                           selectcolor=colors['bg_sidebar'],
                           command=self._on_view_status_change).pack(side=tk.LEFT, padx=(4, 0))

        # 分隔线
        tk.Frame(self.view_frame, bg=colors['border'], height=1).pack(fill=tk.X, padx=16, pady=4)

        # Markdown 内容（题意 + 题解）
        self.view_md = MarkdownView(self.view_frame)
        self.view_md.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 4))

        # 底部按钮
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

            # 元信息
            parts = [f'平台: {row["platform"]}']
            if row.get('platform_id'):
                parts.append(f'编号: {row["platform_id"]}')
            parts.append(f'难度: {row["difficulty"]}')
            if row.get('url'):
                parts.append(f'链接: {row["url"]}')
            try:
                tags = json.loads(row.get('tags') or '[]')
                if tags:
                    parts.append(f'标签: {", ".join(tags)}')
            except Exception:
                pass
            self.view_meta.config(text='  |  '.join(parts))

            # Markdown
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
        """查看模式下直接改状态"""
        if not self._current_id:
            return
        new_status = self.view_status_var.get()
        try:
            conn = get_connection()
            conn.execute(
                "UPDATE problems SET status=?, updated_at=datetime('now','localtime') WHERE id=?",
                (new_status, self._current_id))
            conn.commit()
            conn.close()
            self._refresh_list()
            self.app.set_status(f'状态已更新为「{STATUSES[new_status]}」')
        except Exception as e:
            self.app.set_status(f'状态更新失败: {e}')

    # ============================================================
    # 编辑模式（含录入）
    # ============================================================

    def _build_edit_mode(self):
        colors = self.config.get_colors()
        pad_x = 16

        # 提示
        self.edit_hint = tk.Label(self.edit_frame,
                                   text='',
                                   font=(self.config.get('font_family'), 9),
                                   bg=colors['bg_main'], fg=colors['fg_muted'], anchor=tk.W,
                                   padx=pad_x)
        self.edit_hint.pack(fill=tk.X, pady=(4, 0))

        # 标题行
        tk.Label(self.edit_frame, text='题目名称', font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.W).pack(fill=tk.X, padx=pad_x, pady=(8, 0))
        self.e_title = tk.Entry(self.edit_frame, font=(self.config.get('font_family'), 13, 'bold'),
                                 bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT)
        self.e_title.pack(fill=tk.X, padx=pad_x, pady=(0, 2))
        self.e_title.bind('<KeyRelease>', lambda e: self._mark_dirty())

        # 平台 + 编号 + 难度
        row1 = tk.Frame(self.edit_frame, bg=colors['bg_main'])
        row1.pack(fill=tk.X, padx=pad_x, pady=(4, 2))
        for label, var_name, values, w in [
            ('平台', 'e_platform', PLATFORMS, 14),
            ('编号', 'e_pid', None, 16),
            ('难度', 'e_difficulty', DIFFICULTIES, 12),
        ]:
            tk.Label(row1, text=label, font=(self.config.get('font_family'), 10),
                     bg=colors['bg_main'], fg=colors['fg_secondary']).pack(side=tk.LEFT)
            if values:
                cb = ttk.Combobox(row1, values=values, state='readonly', width=w)
                setattr(self, var_name, cb)
                cb.pack(side=tk.LEFT, padx=(2, 14))
                cb.bind('<<ComboboxSelected>>', lambda e: self._mark_dirty())
            else:
                entry = tk.Entry(row1, font=(self.config.get('font_family'), 10),
                                  bg=colors['bg_input'], fg=colors['fg_primary'],
                                  relief=tk.FLAT, width=w)
                setattr(self, var_name, entry)
                entry.pack(side=tk.LEFT, padx=(2, 14))
                entry.bind('<KeyRelease>', lambda e: self._mark_dirty())

        # 链接
        tk.Label(self.edit_frame, text='题目链接', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.W).pack(fill=tk.X, padx=pad_x, pady=(4, 0))
        self.e_url = tk.Entry(self.edit_frame, font=(self.config.get('font_family'), 10),
                               bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT)
        self.e_url.pack(fill=tk.X, padx=pad_x, pady=(0, 2))
        self.e_url.bind('<KeyRelease>', lambda e: self._mark_dirty())

        # 标签
        tk.Label(self.edit_frame, text='算法标签', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.W).pack(fill=tk.X, padx=pad_x, pady=(4, 0))

        tags_canvas = tk.Canvas(self.edit_frame, bg=colors['bg_main'], height=95, highlightthickness=0)
        tags_canvas.pack(fill=tk.X, padx=pad_x, pady=(0, 2))
        self.e_tags_frame = tk.Frame(tags_canvas, bg=colors['bg_main'])
        tags_canvas.create_window((0, 0), window=self.e_tags_frame, anchor=tk.NW)
        self.e_tags_vars = {}
        col = 0
        for i, tag in enumerate(TAGS):
            var = tk.BooleanVar()
            var.trace_add('write', lambda *a: self._mark_dirty())
            cb = tk.Checkbutton(self.e_tags_frame, text=tag, variable=var,
                                font=(self.config.get('font_family'), 9),
                                bg=colors['bg_main'], fg=colors['fg_primary'],
                                selectcolor=colors['bg_sidebar'])
            cb.grid(row=i // 7, column=i % 7, sticky=tk.W, padx=2, pady=1)
            self.e_tags_vars[tag] = var

        # 题意
        tk.Label(self.edit_frame, text='题意（Markdown）', font=(self.config.get('font_family'), 11, 'bold'),
                 bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.W).pack(fill=tk.X, padx=pad_x, pady=(8, 0))
        self.e_desc = tk.Text(self.edit_frame, font=(self.config.get('code_font_family'), 11),
                               bg=colors['bg_input'], fg=colors['fg_primary'],
                               relief=tk.FLAT, wrap=tk.WORD, height=4, undo=True)
        self.e_desc.pack(fill=tk.X, padx=pad_x, pady=(0, 2))
        self.e_desc.bind('<<Modified>>', lambda e: self._mark_dirty())

        # 题解
        tk.Label(self.edit_frame, text='题解（Markdown）', font=(self.config.get('font_family'), 11, 'bold'),
                 bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.W).pack(fill=tk.X, padx=pad_x, pady=(8, 0))
        self.e_sol = tk.Text(self.edit_frame, font=(self.config.get('code_font_family'), 11),
                              bg=colors['bg_input'], fg=colors['fg_primary'],
                              relief=tk.FLAT, wrap=tk.WORD, height=1, undo=True)
        self.e_sol.pack(fill=tk.BOTH, expand=True, padx=pad_x, pady=(0, 2))
        self.e_sol.bind('<<Modified>>', lambda e: self._mark_dirty())

        # 底部
        bar = tk.Frame(self.edit_frame, bg=colors['bg_sidebar'], height=40)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        bar.pack_propagate(False)
        tk.Button(bar, text='返回查看', font=(self.config.get('font_family'), 10),
                  bg=colors['bg_sidebar'], fg=colors['fg_primary'], relief=tk.FLAT,
                  padx=16, pady=4, cursor='hand2',
                  command=self._exit_edit).pack(side=tk.RIGHT, padx=8)

    def _clear_edit_form(self):
        """清空编辑表单（录入模式）"""
        self.e_title.delete(0, tk.END)
        try:
            self.e_platform.set('洛谷')
        except Exception:
            pass
        try:
            self.e_difficulty.set('暂未评定')
        except Exception:
            pass
        self.e_pid.delete(0, tk.END)
        self.e_url.delete(0, tk.END)
        for var in self.e_tags_vars.values():
            var.set(False)
        self.e_desc.delete('1.0', tk.END)
        self.e_desc.edit_modified(False)
        self.e_sol.delete('1.0', tk.END)
        self.e_sol.edit_modified(False)
        self._dirty = False

    def _fill_edit_form(self, row: dict):
        """填充编辑表单"""
        title = row.get('title', '')
        platform = row.get('platform', '洛谷')
        pid = row.get('platform_id', '')
        diff = row.get('difficulty', '暂未评定')
        url = row.get('url', '')
        desc = row.get('description', '')
        sol = row.get('solution', '')

        self.e_title.delete(0, tk.END)
        self.e_title.insert(0, title)

        # Combobox set
        try:
            self.e_platform.set(platform)
        except Exception:
            pass
        try:
            self.e_difficulty.set(diff)
        except Exception:
            pass

        self.e_pid.delete(0, tk.END)
        self.e_pid.insert(0, pid)

        self.e_url.delete(0, tk.END)
        self.e_url.insert(0, url)

        # Tags
        try:
            tags = json.loads(row.get('tags') or '[]')
        except Exception:
            tags = []
        for tag, var in self.e_tags_vars.items():
            var.set(tag in tags)

        self.e_desc.delete('1.0', tk.END)
        self.e_desc.insert('1.0', desc)
        self.e_desc.edit_modified(False)

        self.e_sol.delete('1.0', tk.END)
        self.e_sol.insert('1.0', sol)
        self.e_sol.edit_modified(False)

        self._dirty = False

    def _mark_dirty(self):
        self._dirty = True

    # ============================================================
    # 交互：查看 / 编辑 / 录入
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
            self.app.set_status(f'加载编辑表单失败: {e}')

    def _start_add(self):
        """开始录入新题"""
        self._auto_save()
        self._current_id = None
        self.edit_hint.config(text='录入完成后切换题目或模块将自动保存')
        self._clear_edit_form()
        self._show_frame('edit')

    def _exit_edit(self):
        """退出编辑 → 查看"""
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
        """离开编辑/录入时自动保存"""
        if self._mode not in ('edit',) or not self._dirty:
            return

        title = self.e_title.get().strip()
        if not title and not self._current_id:
            return  # 录入模式但没标题

        try:
            platform = self.e_platform.get()
        except Exception:
            platform = '洛谷'
        try:
            difficulty = self.e_difficulty.get()
        except Exception:
            difficulty = '暂未评定'
        pid = self.e_pid.get().strip()
        url = self.e_url.get().strip()
        tags = json.dumps([t for t, v in self.e_tags_vars.items() if v.get()], ensure_ascii=False)
        desc = self.e_desc.get('1.0', tk.END).strip()
        sol = self.e_sol.get('1.0', tk.END).strip()

        conn = get_connection()
        if self._current_id:
            # 更新已有题目
            conn.execute(
                """UPDATE problems SET title=?, platform=?, platform_id=?, difficulty=?,
                   tags=?, description=?, solution=?, url=?,
                   updated_at=datetime('now','localtime')
                   WHERE id=?""",
                (title, platform, pid, difficulty, tags, desc, sol, url, self._current_id))
        else:
            # 新建题目
            cursor = conn.execute(
                """INSERT INTO problems (title, platform, platform_id, difficulty, tags,
                   description, solution, url)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (title, platform, pid, difficulty, tags, desc, sol, url))
            self._current_id = cursor.lastrowid

        conn.commit()
        conn.close()
        self._dirty = False

        # 重置 modified 标记
        self.e_desc.edit_modified(False)
        self.e_sol.edit_modified(False)

        self._refresh_list()
        self.app.set_status(f'已自动保存「{title or "..."}」')
    # ============================================================
    # 删除
    # ============================================================

    def _delete_current(self):
        if not self._current_id:
            return
        if not messagebox.askyesno('确认删除', '确定要删除这个题目吗？'):
            return
        try:
            conn = get_connection()
            conn.execute("DELETE FROM problems WHERE id=?", (self._current_id,))
            conn.commit()
            conn.close()
            self._current_id = None
            self._refresh_list()
            self._show_frame('empty')
            self.app.set_status('题目已删除')
        except Exception as e:
            self.app.set_status(f'删除失败: {e}')

    # ============================================================
    # 生命周期钩子
    # ============================================================

    def on_before_leave(self):
        self._auto_save()

    def on_new(self):
        self._start_add()

    def apply_theme(self):
        self._auto_save()
        for w in self.parent.winfo_children():
            w.destroy()
        self._build_ui()
        self._refresh_list()
