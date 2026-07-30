"""
刷题记录模块
左侧：题目列表（点击查看 + [编辑]按钮）+ 筛选栏，始终可见
右侧：查看模式（Markdown） / 编辑模式（表单），内嵌切换，离开自动保存
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

        self._current_id = None
        self._view_mode = 'view'     # 'view' 或 'edit'
        self._dirty = False          # 编辑内容是否有未保存的修改
        self._problems_cache = []    # 题目列表缓存

        self._build_ui()
        self._refresh_list()

    # ============================================================
    # UI 布局
    # ============================================================

    def _build_ui(self):
        colors = self.config.get_colors()

        # --- 顶部筛选栏 ---
        filter_bar = tk.Frame(self.parent, bg=colors['bg_sidebar'], height=42)
        filter_bar.pack(fill=tk.X)
        filter_bar.pack_propagate(False)

        tk.Label(filter_bar, text='状态:', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_sidebar'], fg=colors['fg_secondary']).pack(side=tk.LEFT, padx=(12, 4))
        self.filter_status = tk.StringVar(value='全部')
        cb = ttk.Combobox(filter_bar, textvariable=self.filter_status,
                           values=['全部', '待做', '已做', '复习'], state='readonly', width=6)
        cb.pack(side=tk.LEFT, padx=(0, 12))
        cb.bind('<<ComboboxSelected>>', lambda e: self._refresh_list())

        tk.Label(filter_bar, text='难度:', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_sidebar'], fg=colors['fg_secondary']).pack(side=tk.LEFT)
        self.filter_diff = tk.StringVar(value='全部')
        cb2 = ttk.Combobox(filter_bar, textvariable=self.filter_diff,
                            values=['全部'] + DIFFICULTIES, state='readonly', width=10)
        cb2.pack(side=tk.LEFT, padx=(0, 12))
        cb2.bind('<<ComboboxSelected>>', lambda e: self._refresh_list())

        tk.Frame(filter_bar, bg=colors['bg_sidebar']).pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Button(filter_bar, text='+ 录入题目', font=(self.config.get('font_family'), 10),
                  bg=colors['fg_accent'], fg='#ffffff', relief=tk.FLAT, padx=16, pady=4,
                  cursor='hand2', command=self._open_add_dialog).pack(side=tk.RIGHT, padx=8, pady=8)

        # --- 主体 ---
        main = tk.Frame(self.parent, bg=colors['bg_main'])
        main.pack(fill=tk.BOTH, expand=True)

        self._build_left_panel(main)
        self._build_right_panel(main)

    # ============================================================
    # 左侧面板 — 可滚动题目列表
    # ============================================================

    def _build_left_panel(self, parent):
        colors = self.config.get_colors()
        self.left_panel = tk.Frame(parent, width=280, bg=colors['bg_sidebar'])
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y)
        self.left_panel.pack_propagate(False)

        tk.Label(self.left_panel, text='题目列表', font=(self.config.get('font_family'), 12, 'bold'),
                 bg=colors['bg_sidebar'], fg=colors['fg_primary']).pack(anchor=tk.W, padx=12, pady=(8, 4))

        # 可滚动 Canvas
        self.list_canvas = tk.Canvas(self.left_panel, bg=colors['bg_sidebar'],
                                      highlightthickness=0)
        self.list_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(self.left_panel, orient=tk.VERTICAL,
                                   command=self.list_canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.list_canvas.configure(yscrollcommand=scrollbar.set)

        self.list_inner = tk.Frame(self.list_canvas, bg=colors['bg_sidebar'])
        self._list_window = self.list_canvas.create_window((0, 0), window=self.list_inner,
                                                            anchor=tk.NW)
        self.list_canvas.bind('<Configure>', self._on_canvas_configure)
        self.list_inner.bind('<Configure>', self._on_inner_configure)

    def _on_canvas_configure(self, event):
        self.list_canvas.itemconfig(self._list_window, width=event.width)

    def _on_inner_configure(self, event):
        self.list_canvas.configure(scrollregion=self.list_canvas.bbox('all'))

    def _refresh_list(self):
        # 先自动保存
        self._auto_save_if_dirty()

        for w in self.list_inner.winfo_children():
            w.destroy()

        try:
            conn = get_connection()
            rows = conn.execute(
                "SELECT id, title, platform, difficulty, tags, status FROM problems ORDER BY updated_at DESC"
            ).fetchall()
            conn.close()
            self._problems_cache = [dict(r) for r in rows]

            sf = self.filter_status.get()
            df = self.filter_diff.get()
            colors = self.config.get_colors()

            for row in self._problems_cache:
                status_cn = STATUSES.get(row['status'], row['status'])
                if sf != '全部' and status_cn != sf:
                    continue
                if df != '全部' and row['difficulty'] != df:
                    continue

                # 一行：题目标题(可点击) + [编辑]按钮
                row_frame = tk.Frame(self.list_inner, bg=colors['bg_sidebar'])
                row_frame.pack(fill=tk.X, padx=8, pady=1)

                sym = STATUS_SYMBOLS.get(row['status'], '○')
                diff_short = row['difficulty'][:3] if row['difficulty'] else '--'

                # 题目名 Label（点击 = 查看）
                title_label = tk.Label(
                    row_frame,
                    text=f'{sym}  {row["title"]}',
                    font=(self.config.get('font_family'), 10),
                    bg=colors['bg_sidebar'], fg=colors['fg_primary'],
                    anchor=tk.W, cursor='hand2',
                )
                title_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))
                title_label.bind('<Button-1>', lambda e, pid=row['id']: self._view_problem(pid))
                title_label.bind('<Enter>', lambda e, lb=title_label: lb.configure(
                    fg=colors['fg_accent']))
                title_label.bind('<Leave>', lambda e, lb=title_label: lb.configure(
                    fg=colors['fg_primary']))

                # 平台标签
                tk.Label(
                    row_frame,
                    text=f'[{row["platform"]}]',
                    font=(self.config.get('font_family'), 9),
                    bg=colors['bg_sidebar'], fg=colors['fg_muted'],
                ).pack(side=tk.LEFT, padx=4)

                # 编辑按钮
                edit_btn = tk.Label(
                    row_frame,
                    text='编辑',
                    font=(self.config.get('font_family'), 9),
                    bg=colors['bg_sidebar'], fg=colors['fg_accent'],
                    cursor='hand2', padx=6,
                )
                edit_btn.pack(side=tk.RIGHT, padx=(0, 4))
                edit_btn.bind('<Button-1>', lambda e, pid=row['id']: self._edit_problem(pid))
                edit_btn.bind('<Enter>', lambda e, eb=edit_btn: eb.configure(
                    fg=colors['fg_link']))
                edit_btn.bind('<Leave>', lambda e, eb=edit_btn: eb.configure(
                    fg=colors['fg_accent']))

        except Exception as e:
            self.app.set_status(f'加载题目列表失败: {e}')

    # ============================================================
    # 右侧面板 — 查看模式 / 编辑模式
    # ============================================================

    def _build_right_panel(self, parent):
        colors = self.config.get_colors()
        self.right_panel = tk.Frame(parent, bg=colors['bg_main'])
        self.right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 查看模式
        self.view_frame = tk.Frame(self.right_panel, bg=colors['bg_main'])
        self.detail_md = MarkdownView(self.view_frame)
        self.detail_md.pack(fill=tk.BOTH, expand=True, padx=12, pady=(8, 4))

        # 底部按钮
        view_bar = tk.Frame(self.view_frame, bg=colors['bg_sidebar'], height=40)
        view_bar.pack(fill=tk.X, side=tk.BOTTOM)
        view_bar.pack_propagate(False)
        tk.Button(view_bar, text='编辑题解', font=(self.config.get('font_family'), 10),
                  bg=colors['fg_accent'], fg='#ffffff', relief=tk.FLAT,
                  padx=16, pady=4, cursor='hand2',
                  command=lambda: self._edit_problem(self._current_id)).pack(side=tk.RIGHT, padx=8)
        tk.Button(view_bar, text='删除', font=(self.config.get('font_family'), 10),
                  bg=colors['bg_sidebar'], fg=colors['danger'], relief=tk.FLAT,
                  padx=12, pady=4, cursor='hand2',
                  command=self._delete_current).pack(side=tk.RIGHT, padx=4)

        # 编辑模式
        self._build_edit_mode()

        # 默认显示空状态
        self._show_view()

    def _build_edit_mode(self):
        """构建右侧编辑模式组件（默认隐藏）"""
        colors = self.config.get_colors()
        self.edit_frame = tk.Frame(self.right_panel, bg=colors['bg_main'])

        # 标题（只读）
        tk.Label(self.edit_frame, text='编辑题目', font=(self.config.get('font_family'), 14, 'bold'),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(anchor=tk.W, padx=16, pady=(12, 4))

        self.edit_title_label = tk.Label(
            self.edit_frame, text='',
            font=(self.config.get('font_family'), 16, 'bold'),
            bg=colors['bg_main'], fg=colors['fg_accent'], anchor=tk.W,
        )
        self.edit_title_label.pack(fill=tk.X, padx=16, pady=(0, 4))

        # 状态行
        sf = tk.Frame(self.edit_frame, bg=colors['bg_main'])
        sf.pack(fill=tk.X, padx=16, pady=(4, 8))
        tk.Label(sf, text='状态:', font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(side=tk.LEFT)
        self.edit_status_var = tk.StringVar(value='todo')
        for val, txt in STATUSES.items():
            tk.Radiobutton(sf, text=txt, variable=self.edit_status_var, value=val,
                           font=(self.config.get('font_family'), 10),
                           bg=colors['bg_main'], fg=colors['fg_primary'],
                           selectcolor=colors['bg_sidebar']).pack(side=tk.LEFT, padx=(8, 0))

        # 提示
        tk.Label(self.edit_frame,
                 text='编辑完成后切换到其他题目或模块将自动保存',
                 font=(self.config.get('font_family'), 9),
                 bg=colors['bg_main'], fg=colors['fg_muted'], anchor=tk.W,
        ).pack(fill=tk.X, padx=16, pady=(0, 8))

        # 题解编辑器
        tk.Label(self.edit_frame, text='题解（Markdown）:',
                 font=(self.config.get('font_family'), 11, 'bold'),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(anchor=tk.W, padx=16, pady=(4, 2))

        self.edit_text = tk.Text(
            self.edit_frame,
            font=(self.config.get('code_font_family'), 11),
            bg=colors['bg_input'], fg=colors['fg_primary'],
            relief=tk.FLAT, wrap=tk.WORD,
            undo=True,
        )
        self.edit_text.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 4))
        self.edit_text.bind('<<Modified>>', self._on_text_modified)

        # 手动保存按钮
        btn_bar = tk.Frame(self.edit_frame, bg=colors['bg_sidebar'], height=40)
        btn_bar.pack(fill=tk.X, side=tk.BOTTOM)
        btn_bar.pack_propagate(False)
        tk.Button(btn_bar, text='返回查看', font=(self.config.get('font_family'), 10),
                  bg=colors['bg_sidebar'], fg=colors['fg_primary'], relief=tk.FLAT,
                  padx=16, pady=4, cursor='hand2',
                  command=self._exit_edit).pack(side=tk.RIGHT, padx=8)

    # ============================================================
    # 查看 / 编辑模式切换
    # ============================================================

    def _show_view(self):
        """切换到查看模式"""
        self._view_mode = 'view'
        self.edit_frame.pack_forget()
        self.view_frame.pack(fill=tk.BOTH, expand=True)

    def _show_edit(self):
        """切换到编辑模式"""
        self._view_mode = 'edit'
        self.view_frame.pack_forget()
        self.edit_frame.pack(fill=tk.BOTH, expand=True)

    # ============================================================
    # 题目交互
    # ============================================================

    def _view_problem(self, problem_id: int):
        """点击题目 → 查看模式"""
        self._auto_save_if_dirty()
        self._current_id = problem_id
        self._show_view()
        self._load_detail_view()

    def _edit_problem(self, problem_id: int):
        """点击编辑按钮 → 编辑模式"""
        self._auto_save_if_dirty()
        self._current_id = problem_id
        self._load_edit_form()
        self._show_edit()

    # ============================================================
    # 查看模式 — 加载题目详情
    # ============================================================

    def _load_detail_view(self):
        if not self._current_id:
            self.detail_md.render('*选择一个题目查看详情*')
            return
        try:
            conn = get_connection()
            row = conn.execute(
                "SELECT * FROM problems WHERE id=?", (self._current_id,)
            ).fetchone()
            conn.close()
            if not row:
                return
            row = dict(row)

            md = f'# {row["title"]}\n\n'
            md += '| 字段 | 值 |\n|------|----|\n'
            md += f'| 平台 | {row["platform"]} |\n'
            if row.get('platform_id'):
                md += f'| 编号 | `{row["platform_id"]}` |\n'
            md += f'| 难度 | {row["difficulty"]} |\n'
            md += f'| 状态 | {STATUSES.get(row["status"], row["status"])} |\n'
            if row.get('url'):
                md += f'| 链接 | [{row["url"]}]({row["url"]}) |\n'
            try:
                tags = json.loads(row.get('tags') or '[]')
                if tags:
                    md += f'| 标签 | {", ".join(tags)} |\n'
            except Exception:
                pass
            md += '\n---\n\n'
            md += row.get('solution', '') or '*暂无题解*'

            self.detail_md.render(md)
        except Exception as e:
            self.app.set_status(f'加载详情失败: {e}')

    # ============================================================
    # 编辑模式 — 加载表单
    # ============================================================

    def _load_edit_form(self):
        if not self._current_id:
            return
        try:
            conn = get_connection()
            row = conn.execute(
                "SELECT title, status, solution FROM problems WHERE id=?",
                (self._current_id,)
            ).fetchone()
            conn.close()
            if not row:
                return

            self.edit_title_label.config(text=row['title'])
            self.edit_status_var.set(row['status'])

            # 设置文本
            self.edit_text.delete('1.0', tk.END)
            self.edit_text.insert('1.0', row.get('solution', ''))
            self.edit_text.edit_modified(False)  # 重置 modified 标记
            self._dirty = False

        except Exception as e:
            self.app.set_status(f'加载编辑表单失败: {e}')

    def _on_text_modified(self, event=None):
        """文本框内容变化时标记脏数据"""
        if self.edit_text.edit_modified():
            self._dirty = True

    # ============================================================
    # 自动保存
    # ============================================================

    def _auto_save_if_dirty(self):
        """如果编辑模式有未保存修改，自动保存"""
        if self._view_mode == 'edit' and self._current_id and self._dirty:
            self._do_save()
        self._dirty = False

    def _do_save(self):
        """保存当前编辑内容到数据库"""
        if not self._current_id:
            return
        try:
            status = self.edit_status_var.get()
            solution = self.edit_text.get('1.0', tk.END).strip()
            conn = get_connection()
            conn.execute(
                """UPDATE problems SET status=?, solution=?,
                   updated_at=datetime('now','localtime') WHERE id=?""",
                (status, solution, self._current_id))
            conn.commit()
            conn.close()
            self._dirty = False
            self.edit_text.edit_modified(False)
            self.app.set_status('已自动保存')
            # 刷新列表中的状态符号
            self._refresh_list()
        except Exception as e:
            self.app.set_status(f'保存失败: {e}')

    def _exit_edit(self):
        """手动退出编辑模式"""
        self._auto_save_if_dirty()
        self._show_view()
        self._load_detail_view()

    # ============================================================
    # 模块切换时的自动保存钩子
    # ============================================================

    def on_before_leave(self):
        """其他模块切换过来之前，自动保存"""
        self._auto_save_if_dirty()

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
            self._show_view()
            self.detail_md.render('*题目已删除*')
            self._refresh_list()
            self.app.set_status('题目已删除')
        except Exception as e:
            self.app.set_status(f'删除失败: {e}')

    # ============================================================
    # 录入对话框（保持弹窗方式，因为录入字段太多不适合内嵌）
    # ============================================================

    def _open_add_dialog(self):
        dialog = tk.Toplevel(self.parent)
        dialog.title('录入题目')
        dialog.geometry('700x650')
        dialog.transient(self.parent)
        colors = self.config.get_colors()
        dialog.configure(bg=colors['bg_main'])

        pad = {'padx': 20, 'pady': 3}
        tk.Label(dialog, text='录入新题目', font=(self.config.get('font_family'), 16, 'bold'),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(anchor=tk.W, padx=20, pady=(16, 8))

        # 标题
        tk.Label(dialog, text='题目名称', font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(anchor=tk.W, **pad)
        title_entry = tk.Entry(dialog, font=(self.config.get('font_family'), 12),
                                bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT)
        title_entry.pack(fill=tk.X, **pad)

        # 平台 + 编号
        row1 = tk.Frame(dialog, bg=colors['bg_main'])
        row1.pack(fill=tk.X, **pad)
        tk.Label(row1, text='平台', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(side=tk.LEFT)
        plat_var = tk.StringVar(value='洛谷')
        ttk.Combobox(row1, textvariable=plat_var, values=PLATFORMS, state='readonly', width=12).pack(side=tk.LEFT, padx=(4, 20))
        tk.Label(row1, text='编号', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(side=tk.LEFT)
        pid_entry = tk.Entry(row1, font=(self.config.get('font_family'), 10),
                              bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT, width=14)
        pid_entry.pack(side=tk.LEFT, padx=4)

        # 链接
        tk.Label(dialog, text='题目链接', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(anchor=tk.W, padx=20, pady=(4, 0))
        url_entry = tk.Entry(dialog, font=(self.config.get('font_family'), 10),
                              bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT)
        url_entry.pack(fill=tk.X, padx=20, pady=(0, 4))

        # 难度 + 状态
        row2 = tk.Frame(dialog, bg=colors['bg_main'])
        row2.pack(fill=tk.X, **pad)
        tk.Label(row2, text='难度', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(side=tk.LEFT)
        diff_var = tk.StringVar(value='暂未评定')
        ttk.Combobox(row2, textvariable=diff_var, values=DIFFICULTIES, state='readonly', width=12).pack(side=tk.LEFT, padx=(4, 20))
        tk.Label(row2, text='状态', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(side=tk.LEFT)
        status_var = tk.StringVar(value='todo')
        for val, txt in STATUSES.items():
            tk.Radiobutton(row2, text=txt, variable=status_var, value=val,
                           font=(self.config.get('font_family'), 9),
                           bg=colors['bg_main'], fg=colors['fg_primary']).pack(side=tk.LEFT, padx=2)

        # 标签
        tk.Label(dialog, text='算法标签（多选）', font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(anchor=tk.W, padx=20, pady=(8, 2))
        tags_vars = {}
        tags_fr = tk.Frame(dialog, bg=colors['bg_main'])
        tags_fr.pack(fill=tk.X, padx=20, pady=(0, 4))
        for i, tag in enumerate(TAGS):
            var = tk.BooleanVar()
            tk.Checkbutton(tags_fr, text=tag, variable=var,
                           font=(self.config.get('font_family'), 9),
                           bg=colors['bg_main'], fg=colors['fg_primary']).grid(row=i//6, column=i%6, sticky=tk.W, padx=2, pady=1)
            tags_vars[tag] = var

        # 题解
        tk.Label(dialog, text='题解（Markdown，可选）', font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(anchor=tk.W, padx=20, pady=(8, 2))
        sol_text = tk.Text(dialog, font=(self.config.get('code_font_family'), 11),
                            bg=colors['bg_input'], fg=colors['fg_primary'],
                            relief=tk.FLAT, wrap=tk.WORD, height=8)
        sol_text.pack(fill=tk.X, padx=20, pady=(0, 4))

        # 按钮
        btn_row = tk.Frame(dialog, bg=colors['bg_main'])
        btn_row.pack(fill=tk.X, padx=20, pady=(8, 16))
        tk.Button(btn_row, text='取消', font=(self.config.get('font_family'), 11),
                  bg=colors['bg_sidebar'], fg=colors['fg_primary'], relief=tk.FLAT,
                  padx=16, pady=6, command=dialog.destroy).pack(side=tk.RIGHT, padx=(8, 0))
        tk.Button(btn_row, text='保存', font=(self.config.get('font_family'), 11),
                  bg=colors['fg_accent'], fg='#ffffff', relief=tk.FLAT, padx=20, pady=6,
                  command=lambda: self._do_add_save(
                      title_entry.get().strip(), plat_var.get(), pid_entry.get().strip(),
                      diff_var.get(), status_var.get(), url_entry.get().strip(),
                      tags_vars, sol_text.get('1.0', tk.END).strip(), dialog)
                  ).pack(side=tk.RIGHT)

    def _do_add_save(self, title, platform, pid, diff, status, url, tags_vars, solution, dialog):
        if not title:
            messagebox.showwarning('提示', '请输入题目名称')
            return
        tags = json.dumps([t for t, v in tags_vars.items() if v.get()], ensure_ascii=False)
        try:
            conn = get_connection()
            conn.execute(
                """INSERT INTO problems (title, platform, platform_id, difficulty, tags, status, solution, url)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (title, platform, pid, diff, tags, status, solution, url))
            conn.commit()
            conn.close()
            dialog.destroy()
            self._refresh_list()
            self.app.set_status(f'题目「{title}」已保存')
        except Exception as e:
            self.app.set_status(f'保存失败: {e}')

    def on_new(self):
        self._open_add_dialog()

    def apply_theme(self):
        self._auto_save_if_dirty()
        for w in self.parent.winfo_children():
            w.destroy()
        self._build_ui()
        self._refresh_list()
