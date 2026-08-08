"""
配置管理模块
负责：主题切换（亮色/暗色/跟随系统）、配置文件持久化、颜色方案定义、敏感数据加密存储
"""

import base64
import hashlib
import json
import os
import sys
import platform
import threading
import time
import uuid

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
# 敏感数据加密 —— Fernet 机器绑定密钥
# ============================================================
# 设计思路：
#   - 用 uuid.getnode()（网卡 MAC）+ os.getlogin()（当前用户名）作为机器指纹
#   - 经 PBKDF2-HMAC-SHA256 派生出固定长度的 Fernet 密钥
#   - 同一台机器、同一个用户能解密；换机器或换用户则无法解密（安全降级为空）
#   - 向后兼容：旧 base64 格式的值自动识别并迁移到新加密格式
_FERNET_KEY = None  # 延迟初始化，首次使用时计算


def _get_fernet_key() -> bytes:
    """
    派生机器绑定的 Fernet 密钥。
    密钥 = PBKDF2(MAC地址 + 用户名, salt="OI-Learn-Desktop", 迭代 100000)
    返回 URL-safe base64 编码的 32 字节密钥（Fernet 要求）。
    """
    global _FERNET_KEY
    if _FERNET_KEY is not None:
        return _FERNET_KEY

    # 收集机器指纹
    machine_id = str(uuid.getnode())          # 网卡 MAC 的整数表示
    try:
        user_id = os.getlogin()              # 当前登录用户名
    except Exception:
        user_id = "unknown"

    fingerprint = f"{machine_id}:{user_id}".encode("utf-8")

    # PBKDF2 派生 32 字节密钥（Fernet 需要 url-safe base64 编码的 32 字节）
    key = hashlib.pbkdf2_hmac(
        "sha256",
        fingerprint,
        salt=b"OI-Learn-Desktop-v1",       # 固定 salt，保证同机同用户结果一致
        iterations=100000,                    # 足够慢以抵抗暴力破解
        dklen=32,
    )
    import base64 as b64
    _FERNET_KEY = b64.urlsafe_b64encode(key)
    return _FERNET_KEY


def _encrypt_sensitive(plaintext: str) -> str:
    """用 Fernet 加密敏感字符串，返回 base64 编码的密文。"""
    if not plaintext:
        return ""
    from cryptography.fernet import Fernet
    f = Fernet(_get_fernet_key())
    return f.encrypt(plaintext.encode("utf-8")).decode("ascii")


def _decrypt_sensitive(ciphertext: str) -> str:
    """解密 Fernet 密文。解密失败时返回空字符串并记录日志。"""
    if not ciphertext:
        return ""
    try:
        from cryptography.fernet import Fernet
        f = Fernet(_get_fernet_key())
        return f.decrypt(ciphertext.encode("ascii"), ttl=None).decode("utf-8")
    except Exception:
        # 可能原因：换了机器/用户、数据被篡改、或仍是旧的 base64 格式
        from utils.logger import get_logger
        get_logger("config").warning(
            "Cookie 解密失败（可能换了机器或数据格式变更），将清空"
        )
        return ""


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

    'bg_card_shadow': '#E0DCF0',    # 卡片阴影色
    'nav_indicator': '#7C3AED',     # 导航指示条颜色

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
    'fg_muted': '#8A84A8',
    'fg_accent': '#A78BFA',
    'fg_accent_light': '#C4B5FD',
    'fg_link': '#A78BFA',
    'fg_on_accent': '#FFFFFF',

    'border': '#2E2850',
    'border_active': '#A78BFA',
    'border_card': '#262238',
    'scrollbar': '#3D3860',

    'bg_card_shadow': '#0A0910',    # 卡片阴影色
    'nav_indicator': '#A78BFA',     # 导航指示条颜色

    'success': '#34D399',
    'success_bg': '#064E3B',
    'warning': '#FBBF24',
    'warning_bg': '#78350F',
    'danger': '#F87171',
    'danger_bg': '#7F1D1D',
}


# 系统主题检测缓存
_system_theme_cache = None
_system_theme_checked = 0.0
_SYSTEM_THEME_TTL = 60  # 缓存有效期（秒）


def detect_system_theme() -> str:
    """
    检测操作系统当前使用的主题模式
    Windows: 读取注册表
    macOS: 读取 defaults
    Linux: 读取 gsettings（部分支持）
    返回 'light' 或 'dark'
    """
    global _system_theme_cache, _system_theme_checked
    now = time.time()
    if _system_theme_cache is not None and (now - _system_theme_checked) < _SYSTEM_THEME_TTL:
        return _system_theme_cache

    system = platform.system()
    result = 'light'
    try:
        if system == 'Windows':
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize'
            )
            apps_use_light, _ = winreg.QueryValueEx(key, 'AppsUseLightTheme')
            winreg.CloseKey(key)
            result = 'light' if apps_use_light == 1 else 'dark'

        elif system == 'Darwin':  # macOS
            import subprocess
            proc_result = subprocess.run(
                ['defaults', 'read', '-g', 'AppleInterfaceStyle'],
                capture_output=True, text=True
            )
            if 'Dark' in proc_result.stdout:
                result = 'dark'

        else:  # Linux / 其他
            result = 'light'
    except Exception:
        # 如果检测失败，默认返回亮色
        result = 'light'

    _system_theme_cache = result
    _system_theme_checked = now
    return result


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

        self._debounce_timers = {}
        self._lock = threading.Lock()
        self._load()

    # ---------- 持久化 ----------
    def _load(self):
        """从配置文件加载设置（合并所有保存的键，不限于默认列表）"""
        from utils.logger import get_logger
        _log = get_logger("config")
        path = get_settings_path()
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                # 合并所有保存的键到 _settings（已保存的键覆盖默认值，默认键保留)
                self._settings.update(saved)

                # 解密 luogu_cookie（支持新旧两种格式）
                if 'luogu_cookie' in self._settings and self._settings['luogu_cookie']:
                    raw = self._settings['luogu_cookie']
                    # 尝试 Fernet 解密（新格式）
                    decrypted = _decrypt_sensitive(raw)
                    if decrypted:
                        self._settings['luogu_cookie'] = decrypted
                    else:
                        # 回退：尝试旧 base64 格式（向后兼容）
                        try:
                            self._settings['luogu_cookie'] = base64.b64decode(
                                raw.encode()
                            ).decode()
                            _log.info("检测到旧格式 Cookie，已自动迁移（下次保存将加密）")
                        except Exception:
                            # 既非 Fernet 也非合法 base64，视为明文保持原样
                            pass
            except (json.JSONDecodeError, IOError) as e:
                _log.warning(f"配置文件加载失败: {e}")

    def save(self):
        """保存配置到文件"""
        from utils.logger import get_logger
        _log = get_logger("config")
        path = get_settings_path()
        try:
            # 对 luogu_cookie 进行 Fernet 加密后存储（机器绑定）
            settings_to_save = dict(self._settings)
            if settings_to_save.get('luogu_cookie'):
                settings_to_save['luogu_cookie'] = _encrypt_sensitive(
                    settings_to_save['luogu_cookie']
                )
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(settings_to_save, f, ensure_ascii=False, indent=2)
        except (IOError, TypeError) as e:
            _log.error(f"配置保存失败: {e}")

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
        """获取当前生效的颜色方案（返回副本，防止外部意外修改）"""
        theme = self.get_effective_theme()
        return dict(DARK_THEME if theme == 'dark' else LIGHT_THEME)

    # ---------- 通用存取 ----------
    def get(self, key: str, default=None):
        return self._settings.get(key, default)

    def set(self, key: str, value):
        with self._lock:
            self._settings[key] = value
        self.save()

    def set_debounced(self, key: str, value, delay_ms: int = 500):
        """防抖保存：延迟写入磁盘，高频调用时只保存最后一次"""
        with self._lock:
            self._settings[key] = value
        # 取消已存在的定时器
        if key in self._debounce_timers:
            self._debounce_timers[key].cancel()

        def _do_save(k):
            self.save()
            self._debounce_timers.pop(k, None)

        timer = threading.Timer(delay_ms / 1000.0, _do_save, args=[key])
        timer.daemon = True
        self._debounce_timers[key] = timer
        timer.start()
