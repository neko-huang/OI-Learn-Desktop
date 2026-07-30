"""
主应用窗口
负责：顶部导航栏、7 模块切换、主题应用、全局快捷键、内容区域管理
"""

import tkinter as tk
from tkinter import ttk
from config import Config


MODULES = [
    {'id': 'outline',      'name': '大纲',   'shortcut': 'Ctrl+1'},
    {'id': 'encyclopedia', 'name': '百科',   'shortcut': 'Ctrl+2'},
    {'id': 'problems',     'name': '刷题',   'shortcut': 'Ctrl+3'},
    {'id': 'templates',    'name': '模板',   'shortcut': 'Ctrl+4'},
    {'id': 'mistakes',     'name': '易错集', 'shortcut': 'Ctrl+5'},
    {'id': 'plan',         'name': '计划',   'shortcut': 'Ctrl+6'},
    {'id': 'stats',        'name': '统计',   'shortcut': 'Ctrl+7'},
]


class App(tk.Tk):
    """主应用窗口"""

    def __init__(self):
        super().__init__()

        self.config = Config()
        self.title('InfoLearn — 信息学学习助手')
        self.geometry(self._geometry_string())
        self.minsize(900, 600)

        self.protocol('WM_DELETE_WINDOW', self._on_close)
        self.current_module = None

        self._setup_style()
        self._build_nav_bar()
        self._build_content_area()
        self._build_status_bar()
        self.apply_theme()
        self._bind_shortcuts()
        self.switch_module('outline')

        self.lift()
        self.focus_force()

    # ============================================================
    # 布局构建
    # ============================================================

    def _geometry_string(self) -> str:
        w = self.config.get('window_width', 1200)
        h = self.config.get('window_height', 800)
        x = self.config.get('window_x')
        y = self.config.get('window_y')
        if x is not None and y is not None:
            return f'{w}x{h}+{x}+{y}'
        return f'{w}x{h}'

    def _setup_style(self):
        """初始化 ttk 样式"""
        self.style = ttk.Style()
        # 使用 clam 主题，比 default 更容易定制
        available = self.style.theme_names()
        if 'clam' in available:
            self.style.theme_use('clam')
        elif 'vista' in available:
            self.style.theme_use('vista')

    def _build_nav_bar(self):
        """构建顶部导航栏 —— 仅 7 个模块按钮，无冗余"""
        # 外层容器：白色/深色背景 + 底部分隔线
        self.nav_outer = tk.Frame(self, height=48)
        self.nav_outer.pack(side=tk.TOP, fill=tk.X)
        self.nav_outer.pack_propagate(False)

        # 内层按钮区域（居中排列，不贴边）
        self.nav_frame = tk.Frame(self.nav_outer, height=48)
        self.nav_frame.pack(fill=tk.BOTH, expand=True)
        self.nav_frame.pack_propagate(False)

        # 左侧留白
        left_pad = tk.Frame(self.nav_frame, width=16)
        left_pad.pack(side=tk.LEFT)

        # 7 个模块按钮
        self.nav_buttons = {}
        self.nav_indicators = {}  # 底部指示条
        for mod in MODULES:
            btn = tk.Label(
                self.nav_frame,
                text=mod['name'],
                font=(self.config.get('font_family'), 12),
                cursor='hand2',
                padx=14, pady=10,
            )
            btn.pack(side=tk.LEFT, padx=0)
            btn.bind('<Button-1>', lambda e, mid=mod['id']: self.switch_module(mid))
            btn.bind('<Enter>', lambda e, b=btn: self._nav_hover(b, True))
            btn.bind('<Leave>', lambda e, b=btn: self._nav_hover(b, False))
            self.nav_buttons[mod['id']] = btn

        # 右侧弹簧把设置按钮推到最右边
        spacer = tk.Frame(self.nav_frame)
        spacer.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 设置按钮（齿轮符号）
        self.settings_btn = tk.Label(
            self.nav_frame,
            text='\u2699',
            font=(self.config.get('font_family'), 16),
            cursor='hand2',
            padx=12, pady=8,
        )
        self.settings_btn.pack(side=tk.RIGHT, padx=(0, 12))
        self.settings_btn.bind('<Button-1>', self._on_settings)
        self.settings_btn.bind('<Enter>', lambda e: self._nav_hover(self.settings_btn, True))
        self.settings_btn.bind('<Leave>', lambda e: self._nav_hover(self.settings_btn, False))

        # 底部分隔线 Canvas
        self.nav_separator = tk.Canvas(self.nav_outer, height=2, highlightthickness=0)
        self.nav_separator.pack(side=tk.BOTTOM, fill=tk.X)

    def _nav_hover(self, btn: tk.Label, entering: bool):
        """导航按钮 hover 效果"""
        colors = self.config.get_colors()
        if btn.cget('state') == 'disabled':
            return
        if entering:
            btn.configure(fg=colors['fg_accent'])
        else:
            btn.configure(fg=colors['fg_secondary'])

    def _build_content_area(self):
        """构建内容区域 —— 纯 Frame 切换，无 Notebook 标签栏"""
        self.content_frame = tk.Frame(self)
        self.content_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # 为每个模块创建容器 Frame（初始隐藏）
        self.module_frames = {}
        for mod in MODULES:
            frame = tk.Frame(self.content_frame)
            self.module_frames[mod['id']] = frame

            # 占位文字（后续各模块会替换）
            placeholder = tk.Label(
                frame,
                text=f'{mod["name"]} 模块\n\n功能开发中...',
                font=(self.config.get('font_family'), 14),
            )
            placeholder.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    def _build_status_bar(self):
        """构建底部状态栏"""
        self.status_frame = tk.Frame(self, height=26)
        self.status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_frame.pack_propagate(False)

        # 左侧：状态文字
        self.status_label = tk.Label(
            self.status_frame,
            text='',
            font=(self.config.get('font_family'), 9),
            anchor=tk.W,
        )
        self.status_label.pack(side=tk.LEFT, padx=12)

        # 右侧：快捷键提示
        self.shortcut_hint = tk.Label(
            self.status_frame,
            text='Ctrl+, 设置',
            font=(self.config.get('font_family'), 9),
            anchor=tk.E,
        )
        self.shortcut_hint.pack(side=tk.RIGHT, padx=12)

    # ============================================================
    # 模块切换
    # ============================================================

    def switch_module(self, module_id: str):
        """切换到指定模块 —— 纯 Frame 切换，无冗余标签栏"""
        if module_id not in self.module_frames:
            return

        # 隐藏当前模块
        if self.current_module and self.current_module in self.module_frames:
            self.module_frames[self.current_module].pack_forget()

        # 显示新模块
        self.module_frames[module_id].pack(fill=tk.BOTH, expand=True)

        # 更新导航按钮样式
        self._update_nav_style(module_id)

        self.current_module = module_id
        self.set_status(f'已切换到「{self._module_name(module_id)}」')

    def _update_nav_style(self, active_id: str):
        """更新导航按钮样式：选中=高亮，未选中=常规"""
        colors = self.config.get_colors()
        for mid, btn in self.nav_buttons.items():
            if mid == active_id:
                btn.configure(
                    fg=colors['fg_accent'],
                    font=(self.config.get('font_family'), 12, 'bold'),
                )
                btn.bind('<Button-1>', lambda e: None)  # 禁用重复点击
            else:
                btn.configure(
                    fg=colors['fg_secondary'],
                    font=(self.config.get('font_family'), 12),
                )
                btn.bind('<Button-1>', lambda e, m=mid: self.switch_module(m))

    def _module_name(self, module_id: str) -> str:
        for mod in MODULES:
            if mod['id'] == module_id:
                return mod['name']
        return module_id

    # ============================================================
    # 主题系统
    # ============================================================

    def apply_theme(self):
        """将颜色方案应用到所有组件"""
        colors = self.config.get_colors()

        # 根窗口背景
        self.configure(bg=colors['bg_main'])

        # 导航栏
        self.nav_outer.configure(bg=colors['bg_main'])
        self.nav_frame.configure(bg=colors['bg_main'])

        # 底部分隔线
        self.nav_separator.delete('all')
        self.nav_separator.configure(bg=colors['bg_main'], highlightbackground=colors['bg_main'])
        self.nav_separator.create_line(
            16, 1, self.nav_separator.winfo_width() or 1200, 1,
            fill=colors['border'], width=1
        )

        # 设置按钮
        self.settings_btn.configure(bg=colors['bg_main'], fg=colors['fg_muted'])

        # 导航按钮
        active_id = self.current_module
        for mid, btn in self.nav_buttons.items():
            if mid == active_id:
                btn.configure(bg=colors['bg_main'], fg=colors['fg_accent'])
            else:
                btn.configure(bg=colors['bg_main'], fg=colors['fg_secondary'])

        # 内容区域
        self.content_frame.configure(bg=colors['bg_main'])
        for frame in self.module_frames.values():
            frame.configure(bg=colors['bg_main'])
            for child in frame.winfo_children():
                try:
                    child.configure(bg=colors['bg_main'], fg=colors['fg_secondary'])
                except tk.TclError:
                    pass

        # 状态栏
        self.status_frame.configure(bg=colors['bg_sidebar'])
        self.status_label.configure(bg=colors['bg_sidebar'], fg=colors['fg_muted'])
        self.shortcut_hint.configure(bg=colors['bg_sidebar'], fg=colors['fg_muted'])

    # ============================================================
    # 快捷键
    # ============================================================

    def _bind_shortcuts(self):
        """绑定全局快捷键"""
        for i, mod in enumerate(MODULES, start=1):
            self.bind(f'<Control-Key-{i}>', lambda e, mid=mod['id']: self.switch_module(mid))
            self.bind(f'<Control-KP_{i}>', lambda e, mid=mod['id']: self.switch_module(mid))

        self.bind('<Control-Key-n>', self._on_new)
        self.bind('<Control-Key-N>', self._on_new)
        self.bind('<Control-Key-s>', self._on_save)
        self.bind('<Control-Key-S>', self._on_save)
        self.bind('<Control-Key-f>', self._on_search)
        self.bind('<Control-Key-F>', self._on_search)
        self.bind('<Control-Key-e>', self._on_export)
        self.bind('<Control-Key-E>', self._on_export)
        self.bind('<Control-comma>', self._on_settings)

    def _on_new(self, event=None):
        self.set_status(f'[Ctrl+N] 新建 —「{self._module_name(self.current_module)}」待实现')

    def _on_save(self, event=None):
        self.set_status(f'[Ctrl+S] 保存 —「{self._module_name(self.current_module)}」待实现')

    def _on_search(self, event=None):
        self.set_status(f'[Ctrl+F] 搜索 —「{self._module_name(self.current_module)}」待实现')

    def _on_export(self, event=None):
        self.set_status(f'[Ctrl+E] 导出 —「{self._module_name(self.current_module)}」待实现')

    def _on_settings(self, event=None):
        """打开设置对话框"""
        self._open_settings_dialog()

    # ============================================================
    # 设置对话框
    # ============================================================

    def _open_settings_dialog(self):
        """打开设置对话框（主题选择等）"""
        dialog = tk.Toplevel(self)
        dialog.title('设置')
        dialog.geometry('400x300')
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        colors = self.config.get_colors()
        dialog.configure(bg=colors['bg_main'])

        # 标题
        title = tk.Label(
            dialog,
            text='设置',
            font=(self.config.get('font_family'), 16, 'bold'),
            bg=colors['bg_main'],
            fg=colors['fg_primary'],
        )
        title.pack(pady=(20, 16))

        # 主题选择
        theme_label = tk.Label(
            dialog,
            text='主题模式',
            font=(self.config.get('font_family'), 12),
            bg=colors['bg_main'],
            fg=colors['fg_secondary'],
        )
        theme_label.pack(pady=(0, 8))

        theme_frame = tk.Frame(dialog, bg=colors['bg_main'])
        theme_frame.pack()

        current_mode = self.config.get_theme_mode()
        self._theme_var = tk.StringVar(value=current_mode)

        themes = [
            ('light',  '☀  亮色'),
            ('dark',   '🌙  暗色'),
            ('system', '🔄  跟随系统'),
        ]

        for mode, text in themes:
            rb = tk.Radiobutton(
                theme_frame,
                text=text,
                variable=self._theme_var,
                value=mode,
                font=(self.config.get('font_family'), 11),
                bg=colors['bg_main'],
                fg=colors['fg_primary'],
                selectcolor=colors['bg_sidebar'],
                activebackground=colors['bg_main'],
                activeforeground=colors['fg_accent'],
                cursor='hand2',
                anchor=tk.W,
            )
            rb.pack(fill=tk.X, pady=3)

        # 按钮区
        btn_frame = tk.Frame(dialog, bg=colors['bg_main'])
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=16)

        cancel_btn = tk.Button(
            btn_frame,
            text='取消',
            font=(self.config.get('font_family'), 11),
            bg=colors['bg_sidebar'],
            fg=colors['fg_primary'],
            relief=tk.FLAT,
            padx=20, pady=6,
            cursor='hand2',
            command=dialog.destroy,
        )
        cancel_btn.pack(side=tk.RIGHT, padx=(8, 0))

        save_btn = tk.Button(
            btn_frame,
            text='保存',
            font=(self.config.get('font_family'), 11),
            bg=colors['fg_accent'],
            fg='#ffffff',
            relief=tk.FLAT,
            padx=20, pady=6,
            cursor='hand2',
            command=lambda: self._save_settings(dialog),
        )
        save_btn.pack(side=tk.RIGHT)

    def _save_settings(self, dialog: tk.Toplevel):
        """保存设置并关闭对话框"""
        new_mode = self._theme_var.get()
        old_mode = self.config.get_theme_mode()
        self.config.set_theme_mode(new_mode)
        if new_mode != old_mode:
            self.apply_theme()
        dialog.destroy()
        self.set_status(f'设置已保存')

    # ============================================================
    # 工具方法
    # ============================================================

    def set_status(self, text: str):
        self.status_label.config(text=text)
        self.after(5000, lambda: self._restore_status(text))

    def _restore_status(self, expected_text: str):
        current = self.status_label.cget('text')
        if current == expected_text:
            self.status_label.config(text='')

    def _on_close(self):
        self.config.set('window_width', self.winfo_width())
        self.config.set('window_height', self.winfo_height())
        self.config.set('window_x', self.winfo_x())
        self.config.set('window_y', self.winfo_y())
        self.config.save()
        self.destroy()

    # ============================================================
    # 供各模块调用的接口
    # ============================================================

    def get_module_frame(self, module_id: str) -> tk.Frame:
        """获取指定模块的内容 Frame"""
        return self.module_frames.get(module_id)
