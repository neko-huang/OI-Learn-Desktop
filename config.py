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
    'bg_main': '#F5F2FF',           # 主背景 浅紫白
    'bg_sidebar': '#F0ECFF',        # 侧边/面板 淡紫
    'bg_card': '#FFFFFF',           # 卡片背景
    'bg_nav': '#FFFFFF',            # 导航栏纯白
    'bg_nav_active': '#7C3AED',     # 导航选中 深紫
    'bg_nav_hover': '#F3EEFF',      # 导航悬停
    'bg_input': '#FFFFFF',          # 输入框
    'bg_code': '#F8F5FF',           # 代码块
    'bg_table_header': '#EDE9FE',   # 表头 淡紫
    'bg_table_row_even': '#FFFFFF',
    'bg_table_row_odd': '#FAF8FF',
    'bg_tag': '#EDE9FE',            # 标签
    'bg_tag_active': '#7C3AED',     # 标签选中
    'bg_progress': '#EDE9FE',       # 进度条底色

    'fg_primary': '#1E1B2E',        # 主文字 深紫黑
    'fg_secondary': '#6B6590',      # 次要文字
    'fg_muted': '#9B96B5',          # 弱化文字
    'fg_accent': '#7C3AED',         # 强调色 紫色
    'fg_accent_light': '#A78BFA',   # 浅紫
    'fg_link': '#5B3FCF',           # 链接色
    'fg_on_accent': '#FFFFFF',      # 强调色上文字

    'border': '#E5E0F0',            # 细边框
    'border_active': '#7C3AED',
    'border_card': '#EFEBFC',       # 卡片边框
    'scrollbar': '#CDCAE0',

    'success': '#059669',           # 翠绿
    'success_bg': '#ECFDF5',
    'warning': '#D97706',           # 琥珀
    'warning_bg': '#FFFBEB',
    'danger': '#DC2626',            # 红
    'danger_bg': '#FEF2F2',
}

DARK_THEME = {
    'bg_main': '#13111A',
    'bg_sidebar': '#1A1725',
    'bg_card': '#1E1B2E',
    'bg_nav': '#1A1725',
    'bg_nav_active': '#7C3AED',
    'bg_nav_hover': '#262238',
    'bg_input': '#1E1B2E',
    'bg_code': '#1A1725',
    'bg_table_header': '#262238',
    'bg_table_row_even': '#1E1B2E',
    'bg_table_row_odd': '#1A1725',
    'bg_tag': '#2E2550',
    'bg_tag_active': '#7C3AED',
    'bg_progress': '#262238',

    'fg_primary': '#E8E4F0',
    'fg_secondary': '#A9A0C0',
    'fg_muted': '#6B6590',
    'fg_accent': '#A78BFA',
    'fg_accent_light': '#C4B5FD',
    'fg_link': '#A78BFA',
    'fg_on_accent': '#FFFFFF',

    'border': '#2E2850',
    'border_active': '#A78BFA',
    'border_card': '#262238',
    'scrollbar': '#3D3860',

    'success': '#34D399',
    'success_bg': '#064E3B',
    'warning': '#FBBF24',
    'warning_bg': '#78350F',
    'danger': '#F87171',
    'danger_bg': '#7F1D1D',
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
            # 运行时写入的额外键（默认值确保存在）
            'last_checkin_date': '',
            'checkin_streak': 0,
            'luogu_cookie': '',
            'home_note': '',
            'study_plan': '[]',
        }

        self._load()

    # ---------- 持久化 ----------
    def _load(self):
        """从配置文件加载设置（合并所有保存的键，不限于默认列表）"""
        path = get_settings_path()
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                # 合并所有保存的键到 _settings
                self._settings.update(saved)
                # 确保默认键存在
                for key in list(self._settings.keys()):
                    if key not in saved and key not in self._settings:
                        pass  # 保持默认值
            except (json.JSONDecodeError, IOError):
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
