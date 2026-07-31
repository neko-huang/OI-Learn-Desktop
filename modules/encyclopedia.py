"""
算法百科模块
左侧分类列表 + 搜索栏 + 右侧 Markdown 渲染 + 编辑功能
"""

import tkinter as tk
from tkinter import ttk, messagebox

from config import Config
from db.database import get_connection
from components.markdown_view import MarkdownView

# 预定义分类（与大纲对应）
CATEGORIES = [
    '语言入门', '基础算法', '双指针', '线性数据结构', '树形数据结构',
    '树论', '图论', '搜索', '动态规划', '字符串', '数学', '计算几何',
    '位运算', '博弈论', '概率与期望', '多项式与生成函数', '杂项',
    '工具与技巧', '高级专题', '其他',
]


class EncyclopediaModule:
    """算法百科模块"""

    def __init__(self, app, parent_frame: tk.Frame):
        self.app = app
        self.config = Config()
        self.parent = parent_frame

        for w in parent_frame.winfo_children():
            w.destroy()

        self._editing_id = None   # 当前编辑中的条目 ID
        self._load_entries()
        self._build_ui()
        self._refresh_list()

    # ============================================================
    # 数据加载
    # ============================================================

    def _load_entries(self):
        """从数据库加载所有百科条目的摘要"""
        self.entries = []
        try:
            conn = get_connection()
            rows = conn.execute(
                """SELECT id, title, category, tags, created_at, updated_at
                   FROM encyclopedia ORDER BY updated_at DESC"""
            ).fetchall()
            self.entries = [dict(r) for r in rows]
            conn.close()
        except Exception:
            self.entries = []

    def _load_entry(self, entry_id: int) -> dict:
        """加载单条百科的完整内容"""
        try:
            conn = get_connection()
            row = conn.execute(
                "SELECT * FROM encyclopedia WHERE id=?", (entry_id,)
            ).fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception:
            return None

    def _save_entry(self, title: str, category: str, content: str, tags: str = ''):
        """保存或更新百科条目"""
        try:
            conn = get_connection()
            if self._editing_id:
                conn.execute(
                    """UPDATE encyclopedia SET title=?, category=?, content=?, tags=?,
                       updated_at=datetime('now','localtime') WHERE id=?""",
                    (title, category, content, tags, self._editing_id)
                )
            else:
                conn.execute(
                    """INSERT INTO encyclopedia (title, category, content, tags)
                       VALUES (?, ?, ?, ?)""",
                    (title, category, content, tags)
                )
            conn.commit()
            conn.close()
            self._load_entries()
            self._refresh_list()
            return True
        except Exception as e:
            self.app.set_status(f'保存失败: {e}')
            return False

    def _delete_entry(self, entry_id: int):
        """删除百科条目"""
        if not messagebox.askyesno('确认删除', '确定要删除这个条目吗？'):
            return
        try:
            conn = get_connection()
            conn.execute("DELETE FROM encyclopedia WHERE id=?", (entry_id,))
            conn.commit()
            conn.close()
            self._load_entries()
            self._refresh_list()
            self._show_empty()
            self.app.set_status('条目已删除')
        except Exception as e:
            self.app.set_status(f'删除失败: {e}')

    # ============================================================
    # UI 构建
    # ============================================================

    def _build_ui(self):
        colors = self.config.get_colors()

        # --- 顶部工具栏 ---
        toolbar = tk.Frame(self.parent, bg=colors['bg_sidebar'], height=44)
        toolbar.pack(fill=tk.X)
        toolbar.pack_propagate(False)

        # 搜索框
        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', lambda *a: self._refresh_list())
        search_entry = tk.Entry(
            toolbar,
            textvariable=self.search_var,
            font=(self.config.get('font_family'), 11),
            bg=colors['bg_input'], fg=colors['fg_primary'],
            relief=tk.FLAT, bd=0,
        )
        search_entry.pack(side=tk.LEFT, padx=12, pady=8, fill=tk.X, expand=True)

        # 新建按钮
        new_btn = tk.Button(
            toolbar,
            text='+ 新建条目',
            font=(self.config.get('font_family'), 10),
            bg=colors['fg_accent'], fg='#ffffff',
            relief=tk.FLAT, padx=12, pady=4,
            cursor='hand2',
            command=self._new_entry,
        )
        new_btn.pack(side=tk.RIGHT, padx=8, pady=8)

        # 删除按钮
        self.delete_btn = tk.Button(
            toolbar,
            text='删除',
            font=(self.config.get('font_family'), 10),
            bg=colors['bg_sidebar'], fg=colors['fg_secondary'],
            relief=tk.FLAT, padx=12, pady=4,
            cursor='hand2',
            command=lambda: self._delete_selected(),
            state=tk.DISABLED,
        )
        self.delete_btn.pack(side=tk.RIGHT, pady=8)

        # --- 主体：左侧列表 + 右侧内容 ---
        main = tk.Frame(self.parent, bg=colors['bg_main'])
        main.pack(fill=tk.BOTH, expand=True)

        # 左侧列表面板
        left = tk.Frame(main, width=260, bg=colors['bg_sidebar'])
        left.pack(side=tk.LEFT, fill=tk.Y)
        left.pack_propagate(False)

        tk.Label(
            left, text='条目列表', font=(self.config.get('font_family'), 12, 'bold'),
            bg=colors['bg_sidebar'], fg=colors['fg_primary'], anchor=tk.W,
        ).pack(fill=tk.X, padx=12, pady=(10, 4))

        # 分类筛选
        self.cat_var = tk.StringVar(value='全部')
        self.cat_combo = ttk.Combobox(
            left, textvariable=self.cat_var, values=['全部'] + CATEGORIES,
            state='readonly', width=18,
        )
        self.cat_combo.pack(fill=tk.X, padx=8, pady=(0, 6))
        self.cat_combo.bind('<<ComboboxSelected>>', lambda e: self._refresh_list())

        # 条目列表
        list_frame = tk.Frame(left, bg=colors['bg_sidebar'])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))

        self.entry_listbox = tk.Listbox(
            list_frame,
            font=(self.config.get('font_family'), 10),
            bg=colors['bg_input'], fg=colors['fg_primary'],
            selectbackground=colors['fg_accent'], selectforeground='#ffffff',
            relief=tk.FLAT, bd=0,
            activestyle='none',
        )
        self.entry_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.entry_listbox.bind('<<ListboxSelect>>', self._on_entry_select)

        list_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL,
                                     command=self.entry_listbox.yview)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.entry_listbox.configure(yscrollcommand=list_scroll.set)

        # 右侧内容区
        right = tk.Frame(main, bg=colors['bg_main'])
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 编辑/查看模式切换
        self.view_mode = True  # True=查看, False=编辑
        self.mode_frame = tk.Frame(right, bg=colors['bg_main'])
        self.mode_frame.pack(fill=tk.X, padx=16, pady=(10, 0))

        self.edit_btn = tk.Button(
            self.mode_frame,
            text='编辑',
            font=(self.config.get('font_family'), 10),
            bg=colors['bg_sidebar'], fg=colors['fg_primary'],
            relief=tk.FLAT, padx=12, pady=4,
            cursor='hand2',
            command=self._toggle_edit_mode,
        )
        self.edit_btn.pack(side=tk.RIGHT)

        # 查看模式：Markdown 渲染
        self.markdown_view = MarkdownView(right)
        self.markdown_view.pack(fill=tk.BOTH, expand=True, padx=12, pady=(4, 8))

        # 编辑模式：编辑器
        self._build_editor(right)

    def _build_editor(self, parent):
        """构建编辑器组件（默认隐藏）"""
        colors = self.config.get_colors()

        self.editor_frame = tk.Frame(parent, bg=colors['bg_main'])

        # 标题行
        title_row = tk.Frame(self.editor_frame, bg=colors['bg_main'])
        title_row.pack(fill=tk.X, padx=12, pady=(8, 4))

        tk.Label(title_row, text='标题:', font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(side=tk.LEFT)

        self.edit_title_var = tk.StringVar()
        tk.Entry(
            title_row, textvariable=self.edit_title_var,
            font=(self.config.get('font_family'), 13, 'bold'),
            bg=colors['bg_input'], fg=colors['fg_primary'],
            relief=tk.FLAT, bd=1,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))

        # 分类和标签行
        meta_row = tk.Frame(self.editor_frame, bg=colors['bg_main'])
        meta_row.pack(fill=tk.X, padx=12, pady=(0, 8))

        tk.Label(meta_row, text='分类:', font=(self.config.get('font_family'), 10),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(side=tk.LEFT)

        self.edit_cat_var = tk.StringVar()
        ttk.Combobox(
            meta_row, textvariable=self.edit_cat_var, values=CATEGORIES,
            state='readonly', width=15,
        ).pack(side=tk.LEFT, padx=(4, 16))

        # Markdown 编辑器（纯文本框）
        self.edit_text = tk.Text(
            self.editor_frame,
            font=(self.config.get('code_font_family'), 12),
            bg=colors['bg_input'], fg=colors['fg_primary'],
            relief=tk.FLAT, bd=1,
            wrap=tk.WORD,
            undo=True,
        )
        self.edit_text.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 4))

        # 编辑模式保存按钮
        save_row = tk.Frame(self.editor_frame, bg=colors['bg_main'])
        save_row.pack(fill=tk.X, padx=12, pady=(0, 8))

        tk.Button(
            save_row, text='取消',
            font=(self.config.get('font_family'), 10),
            bg=colors['bg_sidebar'], fg=colors['fg_primary'],
            relief=tk.FLAT, padx=12, pady=4,
            cursor='hand2',
            command=self._cancel_edit,
        ).pack(side=tk.RIGHT, padx=(4, 0))

        tk.Button(
            save_row, text='保存 (Ctrl+S)',
            font=(self.config.get('font_family'), 10),
            bg=colors['fg_accent'], fg='#ffffff',
            relief=tk.FLAT, padx=16, pady=4,
            cursor='hand2',
            command=self._save_current,
        ).pack(side=tk.RIGHT)

    # ============================================================
    # 列表刷新与选择
    # ============================================================

    def _refresh_list(self):
        """根据搜索和分类筛选刷新列表"""
        search = self.search_var.get().lower().strip()
        category = self.cat_var.get()

        self.entry_listbox.delete(0, tk.END)
        self._entry_ids = []

        for entry in self.entries:
            title = entry['title'].lower()
            cat = entry['category']
            tags = (entry.get('tags') or '').lower()

            # 分类筛选
            if category != '全部' and cat != category:
                continue
            # 搜索过滤
            if search and search not in title and search not in tags and search not in cat.lower():
                continue

            self.entry_listbox.insert(tk.END, f'{entry["title"]}  [{entry["category"]}]')
            self._entry_ids.append(entry['id'])

    def _on_entry_select(self, event):
        """选中列表条目时显示内容"""
        sel = self.entry_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self._entry_ids):
            return

        entry_id = self._entry_ids[idx]
        entry = self._load_entry(entry_id)
        if not entry:
            return

        self._editing_id = entry_id
        self.delete_btn.config(state=tk.NORMAL)

        # 查看模式
        self.view_mode = True
        self.edit_btn.config(text='编辑')
        self.markdown_view.pack(fill=tk.BOTH, expand=True, padx=12, pady=(4, 8))
        self.editor_frame.pack_forget()

        # 渲染 Markdown
        self.markdown_view.render(entry.get('content', ''))

    def _show_empty(self):
        """显示空内容"""
        self._editing_id = None
        self.delete_btn.config(state=tk.DISABLED)
        self.view_mode = True
        self.edit_btn.config(text='编辑')
        self.markdown_view.pack(fill=tk.BOTH, expand=True, padx=12, pady=(4, 8))
        self.editor_frame.pack_forget()
        self.markdown_view.render('*选择一个条目查看，或点击「+ 新建条目」创建新内容*')

    # ============================================================
    # 编辑操作
    # ============================================================

    def _new_entry(self):
        """创建新条目"""
        self._editing_id = None
        self._enter_edit_mode('', '', '')

    def _toggle_edit_mode(self):
        """切换查看/编辑模式"""
        if self.view_mode:
            if self._editing_id is None:
                return
            entry = self._load_entry(self._editing_id)
            if entry:
                self._enter_edit_mode(
                    entry.get('title', ''),
                    entry.get('category', ''),
                    entry.get('content', '')
                )
        else:
            self._cancel_edit()

    def _enter_edit_mode(self, title: str, category: str, content: str):
        """进入编辑模式"""
        self.view_mode = False
        self.edit_btn.config(text='查看')

        # 隐藏查看，显示编辑
        self.markdown_view.pack_forget()
        self.editor_frame.pack(fill=tk.BOTH, expand=True)

        # 填充编辑器
        self.edit_title_var.set(title)
        self.edit_cat_var.set(category)
        self.edit_text.delete('1.0', tk.END)
        self.edit_text.insert('1.0', content)

    def _cancel_edit(self):
        """取消编辑"""
        self.view_mode = True
        self.edit_btn.config(text='编辑')
        self.editor_frame.pack_forget()
        self.markdown_view.pack(fill=tk.BOTH, expand=True, padx=12, pady=(4, 8))

        # 重新加载当前查看的条目
        if self._editing_id:
            entry = self._load_entry(self._editing_id)
            if entry:
                self.markdown_view.render(entry.get('content', ''))
        else:
            self._show_empty()

    def _save_current(self):
        """保存当前编辑的内容"""
        title = self.edit_title_var.get().strip()
        if not title:
            messagebox.showwarning('提示', '请输入标题')
            return
        category = self.edit_cat_var.get()
        content = self.edit_text.get('1.0', tk.END).strip()

        if self._save_entry(title, category, content):
            self.view_mode = True
            self.edit_btn.config(text='编辑')
            self.editor_frame.pack_forget()
            self.markdown_view.pack(fill=tk.BOTH, expand=True, padx=12, pady=(4, 8))
            self.markdown_view.render(content)
            self.app.set_status(f'条目「{title}」已保存')

    def _delete_selected(self):
        """删除当前选中的条目"""
        if self._editing_id:
            self._delete_entry(self._editing_id)
            self._editing_id = None

    def on_save(self):
        """Ctrl+S 快捷键处理"""
        if not self.view_mode:
            self._save_current()

    def on_search(self):
        """Ctrl+F 快捷键处理：聚焦搜索框"""
        self.search_var.set('')
        # 搜索框已经处于可聚焦状态

    def on_export(self):
        from services.exporter import export_encyclopedia_to_md
        path = export_encyclopedia_to_md()
        if path:
            self.app.set_status(f'已导出: {path}')
        else:
            self.app.set_status('暂无数据可导出')

    # ============================================================
    # 主题
    # ============================================================

    def apply_theme(self):
        """主题切换时重建 UI"""
        self._load_entries()
        for w in self.parent.winfo_children():
            w.destroy()
        self._build_ui()
        self._refresh_list()
