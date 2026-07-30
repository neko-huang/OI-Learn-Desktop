"""
刷题记录模块
左侧题目列表 + 右侧 Markdown 详情 + 顶部筛选栏
支持题解编辑、状态管理、难度标签筛选、录入对话框
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
    """刷题记录模块 — 左侧列表 + 右侧详情"""

    def __init__(self, app, parent_frame: tk.Frame):
        self.app = app
        self.config = Config()
        self.parent = parent_frame
        for w in parent_frame.winfo_children():
            w.destroy()

        self._current_id = None
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

        # 弹簧
        tk.Frame(filter_bar, bg=colors['bg_sidebar']).pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Button(filter_bar, text='+ 录入题目', font=(self.config.get('font_family'), 10),
                  bg=colors['fg_accent'], fg='#ffffff', relief=tk.FLAT, padx=16, pady=4,
                  cursor='hand2', command=self._open_add_dialog).pack(side=tk.RIGHT, padx=8, pady=8)

        # --- 主体：左侧列表 + 右侧详情 ---
        main = tk.Frame(self.parent, bg=colors['bg_main'])
        main.pack(fill=tk.BOTH, expand=True)

        self._build_left_panel(main)
        self._build_right_panel(main)

    def _build_left_panel(self, parent):
        colors = self.config.get_colors()
        left = tk.Frame(parent, width=240, bg=colors['bg_sidebar'])
        left.pack(side=tk.LEFT, fill=tk.Y)
        left.pack_propagate(False)

        tk.Label(left, text='题目列表', font=(self.config.get('font_family'), 12, 'bold'),
                 bg=colors['bg_sidebar'], fg=colors['fg_primary']).pack(anchor=tk.W, padx=12, pady=(8, 4))

        self.problem_listbox = tk.Listbox(
            left, font=(self.config.get('font_family'), 10),
            bg=colors['bg_input'], fg=colors['fg_primary'],
            selectbackground=colors['fg_accent'], selectforeground='#ffffff',
            relief=tk.FLAT, activestyle='none',
        )
        self.problem_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=(0, 8))
        self.problem_listbox.bind('<<ListboxSelect>>', self._on_select)

        scroll = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.problem_listbox.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=(0, 8), padx=(0, 8))
        self.problem_listbox.configure(yscrollcommand=scroll.set)

    def _build_right_panel(self, parent):
        colors = self.config.get_colors()
        right = tk.Frame(parent, bg=colors['bg_main'])
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.detail_md = MarkdownView(right)
        self.detail_md.pack(fill=tk.BOTH, expand=True, padx=12, pady=(8, 4))

        # 底部操作栏
        bar = tk.Frame(right, bg=colors['bg_sidebar'], height=40)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        bar.pack_propagate(False)

        tk.Button(bar, text='编辑题解', font=(self.config.get('font_family'), 10),
                  bg=colors['fg_accent'], fg='#ffffff', relief=tk.FLAT,
                  padx=16, pady=4, cursor='hand2',
                  command=self._open_edit_dialog).pack(side=tk.RIGHT, padx=8, pady=8)
        tk.Button(bar, text='删除', font=(self.config.get('font_family'), 10),
                  bg=colors['bg_sidebar'], fg=colors['danger'], relief=tk.FLAT,
                  padx=12, pady=4, cursor='hand2',
                  command=self._delete_current).pack(side=tk.RIGHT, padx=4, pady=8)

        self._show_empty_detail()

    # ============================================================
    # 列表刷新
    # ============================================================

    def _refresh_list(self):
        self.problem_listbox.delete(0, tk.END)
        self._list_ids = []

        try:
            conn = get_connection()
            rows = conn.execute(
                "SELECT id, title, platform, difficulty, tags, status FROM problems ORDER BY updated_at DESC"
            ).fetchall()
            conn.close()

            sf = self.filter_status.get()
            df = self.filter_diff.get()

            for row in rows:
                status_cn = STATUSES.get(row['status'], row['status'])
                if sf != '全部' and status_cn != sf:
                    continue
                if df != '全部' and row['difficulty'] != df:
                    continue

                sym = STATUS_SYMBOLS.get(row['status'], '○')
                diff_short = row['difficulty'][:2] if row['difficulty'] else '--'
                self.problem_listbox.insert(tk.END,
                    f'{sym}  {row["title"]}  [{row["platform"]}]  {diff_short}')
                self._list_ids.append(row['id'])
        except Exception as e:
            self.app.set_status(f'加载失败: {e}')

    def _on_select(self, event):
        sel = self.problem_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self._list_ids):
            return
        self._current_id = self._list_ids[idx]
        self._load_detail()

    def _load_detail(self):
        if not self._current_id:
            return
        try:
            conn = get_connection()
            row = conn.execute("SELECT * FROM problems WHERE id=?", (self._current_id,)).fetchone()
            conn.close()
            if not row:
                return
            row = dict(row)

            md = f'# {row["title"]}\n\n'
            md += f'| 字段 | 值 |\n|------|----|\n'
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
            md += row.get('solution', '') or '*暂无题解，点击下方「编辑题解」添加*'

            self.detail_md.render(md)
        except Exception as e:
            self.app.set_status(f'加载详情失败: {e}')

    def _show_empty_detail(self):
        self._current_id = None
        self.detail_md.render('*选择一个题目查看详情，或点击「+ 录入题目」添加新题*')

    # ============================================================
    # 录入对话框
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

        # 平台 + 编号 + 链接
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
        tags_frame = tk.Frame(dialog, bg=colors['bg_main'])
        tags_frame.pack(fill=tk.X, padx=20, pady=(0, 4))
        for i, tag in enumerate(TAGS):
            var = tk.BooleanVar()
            tk.Checkbutton(tags_frame, text=tag, variable=var,
                           font=(self.config.get('font_family'), 9),
                           bg=colors['bg_main'], fg=colors['fg_primary']).grid(row=i//6, column=i%6, sticky=tk.W, padx=2, pady=1)
            tags_vars[tag] = var

        # 题解
        tk.Label(dialog, text='题解（Markdown）', font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(anchor=tk.W, padx=20, pady=(8, 2))
        solution_text = tk.Text(dialog, font=(self.config.get('code_font_family'), 11),
                                 bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT,
                                 wrap=tk.WORD, height=8)
        solution_text.pack(fill=tk.X, padx=20, pady=(0, 4))

        # 按钮
        btn_row = tk.Frame(dialog, bg=colors['bg_main'])
        btn_row.pack(fill=tk.X, padx=20, pady=(8, 16))
        tk.Button(btn_row, text='取消', font=(self.config.get('font_family'), 11),
                  bg=colors['bg_sidebar'], fg=colors['fg_primary'], relief=tk.FLAT,
                  padx=16, pady=6, command=dialog.destroy).pack(side=tk.RIGHT, padx=(8, 0))
        tk.Button(btn_row, text='保存', font=(self.config.get('font_family'), 11),
                  bg=colors['fg_accent'], fg='#ffffff', relief=tk.FLAT,
                  padx=20, pady=6,
                  command=lambda: self._do_save(
                      title_entry.get().strip(), plat_var.get(), pid_entry.get().strip(),
                      diff_var.get(), status_var.get(), url_entry.get().strip(),
                      tags_vars, solution_text.get('1.0', tk.END).strip(), dialog)
                  ).pack(side=tk.RIGHT)

    def _do_save(self, title, platform, pid, diff, status, url, tags_vars, solution, dialog):
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

    # ============================================================
    # 编辑题解对话框
    # ============================================================

    def _open_edit_dialog(self):
        if not self._current_id:
            return
        try:
            conn = get_connection()
            row = conn.execute("SELECT title, solution, status FROM problems WHERE id=?",
                               (self._current_id,)).fetchone()
            conn.close()
            if not row:
                return

            dialog = tk.Toplevel(self.parent)
            dialog.title(f'编辑 — {row["title"]}')
            dialog.geometry('700x550')
            dialog.transient(self.parent)
            colors = self.config.get_colors()
            dialog.configure(bg=colors['bg_main'])

            # 状态
            sf = tk.Frame(dialog, bg=colors['bg_main'])
            sf.pack(fill=tk.X, padx=16, pady=(12, 4))
            tk.Label(sf, text='状态:', font=(self.config.get('font_family'), 11),
                     bg=colors['bg_main'], fg=colors['fg_secondary']).pack(side=tk.LEFT)
            stat_var = tk.StringVar(value=row['status'])
            for val, txt in STATUSES.items():
                tk.Radiobutton(sf, text=txt, variable=stat_var, value=val,
                               font=(self.config.get('font_family'), 10),
                               bg=colors['bg_main'], fg=colors['fg_primary']).pack(side=tk.LEFT, padx=(4, 0))

            tk.Label(dialog, text='题解（Markdown）:', font=(self.config.get('font_family'), 11),
                     bg=colors['bg_main'], fg=colors['fg_secondary']).pack(anchor=tk.W, padx=16, pady=(12, 2))
            text = tk.Text(dialog, font=(self.config.get('code_font_family'), 11),
                            bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT, wrap=tk.WORD)
            text.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 4))
            text.insert('1.0', row.get('solution', ''))

            br = tk.Frame(dialog, bg=colors['bg_main'])
            br.pack(fill=tk.X, padx=16, pady=(0, 12))
            tk.Button(br, text='取消', font=(self.config.get('font_family'), 11),
                      bg=colors['bg_sidebar'], fg=colors['fg_primary'], relief=tk.FLAT,
                      padx=16, pady=6, command=dialog.destroy).pack(side=tk.RIGHT, padx=(8, 0))
            tk.Button(br, text='保存', font=(self.config.get('font_family'), 11),
                      bg=colors['fg_accent'], fg='#ffffff', relief=tk.FLAT,
                      padx=20, pady=6,
                      command=lambda: self._do_save_edit(
                          stat_var.get(), text.get('1.0', tk.END).strip(), dialog)
                      ).pack(side=tk.RIGHT)
        except Exception as e:
            self.app.set_status(f'打开编辑失败: {e}')

    def _do_save_edit(self, status, solution, dialog):
        try:
            conn = get_connection()
            conn.execute(
                """UPDATE problems SET status=?, solution=?,
                   updated_at=datetime('now','localtime') WHERE id=?""",
                (status, solution, self._current_id))
            conn.commit()
            conn.close()
            dialog.destroy()
            self._refresh_list()
            self._load_detail()
            self.app.set_status('题解已保存')
        except Exception as e:
            self.app.set_status(f'保存失败: {e}')

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
            self._show_empty_detail()
            self.app.set_status('题目已删除')
        except Exception as e:
            self.app.set_status(f'删除失败: {e}')

    def on_new(self):
        self._open_add_dialog()

    def apply_theme(self):
        for w in self.parent.winfo_children():
            w.destroy()
        self._build_ui()
        self._refresh_list()
        self._show_empty_detail()
