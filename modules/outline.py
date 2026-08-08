"""
算法大纲模块
左侧树形导航（22大类→主题→知识点）+ 右侧详情
- 掌握度标记 + Markdown 说明
- 自定义条目添加/修改/删除
- 关联百科 + 搜索文章
"""

import json
import time
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox

from config import Config
from db.seed import get_categories_from_db, get_all_subtopic_tags_from_db
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

# 等级显示配置：颜色、背景色、徽标
LEVEL_DISPLAY = {
    'entry':   {'text': '入门', 'color': '#2E7D32', 'bg': '#E8F5E9', 'badge': '🌱'},
    'improve': {'text': '提高', 'color': '#E65100', 'bg': '#FFF3E0', 'badge': '🔥'},
    'noi':     {'text': 'NOI',  'color': '#C62828', 'bg': '#FFEBEE', 'badge': '⚡'},
}


class OutlineModule:

    def __init__(self, app, parent_frame):
        self.app = app
        self.config = Config()
        self.parent = parent_frame
        for w in parent_frame.winfo_children():
            w.destroy()

        self._combined_topics = {}  # 合并内置+自定义条目
        self._current_item_id = None
        self._load_data()
        self._build_ui()

    # ============================================================
    # 数据加载
    # ============================================================

    def _load_data(self):
        """加载内置条目（从数据库）+ 自定义条目"""
        self.categories = get_categories_from_db()
        self.all_topics = get_all_subtopic_tags_from_db()
        self._topic_map = {t['id']: t for t in self.all_topics}

        # 补全 topic_map 的层级信息（从 categories 结构补充）
        for cat in self.categories:
            for topic in cat['topics']:
                for sub in topic['subtopics']:
                    sub_id = sub[0]
                    if sub_id in self._topic_map:
                        self._topic_map[sub_id].update({
                            'category_id': cat['id'],
                            'category_name': cat['name'],
                            'topic_id_parent': topic['id'],
                            'topic_name': topic['name'],
                            'difficulty': sub[3],
                            'level': sub[4],
                            'desc': sub[2],
                        })

        self._custom_topics = {}
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
                    'desc': row.get('description', '') or row.get('desc', ''),
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
                 bg=colors['bg_sidebar'], fg=colors['fg_primary']).pack(fill=tk.X, padx=12, pady=(10, 2))

        # 编辑模式工具栏
        self._edit_mode = False
        edit_toolbar = tk.Frame(left_frame, bg=colors['bg_sidebar'])
        edit_toolbar.pack(fill=tk.X, padx=8, pady=(0, 2))
        self.edit_toggle_btn = tk.Label(edit_toolbar, text='✏️ 编辑',
                                        font=(self.config.get('font_family'), 9),
                                        bg=colors['bg_sidebar'], fg=colors['fg_accent'],
                                        cursor='hand2', padx=6, pady=2)
        self.edit_toggle_btn.pack(side=tk.LEFT, padx=2)
        self.edit_toggle_btn.bind('<Button-1>', lambda e: self._toggle_edit_mode())
        self.edit_add_cat_btn = tk.Label(edit_toolbar, text='+ 大类',
                                         font=(self.config.get('font_family'), 9),
                                         bg=colors['bg_sidebar'], fg=colors['fg_muted'],
                                         cursor='hand2', padx=6, pady=2)
        self.edit_add_cat_btn.pack(side=tk.LEFT, padx=2)
        self.edit_add_cat_btn.bind('<Button-1>', lambda e: self._add_category())
        self.edit_reset_btn = tk.Label(edit_toolbar, text='↺ 重置',
                                       font=(self.config.get('font_family'), 9),
                                       bg=colors['bg_sidebar'], fg=colors['fg_muted'],
                                       cursor='hand2', padx=6, pady=2)
        self.edit_reset_btn.pack(side=tk.LEFT, padx=2)
        self.edit_reset_btn.bind('<Button-1>', lambda e: self._reset_to_factory())
        self._update_edit_toolbar()

        # 等级筛选栏
        self._level_filter = 'all'
        filter_frame = tk.Frame(left_frame, bg=colors['bg_sidebar'])
        filter_frame.pack(fill=tk.X, padx=8, pady=(0, 4))
        filters = [('all', '全部'), ('entry', '🌱入门'), ('improve', '🔥提高'), ('noi', '⚡NOI')]
        self._filter_buttons = {}
        for fkey, ftext in filters:
            btn = tk.Label(filter_frame, text=ftext,
                           font=(self.config.get('font_family'), 9),
                           bg=colors['bg_sidebar'], fg=colors['fg_secondary'],
                           cursor='hand2', padx=6, pady=2)
            btn.pack(side=tk.LEFT, padx=2)
            btn.bind('<Button-1>', lambda e, k=fkey: self._set_level_filter(k))
            self._filter_buttons[fkey] = btn
        self._update_filter_highlight()

        tree_frame = tk.Frame(left_frame, bg=colors['bg_sidebar'])
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))

        self.tree = ttk.Treeview(tree_frame, show='tree', selectmode='browse')
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # 一次性配置 tag 样式（避免每次 _populate_tree 重复配置）
        for lvl_key, lvl_info in LEVEL_DISPLAY.items():
            self.tree.tag_configure(f'level_{lvl_key}', foreground=lvl_info['color'])
        self.tree.tag_configure('category', font=(self.config.get('font_family'), 12, 'bold'))
        self.tree.tag_configure('topic', font=(self.config.get('font_family'), 11))
        self.tree.tag_configure('subtopic', font=(self.config.get('font_family'), 10))
        self.tree.tag_configure('custom', font=(self.config.get('font_family'), 10), foreground='#534AB7')

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

    def _set_level_filter(self, level_key: str):
        """设置等级筛选并刷新树"""
        self._level_filter = level_key
        self._update_filter_highlight()
        self._populate_tree()

    def _update_filter_highlight(self):
        """高亮当前选中的筛选按钮"""
        colors = self.config.get_colors()
        for fkey, btn in self._filter_buttons.items():
            if fkey == self._level_filter:
                btn.config(bg=colors['fg_accent'], fg='#ffffff')
            else:
                btn.config(bg=colors['bg_sidebar'], fg=colors['fg_secondary'])

    def _level_badge(self, level_key: str) -> str:
        """返回带徽标的等级文本，如 '🌱入门'"""
        info = LEVEL_DISPLAY.get(level_key, LEVEL_DISPLAY['entry'])
        return f'{info["badge"]}{info["text"]}'

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

    def _delete_all_tree_items(self):
        """删除所有树节点"""
        self.tree.delete(*self.tree.get_children(''))

    def _populate_tree(self):
        # 记录当前展开的节点，重建后恢复（避免编辑后树全部收起）
        _expanded = set()
        try:
            for item in self.tree.get_children(''):
                if self.tree.item(item, 'open'):
                    _expanded.add(item)
                # 也记录子节点的展开状态
                for child in self.tree.get_children(item):
                    if self.tree.item(child, 'open'):
                        _expanded.add(child)
        except Exception:
            pass

        self._delete_all_tree_items()

        for cat in self.categories:
            cat_node = self.tree.insert('', tk.END, text=cat['name'],
                                         tags=('category',), iid=cat['id'], open=False)
            has_visible = False  # 该分类下是否有可见子节点
            # 插入内置主题
            for topic in cat['topics']:
                topic_node = self.tree.insert(cat_node, tk.END, text=topic['name'],
                                               tags=('topic',), iid=topic['id'], open=False)
                topic_visible = False
                for sub in topic['subtopics']:
                    sub_id = sub[0]
                    sub_level = sub[4]  # level key: entry/improve/noi
                    # 筛选
                    if self._level_filter != 'all' and sub_level != self._level_filter:
                        continue
                    topic_visible = True
                    status = self._progress.get(sub_id, 'none')
                    symbol = self._mastery_symbol(status)
                    badge = self._level_badge(sub_level)
                    self.tree.insert(topic_node, tk.END,
                                      text=f'{symbol} {sub[1]}  [{badge}]',
                                      tags=('subtopic', f'level_{sub_level}'),
                                      iid=sub_id)
                if not topic_visible:
                    self.tree.delete(topic_node)
                else:
                    has_visible = True

            # 插入自定义条目（属于该分类）
            for tid, ct in self._custom_topics.items():
                if ct.get('category_name') == cat['name'] and ct.get('parent_id', '') == cat['id']:
                    ct_level = ct.get('level', 'entry')
                    if self._level_filter != 'all' and ct_level != self._level_filter:
                        continue
                    has_visible = True
                    status = self._progress.get(tid, 'none')
                    symbol = self._mastery_symbol(status)
                    badge = self._level_badge(ct_level)
                    self.tree.insert(cat_node, tk.END,
                                      text=f'{symbol} ✎ {ct["name"]}  [{badge}]',
                                      tags=('custom', f'level_{ct_level}'),
                                      iid=tid)

            if not has_visible:
                self.tree.delete(cat_node)

        # 恢复之前展开的节点
        for item in _expanded:
            try:
                self.tree.item(item, open=True)
            except tk.TclError:
                pass

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
        badge = self._level_badge(level_key)
        self.meta_difficulty.config(text=f'难度: {"★" * diff}')
        self.meta_level.config(text=f'等级: {badge}')

        current = self._progress.get(item_id, 'none')
        self.mastery_var.set(current)
        status_name, fg, bg = MASTERY_MAP[current]
        self.mastery_label.config(text=status_name, fg=fg, bg=bg)

        self._current_item_id = item_id

        # Markdown
        desc = topic_info.get('desc', '暂无详细说明')
        md = f'## {name}\n\n{desc}\n\n'
        md += f'- **难度**: {"★" * diff} ({level})\n'
        md += f'- **等级**: {badge}\n'
        md += f'- **分类**: {cat}\n'
        md += f'- **掌握度**: {status_name}\n'
        self.markdown_view.render(md)

    # ============================================================
    # 右键菜单
    # ============================================================

    def _on_right_click(self, event):
        """右键菜单"""
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return
        self.tree.selection_set(item_id)

        # 判断 item 类型（大类 / 主题 / 子知识点）
        is_cat = any(cat['id'] == item_id for cat in self.categories)
        is_topic = any(
            topic['id'] == item_id
            for cat in self.categories for topic in cat['topics']
        )

        menu = tk.Menu(self.parent, tearoff=0)

        if self._edit_mode:
            if is_cat:
                menu.add_command(label='✏️ 编辑大类', command=lambda: self._edit_category(item_id))
                menu.add_command(label='+ 添加主题', command=lambda: self._add_topic(item_id))
                menu.add_command(label='🗑️ 删除大类', command=lambda: self._delete_category(item_id))
            elif is_topic:
                # 找到所属大类
                parent_cat_id = None
                for cat in self.categories:
                    for topic in cat['topics']:
                        if topic['id'] == item_id:
                            parent_cat_id = cat['id']
                            break
                menu.add_command(label='✏️ 编辑主题', command=lambda: self._edit_topic(item_id))
                menu.add_command(label='+ 添加子知识点', command=lambda: self._add_subtopic(item_id))
                menu.add_command(label='↑ 上移', command=lambda: self._move_topic(item_id, -1))
                menu.add_command(label='↓ 下移', command=lambda: self._move_topic(item_id, 1))
                menu.add_command(label='🗑️ 删除主题', command=lambda: self._delete_topic(item_id))
            else:
                # 子知识点
                menu.add_command(label='✏️ 编辑', command=lambda: self._edit_subtopic(item_id))
                menu.add_command(label='↑ 上移', command=lambda: self._move_subtopic(item_id, -1))
                menu.add_command(label='↓ 下移', command=lambda: self._move_subtopic(item_id, 1))
                menu.add_command(label='🗑️ 删除', command=lambda: self._delete_subtopic(item_id))
        else:
            # 查看模式：只保留原有添加子知识点（任何层级都可添加）
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
        dialog.lift()
        dialog.focus_force()
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
                messagebox.showwarning('提示', '名称不能为空')
                return
            try:
                diff = int(diff_var.get())
                level = REV_LEVEL_MAP.get(lvl_var.get(), 'entry')
                topic_id = f'custom_{int(time.time_ns())}'
                desc = desc_text.get('1.0', tk.END).strip()

                # 获取父节点的分类名
                cat_name = '自定义'
                if parent_id in self._topic_map:
                    cat_name = self._topic_map[parent_id].get('category_name', '自定义')
                else:
                    # 遍历分类查找父节点名称
                    for cat in self.categories:
                        if cat['id'] == parent_id:
                            cat_name = cat['name']
                            break
                        for topic in cat['topics']:
                            if topic['id'] == parent_id:
                                cat_name = cat['name']
                                break

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
        dialog.lift()
        dialog.focus_force()
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
                messagebox.showwarning('提示', '名称不能为空')
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
    # 编辑模式
    # ============================================================

    def _toggle_edit_mode(self):
        self._edit_mode = not self._edit_mode
        self._update_edit_toolbar()
        self._populate_tree()
        if self._edit_mode:
            self.app.set_status('编辑模式已开启 — 右键菜单编辑大纲/标签')
        else:
            self.app.set_status('查看模式')

    def _update_edit_toolbar(self):
        """更新工具栏按钮样式"""
        colors = self.config.get_colors()
        if self._edit_mode:
            self.edit_toggle_btn.config(text='🔍 查看', fg=colors['fg_link'])
            self.edit_add_cat_btn.config(fg=colors['fg_accent'])
            self.edit_reset_btn.config(fg=colors['danger'])
        else:
            self.edit_toggle_btn.config(text='✏️ 编辑', fg=colors['fg_accent'])
            self.edit_add_cat_btn.config(fg=colors['fg_muted'])
            self.edit_reset_btn.config(fg=colors['fg_muted'])

    def _next_sort_order(self, table, parent_field=None, parent_value=None):
        """获取下一个排序序号"""
        conn = get_connection()
        if parent_field and parent_value:
            row = conn.execute(
                f"SELECT MAX(sort_order) as mx FROM {table} WHERE {parent_field}=?",
                (parent_value,)
            ).fetchone()
        else:
            row = conn.execute(f"SELECT MAX(sort_order) as mx FROM {table}").fetchone()
        conn.close()
        return (row['mx'] or 0) + 1

    # ----- 大类 -----

    def _add_category(self):
        if not self._edit_mode:
            self.app.set_status('请先开启编辑模式（点击 ✏️ 编辑）')
            return
        dialog = tk.Toplevel(self.parent)
        dialog.title('添加大类')
        dialog.geometry('420x340')
        dialog.transient(self.parent)
        dialog.lift()
        dialog.focus_force()
        colors = self.config.get_colors()
        dialog.configure(bg=colors['bg_main'])

        tk.Label(dialog, text='添加新大类', font=(self.config.get('font_family'), 13, 'bold'),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(pady=(12, 8))

        tk.Label(dialog, text='名称', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.W).pack(fill=tk.X, padx=20)
        name_var = tk.StringVar()
        tk.Entry(dialog, textvariable=name_var, font=(self.config.get('font_family'), 11),
                 bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT
                 ).pack(fill=tk.X, padx=20, pady=(2, 8), ipady=3)

        tk.Label(dialog, text='描述', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.W).pack(fill=tk.X, padx=20)
        desc_text = tk.Text(dialog, font=(self.config.get('font_family'), 10),
                            bg=colors['bg_input'], fg=colors['fg_primary'],
                            relief=tk.FLAT, wrap=tk.WORD, height=4)
        desc_text.pack(fill=tk.X, padx=20, pady=(2, 8))

        def _save():
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning('提示', '名称不能为空')
                return
            import time
            cat_id = f'custom_cat_{int(time.time_ns())}'
            desc = desc_text.get('1.0', tk.END).strip()
            sort_order = self._next_sort_order('categories')
            try:
                conn = get_connection()
                conn.execute(
                    "INSERT INTO categories (category_id, name, description, sort_order, is_builtin) VALUES (?,?,?,?,0)",
                    (cat_id, name, desc, sort_order))
                conn.commit()
                conn.close()
                dialog.destroy()
                self._load_data()
                self._populate_tree()
                self.app.set_status(f'大类「{name}」已添加')
            except Exception as e:
                self.app.set_status(f'添加失败: {e}')

        tk.Button(dialog, text='保存', font=(self.config.get('font_family'), 11, 'bold'),
                  bg=colors['fg_accent'], fg='#ffffff', padx=20, pady=6, command=_save).pack(pady=8)

    def _edit_category(self, cat_id):
        cat = None
        for c in self.categories:
            if c['id'] == cat_id:
                cat = c
                break
        if not cat:
            return

        dialog = tk.Toplevel(self.parent)
        dialog.title('编辑大类')
        dialog.geometry('420x340')
        dialog.transient(self.parent)
        dialog.lift()
        dialog.focus_force()
        colors = self.config.get_colors()
        dialog.configure(bg=colors['bg_main'])

        tk.Label(dialog, text=f'编辑: {cat["name"]}', font=(self.config.get('font_family'), 13, 'bold'),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(pady=(12, 8))

        tk.Label(dialog, text='名称', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.W).pack(fill=tk.X, padx=20)
        name_var = tk.StringVar(value=cat['name'])
        tk.Entry(dialog, textvariable=name_var, font=(self.config.get('font_family'), 11),
                 bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT
                 ).pack(fill=tk.X, padx=20, pady=(2, 8), ipady=3)

        tk.Label(dialog, text='描述', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.W).pack(fill=tk.X, padx=20)
        desc_text = tk.Text(dialog, font=(self.config.get('font_family'), 10),
                            bg=colors['bg_input'], fg=colors['fg_primary'],
                            relief=tk.FLAT, wrap=tk.WORD, height=4)
        desc_text.insert('1.0', cat.get('desc', ''))
        desc_text.pack(fill=tk.X, padx=20, pady=(2, 8))

        def _save():
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning('提示', '名称不能为空')
                return
            try:
                conn = get_connection()
                conn.execute(
                    "UPDATE categories SET name=?, description=? WHERE category_id=?",
                    (name, desc_text.get('1.0', tk.END).strip(), cat_id))
                conn.commit()
                conn.close()
                dialog.destroy()
                self._load_data()
                self._populate_tree()
                self.app.set_status(f'大类已更新为「{name}」')
            except Exception as e:
                self.app.set_status(f'更新失败: {e}')

        tk.Button(dialog, text='保存', font=(self.config.get('font_family'), 11, 'bold'),
                  bg=colors['fg_accent'], fg='#ffffff', padx=20, pady=6, command=_save).pack(pady=8)

    def _delete_category(self, cat_id):
        cat = next((c for c in self.categories if c['id'] == cat_id), None)
        if not cat:
            return
        if not messagebox.askyesno('确认删除', f'确定删除大类「{cat["name"]}」及其所有主题/子知识点吗？'):
            return
        try:
            conn = get_connection()
            # 删除子知识点
            conn.execute("""
                DELETE FROM category_subtopics WHERE topic_id IN
                (SELECT topic_id FROM category_topics WHERE category_id=?)
            """, (cat_id,))
            # 删除主题
            conn.execute("DELETE FROM category_topics WHERE category_id=?", (cat_id,))
            # 删除大类
            conn.execute("DELETE FROM categories WHERE category_id=?", (cat_id,))
            conn.commit()
            conn.close()
            self._load_data()
            self._populate_tree()
            self._show_detail(False)
            self.app.set_status(f'已删除大类「{cat["name"]}」')
        except Exception as e:
            self.app.set_status(f'删除失败: {e}')

    # ----- 主题 -----

    def _add_topic(self, cat_id):
        cat = next((c for c in self.categories if c['id'] == cat_id), None)
        if not cat:
            return

        dialog = tk.Toplevel(self.parent)
        dialog.title('添加主题')
        dialog.geometry('420x340')
        dialog.transient(self.parent)
        dialog.lift()
        dialog.focus_force()
        colors = self.config.get_colors()
        dialog.configure(bg=colors['bg_main'])

        tk.Label(dialog, text=f'在「{cat["name"]}」下添加主题',
                 font=(self.config.get('font_family'), 13, 'bold'),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(pady=(12, 8))

        tk.Label(dialog, text='名称', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.W).pack(fill=tk.X, padx=20)
        name_var = tk.StringVar()
        tk.Entry(dialog, textvariable=name_var, font=(self.config.get('font_family'), 11),
                 bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT
                 ).pack(fill=tk.X, padx=20, pady=(2, 8), ipady=3)

        tk.Label(dialog, text='描述', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.W).pack(fill=tk.X, padx=20)
        desc_text = tk.Text(dialog, font=(self.config.get('font_family'), 10),
                            bg=colors['bg_input'], fg=colors['fg_primary'],
                            relief=tk.FLAT, wrap=tk.WORD, height=4)
        desc_text.pack(fill=tk.X, padx=20, pady=(2, 8))

        def _save():
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning('提示', '名称不能为空')
                return
            import time
            topic_id = f'custom_topic_{int(time.time_ns())}'
            desc = desc_text.get('1.0', tk.END).strip()
            sort_order = self._next_sort_order('category_topics', 'category_id', cat_id)
            try:
                conn = get_connection()
                conn.execute(
                    "INSERT INTO category_topics (topic_id, category_id, name, description, sort_order, is_builtin) VALUES (?,?,?,?,?,0)",
                    (topic_id, cat_id, name, desc, sort_order))
                conn.commit()
                conn.close()
                dialog.destroy()
                self._load_data()
                self._populate_tree()
                self.app.set_status(f'主题「{name}」已添加')
            except Exception as e:
                self.app.set_status(f'添加失败: {e}')

        tk.Button(dialog, text='保存', font=(self.config.get('font_family'), 11, 'bold'),
                  bg=colors['fg_accent'], fg='#ffffff', padx=20, pady=6, command=_save).pack(pady=8)

    def _edit_topic(self, topic_id):
        # 找到 topic
        topic = None
        for cat in self.categories:
            for t in cat['topics']:
                if t['id'] == topic_id:
                    topic = t
                    break
        if not topic:
            return

        dialog = tk.Toplevel(self.parent)
        dialog.title('编辑主题')
        dialog.geometry('420x340')
        dialog.transient(self.parent)
        dialog.lift()
        dialog.focus_force()
        colors = self.config.get_colors()
        dialog.configure(bg=colors['bg_main'])

        tk.Label(dialog, text=f'编辑: {topic["name"]}',
                 font=(self.config.get('font_family'), 13, 'bold'),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(pady=(12, 8))

        tk.Label(dialog, text='名称', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.W).pack(fill=tk.X, padx=20)
        name_var = tk.StringVar(value=topic['name'])
        tk.Entry(dialog, textvariable=name_var, font=(self.config.get('font_family'), 11),
                 bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT
                 ).pack(fill=tk.X, padx=20, pady=(2, 8), ipady=3)

        tk.Label(dialog, text='描述', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.W).pack(fill=tk.X, padx=20)
        desc_text = tk.Text(dialog, font=(self.config.get('font_family'), 10),
                            bg=colors['bg_input'], fg=colors['fg_primary'],
                            relief=tk.FLAT, wrap=tk.WORD, height=4)
        desc_text.insert('1.0', topic.get('desc', ''))
        desc_text.pack(fill=tk.X, padx=20, pady=(2, 8))

        def _save():
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning('提示', '名称不能为空')
                return
            try:
                conn = get_connection()
                conn.execute(
                    "UPDATE category_topics SET name=?, description=? WHERE topic_id=?",
                    (name, desc_text.get('1.0', tk.END).strip(), topic_id))
                conn.commit()
                conn.close()
                dialog.destroy()
                self._load_data()
                self._populate_tree()
                self.app.set_status(f'主题已更新为「{name}」')
            except Exception as e:
                self.app.set_status(f'更新失败: {e}')

        tk.Button(dialog, text='保存', font=(self.config.get('font_family'), 11, 'bold'),
                  bg=colors['fg_accent'], fg='#ffffff', padx=20, pady=6, command=_save).pack(pady=8)

    def _delete_topic(self, topic_id):
        topic = None
        for cat in self.categories:
            for t in cat['topics']:
                if t['id'] == topic_id:
                    topic = t
                    break
        if not topic:
            return
        if not messagebox.askyesno('确认删除', f'确定删除主题「{topic["name"]}」及其所有子知识点吗？'):
            return
        try:
            conn = get_connection()
            conn.execute("DELETE FROM category_subtopics WHERE topic_id=?", (topic_id,))
            conn.execute("DELETE FROM category_topics WHERE topic_id=?", (topic_id,))
            conn.commit()
            conn.close()
            self._load_data()
            self._populate_tree()
            self._show_detail(False)
            self.app.set_status(f'已删除主题「{topic["name"]}」')
        except Exception as e:
            self.app.set_status(f'删除失败: {e}')

    def _move_topic(self, topic_id, direction):
        """上移(-1)或下移(1)主题"""
        # 找到当前 topic 和同 category 的兄弟 topics
        parent_cat_id = None
        for cat in self.categories:
            for t in cat['topics']:
                if t['id'] == topic_id:
                    parent_cat_id = cat['id']
                    break
        if not parent_cat_id:
            return
        try:
            conn = get_connection()
            topics = conn.execute(
                "SELECT topic_id, sort_order FROM category_topics WHERE category_id=? ORDER BY sort_order",
                (parent_cat_id,)
            ).fetchall()
            idx = next((i for i, t in enumerate(topics) if t['topic_id'] == topic_id), -1)
            if idx < 0 or (direction < 0 and idx == 0) or (direction > 0 and idx >= len(topics) - 1):
                conn.close()
                return
            swap_idx = idx + direction
            # 交换 sort_order
            t1 = topics[idx]['sort_order']
            t2 = topics[swap_idx]['sort_order']
            conn.execute("UPDATE category_topics SET sort_order=? WHERE topic_id=?", (t2, topic_id))
            conn.execute("UPDATE category_topics SET sort_order=? WHERE topic_id=?", (t1, topics[swap_idx]['topic_id']))
            conn.commit()
            conn.close()
            self._load_data()
            self._populate_tree()
        except Exception as e:
            self.app.set_status(f'移动失败: {e}')

    # ----- 子知识点 -----

    def _add_subtopic(self, topic_id):
        # 找到 topic 和所属大类
        topic = None
        cat_name = ''
        for cat in self.categories:
            for t in cat['topics']:
                if t['id'] == topic_id:
                    topic = t
                    cat_name = cat['name']
                    break
        if not topic:
            return

        dialog = tk.Toplevel(self.parent)
        dialog.title('添加子知识点')
        dialog.geometry('450x350')
        dialog.transient(self.parent)
        dialog.lift()
        dialog.focus_force()
        colors = self.config.get_colors()
        dialog.configure(bg=colors['bg_main'])

        tk.Label(dialog, text=f'在「{topic["name"]}」下添加子知识点',
                 font=(self.config.get('font_family'), 13, 'bold'),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(pady=(12, 8))

        tk.Label(dialog, text='名称', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.W).pack(fill=tk.X, padx=20)
        name_var = tk.StringVar()
        tk.Entry(dialog, textvariable=name_var, font=(self.config.get('font_family'), 11),
                 bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT
                 ).pack(fill=tk.X, padx=20, pady=(2, 8), ipady=3)

        row = tk.Frame(dialog, bg=colors['bg_main'])
        row.pack(fill=tk.X, padx=20, pady=(0, 8))
        tk.Label(row, text='难度 (1-8):', font=(self.config.get('font_family'), 10),
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
                messagebox.showwarning('提示', '名称不能为空')
                return
            import time
            sub_id = f'custom_sub_{int(time.time_ns())}'
            desc = desc_text.get('1.0', tk.END).strip()
            diff = int(diff_var.get())
            lvl = {'入门': 'entry', '提高': 'improve', 'NOI': 'noi'}.get(lvl_var.get(), 'entry')
            sort_order = self._next_sort_order('category_subtopics', 'topic_id', topic_id)
            try:
                conn = get_connection()
                conn.execute(
                    "INSERT INTO category_subtopics (subtopic_id, topic_id, name, description, difficulty, level, sort_order, is_builtin) VALUES (?,?,?,?,?,?,?,0)",
                    (sub_id, topic_id, name, desc, diff, lvl, sort_order))
                conn.commit()
                conn.close()
                dialog.destroy()
                self._load_data()
                self._populate_tree()
                self.app.set_status(f'子知识点「{name}」已添加')
            except Exception as e:
                self.app.set_status(f'添加失败: {e}')

        tk.Button(dialog, text='保存', font=(self.config.get('font_family'), 11, 'bold'),
                  bg=colors['fg_accent'], fg='#ffffff', padx=20, pady=6, command=_save).pack(pady=8)

    def _edit_subtopic(self, sub_id):
        # 从 categories 结构中找到子知识点
        sub_info = None
        for cat in self.categories:
            for topic in cat['topics']:
                for sub in topic['subtopics']:
                    if sub[0] == sub_id:
                        sub_info = {
                            'id': sub[0], 'name': sub[1], 'desc': sub[2],
                            'difficulty': sub[3], 'level': sub[4],
                            'topic_id': topic['id'], 'cat_name': cat['name'],
                        }
                        break
        if not sub_info:
            return

        dialog = tk.Toplevel(self.parent)
        dialog.title('编辑子知识点')
        dialog.geometry('450x350')
        dialog.transient(self.parent)
        dialog.lift()
        dialog.focus_force()
        colors = self.config.get_colors()
        dialog.configure(bg=colors['bg_main'])

        tk.Label(dialog, text=f'编辑: {sub_info["name"]}',
                 font=(self.config.get('font_family'), 13, 'bold'),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(pady=(12, 8))

        tk.Label(dialog, text='名称', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.W).pack(fill=tk.X, padx=20)
        name_var = tk.StringVar(value=sub_info['name'])
        tk.Entry(dialog, textvariable=name_var, font=(self.config.get('font_family'), 11),
                 bg=colors['bg_input'], fg=colors['fg_primary'], relief=tk.FLAT
                 ).pack(fill=tk.X, padx=20, pady=(2, 8), ipady=3)

        row = tk.Frame(dialog, bg=colors['bg_main'])
        row.pack(fill=tk.X, padx=20, pady=(0, 8))
        tk.Label(row, text='难度 (1-8):', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(side=tk.LEFT)
        diff_var = tk.StringVar(value=str(sub_info['difficulty']))
        ttk.Combobox(row, textvariable=diff_var, values=[str(i) for i in range(1, 9)],
                      state='readonly', width=4).pack(side=tk.LEFT, padx=4)
        tk.Label(row, text='等级:', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(side=tk.LEFT, padx=(12, 4))
        lvl_var = tk.StringVar(value=LEVEL_MAP.get(sub_info['level'], '入门'))
        ttk.Combobox(row, textvariable=lvl_var, values=['入门', '提高', 'NOI'],
                      state='readonly', width=6).pack(side=tk.LEFT, padx=4)

        tk.Label(dialog, text='描述（Markdown）', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.W).pack(fill=tk.X, padx=20)
        desc_text = tk.Text(dialog, font=(self.config.get('font_family'), 10),
                            bg=colors['bg_input'], fg=colors['fg_primary'],
                            relief=tk.FLAT, wrap=tk.WORD, height=5)
        desc_text.insert('1.0', sub_info['desc'])
        desc_text.pack(fill=tk.X, padx=20, pady=(2, 8))

        def _save():
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning('提示', '名称不能为空')
                return
            try:
                conn = get_connection()
                conn.execute(
                    "UPDATE category_subtopics SET name=?, description=?, difficulty=?, level=? WHERE subtopic_id=?",
                    (name, desc_text.get('1.0', tk.END).strip(),
                     int(diff_var.get()),
                     {'入门': 'entry', '提高': 'improve', 'NOI': 'noi'}.get(lvl_var.get(), 'entry'),
                     sub_id))
                conn.commit()
                conn.close()
                dialog.destroy()
                self._load_data()
                self._populate_tree()
                self.app.set_status(f'子知识点已更新为「{name}」')
            except Exception as e:
                self.app.set_status(f'更新失败: {e}')

        tk.Button(dialog, text='保存', font=(self.config.get('font_family'), 11, 'bold'),
                  bg=colors['fg_accent'], fg='#ffffff', padx=20, pady=6, command=_save).pack(pady=8)

    def _delete_subtopic(self, sub_id):
        sub_name = sub_id
        for cat in self.categories:
            for topic in cat['topics']:
                for sub in topic['subtopics']:
                    if sub[0] == sub_id:
                        sub_name = sub[1]
                        break
        if not messagebox.askyesno('确认删除', f'确定删除子知识点「{sub_name}」吗？'):
            return
        try:
            conn = get_connection()
            conn.execute("DELETE FROM category_subtopics WHERE subtopic_id=?", (sub_id,))
            conn.commit()
            conn.close()
            self._load_data()
            self._populate_tree()
            self._show_detail(False)
            self.app.set_status(f'已删除子知识点「{sub_name}」')
        except Exception as e:
            self.app.set_status(f'删除失败: {e}')

    def _move_subtopic(self, sub_id, direction):
        """上移(-1)或下移(1)子知识点"""
        # 找到所属 topic_id
        parent_topic_id = None
        for cat in self.categories:
            for topic in cat['topics']:
                for sub in topic['subtopics']:
                    if sub[0] == sub_id:
                        parent_topic_id = topic['id']
                        break
        if not parent_topic_id:
            return
        try:
            conn = get_connection()
            subs = conn.execute(
                "SELECT subtopic_id, sort_order FROM category_subtopics WHERE topic_id=? ORDER BY sort_order",
                (parent_topic_id,)
            ).fetchall()
            idx = next((i for i, s in enumerate(subs) if s['subtopic_id'] == sub_id), -1)
            if idx < 0 or (direction < 0 and idx == 0) or (direction > 0 and idx >= len(subs) - 1):
                conn.close()
                return
            swap_idx = idx + direction
            s1 = subs[idx]['sort_order']
            s2 = subs[swap_idx]['sort_order']
            conn.execute("UPDATE category_subtopics SET sort_order=? WHERE subtopic_id=?", (s2, sub_id))
            conn.execute("UPDATE category_subtopics SET sort_order=? WHERE subtopic_id=?", (s1, subs[swap_idx]['subtopic_id']))
            conn.commit()
            conn.close()
            self._load_data()
            self._populate_tree()
        except Exception as e:
            self.app.set_status(f'移动失败: {e}')

    # ----- 重置出厂 -----

    def _reset_to_factory(self):
        if not self._edit_mode:
            self.app.set_status('请先开启编辑模式（点击 ✏️ 编辑）')
            return
        if not messagebox.askyesno('确认重置', '确定恢复出厂大纲/标签吗？\n所有自定义修改将被清除。'):
            return
        try:
            conn = get_connection()
            conn.execute("DELETE FROM category_subtopics")
            conn.execute("DELETE FROM category_topics")
            conn.execute("DELETE FROM categories")
            conn.commit()
            conn.close()
            # 重新从 ALGORITHM_CATEGORIES 导入
            from db.seed import migrate_categories_to_db
            migrate_categories_to_db()
            self._load_data()
            self._populate_tree()
            self._show_detail(False)
            self.app.set_status('已恢复出厂设置')
        except Exception as e:
            self.app.set_status(f'重置失败: {e}')

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
        dialog.lift()
        dialog.focus_force()
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
        info = self._topic_map[item_id]
        name = info['name']
        level_key = info.get('level', 'entry')
        badge = self._level_badge(level_key)
        prefix = '✎ ' if item_id in self._custom_topics else ''
        self.tree.item(item_id, text=f'{symbol} {prefix}{name}  [{badge}]')

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
