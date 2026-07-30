"""
主应用窗口
负责：顶部导航栏、7 模块切换、主题应用、全局快捷键、内容区域管理
"""

import tkinter as tk
from tkinter import ttk
from config import Config, get_data_dir


# ============================================================
# 模块定义 —— 7 个模块的名称、图标和快捷键
# ============================================================
MODULES = [
    {'id': 'outline',     'name': '大纲',  'shortcut': 'Ctrl+1'},
    {'id': 'encyclopedia','name': '百科',  'shortcut': 'Ctrl+2'},
    {'id': 'problems',    'name': '刷题',  'shortcut': 'Ctrl+3'},
    {'id': 'templates',   'name': '模板',  'shortcut': 'Ctrl+4'},
    {'id': 'mistakes',    'name': '易错集','shortcut': 'Ctrl+5'},
    {'id': 'plan',        'name': '计划',  'shortcut': 'Ctrl+6'},
    {'id': 'stats',       'name': '统计',  'shortcut': 'Ctrl+7'},
]


class App(tk.Tk):
    """主应用窗口"""

    def __init__(self):
        super().__init__()

        # ---------- 基础设置 ----------
        self.config = Config()
        self.title('InfoLearn — 信息学学习助手')
        self.geometry(self._geometry_string())

        # 窗口关闭时保存配置
        self.protocol('WM_DELETE_WINDOW', self._on_close)

        # 当前激活的模块
        self.current_module = None

        # ---------- 构建 UI ----------
        self._build_nav_bar()
        self._build_content_area()
        self._build_status_bar()

        # ---------- 应用主题 ----------
        self.apply_theme()

        # ---------- 绑定快捷键 ----------
        self._bind_shortcuts()

        # ---------- 默认打开第一个模块 ----------
        self.switch_module('outline')

        # ---------- 让窗口获得焦点 ----------
        self.lift()
        self.focus_force()

    # ============================================================
    # 布局构建
    # ============================================================

    def _geometry_string(self) -> str:
        """生成窗口几何字符串"""
        w = self.config.get('window_width', 1200)
        h = self.config.get('window_height', 800)
        x = self.config.get('window_x')
        y = self.config.get('window_y')
        if x is not None and y is not None:
            return f'{w}x{h}+{x}+{y}'
        return f'{w}x{h}'

    def _build_nav_bar(self):
        """构建顶部导航栏 —— 7 个模块按钮 + 主题切换按钮"""
        self.nav_frame = tk.Frame(self, height=44)
        self.nav_frame.pack(side=tk.TOP, fill=tk.X)
        self.nav_frame.pack_propagate(False)

        # 模块按钮
        self.nav_buttons = {}
        for i, mod in enumerate(MODULES):
            btn = tk.Button(
                self.nav_frame,
                text=f'  {mod["name"]}  ',
                font=(self.config.get('font_family'), 11),
                relief=tk.FLAT,
                bd=0,
                padx=12, pady=8,
                cursor='hand2',
                command=lambda mid=mod['id']: self.switch_module(mid),
            )
            btn.pack(side=tk.LEFT, padx=(0, 2), pady=4)
            self.nav_buttons[mod['id']] = btn

        # 右侧弹簧 —— 把主题按钮推到最右边
        spacer = tk.Frame(self.nav_frame)
        spacer.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 主题切换按钮
        self.theme_var = tk.StringVar(value=self._theme_indicator())
        self.theme_btn = tk.Button(
            self.nav_frame,
            textvariable=self.theme_var,
            font=(self.config.get('font_family'), 11),
            relief=tk.FLAT,
            bd=0,
            padx=10, pady=8,
            cursor='hand2',
            command=self._cycle_theme,
        )
        self.theme_btn.pack(side=tk.RIGHT, padx=(0, 8), pady=4)

    def _build_content_area(self):
        """构建内容区域 —— 使用 ttk.Notebook 作为子标签容器"""
        self.content_frame = tk.Frame(self)
        self.content_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Notebook 用于各模块内部的子标签页
        self.content_notebook = ttk.Notebook(self.content_frame)
        self.content_notebook.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))

        # 为每个模块创建欢迎页（占位，后续替换为实际内容）
        self.module_frames = {}
        for mod in MODULES:
            frame = tk.Frame(self.content_notebook)
            self.content_notebook.add(frame, text=mod['name'])
            self.module_frames[mod['id']] = frame

            # 占位文字
            placeholder = tk.Label(
                frame,
                text=f'「{mod["name"]}」模块\n\n功能开发中...',
                font=(self.config.get('font_family'), 16),
            )
            placeholder.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    def _build_status_bar(self):
        """构建底部状态栏"""
        self.status_frame = tk.Frame(self, height=24)
        self.status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_frame.pack_propagate(False)

        self.status_label = tk.Label(
            self.status_frame,
            text='就绪',
            font=(self.config.get('font_family'), 9),
            anchor=tk.W,
        )
        self.status_label.pack(side=tk.LEFT, padx=8)

    # ============================================================
    # 模块切换
    # ============================================================

    def switch_module(self, module_id: str):
        """切换到指定模块"""
        if module_id not in self.module_frames:
            return

        # 更新导航按钮样式
        for mid, btn in self.nav_buttons.items():
            if mid == module_id:
                btn.config(state=tk.DISABLED)
                btn.config(relief=tk.SUNKEN)
            else:
                btn.config(state=tk.NORMAL)
                btn.config(relief=tk.FLAT)

        # 切换内容区域
        frame = self.module_frames[module_id]
        self.content_notebook.select(frame)

        self.current_module = module_id
        self.set_status(f'已切换到「{self._module_name(module_id)}」模块')

    def _module_name(self, module_id: str) -> str:
        """根据 ID 获取模块中文名"""
        for mod in MODULES:
            if mod['id'] == module_id:
                return mod['name']
        return module_id

    # ============================================================
    # 主题系统
    # ============================================================

    def apply_theme(self):
        """将当前颜色方案应用到所有组件"""
        colors = self.config.get_colors()

        # 根窗口
        self.configure(bg=colors['bg_main'])

        # 导航栏
        self.nav_frame.configure(bg=colors['bg_nav'])
        for mid, btn in self.nav_buttons.items():
            btn.configure(
                bg=colors['bg_nav'],
                fg=colors['fg_primary'],
                activebackground=colors['bg_nav_active'],
                activeforeground=colors['fg_primary'],
            )
            # 当前激活模块的特殊样式
            if mid == self.current_module:
                btn.configure(
                    bg=colors['bg_nav_active'],
                    fg=colors['fg_accent'],
                )

        # 主题切换按钮
        self.theme_btn.configure(
            bg=colors['bg_nav'],
            fg=colors['fg_muted'],
            activebackground=colors['bg_nav_active'],
            activeforeground=colors['fg_primary'],
        )

        # 内容区域
        self.content_frame.configure(bg=colors['bg_main'])

        # 每个模块的占位 frame
        for frame in self.module_frames.values():
            frame.configure(bg=colors['bg_main'])
            for child in frame.winfo_children():
                try:
                    child.configure(bg=colors['bg_main'], fg=colors['fg_secondary'])
                except tk.TclError:
                    pass

        # 状态栏
        self.status_frame.configure(bg=colors['bg_sidebar'])
        self.status_label.configure(
            bg=colors['bg_sidebar'],
            fg=colors['fg_muted'],
        )

        # 更新主题指示器
        self.theme_var.set(self._theme_indicator())

    def _theme_indicator(self) -> str:
        """获取主题指示器文字"""
        mode = self.config.get_theme_mode()
        if mode == 'system':
            actual = self.config.get_effective_theme()
            return f' 跟随系统 ({actual}) '
        elif mode == 'dark':
            return ' 暗色 '
        else:
            return ' 亮色 '

    def _cycle_theme(self):
        """循环切换主题模式：亮色 → 暗色 → 跟随系统 → 亮色"""
        current = self.config.get_theme_mode()
        next_theme = {
            'light': 'dark',
            'dark': 'system',
            'system': 'light',
        }
        new_mode = next_theme.get(current, 'light')
        self.config.set_theme_mode(new_mode)
        self.apply_theme()
        self.set_status(f'主题已切换为：{self._theme_indicator().strip()}')

    # ============================================================
    # 快捷键
    # ============================================================

    def _bind_shortcuts(self):
        """绑定全局快捷键"""
        # Ctrl+1~7: 切换模块
        for i, mod in enumerate(MODULES, start=1):
            self.bind(f'<Control-Key-{i}>', lambda e, mid=mod['id']: self.switch_module(mid))
            # 小键盘也支持
            self.bind(f'<Control-KP_{i}>', lambda e, mid=mod['id']: self.switch_module(mid))

        # Ctrl+N: 新建（根据当前模块，后续各模块实现具体逻辑）
        self.bind('<Control-Key-n>', self._on_new)
        self.bind('<Control-Key-N>', self._on_new)

        # Ctrl+S: 保存
        self.bind('<Control-Key-s>', self._on_save)
        self.bind('<Control-Key-S>', self._on_save)

        # Ctrl+F: 搜索
        self.bind('<Control-Key-f>', self._on_search)
        self.bind('<Control-Key-F>', self._on_search)

        # Ctrl+E: 导出
        self.bind('<Control-Key-e>', self._on_export)
        self.bind('<Control-Key-E>', self._on_export)

        # Ctrl+,: 打开设置
        self.bind('<Control-comma>', self._on_settings)

    def _on_new(self, event=None):
        self.set_status(f'[Ctrl+N] 新建 — 模块「{self._module_name(self.current_module)}」待实现')

    def _on_save(self, event=None):
        self.set_status(f'[Ctrl+S] 保存 — 模块「{self._module_name(self.current_module)}」待实现')

    def _on_search(self, event=None):
        self.set_status(f'[Ctrl+F] 搜索 — 模块「{self._module_name(self.current_module)}」待实现')

    def _on_export(self, event=None):
        self.set_status(f'[Ctrl+E] 导出 — 模块「{self._module_name(self.current_module)}」待实现')

    def _on_settings(self, event=None):
        self.set_status('[Ctrl+,] 设置 — 待实现')

    # ============================================================
    # 工具方法
    # ============================================================

    def set_status(self, text: str):
        """设置状态栏文字"""
        self.status_label.config(text=text)
        # 5 秒后自动恢复为"就绪"（仅当没有被其他消息覆盖时）
        self.after(5000, lambda: self._restore_status(text))

    def _restore_status(self, expected_text: str):
        """如果状态栏文字没有被修改，恢复为默认"""
        current = self.status_label.cget('text')
        if current == expected_text:
            self.status_label.config(text='就绪')

    def _on_close(self):
        """窗口关闭时的处理"""
        # 保存窗口大小和位置
        self.config.set('window_width', self.winfo_width())
        self.config.set('window_height', self.winfo_height())
        self.config.set('window_x', self.winfo_x())
        self.config.set('window_y', self.winfo_y())
        self.config.save()
        self.destroy()

    # ============================================================
    # 供各模块调用的接口 —— 获取当前模块的容器 Frame
    # ============================================================

    def get_module_frame(self, module_id: str) -> tk.Frame:
        """获取指定模块的内容 Frame，供各模块在此 Frame 内构建 UI"""
        return self.module_frames.get(module_id)

    def get_content_notebook(self) -> ttk.Notebook:
        """获取内容区的 Notebook（供模块创建子标签页）"""
        return self.content_notebook
