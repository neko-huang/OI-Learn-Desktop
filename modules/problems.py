"""
刷题记录模块
三子视图：录入题目 / 题目列表 / 题目详情
支持 Markdown 题解编辑、难度标签筛选、状态管理
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
TAGS = [
    '模拟', '贪心', '二分', '枚举', '分治', '排序', '双指针', '滑动窗口',
    '栈', '队列', '链表', '哈希', '前缀和', '差分', 'ST表', '分块',
    '并查集', '树状数组', '线段树', '堆', '平衡树', 'Trie', 'LCT',
    'LCA', '树链剖分', '点分治', '基环树',
    'BFS', 'DFS', '拓扑排序', 'Dijkstra', 'Floyd', 'MST',
    'SCC', '网络流', '二分图', '2-SAT', '欧拉回路',
    '剪枝', '记忆化', 'A*', 'IDA*', '双向BFS', 'DLX',
    '背包DP', '区间DP', '树形DP', '状压DP', '数位DP',
    '斜率优化', '矩阵加速', 'WQS二分',
    'KMP', 'AC自动机', 'SA', 'SAM', 'Manacher',
    '数论', '组合数学', '博弈论', '概率期望',
    'FFT', 'NTT', '生成函数', '计算几何', '构造', '交互',
]


class ProblemsModule:
    """刷题记录模块"""

    def __init__(self, app, parent_frame: tk.Frame):
        self.app = app
        self.config = Config()
        self.parent = parent_frame
        for w in parent_frame.winfo_children():
            w.destroy()

        self._current_view = 'list'
        self._current_problem_id = None

        self._build_ui()
        self._show_view('list')

    # ============================================================
    # UI 框架
    # ============================================================

    def _build_ui(self):
        colors = self.config.get_colors()

        # 子标签栏
        sub_nav = tk.Frame(self.parent, bg=colors['bg_sidebar'], height=36)
        sub_nav.pack(fill=tk.X)
        sub_nav.pack_propagate(False)

        self.sub_buttons = {}
        for view_id, name in [('add', '录入'), ('list', '列表'), ('detail', '详情')]:
            btn = tk.Label(
                sub_nav, text=name,
                font=(self.config.get('font_family'), 11),
                cursor='hand2', padx=16, pady=6,
                bg=colors['bg_sidebar'], fg=colors['fg_secondary'],
            )
            btn.pack(side=tk.LEFT, padx=0)
            btn.bind('<Button-1>', lambda e, v=view_id: self._show_view(v))
            self.sub_buttons[view_id] = btn

        # 内容容器
        self.view_frame = tk.Frame(self.parent, bg=colors['bg_main'])
        self.view_frame.pack(fill=tk.BOTH, expand=True)

        # 子视图容器
        self._views = {}
        for name in ('add', 'list', 'detail'):
            self._views[name] = tk.Frame(self.view_frame, bg=colors['bg_main'])

        self._build_add_view()
        self._build_list_view()
        self._build_detail_view()

    def _show_view(self, view_id: str):
        colors = self.config.get_colors()
        for vid, btn in self.sub_buttons.items():
            if vid == view_id:
                btn.config(fg=colors['fg_accent'], font=(self.config.get('font_family'), 11, 'bold'))
            else:
                btn.config(fg=colors['fg_secondary'], font=(self.config.get('font_family'), 11))

        for v in self._views.values():
            v.pack_forget()

        self._views[view_id].pack(fill=tk.BOTH, expand=True)
        self._current_view = view_id

        if view_id == 'list':
            self._refresh_problem_list()

    # ============================================================
    # 录入视图
    # ============================================================

    def _build_add_view(self):
        parent = self._views['add']
        colors = self.config.get_colors()

        canvas = tk.Canvas(parent, bg=colors['bg_main'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=colors['bg_main'])

        scroll_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=scroll_frame, anchor=tk.NW, width=660)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def label(text):
            return tk.Label(scroll_frame, text=text, font=(self.config.get('font_family'), 11),
                            bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.W)

        # 标题
        tk.Label(scroll_frame, text='录入新题目', font=(self.config.get('font_family'), 18, 'bold'),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(anchor=tk.W, padx=24, pady=(16, 8))

        # 题目标题
        label('题目名称').pack(anchor=tk.W, padx=24, pady=(8, 2))
        self.add_title = tk.Entry(scroll_frame, font=(self.config.get('font_family'), 12),
                                   bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT)
        self.add_title.pack(fill=tk.X, padx=24, pady=(0, 4))

        # 平台
        label('OJ 平台').pack(anchor=tk.W, padx=24, pady=(8, 2))
        self.add_platform_var = tk.StringVar(value='洛谷')
        ttk.Combobox(scroll_frame, textvariable=self.add_platform_var,
                      values=PLATFORMS, state='readonly', width=16).pack(anchor=tk.W, padx=24, pady=(0, 4))

        # 题目链接
        label('题目链接').pack(anchor=tk.W, padx=24, pady=(8, 2))
        self.add_url = tk.Entry(scroll_frame, font=(self.config.get('font_family'), 11),
                                 bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT)
        self.add_url.pack(fill=tk.X, padx=24, pady=(0, 4))

        # 平台 ID
        label('题目编号（如 CF 1500A）').pack(anchor=tk.W, padx=24, pady=(8, 2))
        self.add_pid = tk.Entry(scroll_frame, font=(self.config.get('font_family'), 11),
                                 bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT)
        self.add_pid.pack(fill=tk.X, padx=24, pady=(0, 4))

        # 难度
        label('难度').pack(anchor=tk.W, padx=24, pady=(8, 2))
        self.add_diff_var = tk.StringVar(value='暂未评定')
        ttk.Combobox(scroll_frame, textvariable=self.add_diff_var,
                      values=DIFFICULTIES, state='readonly', width=16).pack(anchor=tk.W, padx=24, pady=(0, 4))

        # 状态
        label('做题状态').pack(anchor=tk.W, padx=24, pady=(8, 2))
        status_frame = tk.Frame(scroll_frame, bg=colors['bg_main'])
        status_frame.pack(anchor=tk.W, padx=24, pady=(0, 4))
        self.add_status_var = tk.StringVar(value='todo')
        for val, txt in STATUSES.items():
            tk.Radiobutton(status_frame, text=txt, variable=self.add_status_var, value=val,
                           font=(self.config.get('font_family'), 10),
                           bg=colors['bg_main'], fg=colors['fg_primary'],
                           selectcolor=colors['bg_sidebar']).pack(side=tk.LEFT, padx=(0, 16))

        # 标签
        label('算法标签（多选）').pack(anchor=tk.W, padx=24, pady=(8, 2))
        self.add_tags_vars = {}
        tags_frame = tk.Frame(scroll_frame, bg=colors['bg_main'])
        tags_frame.pack(fill=tk.X, padx=24, pady=(0, 4))
        for i, tag in enumerate(TAGS):
            var = tk.BooleanVar()
            cb = tk.Checkbutton(tags_frame, text=tag, variable=var,
                                font=(self.config.get('font_family'), 9),
                                bg=colors['bg_main'], fg=colors['fg_primary'],
                                selectcolor=colors['bg_sidebar'])
            cb.grid(row=i // 6, column=i % 6, sticky=tk.W, padx=2, pady=1)
            self.add_tags_vars[tag] = var

        # 题解
        label('题解（Markdown）').pack(anchor=tk.W, padx=24, pady=(12, 2))
        self.add_solution = tk.Text(scroll_frame, height=10,
                                     font=(self.config.get('code_font_family'), 11),
                                     bg=colors['bg_input'], fg=colors['fg_primary'],
                                     relief=tk.FLAT, wrap=tk.WORD)
        self.add_solution.pack(fill=tk.X, padx=24, pady=(0, 4))

        # 提交按钮
        tk.Button(scroll_frame, text='保存题目', font=(self.config.get('font_family'), 12),
                  bg=colors['fg_accent'], fg='#ffffff', relief=tk.FLAT, padx=24, pady=8,
                  cursor='hand2', command=self._save_problem).pack(pady=16)

    def _save_problem(self):
        title = self.add_title.get().strip()
        if not title:
            messagebox.showwarning('提示', '请输入题目名称')
            return

        platform = self.add_platform_var.get()
        tags = json.dumps([t for t, v in self.add_tags_vars.items() if v.get()], ensure_ascii=False)

        try:
            conn = get_connection()
            conn.execute(
                """INSERT INTO problems (title, platform, platform_id, difficulty, tags, status, solution, url)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (title, platform, self.add_pid.get().strip(),
                 self.add_diff_var.get(), tags, self.add_status_var.get(),
                 self.add_solution.get('1.0', tk.END).strip(),
                 self.add_url.get().strip())
            )
            conn.commit()
            conn.close()

            # 清空表单
            self.add_title.delete(0, tk.END)
            self.add_pid.delete(0, tk.END)
            self.add_url.delete(0, tk.END)
            self.add_solution.delete('1.0', tk.END)
            for var in self.add_tags_vars.values():
                var.set(False)

            self.app.set_status(f'题目「{title}」已保存')
            self._show_view('list')
        except Exception as e:
            self.app.set_status(f'保存失败: {e}')

    # ============================================================
    # 列表视图
    # ============================================================

    def _build_list_view(self):
        parent = self._views['list']
        colors = self.config.get_colors()

        # 筛选栏
        filter_bar = tk.Frame(parent, bg=colors['bg_sidebar'], height=40)
        filter_bar.pack(fill=tk.X)
        filter_bar.pack_propagate(False)

        tk.Label(filter_bar, text='状态:', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_sidebar'], fg=colors['fg_secondary']).pack(side=tk.LEFT, padx=(12, 4))

        self.filter_status_var = tk.StringVar(value='全部')
        ttk.Combobox(filter_bar, textvariable=self.filter_status_var,
                      values=['全部'] + list(STATUSES.values()),
                      state='readonly', width=8).pack(side=tk.LEFT, padx=(0, 12))
        self.filter_status_var.trace_add('write', lambda *a: self._refresh_problem_list())

        tk.Label(filter_bar, text='难度:', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_sidebar'], fg=colors['fg_secondary']).pack(side=tk.LEFT, padx=4)

        self.filter_diff_var = tk.StringVar(value='全部')
        ttk.Combobox(filter_bar, textvariable=self.filter_diff_var,
                      values=['全部'] + DIFFICULTIES,
                      state='readonly', width=10).pack(side=tk.LEFT, padx=(0, 12))
        self.filter_diff_var.trace_add('write', lambda *a: self._refresh_problem_list())

        # 表格
        tree_frame = tk.Frame(parent, bg=colors['bg_main'])
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        columns = ('title', 'platform', 'difficulty', 'tags', 'status')
        self.problem_tree = ttk.Treeview(tree_frame, columns=columns, show='headings',
                                          selectmode='browse')
        self.problem_tree.heading('title', text='题目')
        self.problem_tree.heading('platform', text='平台')
        self.problem_tree.heading('difficulty', text='难度')
        self.problem_tree.heading('tags', text='标签')
        self.problem_tree.heading('status', text='状态')

        self.problem_tree.column('title', width=250)
        self.problem_tree.column('platform', width=80)
        self.problem_tree.column('difficulty', width=80)
        self.problem_tree.column('tags', width=200)
        self.problem_tree.column('status', width=60)

        self.problem_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.problem_tree.bind('<Double-1>', self._on_problem_double_click)

        tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL,
                                     command=self.problem_tree.yview)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.problem_tree.configure(yscrollcommand=tree_scroll.set)

    def _refresh_problem_list(self):
        self.problem_tree.delete(*self.problem_tree.get_children())

        try:
            conn = get_connection()
            rows = conn.execute(
                "SELECT id, title, platform, difficulty, tags, status FROM problems ORDER BY updated_at DESC"
            ).fetchall()
            conn.close()

            status_filter = self.filter_status_var.get()
            diff_filter = self.filter_diff_var.get()

            for row in rows:
                if status_filter != '全部':
                    status_cn = STATUSES.get(row['status'], row['status'])
                    if status_cn != status_filter:
                        continue
                if diff_filter != '全部' and row['difficulty'] != diff_filter:
                    continue

                tags_text = ''
                try:
                    tags = json.loads(row['tags'] or '[]')
                    tags_text = ', '.join(tags[:4])
                except Exception:
                    tags_text = ''

                self.problem_tree.insert('', tk.END,
                    iid=str(row['id']),
                    values=(row['title'], row['platform'], row['difficulty'],
                            tags_text, STATUSES.get(row['status'], row['status'])))
        except Exception as e:
            self.app.set_status(f'加载题目列表失败: {e}')

    def _on_problem_double_click(self, event):
        sel = self.problem_tree.selection()
        if sel:
            self._current_problem_id = int(sel[0])
            self._load_detail_view()
            self._show_view('detail')

    # ============================================================
    # 详情视图
    # ============================================================

    def _build_detail_view(self):
        parent = self._views['detail']
        colors = self.config.get_colors()

        self.detail_md = MarkdownView(parent)
        self.detail_md.pack(fill=tk.BOTH, expand=True, padx=12, pady=(8, 4))

        # 底部操作按钮
        btn_bar = tk.Frame(parent, bg=colors['bg_sidebar'], height=40)
        btn_bar.pack(fill=tk.X, side=tk.BOTTOM)
        btn_bar.pack_propagate(False)

        tk.Button(btn_bar, text='返回列表', font=(self.config.get('font_family'), 10),
                  bg=colors['bg_sidebar'], fg=colors['fg_primary'],
                  relief=tk.FLAT, padx=12, pady=4, cursor='hand2',
                  command=lambda: self._show_view('list')).pack(side=tk.LEFT, padx=12)

        tk.Button(btn_bar, text='删除', font=(self.config.get('font_family'), 10),
                  bg=colors['bg_sidebar'], fg=colors['danger'],
                  relief=tk.FLAT, padx=12, pady=4, cursor='hand2',
                  command=self._delete_problem).pack(side=tk.RIGHT, padx=12)

        tk.Button(btn_bar, text='编辑题解', font=(self.config.get('font_family'), 10),
                  bg=colors['fg_accent'], fg='#ffffff',
                  relief=tk.FLAT, padx=16, pady=4, cursor='hand2',
                  command=self._open_edit_dialog).pack(side=tk.RIGHT, padx=4)

    def _load_detail_view(self):
        if not self._current_problem_id:
            return
        try:
            conn = get_connection()
            row = conn.execute(
                "SELECT * FROM problems WHERE id=?", (self._current_problem_id,)
            ).fetchone()
            conn.close()
            if not row:
                return
            row = dict(row)

            md = f'# {row["title"]}\n\n'
            md += f'- **平台**: {row["platform"]}  '
            if row.get('platform_id'):
                md += f'`{row["platform_id"]}`'
            md += '\n'
            md += f'- **难度**: {row["difficulty"]}\n'
            md += f'- **状态**: {STATUSES.get(row["status"], row["status"])}\n'
            if row.get('url'):
                md += f'- **链接**: [{row["url"]}]({row["url"]})\n'
            try:
                tags = json.loads(row.get('tags') or '[]')
                if tags:
                    md += f'- **标签**: {", ".join(tags)}\n'
            except Exception:
                pass
            md += '\n---\n\n'
            md += row.get('solution', '') or '*暂无题解*'

            self.detail_md.render(md)
        except Exception as e:
            self.app.set_status(f'加载详情失败: {e}')

    def _open_edit_dialog(self):
        if not self._current_problem_id:
            return
        try:
            conn = get_connection()
            row = conn.execute(
                "SELECT title, solution, status FROM problems WHERE id=?",
                (self._current_problem_id,)
            ).fetchone()
            conn.close()
            if not row:
                return

            dialog = tk.Toplevel(self.parent)
            dialog.title(f'编辑 — {row["title"]}')
            dialog.geometry('800x600')
            dialog.transient(self.parent)
            colors = self.config.get_colors()
            dialog.configure(bg=colors['bg_main'])

            # 状态修改
            status_row = tk.Frame(dialog, bg=colors['bg_main'])
            status_row.pack(fill=tk.X, padx=16, pady=(12, 4))
            tk.Label(status_row, text='状态:', font=(self.config.get('font_family'), 11),
                     bg=colors['bg_main'], fg=colors['fg_secondary']).pack(side=tk.LEFT)
            status_var = tk.StringVar(value=row['status'])
            for val, txt in STATUSES.items():
                tk.Radiobutton(status_row, text=txt, variable=status_var, value=val,
                               font=(self.config.get('font_family'), 10),
                               bg=colors['bg_main'], fg=colors['fg_primary']).pack(side=tk.LEFT, padx=(4, 0))

            # 题解编辑器
            tk.Label(dialog, text='题解（Markdown）:', font=(self.config.get('font_family'), 11),
                     bg=colors['bg_main'], fg=colors['fg_secondary']).pack(anchor=tk.W, padx=16, pady=(12, 2))

            text_editor = tk.Text(dialog, font=(self.config.get('code_font_family'), 11),
                                   bg=colors['bg_input'], fg=colors['fg_primary'],
                                   relief=tk.FLAT, wrap=tk.WORD)
            text_editor.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 4))
            text_editor.insert('1.0', row.get('solution', ''))

            btn_row = tk.Frame(dialog, bg=colors['bg_main'])
            btn_row.pack(fill=tk.X, padx=16, pady=(0, 12))
            tk.Button(btn_row, text='取消', font=(self.config.get('font_family'), 11),
                      bg=colors['bg_sidebar'], fg=colors['fg_primary'],
                      relief=tk.FLAT, padx=16, pady=6, command=dialog.destroy).pack(side=tk.RIGHT, padx=(8, 0))
            tk.Button(btn_row, text='保存', font=(self.config.get('font_family'), 11),
                      bg=colors['fg_accent'], fg='#ffffff',
                      relief=tk.FLAT, padx=20, pady=6,
                      command=lambda: self._save_problem_edit(
                          self._current_problem_id, status_var.get(),
                          text_editor.get('1.0', tk.END).strip(), dialog)
                      ).pack(side=tk.RIGHT)
        except Exception as e:
            self.app.set_status(f'打开编辑失败: {e}')

    def _save_problem_edit(self, pid, status, solution, dialog):
        try:
            conn = get_connection()
            conn.execute(
                """UPDATE problems SET status=?, solution=?,
                   updated_at=datetime('now','localtime') WHERE id=?""",
                (status, solution, pid))
            conn.commit()
            conn.close()
            dialog.destroy()
            self._load_detail_view()
            self.app.set_status('题解已保存')
        except Exception as e:
            self.app.set_status(f'保存失败: {e}')

    def _delete_problem(self):
        if not self._current_problem_id:
            return
        if not messagebox.askyesno('确认删除', '确定要删除这个题目吗？'):
            return
        try:
            conn = get_connection()
            conn.execute("DELETE FROM problems WHERE id=?", (self._current_problem_id,))
            conn.commit()
            conn.close()
            self._current_problem_id = None
            self._show_view('list')
            self.app.set_status('��目已删除')
        except Exception as e:
            self.app.set_status(f'删除失败: {e}')

    def on_new(self):
        self._show_view('add')

    def on_search(self):
        self._show_view('list')

    def apply_theme(self):
        for w in self.parent.winfo_children():
            w.destroy()
        self._build_ui()
        self._show_view('list')
