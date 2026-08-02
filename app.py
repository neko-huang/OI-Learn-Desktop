"""
主应用窗口
负责：顶部导航栏、7 模块切换、主题应用、全局快捷键、内容区域管理
"""

import tkinter as tk
from tkinter import ttk
from config import Config
from db.database import initialize_database, migrate
from db.seed import seed_database


MODULES = [
    {'id': 'home',         'name': '首页',   'shortcut': 'Ctrl+1'},
    {'id': 'outline',      'name': '大纲',   'shortcut': 'Ctrl+2'},
    {'id': 'encyclopedia', 'name': '百科',   'shortcut': 'Ctrl+3'},
    {'id': 'problems',     'name': '刷题',   'shortcut': 'Ctrl+4'},
    {'id': 'templates',    'name': '模板',   'shortcut': 'Ctrl+5'},
    {'id': 'mistakes',     'name': '易错集', 'shortcut': 'Ctrl+6'},
    {'id': 'plan',         'name': '练习',   'shortcut': 'Ctrl+7'},
    {'id': 'stats',        'name': '统计',   'shortcut': 'Ctrl+8'},
]

# 模块懒加载注册表：模块ID → (导入路径, 类名)
_MODULE_LOADER = {
    'home':         ('modules.home',         'HomeModule'),
    'outline':      ('modules.outline',      'OutlineModule'),
    'encyclopedia': ('modules.encyclopedia', 'EncyclopediaModule'),
    'problems':     ('modules.problems',     'ProblemsModule'),
    'templates':    ('modules.templates',    'TemplatesModule'),
    'mistakes':     ('modules.mistakes',     'MistakesModule'),
    'plan':         ('modules.plan',         'PlanModule'),
    'stats':        ('modules.stats',        'StatsModule'),
}


class App(tk.Tk):
    """主应用窗口"""

    def __init__(self):
        super().__init__()

        self.config = Config()
        self.title('InfoLearn — 信息学学习助手')
        self.geometry(self._geometry_string())
        self.minsize(900, 600)

        # 设置窗口图标
        self._set_window_icon()

        self.protocol('WM_DELETE_WINDOW', self._on_close)
        self.current_module = None

        # 已加载的模块实例（懒加载）
        self._loaded_modules = {}

        # 先构建 UI，让窗口尽快显示
        self._setup_style()
        self._build_nav_bar()
        self._build_content_area()
        self._build_status_bar()
        self.apply_theme()
        self._bind_shortcuts()

        # 延迟执行重量级操作：数据库初始化 + 首页加载
        # 避免阻塞 mainloop 启动导致窗口迟迟不显示
        self.after(100, self._deferred_init)

        self.lift()
        self.focus_force()

    def _set_window_icon(self):
        """设置窗口图标"""
        import os
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'app_icon.png')
        if os.path.exists(icon_path):
            try:
                icon = tk.PhotoImage(file=icon_path)
                self.iconphoto(True, icon)
                self._icon_ref = icon  # 保持引用防止被 GC
            except Exception:
                pass

    def _deferred_init(self):
        """延迟初始化：数据库 + 种子数据 + 首页加载（窗口已显示后执行）"""
        import threading
        self.set_status('正在初始化数据库...')

        def _init_db():
            try:
                initialize_database()
                migrate()
                seed_msg = seed_database()
                self.after(0, lambda: self._on_db_ready(seed_msg))
            except Exception as e:
                self.after(0, lambda: self.set_status(f'数据库初始化异常: {e}'))

        threading.Thread(target=_init_db, daemon=True).start()

    def _on_db_ready(self, seed_msg):
        """数据库初始化完成后的回调"""
        # 只在未切换到任何模块时才切到首页
        # 避免打断用户已主动导航到的模块
        if self.current_module is None:
            self.switch_module('home')
        if seed_msg:
            self.set_status(seed_msg)

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
        """顶部导航栏 — 现代风格"""
        colors = self.config.get_colors()
        self.nav_outer = tk.Frame(self, bg=colors['bg_nav'], height=50)
        self.nav_outer.pack(side=tk.TOP, fill=tk.X)
        self.nav_outer.pack_propagate(False)

        self.nav_frame = tk.Frame(self.nav_outer, bg=colors['bg_nav'], height=50)
        self.nav_frame.pack(fill=tk.BOTH, expand=True)
        self.nav_frame.pack_propagate(False)

        left_pad = tk.Frame(self.nav_frame, bg=colors['bg_nav'], width=16)
        left_pad.pack(side=tk.LEFT)

        self.nav_buttons = {}
        self._nav_indicator_frames = {}  # 指示条容器
        self._nav_containers = {}  # 导航按钮容器
        for mod in MODULES:
            btn_container = tk.Frame(self.nav_frame, bg=colors['bg_nav'], cursor='hand2')
            btn_container.pack(side=tk.LEFT)
            self._nav_containers[mod['id']] = btn_container

            # 底部指示条 — 先 pack 在底部，z-order 在 Label 之下，不会遮挡点击
            indicator_frame = tk.Frame(btn_container, bg=colors['nav_indicator'], height=3)
            indicator_frame.pack(fill=tk.X, side=tk.BOTTOM)
            indicator_frame.pack_propagate(False)
            indicator_frame.pack_forget()  # 初始隐藏
            self._nav_indicator_frames[mod['id']] = indicator_frame

            btn = tk.Label(
                btn_container, text=mod['name'],
                font=(self.config.get('font_family'), 12),
                cursor='hand2', padx=16, pady=12,
                bg=colors['bg_nav'], fg=colors['fg_secondary'],
            )
            btn.pack()
            self.nav_buttons[mod['id']] = btn

            # 点击事件直接绑定在 Label 上（Tkinter 子控件事件不会冒泡到父 Frame）
            # ⚠️ 注意：<Button-1> 和 <ButtonPress-1> 是同一个事件，不能同时绑定
            # 否则第二个会覆盖第一个，导致 switch_module 不触发
            mid = mod['id']
            btn.bind('<Button-1>', lambda e, m=mid: self.switch_module(m))
            btn.bind('<ButtonRelease-1>', lambda e, b=btn: b.configure(fg=self.config.get_colors()['fg_accent']))
            btn.bind('<Enter>', lambda e, b=btn, m=mid: self._nav_hover_enter(m, b))
            btn.bind('<Leave>', lambda e, b=btn, m=mid: self._nav_hover_leave(m, b))
            # 指示条也响应点击，消除底部 3px 盲区
            indicator_frame.bind('<Button-1>', lambda e, m=mid: self.switch_module(m))

        spacer = tk.Frame(self.nav_frame, bg=colors['bg_nav'])
        spacer.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.settings_btn = tk.Label(
            self.nav_frame, text='\u2699',
            font=(self.config.get('font_family'), 18),
            cursor='hand2', padx=12, pady=10,
            bg=colors['bg_nav'], fg=colors['fg_muted'],
        )
        self.settings_btn.pack(side=tk.RIGHT, padx=(0, 12))
        self.settings_btn.bind('<Button-1>', self._on_settings)
        self.settings_btn.bind('<Enter>', lambda e: self.settings_btn.configure(fg=self.config.get_colors()['fg_accent']))
        self.settings_btn.bind('<Leave>', lambda e: self.settings_btn.configure(fg=self.config.get_colors()['fg_muted']))

        # 底部细线
        self.nav_sep = tk.Frame(self.nav_outer, bg=colors['border'], height=1)
        self.nav_sep.pack(side=tk.BOTTOM, fill=tk.X)

    def _nav_hover_enter(self, module_id, btn):
        """鼠标进入导航按钮区域"""
        colors = self.config.get_colors()
        active = getattr(self, '_active_module', None)
        if module_id != active:
            btn.configure(fg=colors['fg_accent'])

    def _nav_hover_leave(self, module_id, btn):
        """鼠标离开导航按钮区域"""
        colors = self.config.get_colors()
        active = getattr(self, '_active_module', None)
        if module_id == active:
            btn.configure(fg=colors['fg_accent'])
        else:
            btn.configure(fg=colors['fg_secondary'])

    def _update_nav_active(self):
        """更新导航栏选中状态（含指示条动画效果）"""
        colors = self.config.get_colors()
        active = getattr(self, '_active_module', 'home')
        for mid, btn in self.nav_buttons.items():
            indicator_frame = self._nav_indicator_frames.get(mid)
            if mid == active:
                btn.configure(fg=colors['fg_accent'], font=(self.config.get('font_family'), 12, 'bold'))
                if indicator_frame:
                    indicator_frame.pack(fill=tk.X, side=tk.BOTTOM)
            else:
                btn.configure(fg=colors['fg_secondary'], font=(self.config.get('font_family'), 12))
                if indicator_frame:
                    indicator_frame.pack_forget()

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
        """切换到指定模块，首次访问时懒加载"""
        if module_id not in self.module_frames:
            return

        # 通知当前模块即将离开（自动保存等）
        if self.current_module and self.current_module in self._loaded_modules:
            module = self._loaded_modules[self.current_module]
            if hasattr(module, 'on_before_leave'):
                module.on_before_leave()

        # 懒加载：首次切换时初始化模块
        if module_id not in self._loaded_modules:
            self._load_module(module_id)

        # 隐藏当前模块
        if self.current_module and self.current_module in self.module_frames:
            self.module_frames[self.current_module].pack_forget()

        # 显示新模块
        self.module_frames[module_id].pack(fill=tk.BOTH, expand=True)

        # 更新导航按钮样式
        self._update_nav_style(module_id)

        self.current_module = module_id
        self.set_status(f'已切换到「{self._module_name(module_id)}」')

    def _load_module(self, module_id: str):
        """懒加载模块类并实例化"""
        loader_info = _MODULE_LOADER.get(module_id)
        if not loader_info:
            self.set_status(f'模块「{self._module_name(module_id)}」尚未实现')
            return

        import_path, class_name = loader_info
        frame = self.module_frames[module_id]
        try:
            mod = __import__(import_path, fromlist=[class_name])
            cls = getattr(mod, class_name)
            # 清除占位内容
            for w in frame.winfo_children():
                w.destroy()
            # 实例化模块
            instance = cls(self, frame)
            self._loaded_modules[module_id] = instance
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.set_status(f'加载模块失败: {e}')
            # 在 frame 中显示错误提示，避免空白页面
            for w in frame.winfo_children():
                w.destroy()
            colors = self.config.get_colors()
            err_frame = tk.Frame(frame, bg=colors['bg_main'])
            err_frame.pack(fill=tk.BOTH, expand=True)
            tk.Label(err_frame, text=f'⚠️ 模块加载失败',
                     font=(self.config.get('font_family'), 16, 'bold'),
                     bg=colors['bg_main'], fg=colors['danger']).pack(pady=(40, 8))
            tk.Label(err_frame, text=str(e),
                     font=(self.config.get('font_family'), 11),
                     bg=colors['bg_main'], fg=colors['fg_secondary'],
                     wraplength=500, justify=tk.LEFT).pack(pady=4, padx=20)
            tk.Label(err_frame, text='请检查依赖是否安装完整，或查看控制台日志',
                     font=(self.config.get('font_family'), 10),
                     bg=colors['bg_main'], fg=colors['fg_muted']).pack(pady=4)

    def _update_nav_style(self, active_id: str):
        """更新导航按钮样式"""
        self._active_module = active_id
        self._update_nav_active()

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
        self.nav_outer.configure(bg=colors['bg_nav'])
        self.nav_frame.configure(bg=colors['bg_nav'])
        self.nav_sep.configure(bg=colors['border'])
        for w in self.nav_frame.winfo_children():
            try: w.configure(bg=colors['bg_nav'])
            except: pass
        # 更新导航按钮容器、按钮标签和指示条
        for mid, btn in self.nav_buttons.items():
            container = self._nav_containers.get(mid)
            if container:
                container.configure(bg=colors['bg_nav'])
            btn.configure(bg=colors['bg_nav'])
            indicator_frame = self._nav_indicator_frames.get(mid)
            if indicator_frame:
                indicator_frame.configure(bg=colors['nav_indicator'])
        self.settings_btn.configure(bg=colors['bg_nav'], fg=colors['fg_muted'])
        self._update_nav_active()

        # 内容区域
        self.content_frame.configure(bg=colors['bg_main'])
        for frame in self.module_frames.values():
            frame.configure(bg=colors['bg_main'])

        # 状态栏
        self.status_frame.configure(bg=colors['bg_sidebar'])
        self.status_label.configure(bg=colors['bg_sidebar'], fg=colors['fg_muted'])
        self.shortcut_hint.configure(bg=colors['bg_sidebar'], fg=colors['fg_muted'])

        # 已加载模块的主题更新
        for module_instance in self._loaded_modules.values():
            if hasattr(module_instance, 'apply_theme'):
                module_instance.apply_theme()

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
        self._delegate_to_module('on_new') or \
            self.set_status(f'[Ctrl+N] 新建 —「{self._module_name(self.current_module)}」待实现')

    def _on_save(self, event=None):
        self._delegate_to_module('on_save') or \
            self.set_status(f'[Ctrl+S] 保存 —「{self._module_name(self.current_module)}」待实现')

    def _on_search(self, event=None):
        self._delegate_to_module('on_search') or \
            self.set_status(f'[Ctrl+F] 搜索 —「{self._module_name(self.current_module)}」待实现')

    def _on_export(self, event=None):
        self._delegate_to_module('on_export') or \
            self.set_status(f'[Ctrl+E] 导出 —「{self._module_name(self.current_module)}」待实现')

    def _delegate_to_module(self, method_name: str) -> bool:
        """将事件委托给当前模块的对应方法，返回 True 表示已处理"""
        if self.current_module and self.current_module in self._loaded_modules:
            module = self._loaded_modules[self.current_module]
            if hasattr(module, method_name):
                getattr(module, method_name)()
                return True
        return False

    def _on_settings(self, event=None):
        """打开设置对话框"""
        self._open_settings_dialog()

    # ============================================================
    # 设置对话框
    # ============================================================

    def _open_settings_dialog(self):
        """打开设置对话框（主题 + 洛谷 Cookie）"""
        from modules.settings import SettingsDialog
        SettingsDialog(self)

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
        # 通知当前模块（自动保存等）
        for module in self._loaded_modules.values():
            if hasattr(module, 'on_before_leave'):
                module.on_before_leave()
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
