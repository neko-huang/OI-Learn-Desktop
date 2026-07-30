"""
算法大纲模块
左侧树形导航（21大类→主题→知识点）+ 右侧详情（掌握度标记 + Markdown 说明 + 进度统计）
"""

import tkinter as tk
from tkinter import ttk

from config import Config
from db.seed import get_categories, get_all_topic_ids
from db.database import get_connection
from components.markdown_view import MarkdownView

# 掌握程度映射
MASTERY_MAP = {
    'none':      ('未学',   '#888', '#e0e0e0'),
    'learning':  ('学习中', '#BA7517', '#FAEEDA'),
    'familiar':  ('熟悉',   '#185FA5', '#E6F1FB'),
    'mastered':  ('已掌握', '#3B6D11', '#EAF3DE'),
}

LEVEL_MAP = {
    'entry':   '入门',
    'improve': '提高',
    'noi':     'NOI',
}


class OutlineModule:
    """算法大纲模块"""

    def __init__(self, app, parent_frame: tk.Frame):
        self.app = app
        self.config = Config()
        self.parent = parent_frame

        # 清除占位内容
        for w in parent_frame.winfo_children():
            w.destroy()

        # 加载数据
        self.categories = get_categories()
        self.all_topics = get_all_topic_ids()
        self._topic_map = {t['topic_id']: t for t in self.all_topics}

        self._load_progress()
        self._build_ui()

    # ============================================================
    # UI 构建
    # ============================================================

    def _build_ui(self):
        """三栏布局：左侧树 + 中间详情 + 右侧统计"""
        colors = self.config.get_colors()

        # --- 左侧面板：Treeview ---
        left_frame = tk.Frame(self.parent, width=320, bg=colors['bg_sidebar'])
        left_frame.pack(side=tk.LEFT, fill=tk.Y)
        left_frame.pack_propagate(False)

        # 顶部标题
        tk.Label(
            left_frame, text='算法大纲',
            font=(self.config.get('font_family'), 13, 'bold'),
            bg=colors['bg_sidebar'], fg=colors['fg_primary'],
            anchor=tk.W,
        ).pack(fill=tk.X, padx=12, pady=(10, 6))

        # 树形控件
        tree_frame = tk.Frame(left_frame, bg=colors['bg_sidebar'])
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))

        self.tree = ttk.Treeview(
            tree_frame,
            columns=('status',),
            show='tree',
            selectmode='browse',
        )
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.bind('<<TreeviewSelect>>', self._on_select)
        self.tree.bind('<Double-1>', self._on_double_click)

        # 填充树
        self._populate_tree()

        # --- 右侧主内容 ---
        right_frame = tk.Frame(self.parent, bg=colors['bg_main'])
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 知识点标题
        self.detail_title = tk.Label(
            right_frame,
            text='',
            font=(self.config.get('font_family'), 18, 'bold'),
            bg=colors['bg_main'], fg=colors['fg_primary'],
            anchor=tk.W, justify=tk.LEFT,
        )
        self.detail_title.pack(fill=tk.X, padx=16, pady=(12, 4))

        # 元信息行：难度 + 等级 + 掌握度
        meta_frame = tk.Frame(right_frame, bg=colors['bg_main'])
        meta_frame.pack(fill=tk.X, padx=16, pady=(0, 8))

        self.meta_difficulty = tk.Label(meta_frame, text='', font=(self.config.get('font_family'), 10),
                                         bg=colors['bg_main'], fg=colors['fg_secondary'])
        self.meta_difficulty.pack(side=tk.LEFT, padx=(0, 16))

        self.meta_level = tk.Label(meta_frame, text='', font=(self.config.get('font_family'), 10),
                                    bg=colors['bg_main'], fg=colors['fg_secondary'])
        self.meta_level.pack(side=tk.LEFT, padx=(0, 16))

        # 掌握度选择
        self.mastery_var = tk.StringVar(value='none')
        self.mastery_combo = ttk.Combobox(
            meta_frame,
            textvariable=self.mastery_var,
            values=['none', 'learning', 'familiar', 'mastered'],
            state='readonly',
            width=10,
        )
        self.mastery_combo.pack(side=tk.LEFT, padx=(0, 8))
        self.mastery_combo.bind('<<ComboboxSelected>>', self._on_mastery_changed)

        self.mastery_label = tk.Label(meta_frame, text='', font=(self.config.get('font_family'), 10),
                                       bg=colors['bg_main'])
        self.mastery_label.pack(side=tk.LEFT)

        # --- Markdown 内容 ---
        self.markdown_view = MarkdownView(right_frame)
        self.markdown_view.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))

    def _populate_tree(self):
        """填充树形大纲"""
        self.tree.delete(*self.tree.get_children())

        for cat in self.categories:
            cat_node = self.tree.insert('', tk.END, text=cat['name'],
                                         values=('cat',), tags=('category',),
                                         iid=cat['id'], open=False)
            for topic in cat['topics']:
                topic_node = self.tree.insert(cat_node, tk.END,
                                               text=f"  {topic['name']}",
                                               values=('topic',),
                                               tags=('topic',),
                                               iid=topic['id'], open=False)
                for sub in topic['subtopics']:
                    sub_id = sub[0]
                    status = self._progress.get(sub_id, 'none')
                    symbol = self._mastery_symbol(status)
                    self.tree.insert(topic_node, tk.END,
                                      text=f'    {symbol} {sub[1]}',
                                      values=(sub_id,),
                                      tags=('subtopic',),
                                      iid=sub_id)

        # 配置标签样式
        self.tree.tag_configure('category', font=(self.config.get('font_family'), 12, 'bold'))
        self.tree.tag_configure('topic', font=(self.config.get('font_family'), 11))
        self.tree.tag_configure('subtopic', font=(self.config.get('font_family'), 10))

    # ============================================================
    # 进度管理
    # ============================================================

    def _load_progress(self):
        """从数据库加载掌握度"""
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
        """保存掌握度到数据库"""
        self._progress[topic_id] = mastery
        try:
            conn = get_connection()
            conn.execute(
                """INSERT INTO outline_progress (topic_id, mastery)
                   VALUES (?, ?)
                   ON CONFLICT(topic_id) DO UPDATE SET
                     mastery=excluded.mastery,
                     updated_at=datetime('now','localtime')""",
                (topic_id, mastery)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            self.app.set_status(f'保存失败: {e}')

    def _mastery_symbol(self, status: str) -> str:
        symbols = {'none': '○', 'learning': '◐', 'familiar': '◉', 'mastered': '●'}
        return symbols.get(status, '○')

    # ============================================================
    # 事件处理
    # ============================================================

    def _on_select(self, event):
        """树节点选中时更新右侧详情"""
        selection = self.tree.selection()
        if not selection:
            return

        item_id = selection[0]
        topic_info = self._topic_map.get(item_id)

        if not topic_info:
            return

        colors = self.config.get_colors()

        # 标题
        category = topic_info.get('category_name', '')
        name = topic_info['name']
        self.detail_title.config(text=f'{category} › {name}')

        # 元信息
        diff = topic_info['difficulty']
        level = LEVEL_MAP.get(topic_info['level'], topic_info['level'])
        self.meta_difficulty.config(text=f'难度: {"★" * diff}')
        self.meta_level.config(text=f'等级: {level}')

        # 掌握度
        current = self._progress.get(item_id, 'none')
        self.mastery_var.set(current)
        status_name, fg, bg = MASTERY_MAP[current]
        self.mastery_label.config(text=status_name, fg=fg, bg=bg)

        # Markdown 内容
        desc = topic_info.get('desc', '暂无详细说明')
        content = f'## {name}\n\n{desc}\n\n'
        content += f'- **难度**: {"★" * diff} ({level})\n'
        content += f'- **分类**: {category}\n'
        content += f'- **掌握度**: {status_name}\n'

        self.markdown_view.render(content)

    def _on_double_click(self, event):
        """双击切换掌握度"""
        selection = self.tree.selection()
        if not selection:
            return
        item_id = selection[0]
        if item_id not in self._topic_map:
            return

        cycle = {'none': 'learning', 'learning': 'familiar',
                 'familiar': 'mastered', 'mastered': 'none'}
        current = self._progress.get(item_id, 'none')
        new_mastery = cycle[current]
        self._save_progress(item_id, new_mastery)

        # 更新树节点文字
        symbol = self._mastery_symbol(new_mastery)
        name = self._topic_map[item_id]['name']
        self.tree.item(item_id, text=f'    {symbol} {name}')

        # 更新界面
        self.mastery_var.set(new_mastery)
        status_name, fg, bg = MASTERY_MAP[new_mastery]
        self.mastery_label.config(text=status_name, fg=fg, bg=bg)
        self.app.set_status(f'「{name}」→ {status_name}')

    def _on_mastery_changed(self, event):
        """下拉框改变掌握度"""
        selection = self.tree.selection()
        if not selection:
            return
        item_id = selection[0]
        if item_id not in self._topic_map:
            return

        new_mastery = self.mastery_var.get()
        self._save_progress(item_id, new_mastery)

        # 更新树节点
        symbol = self._mastery_symbol(new_mastery)
        name = self._topic_map[item_id]['name']
        self.tree.item(item_id, text=f'    {symbol} {name}')

        status_name, fg, bg = MASTERY_MAP[new_mastery]
        self.mastery_label.config(text=status_name, fg=fg, bg=bg)
        self.app.set_status(f'「{name}」→ {status_name}')

    def apply_theme(self):
        """响应主题切换 — 重建 UI 以应用新颜色"""
        # 保存树展开状态
        expanded = [item for item in self.tree.get_children('') if self.tree.item(item, 'open')]
        # 重建
        for w in self.parent.winfo_children():
            w.destroy()
        self._build_ui()
        # 恢复展开状态
        for item in expanded:
            try:
                self.tree.item(item, open=True)
            except tk.TclError:
                pass
