"""
算法模板库模块
分类浏览 + 搜索 + Markdown 详情 + 代码语法高亮 + 收藏 + CRUD
"""

import json
import tkinter as tk
from tkinter import ttk, messagebox

from config import Config
from db.database import get_connection
from components.markdown_view import MarkdownView

CATEGORIES = ['数据结构', '图论', 'DP', '数学', '字符串', '搜索', '工具与技巧', '其他']
LANGUAGES = ['cpp', 'python', 'java']


class TemplatesModule:
    """算法模板库模块"""

    def __init__(self, app, parent_frame: tk.Frame):
        self.app = app
        self.config = Config()
        self.parent = parent_frame
        for w in parent_frame.winfo_children():
            w.destroy()

        self._current_template_id = None
        self._load_templates()
        self._build_ui()
        self._refresh_list()

    # ============================================================
    # 数据
    # ============================================================

    def _load_templates(self):
        self.templates = []
        try:
            conn = get_connection()
            rows = conn.execute(
                """SELECT id, name, category, language, code, note, is_starred, updated_at
                   FROM templates ORDER BY is_starred DESC, updated_at DESC"""
            ).fetchall()
            self.templates = [dict(r) for r in rows]
            conn.close()
        except Exception:
            self.templates = []

    def _save_template(self, name, category, language, code, note):
        try:
            conn = get_connection()
            if self._current_template_id:
                conn.execute(
                    """UPDATE templates SET name=?, category=?, language=?, code=?, note=?,
                       updated_at=datetime('now','localtime') WHERE id=?""",
                    (name, category, language, code, note, self._current_template_id))
            else:
                conn.execute(
                    """INSERT INTO templates (name, category, language, code, note)
                       VALUES (?, ?, ?, ?, ?)""",
                    (name, category, language, code, note))
            conn.commit()
            conn.close()
            self._load_templates()
            self._refresh_list()
            return True
        except Exception as e:
            self.app.set_status(f'保存失败: {e}')
            return False

    def _toggle_star(self, template_id):
        try:
            conn = get_connection()
            conn.execute(
                "UPDATE templates SET is_starred = 1 - is_starred WHERE id=?",
                (template_id,))
            conn.commit()
            conn.close()
            self._load_templates()
            self._refresh_list()
            self._load_detail()
        except Exception as e:
            self.app.set_status(f'操作失败: {e}')

    def _delete_template(self, template_id):
        if not messagebox.askyesno('确认删除', '确定要删除这个模板吗？'):
            return
        try:
            conn = get_connection()
            conn.execute("DELETE FROM templates WHERE id=?", (template_id,))
            conn.commit()
            conn.close()
            self._current_template_id = None
            self._load_templates()
            self._refresh_list()
            self._show_empty()
            self.app.set_status('模板已删除')
        except Exception as e:
            self.app.set_status(f'删除失败: {e}')

    # ============================================================
    # UI 构建
    # ============================================================

    def _build_ui(self):
        colors = self.config.get_colors()

        # 顶部工具栏
        toolbar = tk.Frame(self.parent, bg=colors['bg_sidebar'], height=44)
        toolbar.pack(fill=tk.X)
        toolbar.pack_propagate(False)

        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', lambda *a: self._refresh_list())
        tk.Entry(toolbar, textvariable=self.search_var, font=(self.config.get('font_family'), 11),
                 bg=colors['bg_input'], fg=colors['fg_primary'],
                 relief=tk.FLAT).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=12, pady=8)

        tk.Button(toolbar, text='+ 新建', font=(self.config.get('font_family'), 10),
                  bg=colors['fg_accent'], fg='#ffffff',
                  relief=tk.FLAT, padx=12, pady=4, cursor='hand2',
                  command=self._new_template).pack(side=tk.RIGHT, padx=8, pady=8)

        # 主体：左侧列表 + 右侧内容
        main = tk.Frame(self.parent, bg=colors['bg_main'])
        main.pack(fill=tk.BOTH, expand=True)

        # 左侧
        left = tk.Frame(main, width=280, bg=colors['bg_sidebar'])
        left.pack(side=tk.LEFT, fill=tk.Y)
        left.pack_propagate(False)

        tk.Label(left, text='模板库', font=(self.config.get('font_family'), 13, 'bold'),
                 bg=colors['bg_sidebar'], fg=colors['fg_primary']).pack(anchor=tk.W, padx=12, pady=(10, 4))

        # 分类 + 语言筛选
        self.cat_var = tk.StringVar(value='全部')
        ttk.Combobox(left, textvariable=self.cat_var, values=['全部'] + CATEGORIES,
                      state='readonly', width=18).pack(fill=tk.X, padx=8, pady=(0, 4))
        self.cat_var.trace_add('write', lambda *a: self._refresh_list())

        self.lang_var = tk.StringVar(value='全部')
        ttk.Combobox(left, textvariable=self.lang_var,
                      values=['全部', 'C++', 'Python', 'Java'],
                      state='readonly', width=18).pack(fill=tk.X, padx=8, pady=(0, 6))
        self.lang_var.trace_add('write', lambda *a: self._refresh_list())

        # 模板列表
        list_frame = tk.Frame(left, bg=colors['bg_sidebar'])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))

        self.template_listbox = tk.Listbox(
            list_frame, font=(self.config.get('font_family'), 10),
            bg=colors['bg_input'], fg=colors['fg_primary'],
            selectbackground=colors['fg_accent'], selectforeground='#ffffff',
            relief=tk.FLAT, activestyle='none',
        )
        self.template_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.template_listbox.bind('<<ListboxSelect>>', self._on_select)

        list_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL,
                                     command=self.template_listbox.yview)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.template_listbox.configure(yscrollcommand=list_scroll.set)

        # 右侧
        right = tk.Frame(main, bg=colors['bg_main'])
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.detail_md = MarkdownView(right)
        self.detail_md.pack(fill=tk.BOTH, expand=True, padx=12, pady=(8, 4))

        # 底部操作栏
        btn_bar = tk.Frame(right, bg=colors['bg_sidebar'], height=40)
        btn_bar.pack(fill=tk.X, side=tk.BOTTOM)
        btn_bar.pack_propagate(False)

        tk.Button(btn_bar, text='⭐ 收藏', font=(self.config.get('font_family'), 10),
                  bg=colors['bg_sidebar'], fg=colors['fg_primary'],
                  relief=tk.FLAT, padx=12, pady=4, cursor='hand2',
                  command=lambda: self._toggle_star(self._current_template_id)
                  ).pack(side=tk.LEFT, padx=12)

        tk.Button(btn_bar, text='删除', font=(self.config.get('font_family'), 10),
                  bg=colors['bg_sidebar'], fg='#A32D2D',
                  relief=tk.FLAT, padx=12, pady=4, cursor='hand2',
                  command=lambda: self._delete_template(self._current_template_id)
                  ).pack(side=tk.RIGHT, padx=12)

        tk.Button(btn_bar, text='编辑', font=(self.config.get('font_family'), 10),
                  bg=colors['fg_accent'], fg='#ffffff',
                  relief=tk.FLAT, padx=16, pady=4, cursor='hand2',
                  command=self._edit_current).pack(side=tk.RIGHT, padx=4)

    # ============================================================
    # 列表
    # ============================================================

    def _refresh_list(self):
        search = self.search_var.get().lower().strip()
        cat = self.cat_var.get()
        lang = self.lang_var.get()

        lang_map = {'C++': 'cpp', 'Python': 'python', 'Java': 'java'}
        lang_filter = lang_map.get(lang)

        self.template_listbox.delete(0, tk.END)
        self._list_ids = []

        for t in self.templates:
            if cat != '全部' and t['category'] != cat:
                continue
            if lang_filter and t['language'] != lang_filter:
                continue
            if search and search not in t['name'].lower() and search not in (t.get('note') or '').lower():
                continue

            star = '⭐ ' if t['is_starred'] else '   '
            lang_label = {'cpp': 'C++', 'python': 'Py', 'java': 'Java'}.get(t['language'], '')
            self.template_listbox.insert(tk.END, f'{star} {t["name"]}  [{lang_label}]')
            self._list_ids.append(t['id'])

    def _on_select(self, event):
        sel = self.template_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self._list_ids):
            return
        self._current_template_id = self._list_ids[idx]
        self._load_detail()

    def _load_detail(self):
        if not self._current_template_id:
            return
        # Find in loaded templates
        t = next((t for t in self.templates if t['id'] == self._current_template_id), None)
        if not t:
            return

        lang_map = {'cpp': 'cpp', 'python': 'python', 'java': 'java'}
        lang = lang_map.get(t['language'], 'cpp')

        md = f'# {t["name"]}\n\n'
        md += f'- **分类**: {t["category"]}  |  **语言**: {lang}\n'
        if t.get('note'):
            md += f'\n{t["note"]}\n'
        md += f'\n```{lang}\n{t["code"]}\n```\n'

        self.detail_md.render(md)

    def _show_empty(self):
        self._current_template_id = None
        self.detail_md.render('*选择一个模板查看详情，或点击「+ 新建」创建模板*')

    # ============================================================
    # 编辑
    # ============================================================

    def _new_template(self):
        self._open_editor(None)

    def _edit_current(self):
        if not self._current_template_id:
            return
        t = next((t for t in self.templates if t['id'] == self._current_template_id), None)
        if t:
            self._open_editor(t)

    def _open_editor(self, template_data):
        dialog = tk.Toplevel(self.parent)
        dialog.title('新建模板' if not template_data else f'编辑 — {template_data.get("name", "")}')
        dialog.geometry('700x600')
        dialog.transient(self.parent)
        colors = self.config.get_colors()
        dialog.configure(bg=colors['bg_main'])

        pad = {'padx': 16, 'pady': 2}

        # 名称
        tk.Label(dialog, text='模板名称', font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(anchor=tk.W, **pad)
        name_var = tk.StringVar(value=template_data.get('name', '') if template_data else '')
        tk.Entry(dialog, textvariable=name_var, font=(self.config.get('font_family'), 12, 'bold'),
                 bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT).pack(fill=tk.X, **pad)

        # 分类 + 语言
        row = tk.Frame(dialog, bg=colors['bg_main'])
        row.pack(fill=tk.X, **pad)
        tk.Label(row, text='分类:', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(side=tk.LEFT)
        cat_var = tk.StringVar(value=template_data.get('category', '数据结构') if template_data else '数据结构')
        ttk.Combobox(row, textvariable=cat_var, values=CATEGORIES, state='readonly', width=12).pack(side=tk.LEFT, padx=(4, 20))

        tk.Label(row, text='语言:', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(side=tk.LEFT)
        lang_var = tk.StringVar(value=template_data.get('language', 'cpp') if template_data else 'cpp')
        ttk.Combobox(row, textvariable=lang_var, values=LANGUAGES, state='readonly', width=8).pack(side=tk.LEFT, padx=4)

        # 备注
        tk.Label(dialog, text='备注（Markdown）', font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(anchor=tk.W, padx=16, pady=(12, 2))
        note_text = tk.Text(dialog, height=3, font=(self.config.get('font_family'), 10),
                             bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT, wrap=tk.WORD)
        note_text.pack(fill=tk.X, **pad)
        if template_data and template_data.get('note'):
            note_text.insert('1.0', template_data['note'])

        # 代码
        tk.Label(dialog, text='代码', font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(anchor=tk.W, padx=16, pady=(12, 2))
        code_text = tk.Text(dialog, font=(self.config.get('code_font_family'), 11),
                             bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT, wrap=tk.NONE)
        code_text.pack(fill=tk.BOTH, expand=True, **pad)
        if template_data and template_data.get('code'):
            code_text.insert('1.0', template_data['code'])

        # 按钮
        btn_row = tk.Frame(dialog, bg=colors['bg_main'])
        btn_row.pack(fill=tk.X, padx=16, pady=(8, 12))
        tk.Button(btn_row, text='取消', font=(self.config.get('font_family'), 11),
                  bg=colors['bg_sidebar'], fg=colors['fg_primary'],
                  relief=tk.FLAT, padx=16, pady=6, command=dialog.destroy).pack(side=tk.RIGHT, padx=(8, 0))
        tk.Button(btn_row, text='保存', font=(self.config.get('font_family'), 11),
                  bg=colors['fg_accent'], fg='#ffffff',
                  relief=tk.FLAT, padx=20, pady=6,
                  command=lambda: self._do_save(
                      name_var.get().strip(), cat_var.get(), lang_var.get(),
                      code_text.get('1.0', tk.END).strip(),
                      note_text.get('1.0', tk.END).strip(), dialog)
                  ).pack(side=tk.RIGHT)

    def _do_save(self, name, cat, lang, code, note, dialog):
        if not name:
            messagebox.showwarning('提示', '请输入名称')
            return
        if not code:
            messagebox.showwarning('提示', '请输入代码')
            return
        if self._save_template(name, cat, lang, code, note):
            dialog.destroy()
            self._current_template_id = self.templates[0]['id'] if self.templates else None
            self._refresh_list()
            self._load_detail()
            self.app.set_status(f'模板「{name}」已保存')

    def on_new(self):
        self._new_template()

    def on_search(self):
        # 聚焦搜索框
        pass

    def apply_theme(self):
        self._load_templates()
        for w in self.parent.winfo_children():
            w.destroy()
        self._build_ui()
        self._refresh_list()
