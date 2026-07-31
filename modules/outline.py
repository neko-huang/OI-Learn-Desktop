"""
算法大纲模块
左侧树形导航（22大类→主题→知识点）+ 右侧详情
- 掌握度标记 + Markdown 说明
- 自定义条目添加/修改/删除
- 关联百科 + 搜索文章
"""

import json
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox

from config import Config
from db.seed import get_categories, get_all_topic_ids
from db.database import get_connection
from components.markdown_view import MarkdownView

MASTERY_MAP = {
    'none':      ('未学',   '#888', '#e0e0e0'),
    'learning':  ('学习中', '#BA7517', '#FAEEDA'),
    'familiar':  ('熟悉',   '#185FA5', '#E6F1FB'),
    'mastered':  ('已掌握', '#3B6D11', '#EAF3DE'),
}

LEVEL_MAP = {'entry': '入门', 'improve': '提高', 'noi': 'NOI'}
REV_LEVEL_MAP = {'入门': 'entry', '提高': 'improve', 'NOI': 'noi'}


class OutlineModule:

    def __init__(self, app, parent_frame):
        self.app = app
        self.config = Config()
        self.parent = parent_frame
        for w in parent_frame.winfo_children():
            w.destroy()

        self._combined_topics = {}  # 合并内置+自定义条目
        self._load_data()
        self._build_ui()

    # ============================================================
    # 数据加载
    # ============================================================

    def _load_data(self):
        """加载内置条目 + 自定义条目"""
        self.categories = get_categories()
        self.all_topics = get_all_topic_ids()
        self._topic_map = {t['topic_id']: t for t in self.all_topics}

        self._custom_topics = {}  # topic_id -> {id,parent_id,name,desc,difficulty,level,category_name}
        try:
            conn = get_connection()
            rows = conn.execute("SELECT * FROM custom_topics").fetchall()
            conn.close()
            for row in rows:
                row = dict(row)
                self._custom_topics[row['topic_id']] = row
                self._topic_map[row['topic_id']] = {
                    'topic_id': row['topic_id'],
                    'name': row['name'],
                    'desc': row.get('desc', ''),
                    'difficulty': row.get('difficulty', 1),
                    'level': row.get('level', 'entry'),
                    'category_name': row.get('category_name', '自定义'),
                }
        except Exception:
            self._custom_topics = {}

        self._load_progress()

    # ============================================================
    # UI
    # ============================================================

    def _build_ui(self):
        colors = self.config.get_colors()

        left_frame = tk.Frame(self.parent, width=320, bg=colors['bg_sidebar'])
        left_frame.pack(side=tk.LEFT, fill=tk.Y)
        left_frame.pack_propagate(False)

        tk.Label(left_frame, text='算法大纲', font=(self.config.get('font_family'), 13, 'bold'),
                 bg=colors['bg_sidebar'], fg=colors['fg_primary']).pack(fill=tk.X, padx=12, pady=(10, 6))

        tree_frame = tk.Frame(left_frame, bg=colors['bg_sidebar'])
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))

        self.tree = ttk.Treeview(tree_frame, show='tree', selectmode='browse')
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.bind('<<TreeviewSelect>>', self._on_select)
        self.tree.bind('<Button-3>', self._on_right_click)  # 右键菜单
        self._populate_tree()

        # 右侧
        right_frame = tk.Frame(self.parent, bg=colors['bg_main'])
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 空状态
        self.empty_frame = tk.Frame(right_frame, bg=colors['bg_main'])
        tk.Label(self.empty_frame, text='选择左侧知识点查看详情',
                 font=(self.config.get('font_family'), 14),
                 bg=colors['bg_main'], fg=colors['fg_muted']).place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # 内容区（初始隐藏）
        self.detail_frame = tk.Frame(right_frame, bg=colors['bg_main'])

        self.detail_title = tk.Label(self.detail_frame, text='',
                                      font=(self.config.get('font_family'), 18, 'bold'),
                                      bg=colors['bg_main'], fg=colors['fg_primary'], anchor=tk.W)
        self.detail_title.pack(fill=tk.X, padx=16, pady=(12, 4))

        meta_frame = tk.Frame(self.detail_frame, bg=colors['bg_main'])
        meta_frame.pack(fill=tk.X, padx=16, pady=(0, 8))

        self.meta_difficulty = tk.Label(meta_frame, text='', font=(self.config.get('font_family'), 10),
                                         bg=colors['bg_main'], fg=colors['fg_secondary'])
        self.meta_difficulty.pack(side=tk.LEFT, padx=(0, 16))
        self.meta_level = tk.Label(meta_frame, text='', font=(self.config.get('font_family'), 10),
                                    bg=colors['bg_main'], fg=colors['fg_secondary'])
        self.meta_level.pack(side=tk.LEFT, padx=(0, 16))

        self.mastery_var = tk.StringVar(value='none')
        self.mastery_combo = ttk.Combobox(meta_frame, textvariable=self.mastery_var,
                                           values=['none', 'learning', 'familiar', 'mastered'],
                                           state='readonly', width=10)
        self.mastery_combo.pack(side=tk.LEFT, padx=(0, 8))
        self.mastery_combo.bind('<<ComboboxSelected>>', self._on_mastery_changed)

        self.mastery_label = tk.Label(meta_frame, text='', font=(self.config.get('font_family'), 10),
                                       bg=colors['bg_main'])
        self.mastery_label.pack(side=tk.LEFT)

        # 操作按钮行
        btn_row = tk.Frame(self.detail_frame, bg=colors['bg_main'])
        btn_row.pack(fill=tk.X, padx=16, pady=(0, 4))
        tk.Button(btn_row, text='关联百科', font=(self.config.get('font_family'), 9),
                  bg=colors['bg_sidebar'], fg=colors['fg_accent'], relief=tk.FLAT,
                  cursor='hand2', command=self._link_encyclopedia).pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(btn_row, text='搜索文章', font=(self.config.get('font_family'), 9),
                  bg=colors['bg_sidebar'], fg=colors['fg_accent'], relief=tk.FLAT,
                  cursor='hand2', command=self._search_articles).pack(side=tk.LEFT)

        self.markdown_view = MarkdownView(self.detail_frame)
        self.markdown_view.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))

        self._show_detail(False)

    def _show_detail(self, show: bool):
        self.empty_frame.pack_forget()
        self.detail_frame.pack_forget()
        if show:
            self.detail_frame.pack(fill=tk.BOTH, expand=True)
        else:
            self.empty_frame.pack(fill=tk.BOTH, expand=True)

    # ============================================================
    # 树
    # ============================================================

    def _populate_tree(self):
        self.tree.delete(*self.tree.get_children())

        for cat in self.categories:
            cat_node = self.tree.insert('', tk.END, text=cat['name'],
                                         tags=('category',), iid=cat['id'], open=False)
            # 插入内置主题
            for topic in cat['topics']:
                topic_node = self.tree.insert(cat_node, tk.END, text=topic['name'],
                                               tags=('topic',), iid=topic['id'], open=False)
                for sub in topic['subtopics']:
                    sub_id = sub[0]
                    status = self._progress.get(sub_id, 'none')
                    symbol = self._mastery_symbol(status)
                    self.tree.insert(topic_node, tk.END, text=f'{symbol} {sub[1]}',
                                      tags=('subtopic',), iid=sub_id)

            # 插入自定义条目（属于该分类）
            for tid, ct in self._custom_topics.items():
                if ct.get('category_name') == cat['name'] and ct.get('parent_id', '') == cat['id']:
                    status = self._progress.get(tid, 'none')
                    symbol = self._mastery_symbol(status)
                    self.tree.insert(cat_node, tk.END, text=f'{symbol} ✎ {ct["name"]}',
                                      tags=('custom',), iid=tid)

        self.tree.tag_configure('category', font=(self.config.get('font_family'), 12, 'bold'))
        self.tree.tag_configure('topic', font=(self.config.get('font_family'), 11))
        self.tree.tag_configure('subtopic', font=(self.config.get('font_family'), 10))
        self.tree.tag_configure('custom', font=(self.config.get('font_family'), 10), foreground='#534AB7')

    # ============================================================
    # 进度
    # ============================================================

    def _load_progress(self):
        self._progress = {}
        try:
            conn = get_connection()
            rows = conn.execute("SELECT topic_id, mastery FROM outline_progress").fetchall()
            for row in rows:
                self._progress[row['topic_id']] = row['mastery']
            conn.close()
        except Exception:
            pass

    def _save_progress(self, topic_id: str, mastery: str):
        self._progress[topic_id] = mastery
        try:
            conn = get_connection()
            conn.execute(
                """INSERT INTO outline_progress (topic_id, mastery) VALUES (?, ?)
                   ON CONFLICT(topic_id) DO UPDATE SET mastery=excluded.mastery,
                   updated_at=datetime('now','localtime')""",
                (topic_id, mastery))
            conn.commit()
            conn.close()
        except Exception as e:
            self.app.set_status(f'保存失败: {e}')

    def _mastery_symbol(self, status: str) -> str:
        return {'none': '○', 'learning': '◐', 'familiar': '◉', 'mastered': '●'}.get(status, '○')

    # ============================================================
    # 事件
    # ============================================================

    def _on_select(self, event):
        selection = self.tree.selection()
        if not selection:
            self._show_detail(False)
            return
        item_id = selection[0]
        topic_info = self._topic_map.get(item_id)
        if not topic_info:
            self._show_detail(False)
            return

        self._show_detail(True)

        name = topic_info['name']
        cat = topic_info.get('category_name', '')
        self.detail_title.config(text=f'{cat} › {name}' if cat else name)

        diff = topic_info.get('difficulty', 1)
        level_key = topic_info.get('level', 'entry')
        level = LEVEL_MAP.get(level_key, level_key)
        self.meta_difficulty.config(text=f'难度: {"★" * diff}')
        self.meta_level.config(text=f'等级: {level}')

        current = self._progress.get(item_id, 'none')
        self.mastery_var.set(current)
        status_name, fg, bg = MASTERY_MAP[current]
        self.mastery_label.config(text=status_name, fg=fg, bg=bg)

        self._current_item_id = item_id

        # Markdown
        desc = topic_info.get('desc', '暂无详细说明')
        md = f'## {name}\n\n{desc}\n\n'
        md += f'- **难度**: {"★" * diff} ({level})\n'
        md += f'- **分类**: {cat}\n'
        md += f'- **掌握度**: {status_name}\n'
        self.markdown_view.render(md)

    # ============================================================
    # 右键菜单
    # ============================================================

    def _on_right_click(self, event):
        """右键菜单：添加子知识点 / 编辑 / 删除"""
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return
        self.tree.selection_set(item_id)

        menu = tk.Menu(self.parent, tearoff=0)
        menu.add_command(label='添加子知识点', command=lambda: self._add_custom_item(item_id))

        if item_id in self._custom_topics:
            menu.add_command(label='编辑', command=lambda: self._edit_custom_item(item_id))
            menu.add_separator()
            menu.add_command(label='删除', command=lambda: self._delete_custom_item(item_id))

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _add_custom_item(self, parent_id):
        """添加自定义子知识点"""
        dialog = tk.Toplevel(self.parent)
        dialog.title('添加知识点')
        dialog.geometry('450x350')
        dialog.transient(self.parent)
        colors = self.config.get_colors()
        dialog.configure(bg=colors['bg_main'])

        tk.Label(dialog, text='添加自定义知识点', font=(self.config.get('font_family'), 13, 'bold'),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(pady=(12, 8))

        tk.Label(dialog, text='名称', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.W).pack(fill=tk.X, padx=20)
        name_var = tk.StringVar()
        tk.Entry(dialog, textvariable=name_var, font=(self.config.get('font_family'), 11),
                 bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT
                 ).pack(fill=tk.X, padx=20, pady=(2, 8), ipady=3)

        # 难度 + 等级
        row = tk.Frame(dialog, bg=colors['bg_main'])
        row.pack(fill=tk.X, padx=20, pady=(0, 8))
        tk.Label(row, text='难度 (1-8星):', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(side=tk.LEFT)
        diff_var = tk.StringVar(value='1')
        ttk.Combobox(row, textvariable=diff_var, values=[str(i) for i in range(1, 9)],
                      state='readonly', width=4).pack(side=tk.LEFT, padx=4)
        tk.Label(row, text='等级:', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(side=tk.LEFT, padx=(12, 4))
        lvl_var = tk.StringVar(value='入门')
        ttk.Combobox(row, textvariable=lvl_var, values=['入门', '提高', 'NOI'],
                      state='readonly', width=6).pack(side=tk.LEFT, padx=4)

        tk.Label(dialog, text='描述（Markdown）', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.W).pack(fill=tk.X, padx=20)
        desc_text = tk.Text(dialog, font=(self.config.get('font_family'), 10),
                            bg=colors['bg_input'], fg=colors['fg_primary'],
                            relief=tk.FLAT, wrap=tk.WORD, height=5)
        desc_text.pack(fill=tk.X, padx=20, pady=(2, 8))

        def _save():
            name = name_var.get().strip()
            if not name:
                return
            try:
                diff = int(diff_var.get())
                level = REV_LEVEL_MAP.get(lvl_var.get(), 'entry')
                topic_id = f'custom_{name}_{len(self._custom_topics)}'
                desc = desc_text.get('1.0', tk.END).strip()

                # 获取父节点的分类名
                cat_name = '自定义'
                if parent_id in self._topic_map:
                    cat_name = self._topic_map[parent_id].get('category_name', '自定义')

                conn = get_connection()
                conn.execute(
                    "INSERT INTO custom_topics (topic_id, parent_id, name, desc, difficulty, level, category_name) VALUES (?,?,?,?,?,?,?)",
                    (topic_id, parent_id, name, desc, diff, level, cat_name))
                conn.commit()
                conn.close()

                dialog.destroy()
                self._load_data()
                self._populate_tree()
                self.app.set_status(f'「{name}」已添加')
            except Exception as e:
                self.app.set_status(f'添加失败: {e}')

        tk.Button(dialog, text='保存', font=(self.config.get('font_family'), 11, 'bold'),
                  bg=colors['fg_accent'], fg='#ffffff', padx=20, pady=6, command=_save).pack(pady=8)

    def _edit_custom_item(self, topic_id):
        ct = self._custom_topics.get(topic_id)
        if not ct:
            return
        dialog = tk.Toplevel(self.parent)
        dialog.title('编辑知识点')
        dialog.geometry('450x350')
        dialog.transient(self.parent)
        colors = self.config.get_colors()
        dialog.configure(bg=colors['bg_main'])

        tk.Label(dialog, text=f'编辑: {ct["name"]}', font=(self.config.get('font_family'), 13, 'bold'),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(pady=(12, 8))

        tk.Label(dialog, text='名称', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.W).pack(fill=tk.X, padx=20)
        name_var = tk.StringVar(value=ct['name'])
        tk.Entry(dialog, textvariable=name_var, font=(self.config.get('font_family'), 11),
                 bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT
                 ).pack(fill=tk.X, padx=20, pady=(2, 8), ipady=3)

        row = tk.Frame(dialog, bg=colors['bg_main'])
        row.pack(fill=tk.X, padx=20, pady=(0, 8))
        tk.Label(row, text='难度 (1-8):', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(side=tk.LEFT)
        diff_var = tk.StringVar(value=str(ct.get('difficulty', 1)))
        ttk.Combobox(row, textvariable=diff_var, values=[str(i) for i in range(1, 9)],
                      state='readonly', width=4).pack(side=tk.LEFT, padx=4)
        tk.Label(row, text='等级:', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(side=tk.LEFT, padx=(12, 4))
        lvl_var = tk.StringVar(value=LEVEL_MAP.get(ct.get('level', 'entry'), '入门'))
        ttk.Combobox(row, textvariable=lvl_var, values=['入门', '提高', 'NOI'],
                      state='readonly', width=6).pack(side=tk.LEFT, padx=4)

        tk.Label(dialog, text='描述（Markdown）', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.W).pack(fill=tk.X, padx=20)
        desc_text = tk.Text(dialog, font=(self.config.get('font_family'), 10),
                            bg=colors['bg_input'], fg=colors['fg_primary'],
                            relief=tk.FLAT, wrap=tk.WORD, height=5)
        desc_text.insert('1.0', ct.get('desc', ''))
        desc_text.pack(fill=tk.X, padx=20, pady=(2, 8))

        def _save():
            name = name_var.get().strip()
            if not name:
                return
            try:
                conn = get_connection()
                conn.execute(
                    "UPDATE custom_topics SET name=?, desc=?, difficulty=?, level=? WHERE topic_id=?",
                    (name, desc_text.get('1.0', tk.END).strip(),
                     int(diff_var.get()), REV_LEVEL_MAP.get(lvl_var.get(), 'entry'), topic_id))
                conn.commit()
                conn.close()
                dialog.destroy()
                self._load_data()
                self._populate_tree()
                self.app.set_status(f'「{name}」已更新')
            except Exception as e:
                self.app.set_status(f'编辑失败: {e}')

        tk.Button(dialog, text='保存', font=(self.config.get('font_family'), 11, 'bold'),
                  bg=colors['fg_accent'], fg='#ffffff', padx=20, pady=6, command=_save).pack(pady=8)

    def _delete_custom_item(self, topic_id):
        ct = self._custom_topics.get(topic_id)
        if not ct:
            return
        if not messagebox.askyesno('确认删除', f'确定删除「{ct["name"]}」吗？'):
            return
        try:
            conn = get_connection()
            conn.execute("DELETE FROM custom_topics WHERE topic_id=?", (topic_id,))
            conn.commit()
            conn.close()
            self._load_data()
            self._populate_tree()
            self._show_detail(False)
            self.app.set_status('已删除')
        except Exception as e:
            self.app.set_status(f'删除失败: {e}')

    # ============================================================
    # 关联百科 + 搜索文章
    # ============================================================

    def _link_encyclopedia(self):
        if not hasattr(self, '_current_item_id'):
            return
        try:
            conn = get_connection()
            rows = conn.execute("SELECT id, title FROM encyclopedia ORDER BY title").fetchall()
            conn.close()
        except Exception:
            rows = []

        if not rows:
            self.app.set_status('百科中暂无条目')
            return

        dialog = tk.Toplevel(self.parent)
        dialog.title('关联百科条目')
        dialog.geometry('400x350')
        dialog.transient(self.parent)
        colors = self.config.get_colors()
        dialog.configure(bg=colors['bg_main'])

        tk.Label(dialog, text='选择要关联的百科条目', font=(self.config.get('font_family'), 12, 'bold'),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(pady=(10, 6))

        search_var = tk.StringVar()
        tk.Entry(dialog, textvariable=search_var, font=(self.config.get('font_family'), 11),
                 bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT
                 ).pack(fill=tk.X, padx=16, pady=(0, 6))

        listbox = tk.Listbox(dialog, font=(self.config.get('font_family'), 10),
                             bg=colors['bg_input'], fg=colors['fg_primary'],
                             selectbackground=colors['fg_accent'])
        listbox.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 8))
        ids = []

        def _refresh():
            listbox.delete(0, tk.END)
            ids.clear()
            s = search_var.get().lower().strip()
            for r in rows:
                if s and s not in r['title'].lower():
                    continue
                listbox.insert(tk.END, r['title'])
                ids.append(r['id'])

        search_var.trace_add('write', lambda *a: _refresh())
        _refresh()

        def _link():
            sel = listbox.curselection()
            if not sel:
                return
            eid = ids[sel[0]]
            try:
                conn = get_connection()
                conn.execute("UPDATE encyclopedia SET topic_id=? WHERE id=?",
                              (self._current_item_id, eid))
                conn.commit()
                conn.close()
                dialog.destroy()
                self.app.set_status('已关联')
            except Exception as e:
                self.app.set_status(f'关联失败: {e}')

        tk.Button(dialog, text='关联选中条目', font=(self.config.get('font_family'), 11, 'bold'),
                  bg=colors['fg_accent'], fg='#ffffff', padx=16, pady=6,
                  command=_link).pack()

    def _search_articles(self):
        if not hasattr(self, '_current_item_id'):
            return
        info = self._topic_map.get(self._current_item_id)
        if not info:
            return
        name = info['name']
        # 打开浏览器搜索
        import urllib.parse
        query = urllib.parse.quote(f'{name} 算法')
        webbrowser.open(f'https://www.baidu.com/s?wd={query}')
        self.app.set_status(f'已在浏览器搜索「{name} 算法」')

    # ============================================================
    # 掌握度
    # ============================================================

    def _on_mastery_changed(self, event):
        selection = self.tree.selection()
        if not selection:
            return
        item_id = selection[0]
        if item_id not in self._topic_map:
            return

        new_mastery = self.mastery_var.get()
        self._save_progress(item_id, new_mastery)

        symbol = self._mastery_symbol(new_mastery)
        name = self._topic_map[item_id]['name']
        self.tree.item(item_id, text=f'{symbol} {name}')

        status_name, fg, bg = MASTERY_MAP[new_mastery]
        self.mastery_label.config(text=status_name, fg=fg, bg=bg)
        self.app.set_status(f'「{name}」→ {status_name}')

    def on_export(self):
        from services.exporter import export_outline_progress_to_json
        path = export_outline_progress_to_json()
        if path:
            self.app.set_status(f'已导出: {path}')
        else:
            self.app.set_status('暂无进度数据可导出')

    def apply_theme(self):
        expanded = [item for item in self.tree.get_children('') if self.tree.item(item, 'open')]
        for w in self.parent.winfo_children():
            w.destroy()
        self._build_ui()
        for item in expanded:
            try:
                self.tree.item(item, open=True)
            except tk.TclError:
                pass
