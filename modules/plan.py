"""
练习计划模块（题单 + VP 合并）
左侧计划列表 + 右侧计划详情（含题目列表、进度追踪）
"""

import json
import tkinter as tk
from tkinter import ttk, messagebox

from config import Config
from db.database import get_connection
from components.markdown_view import MarkdownView

STATUS_SYMBOLS = {'todo': '○', 'done': '●', 'skipped': '⊘'}


class PlanModule:

    def __init__(self, app, parent_frame):
        self.app = app
        self.config = Config()
        self.parent = parent_frame
        for w in parent_frame.winfo_children():
            w.destroy()

        self._current_plan_id = None
        self._dirty = False
        self._mode = 'view'

        self._build_ui()
        self._refresh_plan_list()

    # ============================================================
    # UI
    # ============================================================

    def _build_ui(self):
        colors = self.config.get_colors()

        # 顶部工具栏
        top = tk.Frame(self.parent, bg=colors['bg_sidebar'], height=42)
        top.pack(fill=tk.X)
        top.pack_propagate(False)

        tk.Label(top, text='练习计划', font=(self.config.get('font_family'), 12, 'bold'),
                 bg=colors['bg_sidebar'], fg=colors['fg_primary']).pack(side=tk.LEFT, padx=12, pady=8)

        tk.Frame(top, bg=colors['bg_sidebar']).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(top, text='+ 新建计划', font=(self.config.get('font_family'), 10),
                  bg=colors['fg_accent'], fg='#ffffff', relief=tk.FLAT,
                  padx=16, pady=4, cursor='hand2',
                  command=self._new_plan).pack(side=tk.RIGHT, padx=8, pady=8)

        # 主体
        main = tk.Frame(self.parent, bg=colors['bg_main'])
        main.pack(fill=tk.BOTH, expand=True)

        self._build_left(main)
        self._build_right(main)

    def _build_left(self, parent):
        colors = self.config.get_colors()
        left = tk.Frame(parent, bg=colors['bg_sidebar'], width=260)
        left.pack(side=tk.LEFT, fill=tk.Y)
        left.pack_propagate(False)

        tk.Label(left, text='计划列表', font=(self.config.get('font_family'), 12, 'bold'),
                 bg=colors['bg_sidebar'], fg=colors['fg_primary']
                 ).pack(anchor=tk.W, padx=12, pady=(6, 4))

        self.plan_listbox = tk.Listbox(
            left, font=(self.config.get('font_family'), 10),
            bg=colors['bg_input'], fg=colors['fg_primary'],
            selectbackground=colors['fg_accent'], selectforeground='#ffffff',
            relief=tk.FLAT, activestyle='none',
        )
        self.plan_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=(0, 8))
        self.plan_listbox.bind('<<ListboxSelect>>', self._on_plan_select)

        sb = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.plan_listbox.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y, pady=(0, 8), padx=(0, 8))
        self.plan_listbox.configure(yscrollcommand=sb.set)

    def _build_right(self, parent):
        colors = self.config.get_colors()
        self.right = tk.Frame(parent, bg=colors['bg_main'])
        self.right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 空状态
        self.empty_frame = tk.Frame(self.right, bg=colors['bg_main'])
        tk.Label(self.empty_frame, text='选择一个计划查看\n或点击「+ 新建计划」创建',
                 font=(self.config.get('font_family'), 14),
                 bg=colors['bg_main'], fg=colors['fg_muted']
                 ).place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # 查看模式
        self.view_frame = tk.Frame(self.right, bg=colors['bg_main'])

        # 计划标题行
        header = tk.Frame(self.view_frame, bg=colors['bg_main'])
        header.pack(fill=tk.X, padx=16, pady=(12, 4))

        self.plan_title = tk.Label(header, text='', font=(self.config.get('font_family'), 18, 'bold'),
                                    bg=colors['bg_main'], fg=colors['fg_primary'], anchor=tk.W)
        self.plan_title.pack(side=tk.LEFT)

        # 操作按钮
        btn_fr = tk.Frame(header, bg=colors['bg_main'])
        btn_fr.pack(side=tk.RIGHT)
        tk.Button(btn_fr, text='删除计划', font=(self.config.get('font_family'), 10),
                  bg=colors['bg_main'], fg=colors['danger'], relief=tk.FLAT, cursor='hand2',
                  command=self._delete_plan).pack(side=tk.RIGHT, padx=(8, 0))
        tk.Button(btn_fr, text='+ 添加题目', font=(self.config.get('font_family'), 10),
                  bg=colors['fg_accent'], fg='#ffffff', relief=tk.FLAT,
                  padx=12, pady=4, cursor='hand2',
                  command=self._add_problem_dialog).pack(side=tk.RIGHT, padx=(8, 0))

        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.view_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=16, pady=(0, 2))

        self.progress_label = tk.Label(self.view_frame, text='', font=(self.config.get('font_family'), 10),
                                        bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.E)
        self.progress_label.pack(fill=tk.X, padx=16, pady=(0, 8))

        # 题目列表（可滚动画布）
        self.problems_canvas = tk.Canvas(self.view_frame, bg=colors['bg_main'], highlightthickness=0)
        self.problems_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8)
        psb = ttk.Scrollbar(self.view_frame, orient=tk.VERTICAL, command=self.problems_canvas.yview)
        psb.pack(side=tk.RIGHT, fill=tk.Y)
        self.problems_canvas.configure(yscrollcommand=psb.set)

        self.problems_inner = tk.Frame(self.problems_canvas, bg=colors['bg_main'])
        self._problems_win = self.problems_canvas.create_window(
            (0, 0), window=self.problems_inner, anchor=tk.NW)
        self.problems_canvas.bind('<Configure>',
            lambda e: self.problems_canvas.itemconfig(self._problems_win, width=e.width - 4))
        self.problems_inner.bind('<Configure>',
            lambda e: self.problems_canvas.configure(scrollregion=self.problems_canvas.bbox('all')))

        self._show_frame('empty')

    def _show_frame(self, name):
        self._mode = name
        for n in ('view', 'edit', 'empty'):
            if hasattr(self, f'{n}_frame'):
                getattr(self, f'{n}_frame').pack_forget()
        getattr(self, f'{name}_frame').pack(fill=tk.BOTH, expand=True)

    # ============================================================
    # 计划列表
    # ============================================================

    def _refresh_plan_list(self):
        self.plan_listbox.delete(0, tk.END)
        self._plan_ids = []

        try:
            conn = get_connection()
            rows = conn.execute(
                "SELECT id, name, status FROM practice_plans ORDER BY created_at DESC"
            ).fetchall()
            conn.close()

            for row in rows:
                status_mark = '✓ ' if row['status'] == 'completed' else '  '
                self.plan_listbox.insert(tk.END, f'{status_mark}{row["name"]}')
                self._plan_ids.append(row['id'])
        except Exception:
            pass

    def _on_plan_select(self, event):
        sel = self.plan_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self._plan_ids):
            return
        self._current_plan_id = self._plan_ids[idx]
        self._show_frame('view')
        self._load_plan_view()

    def _load_plan_view(self):
        if not self._current_plan_id:
            return
        colors = self.config.get_colors()

        try:
            conn = get_connection()
            plan = conn.execute(
                "SELECT * FROM practice_plans WHERE id=?", (self._current_plan_id,)
            ).fetchone()
            if not plan:
                conn.close()
                return
            plan = dict(plan)

            # 题目列表
            items = conn.execute(
                """SELECT * FROM plan_problems WHERE plan_id=?
                   ORDER BY sort_order, id"""
                , (self._current_plan_id,)
            ).fetchall()
            conn.close()

            self.plan_title.config(text=plan['name'])

            # 计算进度
            total = len(items)
            done = sum(1 for it in items if it['status'] == 'done')
            pct = (done / total * 100) if total > 0 else 0
            self.progress_var.set(pct)
            self.progress_label.config(text=f'{done}/{total} 已完成 ({pct:.0f}%)' if total > 0 else '暂无题目')

            # 渲染题目列表
            for w in self.problems_inner.winfo_children():
                w.destroy()

            for i, item in enumerate(items):
                item = dict(item)
                rf = tk.Frame(self.problems_inner, bg=colors['bg_main'])
                rf.pack(fill=tk.X, padx=12, pady=2)

                sym = STATUS_SYMBOLS.get(item['status'], '○')
                title = item['title'] or f'题目 #{i+1}'

                # 状态切换按钮
                status_btn = tk.Label(rf, text=sym, font=(self.config.get('font_family'), 14),
                                       bg=colors['bg_main'],
                                       fg=colors['success'] if item['status'] == 'done' else colors['fg_muted'],
                                       cursor='hand2', padx=4)
                status_btn.pack(side=tk.LEFT)
                status_btn.bind('<Button-1>', lambda e, it=item: self._toggle_item_status(it['id']))

                # 题号 + 标题
                tk.Label(rf, text=f'{i+1}. {title}',
                         font=(self.config.get('font_family'), 11),
                         bg=colors['bg_main'], fg=colors['fg_primary'], anchor=tk.W
                         ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

                # 平台标记
                if item.get('platform'):
                    tk.Label(rf, text=f'[{item["platform"]}]',
                             font=(self.config.get('font_family'), 9),
                             bg=colors['bg_main'], fg=colors['fg_muted']
                             ).pack(side=tk.LEFT, padx=4)

                # 删除按钮
                del_btn = tk.Label(rf, text='×', font=(self.config.get('font_family'), 12),
                                    bg=colors['bg_main'], fg=colors['fg_muted'],
                                    cursor='hand2', padx=4)
                del_btn.pack(side=tk.RIGHT)
                del_btn.bind('<Button-1>', lambda e, it=item: self._remove_item(it['id']))
                del_btn.bind('<Enter>', lambda e, b=del_btn: b.configure(fg=colors['danger']))
                del_btn.bind('<Leave>', lambda e, b=del_btn: b.configure(fg=colors['fg_muted']))

        except Exception as e:
            self.app.set_status(f'加载计划失败: {e}')

    def _toggle_item_status(self, item_id):
        try:
            conn = get_connection()
            current = conn.execute(
                "SELECT status FROM plan_problems WHERE id=?", (item_id,)
            ).fetchone()
            if current:
                new_status = 'todo' if current['status'] == 'done' else 'done'
                conn.execute(
                    "UPDATE plan_problems SET status=? WHERE id=?", (new_status, item_id))
                conn.commit()
            conn.close()
            self._load_plan_view()
            self._refresh_plan_list()
        except Exception as e:
            self.app.set_status(f'状态更新失败: {e}')

    def _remove_item(self, item_id):
        try:
            conn = get_connection()
            conn.execute("DELETE FROM plan_problems WHERE id=?", (item_id,))
            conn.commit()
            conn.close()
            self._load_plan_view()
            self.app.set_status('题目已移除')
        except Exception as e:
            self.app.set_status(f'删除失败: {e}')

    # ============================================================
    # 操作：新建 / 删除计划
    # ============================================================

    def _new_plan(self):
        dialog = tk.Toplevel(self.parent)
        dialog.title('新建练习计划')
        dialog.geometry('400x250')
        dialog.transient(self.parent)
        colors = self.config.get_colors()
        dialog.configure(bg=colors['bg_main'])

        tk.Label(dialog, text='新建练习计划', font=(self.config.get('font_family'), 14, 'bold'),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(pady=(16, 12))

        tk.Label(dialog, text='计划名称', font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(anchor=tk.W, padx=20)
        name_var = tk.StringVar()
        tk.Entry(dialog, textvariable=name_var, font=(self.config.get('font_family'), 12),
                 bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT
                 ).pack(fill=tk.X, padx=20, pady=(2, 10), ipady=4)

        tk.Label(dialog, text='描述（可选）', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(anchor=tk.W, padx=20)
        desc_text = tk.Text(dialog, font=(self.config.get('font_family'), 10),
                            bg=colors['bg_input'], fg=colors['fg_primary'],
                            relief=tk.FLAT, height=3, wrap=tk.WORD)
        desc_text.pack(fill=tk.X, padx=20, pady=(2, 10))

        btn_row = tk.Frame(dialog, bg=colors['bg_main'])
        btn_row.pack(fill=tk.X, padx=20, pady=(0, 12))
        tk.Button(btn_row, text='取消', font=(self.config.get('font_family'), 11),
                  bg=colors['bg_sidebar'], fg=colors['fg_primary'],
                  relief=tk.FLAT, padx=16, pady=6,
                  command=dialog.destroy).pack(side=tk.RIGHT, padx=(8, 0))
        tk.Button(btn_row, text='创建', font=(self.config.get('font_family'), 11),
                  bg=colors['fg_accent'], fg='#ffffff', relief=tk.FLAT,
                  padx=16, pady=6,
                  command=lambda: self._do_create_plan(
                      name_var.get().strip(), desc_text.get('1.0', tk.END).strip(), dialog)
                  ).pack(side=tk.RIGHT)

    def _do_create_plan(self, name, desc, dialog):
        if not name:
            messagebox.showwarning('提示', '请输入计划名称')
            return
        try:
            conn = get_connection()
            conn.execute(
                "INSERT INTO practice_plans (name, description) VALUES (?, ?)",
                (name, desc))
            conn.commit()
            conn.close()
            dialog.destroy()
            self._refresh_plan_list()
            self.app.set_status(f'计划「{name}」已创建')
        except Exception as e:
            self.app.set_status(f'创建失败: {e}')

    def _delete_plan(self):
        if not self._current_plan_id:
            return
        if not messagebox.askyesno('确认删除', '确定要删除这个计划吗？\n（计划内的题目也会被删除）'):
            return
        try:
            conn = get_connection()
            conn.execute("DELETE FROM practice_plans WHERE id=?", (self._current_plan_id,))
            conn.commit()
            conn.close()
            self._current_plan_id = None
            self._refresh_plan_list()
            self._show_frame('empty')
            self.app.set_status('计划已删除')
        except Exception as e:
            self.app.set_status(f'删除失败: {e}')

    # ============================================================
    # 添加题目
    # ============================================================

    def _add_problem_dialog(self):
        if not self._current_plan_id:
            return

        dialog = tk.Toplevel(self.parent)
        dialog.title('添加题目到计划')
        dialog.geometry('600x500')
        dialog.transient(self.parent)
        colors = self.config.get_colors()
        dialog.configure(bg=colors['bg_main'])

        # 从本地题库选择
        tk.Label(dialog, text='从刷题库选择', font=(self.config.get('font_family'), 13, 'bold'),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(anchor=tk.W, padx=16, pady=(12, 6))

        # 搜索
        search_var = tk.StringVar()
        search_fr = tk.Frame(dialog, bg=colors['bg_sidebar'])
        search_fr.pack(fill=tk.X, padx=12, pady=(0, 4))
        tk.Entry(search_fr, textvariable=search_var, font=(self.config.get('font_family'), 10),
                 bg=colors['bg_input'], fg=colors['fg_primary'],
                 relief=tk.FLAT).pack(fill=tk.X, padx=8, pady=6)

        # 题目列表
        list_frame = tk.Frame(dialog, bg=colors['bg_main'])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 4))

        problem_listbox = tk.Listbox(list_frame, font=(self.config.get('font_family'), 10),
                                      bg=colors['bg_input'], fg=colors['fg_primary'],
                                      selectbackground=colors['fg_accent'])
        problem_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=problem_listbox.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        problem_listbox.configure(yscrollcommand=scroll.set)

        _local_ids = []

        def refresh_local():
            problem_listbox.delete(0, tk.END)
            _local_ids.clear()
            try:
                conn = get_connection()
                rows = conn.execute(
                    "SELECT id, title, platform, platform_id, difficulty FROM problems ORDER BY updated_at DESC"
                ).fetchall()
                conn.close()
                s = search_var.get().lower().strip()
                for row in rows:
                    title = row['title'].lower()
                    pid = (row['platform_id'] or '').lower()
                    if s and s not in title and s not in pid:
                        continue
                    problem_listbox.insert(tk.END,
                        f'{row["title"]}  [{row["platform"]}]  {row["difficulty"]}')
                    _local_ids.append(row['id'])
            except Exception:
                pass

        search_var.trace_add('write', lambda *a: refresh_local())
        refresh_local()

        # 手动输入外部题目
        sep = tk.Frame(dialog, bg=colors['border'], height=1)
        sep.pack(fill=tk.X, padx=12, pady=8)
        tk.Label(dialog, text='或手动输入外部题目', font=(self.config.get('font_family'), 13, 'bold'),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(anchor=tk.W, padx=16)

        ext_frame = tk.Frame(dialog, bg=colors['bg_main'])
        ext_frame.pack(fill=tk.X, padx=16, pady=(6, 4))
        tk.Label(ext_frame, text='标题', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(anchor=tk.W)
        ext_title = tk.Entry(ext_frame, font=(self.config.get('font_family'), 11),
                              bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT)
        ext_title.pack(fill=tk.X, pady=(2, 4), ipady=3)

        ext_row = tk.Frame(ext_frame, bg=colors['bg_main'])
        ext_row.pack(fill=tk.X)
        tk.Label(ext_row, text='平台', font=(self.config.get('font_family'), 9),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(side=tk.LEFT)
        ext_platform = tk.StringVar(value='手动输入')
        ttk.Combobox(ext_row, textvariable=ext_platform,
                      values=['手动输入', 'Codeforces', '洛谷', 'AtCoder', '其他'],
                      state='readonly', width=12).pack(side=tk.LEFT, padx=4)

        # 操作按钮
        btn_fr = tk.Frame(dialog, bg=colors['bg_main'])
        btn_fr.pack(fill=tk.X, padx=12, pady=12)
        tk.Button(btn_fr, text='关闭', font=(self.config.get('font_family'), 11),
                  bg=colors['bg_sidebar'], fg=colors['fg_primary'],
                  relief=tk.FLAT, padx=16, pady=6,
                  command=dialog.destroy).pack(side=tk.RIGHT, padx=(8, 0))
        tk.Button(btn_fr, text='添加外部题', font=(self.config.get('font_family'), 11),
                  bg=colors['fg_accent'], fg='#ffffff', relief=tk.FLAT,
                  padx=12, pady=6,
                  command=lambda: self._add_external_problem(
                      ext_title.get().strip(), ext_platform.get(), dialog)
                  ).pack(side=tk.RIGHT, padx=4)
        tk.Button(btn_fr, text='添加选中题目', font=(self.config.get('font_family'), 11),
                  bg=colors['fg_accent'], fg='#ffffff', relief=tk.FLAT,
                  padx=12, pady=6,
                  command=lambda: self._add_local_problem(problem_listbox, _local_ids, dialog)
                  ).pack(side=tk.RIGHT, padx=4)

    def _add_local_problem(self, listbox, ids, dialog):
        sel = listbox.curselection()
        if not sel:
            messagebox.showwarning('提示', '请先选择一道题目')
            return
        idx = sel[0]
        if idx >= len(ids):
            return
        pid = ids[idx]
        try:
            conn = get_connection()
            row = conn.execute("SELECT * FROM problems WHERE id=?", (pid,)).fetchone()
            if row:
                row = dict(row)
                # 获取当前计划的最大 sort_order
                max_order = conn.execute(
                    "SELECT MAX(sort_order) as m FROM plan_problems WHERE plan_id=?",
                    (self._current_plan_id,)
                ).fetchone()
                next_order = (max_order['m'] or 0) + 1
                conn.execute(
                    """INSERT INTO plan_problems
                       (plan_id, problem_id, platform, platform_id, title, difficulty, tags, sort_order)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (self._current_plan_id, row['id'], row['platform'], row.get('platform_id', ''),
                     row['title'], row.get('difficulty', ''), row.get('tags', ''), next_order))
                conn.commit()
            conn.close()
            self._load_plan_view()
            self.app.set_status(f'已添加「{row["title"]}」')
        except Exception as e:
            self.app.set_status(f'添加失败: {e}')

    def _add_external_problem(self, title, platform, dialog):
        if not title:
            messagebox.showwarning('提示', '请输入题目标题')
            return
        try:
            conn = get_connection()
            max_order = conn.execute(
                "SELECT MAX(sort_order) as m FROM plan_problems WHERE plan_id=?",
                (self._current_plan_id,)
            ).fetchone()
            next_order = (max_order['m'] or 0) + 1
            conn.execute(
                """INSERT INTO plan_problems
                   (plan_id, platform, title, sort_order)
                   VALUES (?, ?, ?, ?)""",
                (self._current_plan_id, platform, title, next_order))
            conn.commit()
            conn.close()
            self._load_plan_view()
            self.app.set_status(f'已添加外部题「{title}」')
        except Exception as e:
            self.app.set_status(f'添加失败: {e}')

    def on_new(self):
        self._new_plan()

    def apply_theme(self):
        for w in self.parent.winfo_children():
            w.destroy()
        self._build_ui()
        self._refresh_plan_list()
