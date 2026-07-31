"""
易错集模块
左侧列表 + 右侧错误/正确代码对比 + Markdown原因分析
支持关联刷题记录、自动保存
"""

import tkinter as tk
from tkinter import ttk, messagebox

from config import Config
from db.database import get_connection
from components.markdown_view import MarkdownView


class MistakesModule:

    def __init__(self, app, parent_frame):
        self.app = app
        self.config = Config()
        self.parent = parent_frame
        for w in parent_frame.winfo_children():
            w.destroy()

        self._current_id = None
        self._mode = 'view'
        self._dirty = False

        self._build_ui()
        self._refresh_list()

    # ============================================================
    # UI
    # ============================================================

    def _build_ui(self):
        colors = self.config.get_colors()

        # 顶部工具栏
        top = tk.Frame(self.parent, bg=colors['bg_sidebar'], height=42)
        top.pack(fill=tk.X)
        top.pack_propagate(False)

        tk.Label(top, text='搜索:', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_sidebar'], fg=colors['fg_secondary']).pack(side=tk.LEFT, padx=(12, 4))
        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', lambda *a: self._refresh_list())
        tk.Entry(top, textvariable=self.search_var, font=(self.config.get('font_family'), 10),
                 bg=colors['bg_input'], fg=colors['fg_primary'],
                 relief=tk.FLAT, width=20).pack(side=tk.LEFT)

        tk.Frame(top, bg=colors['bg_sidebar']).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(top, text='+ 新建', font=(self.config.get('font_family'), 10),
                  bg=colors['fg_accent'], fg='#ffffff', relief=tk.FLAT,
                  padx=16, pady=4, cursor='hand2',
                  command=self._new_entry).pack(side=tk.RIGHT, padx=8, pady=8)

        # 主体
        main = tk.Frame(self.parent, bg=colors['bg_main'])
        main.pack(fill=tk.BOTH, expand=True)

        self._build_left(main)
        self._build_right(main)

    def _build_left(self, parent):
        colors = self.config.get_colors()
        left = tk.Frame(parent, bg=colors['bg_sidebar'], width=280)
        left.pack(side=tk.LEFT, fill=tk.Y)
        left.pack_propagate(False)

        tk.Label(left, text='易错集', font=(self.config.get('font_family'), 12, 'bold'),
                 bg=colors['bg_sidebar'], fg=colors['fg_primary']
                 ).pack(anchor=tk.W, padx=12, pady=(6, 4))

        self.mistakes_listbox = tk.Listbox(
            left, font=(self.config.get('font_family'), 10),
            bg=colors['bg_input'], fg=colors['fg_primary'],
            selectbackground=colors['fg_accent'], selectforeground='#ffffff',
            relief=tk.FLAT, activestyle='none',
        )
        self.mistakes_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=(0, 8))
        self.mistakes_listbox.bind('<<ListboxSelect>>', self._on_select)

        sb = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.mistakes_listbox.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y, pady=(0, 8), padx=(0, 8))
        self.mistakes_listbox.configure(yscrollcommand=sb.set)

    def _build_right(self, parent):
        colors = self.config.get_colors()
        self.right = tk.Frame(parent, bg=colors['bg_main'])
        self.right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 查看模式
        self.view_frame = tk.Frame(self.right, bg=colors['bg_main'])
        self._build_view()
        # 编辑模式
        self.edit_frame = tk.Frame(self.right, bg=colors['bg_main'])
        self._build_edit()
        # 空状态
        self.empty_frame = tk.Frame(self.right, bg=colors['bg_main'])
        tk.Label(self.empty_frame, text='选择一个易错记录查看\n或点击「+ 新建」添加',
                 font=(self.config.get('font_family'), 14),
                 bg=colors['bg_main'], fg=colors['fg_muted']
                 ).place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        self._show_frame('empty')

    def _build_view(self):
        colors = self.config.get_colors()
        pad = 16

        self.view_title = tk.Label(self.view_frame, text='',
                                    font=(self.config.get('font_family'), 16, 'bold'),
                                    bg=colors['bg_main'], fg=colors['fg_primary'], anchor=tk.W)
        self.view_title.pack(fill=tk.X, padx=pad, pady=(12, 4))

        # 查看用 Markdown
        self.view_md = MarkdownView(self.view_frame)
        self.view_md.pack(fill=tk.BOTH, expand=True, padx=12, pady=(4, 4))

        bar = tk.Frame(self.view_frame, bg=colors['bg_sidebar'], height=40)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        bar.pack_propagate(False)
        tk.Button(bar, text='删除', font=(self.config.get('font_family'), 10),
                  bg=colors['bg_sidebar'], fg=colors['danger'], relief=tk.FLAT,
                  padx=12, pady=4, command=self._delete_current).pack(side=tk.RIGHT, padx=8)
        tk.Button(bar, text='编辑', font=(self.config.get('font_family'), 10),
                  bg=colors['fg_accent'], fg='#ffffff', relief=tk.FLAT,
                  padx=16, pady=4, command=lambda: self._edit_entry(self._current_id)
                  ).pack(side=tk.RIGHT, padx=4)

    def _build_edit(self):
        colors = self.config.get_colors()
        pad = 16

        tk.Label(self.edit_frame, text='编辑完成后切换将自动保存', font=(self.config.get('font_family'), 9),
                 bg=colors['bg_main'], fg=colors['fg_muted'], anchor=tk.W
                 ).pack(fill=tk.X, padx=pad, pady=(6, 0))

        # 标题
        tk.Label(self.edit_frame, text='错误描述', font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.W).pack(fill=tk.X, padx=pad, pady=(8, 0))
        self.e_title = tk.Entry(self.edit_frame, font=(self.config.get('font_family'), 12, 'bold'),
                                 bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT)
        self.e_title.pack(fill=tk.X, padx=pad, pady=(2, 4), ipady=4)
        self.e_title.bind('<KeyRelease>', lambda e: self._mark_dirty())

        # 错误代码 + 正确代码（左右并列）
        code_row = tk.Frame(self.edit_frame, bg=colors['bg_main'])
        code_row.pack(fill=tk.BOTH, expand=True, padx=pad, pady=(8, 0))

        # 错误代码
        left_code = tk.Frame(code_row, bg=colors['bg_main'])
        left_code.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))
        tk.Label(left_code, text='❌ 错误代码', font=(self.config.get('font_family'), 11, 'bold'),
                 bg=colors['bg_main'], fg=colors['danger']).pack(anchor=tk.W)
        self.e_wrong = tk.Text(left_code, font=(self.config.get('code_font_family'), 11),
                                bg=colors['bg_input'], fg=colors['fg_primary'],
                                relief=tk.FLAT, wrap=tk.NONE, undo=True)
        self.e_wrong.pack(fill=tk.BOTH, expand=True, pady=(2, 0))
        self.e_wrong.bind('<KeyRelease>', lambda e: self._mark_dirty())

        # 正确代码
        right_code = tk.Frame(code_row, bg=colors['bg_main'])
        right_code.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 0))
        tk.Label(right_code, text='✅ 正确代码', font=(self.config.get('font_family'), 11, 'bold'),
                 bg=colors['bg_main'], fg=colors['success']).pack(anchor=tk.W)
        self.e_correct = tk.Text(right_code, font=(self.config.get('code_font_family'), 11),
                                  bg=colors['bg_input'], fg=colors['fg_primary'],
                                  relief=tk.FLAT, wrap=tk.NONE, undo=True)
        self.e_correct.pack(fill=tk.BOTH, expand=True, pady=(2, 0))
        self.e_correct.bind('<KeyRelease>', lambda e: self._mark_dirty())

        # 错误原因
        tk.Label(self.edit_frame, text='错误原因（Markdown）', font=(self.config.get('font_family'), 11, 'bold'),
                 bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.W).pack(fill=tk.X, padx=pad, pady=(12, 0))
        self.e_reason = tk.Text(self.edit_frame, font=(self.config.get('code_font_family'), 11),
                                 bg=colors['bg_input'], fg=colors['fg_primary'],
                                 relief=tk.FLAT, wrap=tk.WORD, undo=True, height=4)
        self.e_reason.pack(fill=tk.X, padx=pad, pady=(2, 4))
        self.e_reason.bind('<KeyRelease>', lambda e: self._mark_dirty())

        bar = tk.Frame(self.edit_frame, bg=colors['bg_sidebar'], height=40)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        bar.pack_propagate(False)
        tk.Button(bar, text='返回查看', font=(self.config.get('font_family'), 10),
                  bg=colors['bg_sidebar'], fg=colors['fg_primary'], relief=tk.FLAT,
                  padx=16, pady=4, command=self._exit_edit).pack(side=tk.RIGHT, padx=8)

    # ============================================================
    # 列表
    # ============================================================

    def _refresh_list(self):
        self.mistakes_listbox.delete(0, tk.END)
        self._list_ids = []

        search = self.search_var.get().lower().strip()
        try:
            conn = get_connection()
            rows = conn.execute("SELECT id, title, created_at FROM mistakes ORDER BY updated_at DESC").fetchall()
            conn.close()
        except Exception:
            rows = []

        for row in rows:
            title = row['title'] or '(未命名)'
            if search and search not in title.lower():
                continue
            self.mistakes_listbox.insert(tk.END, title)
            self._list_ids.append(row['id'])

    def _on_select(self, event):
        sel = self.mistakes_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self._list_ids):
            return
        self._auto_save()
        self._current_id = self._list_ids[idx]
        self._show_frame('view')
        self._load_view()

    def _load_view(self):
        if not self._current_id:
            return
        try:
            conn = get_connection()
            row = conn.execute("SELECT * FROM mistakes WHERE id=?", (self._current_id,)).fetchone()
            conn.close()
            if not row:
                return
            row = dict(row)

            self.view_title.config(text=row.get('title', '(未命名)'))

            md = f'## 错误原因\n\n{row.get("reason", "") or "*暂无*"}\n\n'
            if row.get('wrong_code'):
                md += '## 错误代码\n\n```cpp\n' + row['wrong_code'] + '\n```\n\n'
            if row.get('correct_code'):
                md += '## 正确代码\n\n```cpp\n' + row['correct_code'] + '\n```\n'

            self.view_md.render(md)
        except Exception as e:
            self.app.set_status(f'加载失败: {e}')

    # ============================================================
    # 编辑
    # ============================================================

    def _new_entry(self):
        self._auto_save()
        self._current_id = None
        self.e_title.delete(0, tk.END)
        self.e_wrong.delete('1.0', tk.END)
        self.e_correct.delete('1.0', tk.END)
        self.e_reason.delete('1.0', tk.END)
        self._dirty = False
        self._show_frame('edit')

    def _edit_entry(self, entry_id):
        if not entry_id:
            return
        self._auto_save()
        self._current_id = entry_id
        try:
            conn = get_connection()
            row = conn.execute("SELECT * FROM mistakes WHERE id=?", (entry_id,)).fetchone()
            conn.close()
            if row:
                row = dict(row)
                self.e_title.delete(0, tk.END)
                self.e_title.insert(0, row.get('title', ''))
                self.e_wrong.delete('1.0', tk.END)
                self.e_wrong.insert('1.0', row.get('wrong_code', ''))
                self.e_correct.delete('1.0', tk.END)
                self.e_correct.insert('1.0', row.get('correct_code', ''))
                self.e_reason.delete('1.0', tk.END)
                self.e_reason.insert('1.0', row.get('reason', ''))
                self._dirty = False
                self._show_frame('edit')
        except Exception as e:
            self.app.set_status(f'加载失败: {e}')

    def _exit_edit(self):
        self._auto_save()
        if self._current_id:
            self._show_frame('view')
            self._load_view()
        else:
            self._show_frame('empty')

    def _auto_save(self):
        if self._mode != 'edit' or not self._dirty:
            return
        title = self.e_title.get().strip()
        wrong = self.e_wrong.get('1.0', tk.END).strip()
        correct = self.e_correct.get('1.0', tk.END).strip()
        reason = self.e_reason.get('1.0', tk.END).strip()

        try:
            conn = get_connection()
            if self._current_id:
                conn.execute(
                    """UPDATE mistakes SET title=?, wrong_code=?, correct_code=?, reason=?,
                       updated_at=datetime('now','localtime') WHERE id=?""",
                    (title, wrong, correct, reason, self._current_id))
            else:
                cursor = conn.execute(
                    """INSERT INTO mistakes (title, wrong_code, correct_code, reason)
                       VALUES (?, ?, ?, ?)""",
                    (title, wrong, correct, reason))
                self._current_id = cursor.lastrowid
            conn.commit()
            conn.close()
        except Exception as e:
            self.app.set_status(f'保存失败: {e}')
            return

        self._dirty = False
        self._refresh_list()
        self.app.set_status(f'已自动保存「{title or "..."}」')

    def _delete_current(self):
        if not self._current_id:
            return
        if not messagebox.askyesno('确认删除', '确定要删除这条记录吗？'):
            return
        try:
            conn = get_connection()
            conn.execute("DELETE FROM mistakes WHERE id=?", (self._current_id,))
            conn.commit()
            conn.close()
            self._current_id = None
            self._refresh_list()
            self._show_frame('empty')
            self.app.set_status('已删除')
        except Exception as e:
            self.app.set_status(f'删除失败: {e}')

    def _show_frame(self, name):
        self._mode = name
        for n in ('view', 'edit', 'empty'):
            getattr(self, f'{n}_frame').pack_forget()
        getattr(self, f'{name}_frame').pack(fill=tk.BOTH, expand=True)

    def _mark_dirty(self):
        self._dirty = True

    def on_before_leave(self):
        self._auto_save()

    def on_new(self):
        self._new_entry()

    def apply_theme(self):
        self._auto_save()
        for w in self.parent.winfo_children():
            w.destroy()
        self._build_ui()
        self._refresh_list()
