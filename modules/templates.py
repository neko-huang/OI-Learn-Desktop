"""
算法模板库模块 - 内嵌编辑
"""

import tkinter as tk
from tkinter import ttk, messagebox

from config import Config
from db.database import get_connection
from components.markdown_view import MarkdownView

CATEGORIES = ['数据结构', '图论', 'DP', '数学', '字符串', '搜索', '工具与技巧', '其他']
LANGUAGES = ['cpp', 'python', 'java']


class TemplatesModule:

    def __init__(self, app, parent_frame):
        self.app = app
        self.config = Config()
        self.parent = parent_frame
        for w in parent_frame.winfo_children():
            w.destroy()

        self._current_id = None
        self._mode = 'view'
        self._dirty = False
        self._load_templates()
        self._build_ui()
        self._refresh_list()

    def _load_templates(self):
        try:
            conn = get_connection()
            rows = conn.execute(
                "SELECT id, name, category, language, code, note, is_starred FROM templates ORDER BY is_starred DESC, updated_at DESC"
            ).fetchall()
            self.templates = [dict(r) for r in rows]
            conn.close()
        except Exception as e:
            self.app.set_status(f'加载模板失败: {e}')
            # 保留旧数据

    def _build_ui(self):
        colors = self.config.get_colors()

        top = tk.Frame(self.parent, bg=colors['bg_sidebar'], height=42)
        top.pack(fill=tk.X)
        top.pack_propagate(False)

        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', lambda *a: self._refresh_list())
        self.search_entry = tk.Entry(top, textvariable=self.search_var, font=(self.config.get('font_family'), 11),
                 bg=colors['bg_input'], fg=colors['fg_primary'],
                 relief=tk.FLAT)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=12, pady=8)

        tk.Button(top, text='+ 新建', font=(self.config.get('font_family'), 10),
                  bg=colors['fg_accent'], fg='#ffffff', relief=tk.FLAT,
                  padx=12, pady=4, cursor='hand2',
                  command=self._start_add).pack(side=tk.RIGHT, padx=8, pady=8)

        main = tk.Frame(self.parent, bg=colors['bg_main'])
        main.pack(fill=tk.BOTH, expand=True)

        # 左侧
        left = tk.Frame(main, width=280, bg=colors['bg_sidebar'])
        left.pack(side=tk.LEFT, fill=tk.Y)
        left.pack_propagate(False)

        tk.Label(left, text='模板库', font=(self.config.get('font_family'), 13, 'bold'),
                 bg=colors['bg_sidebar'], fg=colors['fg_primary']).pack(anchor=tk.W, padx=12, pady=(10, 4))

        self.cat_var = tk.StringVar(value='全部')
        ttk.Combobox(left, textvariable=self.cat_var, values=['全部'] + CATEGORIES,
                      state='readonly', width=18).pack(fill=tk.X, padx=8, pady=(0, 4))
        self.cat_var.trace_add('write', lambda *a: self._refresh_list())

        self.lang_var = tk.StringVar(value='全部')
        ttk.Combobox(left, textvariable=self.lang_var,
                      values=['全部', 'cpp', 'python', 'java'],
                      state='readonly', width=18).pack(fill=tk.X, padx=8, pady=(0, 6))
        self.lang_var.trace_add('write', lambda *a: self._refresh_list())

        list_frame = tk.Frame(left, bg=colors['bg_sidebar'])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))

        self.listbox = tk.Listbox(list_frame, font=(self.config.get('font_family'), 10),
                                   bg=colors['bg_input'], fg=colors['fg_primary'],
                                   selectbackground=colors['fg_accent'], selectforeground='#ffffff',
                                   relief=tk.FLAT, activestyle='none')
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.listbox.bind('<<ListboxSelect>>', self._on_select)

        sb = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.listbox.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.configure(yscrollcommand=sb.set)

        # 右侧
        self.right = tk.Frame(main, bg=colors['bg_main'])
        self.right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 查看模式
        self.view_frame = tk.Frame(self.right, bg=colors['bg_main'])
        self.detail_md = MarkdownView(self.view_frame)
        self.detail_md.pack(fill=tk.BOTH, expand=True, padx=12, pady=(8, 4))

        vbar = tk.Frame(self.view_frame, bg=colors['bg_sidebar'], height=40)
        vbar.pack(fill=tk.X, side=tk.BOTTOM)
        vbar.pack_propagate(False)
        tk.Button(vbar, text='⭐', font=(self.config.get('font_family'), 12),
                  bg=colors['bg_sidebar'], fg=colors['fg_accent'], relief=tk.FLAT,
                  cursor='hand2', padx=12,
                  command=lambda: self._toggle_star(self._current_id)).pack(side=tk.LEFT, padx=12)
        tk.Button(vbar, text='删除', font=(self.config.get('font_family'), 10),
                  bg=colors['bg_sidebar'], fg=colors['danger'], relief=tk.FLAT,
                  cursor='hand2', command=self._delete_current).pack(side=tk.RIGHT, padx=8)
        tk.Button(vbar, text='编辑', font=(self.config.get('font_family'), 10),
                  bg=colors['fg_accent'], fg='#ffffff', relief=tk.FLAT,
                  cursor='hand2', command=self._start_edit).pack(side=tk.RIGHT, padx=4)

        # 编辑模式
        self._build_edit()
        self._build_empty()
        self._show_frame('empty')

    def _build_edit(self):
        colors = self.config.get_colors()
        self.edit_frame = tk.Frame(self.right, bg=colors['bg_main'])
        pad_x = 16

        tk.Label(self.edit_frame, text='编辑完成后切换将自动保存', font=(self.config.get('font_family'), 9),
                 bg=colors['bg_main'], fg=colors['fg_muted'], anchor=tk.W).pack(fill=tk.X, padx=pad_x, pady=(6, 0))

        tk.Label(self.edit_frame, text='名称', font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.W).pack(fill=tk.X, padx=pad_x, pady=(8, 0))
        self.e_name = tk.Entry(self.edit_frame, font=(self.config.get('font_family'), 12, 'bold'),
                                bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT)
        self.e_name.pack(fill=tk.X, padx=pad_x, pady=(2, 4), ipady=4)

        row = tk.Frame(self.edit_frame, bg=colors['bg_main'])
        row.pack(fill=tk.X, padx=pad_x, pady=(4, 4))
        tk.Label(row, text='分类', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(side=tk.LEFT)
        self.e_cat = ttk.Combobox(row, values=CATEGORIES, state='readonly', width=14)
        self.e_cat.pack(side=tk.LEFT, padx=4)
        self.e_cat.set('数据结构')
        tk.Label(row, text='语言', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(side=tk.LEFT, padx=(16, 4))
        self.e_lang = ttk.Combobox(row, values=LANGUAGES, state='readonly', width=8)
        self.e_lang.pack(side=tk.LEFT, padx=4)
        self.e_lang.set('cpp')

        tk.Label(self.edit_frame, text='备注', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.W).pack(fill=tk.X, padx=pad_x, pady=(8, 0))
        self.e_note = tk.Text(self.edit_frame, font=(self.config.get('font_family'), 10),
                               bg=colors['bg_input'], fg=colors['fg_primary'],
                               relief=tk.FLAT, wrap=tk.WORD, height=2, undo=True)
        self.e_note.pack(fill=tk.X, padx=pad_x, pady=(2, 4))

        tk.Label(self.edit_frame, text='代码', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.W).pack(fill=tk.X, padx=pad_x, pady=(8, 0))
        self.e_code = tk.Text(self.edit_frame, font=(self.config.get('code_font_family'), 11),
                               bg=colors['bg_input'], fg=colors['fg_primary'],
                               relief=tk.FLAT, wrap=tk.NONE, undo=True)
        self.e_code.pack(fill=tk.BOTH, expand=True, padx=pad_x, pady=(2, 2))
        # 水平滚动条
        code_xsb = ttk.Scrollbar(self.edit_frame, orient=tk.HORIZONTAL, command=self.e_code.xview)
        code_xsb.pack(fill=tk.X, padx=pad_x)
        self.e_code.configure(xscrollcommand=code_xsb.set)

        ebar = tk.Frame(self.edit_frame, bg=colors['bg_sidebar'], height=40)
        ebar.pack(fill=tk.X, side=tk.BOTTOM)
        ebar.pack_propagate(False)
        tk.Button(ebar, text='返回查看', font=(self.config.get('font_family'), 10),
                  bg=colors['bg_sidebar'], fg=colors['fg_primary'], relief=tk.FLAT,
                  padx=16, pady=4, command=self._exit_edit).pack(side=tk.RIGHT, padx=8)

        # 编辑字段变化时标记 dirty
        self.e_name.bind('<KeyRelease>', lambda e: self._mark_dirty())
        self.e_note.bind('<KeyRelease>', lambda e: self._mark_dirty())
        self.e_code.bind('<KeyRelease>', lambda e: self._mark_dirty())
        self.e_cat.bind('<<ComboboxSelected>>', lambda e: self._mark_dirty())
        self.e_lang.bind('<<ComboboxSelected>>', lambda e: self._mark_dirty())

    def _build_empty(self):
        colors = self.config.get_colors()
        self.empty_frame = tk.Frame(self.right, bg=colors['bg_main'])
        tk.Label(self.empty_frame, text='选择一个模板查看\n或点击「+ 新建」创建',
                 font=(self.config.get('font_family'), 14),
                 bg=colors['bg_main'], fg=colors['fg_muted']
                 ).place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    def _show_frame(self, name):
        self._mode = name
        for n in ('view', 'edit', 'empty'):
            getattr(self, f'{n}_frame').pack_forget()
        getattr(self, f'{name}_frame').pack(fill=tk.BOTH, expand=True)

    def _mark_dirty(self, event=None):
        self._dirty = True

    def _refresh_list(self):
        search = self.search_var.get().lower().strip()
        cat = self.cat_var.get()
        lang = self.lang_var.get()
        lang_filter = lang if lang != '全部' else None

        self.listbox.delete(0, tk.END)
        self._list_ids = []
        for t in self.templates:
            if cat != '全部' and t['category'] != cat:
                continue
            if lang_filter and t['language'] != lang_filter:
                continue
            if search and search not in t['name'].lower():
                continue
            star = '⭐ ' if t['is_starred'] else '   '
            self.listbox.insert(tk.END, f'{star}{t["name"]}')
            self._list_ids.append(t['id'])

    def _on_select(self, event):
        sel = self.listbox.curselection()
        if not sel:
            return
        self._auto_save()
        idx = sel[0]
        if idx >= len(self._list_ids):
            return
        self._current_id = self._list_ids[idx]
        self._show_frame('view')
        self._load_view()

    def _load_view(self):
        if not self._current_id:
            return
        t = next((t for t in self.templates if t['id'] == self._current_id), None)
        if not t:
            return
        lang = t['language']
        md = f'# {t["name"]}\n\n- **分类**: {t["category"]}  |  **语言**: {lang}\n'
        if t.get('note'):
            md += f'\n{t["note"]}\n'
        md += f'\n```{lang}\n{t["code"]}\n```\n'
        self.detail_md.render(md)

    def _start_add(self):
        self._auto_save()
        self._current_id = None
        self.e_name.delete(0, tk.END)
        self.e_cat.set('数据结构')
        self.e_lang.set('cpp')
        self.e_note.delete('1.0', tk.END)
        self.e_code.delete('1.0', tk.END)
        self._dirty = False
        self._show_frame('edit')

    def _start_edit(self):
        if not self._current_id:
            return
        self._auto_save()
        t = next((t for t in self.templates if t['id'] == self._current_id), None)
        if not t:
            return
        self.e_name.delete(0, tk.END)
        self.e_name.insert(0, t['name'])
        self.e_cat.set(t.get('category', '数据结构'))
        self.e_lang.set(t.get('language', 'cpp'))
        self.e_note.delete('1.0', tk.END)
        self.e_note.insert('1.0', t.get('note', ''))
        self.e_code.delete('1.0', tk.END)
        self.e_code.insert('1.0', t.get('code', ''))
        self._dirty = False
        self._show_frame('edit')

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
        name = self.e_name.get().strip()
        if not name:
            name = '未命名模板'
            self.e_name.delete(0, tk.END)
            self.e_name.insert(0, name)
        cat = self.e_cat.get()
        lang = self.e_lang.get()
        note = self.e_note.get('1.0', tk.END).strip()
        code = self.e_code.get('1.0', tk.END).strip()
        try:
            conn = get_connection()
            if self._current_id:
                conn.execute(
                    "UPDATE templates SET name=?, category=?, language=?, code=?, note=?, updated_at=datetime('now','localtime') WHERE id=?",
                    (name, cat, lang, code, note, self._current_id))
            else:
                cursor = conn.execute(
                    "INSERT INTO templates (name, category, language, code, note) VALUES (?,?,?,?,?)",
                    (name, cat, lang, code, note))
                self._current_id = cursor.lastrowid
            conn.commit()
            conn.close()
        except Exception as e:
            self.app.set_status(f'保存失败: {e}')
            return
        self._dirty = False
        self._load_templates()
        self._refresh_list()
        self.app.set_status(f'已自动保存「{name}」')

    def _toggle_star(self, tid):
        if not tid:
            return
        try:
            conn = get_connection()
            conn.execute("UPDATE templates SET is_starred = 1 - is_starred WHERE id=?", (tid,))
            conn.commit()
            conn.close()
            self._load_templates()
            self._refresh_list()
            self._load_view()
        except Exception as e:
            self.app.set_status(f'操作失败: {e}')

    def _delete_current(self):
        if not self._current_id:
            return
        if not messagebox.askyesno('确认删除', '确定要删除这个模板吗？'):
            return
        try:
            conn = get_connection()
            conn.execute("DELETE FROM templates WHERE id=?", (self._current_id,))
            conn.commit()
            conn.close()
            self._current_id = None
            self._load_templates()
            self._refresh_list()
            self._show_frame('empty')
        except Exception as e:
            self.app.set_status(f'操作失败: {e}')

    def on_before_leave(self):
        self._auto_save()

    def on_search(self):
        """Ctrl+F: 聚焦搜索框并全选"""
        self.search_entry.focus_set()
        self.search_entry.select_range(0, 'end')

    def on_new(self):
        self._start_add()

    def on_export(self):
        from services.exporter import export_templates_to_md
        path = export_templates_to_md()
        if path:
            self.app.set_status(f'已导出: {path}')
        else:
            self.app.set_status('暂无数据可导出')

    def apply_theme(self):
        self._auto_save()
        for w in self.parent.winfo_children():
            w.destroy()
        self._load_templates()
        self._build_ui()
        self._refresh_list()
