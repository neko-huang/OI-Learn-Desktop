"""
配置管理模块
负责：主题切换（亮色/暗色/跟随系统）、配置文件持久化、颜色方案定义
"""

import json
import os
import sys
import platform

# ============================================================
# 路径工具 —— 所有路径都相对于程序所在目录
# ============================================================
def get_app_dir() -> str:
    """获取程序根目录（打包后指向 .exe 所在目录，开发时指向项目目录）"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后，sys.executable 是 .exe 路径
        return os.path.dirname(sys.executable)
    else:
        # 开发时，main.py 的上一级就是项目根目录
        return os.path.dirname(os.path.abspath(__file__))


def get_data_dir() -> str:
    """获取 data 目录，如果不存在则创建"""
    data_dir = os.path.join(get_app_dir(), 'data')
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def get_settings_path() -> str:
    """获取配置文件路径"""
    return os.path.join(get_data_dir(), 'settings.json')


# ============================================================
# 颜色方案定义
# ============================================================
# 亮色主题颜色
LIGHT_THEME = {
    'bg_main': '#ffffff',           # 主背景
    'bg_sidebar': '#f5f5f5',        # 侧边栏背景
    'bg_nav': '#e8e8e8',            # 导航栏背景
    'bg_nav_active': '#d0d0ff',     # 导航栏选中状态
    'bg_input': '#ffffff',          # 输入框背景
    'bg_code': '#f0f0f0',           # 代码块背景
    'bg_table_header': '#e8e8e8',   # 表头背景
    'bg_table_row_even': '#ffffff', # 表格偶数行
    'bg_table_row_odd': '#f8f8f8',  # 表格奇数行
    'bg_tag': '#e0e0ff',            # 标签背景

    'fg_primary': '#1a1a1a',        # 主文字
    'fg_secondary': '#555555',      # 次要文字
    'fg_muted': '#888888',          # 弱化文字
    'fg_accent': '#534AB7',         # 强调色（紫色）
    'fg_link': '#185FA5',           # 链接色

    'border': '#cccccc',            # 边框
    'border_active': '#534AB7',     # 选中边框
    'scrollbar': '#bbbbbb',         # 滚动条

    'success': '#3B6D11',           # 绿色（已完成）
    'warning': '#854F0B',           # 橙色（进行中）
    'danger': '#A32D2D',            # 红色（错误）
}

# 暗色主题颜色
DARK_THEME = {
    'bg_main': '#1e1e1e',
    'bg_sidebar': '#252526',
    'bg_nav': '#2d2d30',
    'bg_nav_active': '#3d3d6b',
    'bg_input': '#2d2d30',
    'bg_code': '#2d2d30',
    'bg_table_header': '#333333',
    'bg_table_row_even': '#1e1e1e',
    'bg_table_row_odd': '#252526',
    'bg_tag': '#3d3d6b',

    'fg_primary': '#cccccc',
    'fg_secondary': '#999999',
    'fg_muted': '#666666',
    'fg_accent': '#AFA9EC',
    'fg_link': '#85B7EB',

    'border': '#3e3e42',
    'border_active': '#AFA9EC',
    'scrollbar': '#555555',

    'success': '#97C459',
    'warning': '#FAC775',
    'danger': '#F09595',
}


def detect_system_theme() -> str:
    """
    检测操作系统当前使用的主题模式
    Windows: 读取注册表
    macOS: 读取 defaults
    Linux: 读取 gsettings（部分支持）
    返回 'light' 或 'dark'
    """
    system = platform.system()
    try:
        if system == 'Windows':
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize'
            )
            apps_use_light, _ = winreg.QueryValueEx(key, 'AppsUseLightTheme')
            winreg.CloseKey(key)
            return 'light' if apps_use_light == 1 else 'dark'

        elif system == 'Darwin':  # macOS
            import subprocess
            result = subprocess.run(
                ['defaults', 'read', '-g', 'AppleInterfaceStyle'],
                capture_output=True, text=True
            )
            if 'Dark' in result.stdout:
                return 'dark'
            return 'light'

        else:  # Linux / 其他
            return 'light'
    except Exception:
        # 如果检测失败，默认返回亮色
        return 'light'


# ============================================================
# 配置管理器
# ============================================================
class Config:
    """应用配置管理器，单例模式"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # 默认配置
        self._settings = {
            'theme_mode': 'system',         # 'light' | 'dark' | 'system'
            'window_width': 1200,
            'window_height': 800,
            'window_x': None,               # 窗口 X 位置（None = 居中）
            'window_y': None,
            'font_family': 'Microsoft YaHei' if platform.system() == 'Windows' else 'sans-serif',
            'font_size': 11,
            'code_font_family': 'Consolas' if platform.system() == 'Windows' else 'monospace',
            'code_font_size': 11,
        }

        self._load()

    # ---------- 持久化 ----------
    def _load(self):
        """从配置文件加载设置"""
        path = get_settings_path()
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                # 只合并已知配置项，防止脏数据
                for key in self._settings:
                    if key in saved:
                        self._settings[key] = saved[key]
            except (json.JSONDecodeError, IOError):
                # 配置文件损坏或无法读取，使用默认值
                pass

    def save(self):
        """保存配置到文件"""
        path = get_settings_path()
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"[配置] 保存失败: {e}")

    # ---------- 主题相关 ----------
    def get_theme_mode(self) -> str:
        return self._settings['theme_mode']

    def set_theme_mode(self, mode: str):
        """设置主题模式：'light' | 'dark' | 'system'"""
        if mode not in ('light', 'dark', 'system'):
            raise ValueError(f"不支持的主题模式: {mode}")
        self._settings['theme_mode'] = mode
        self.save()

    def get_effective_theme(self) -> str:
        """获取实际生效的主题（解析 'system' → 'light'/'dark'）"""
        mode = self._settings['theme_mode']
        if mode == 'system':
            return detect_system_theme()
        return mode

    def get_colors(self) -> dict:
        """获取当前生效的颜色方案"""
        theme = self.get_effective_theme()
        return DARK_THEME if theme == 'dark' else LIGHT_THEME

    # ---------- 通用存取 ----------
    def get(self, key: str, default=None):
        return self._settings.get(key, default)

    def set(self, key: str, value):
        self._settings[key] = value
        self.save()
