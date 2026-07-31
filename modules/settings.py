"""
设置对话框
主题选择 + 洛谷 Cookie 配置
"""

import tkinter as tk
from tkinter import ttk

from config import Config


class SettingsDialog:

    def __init__(self, app):
        self.app = app
        self.config = Config()

        self.dialog = tk.Toplevel(app)
        self.dialog.title('设置')
        self.dialog.geometry('500x350')
        self.dialog.transient(app)
        self.dialog.resizable(False, False)
        colors = self.config.get_colors()
        self.dialog.configure(bg=colors['bg_main'])

        tk.Label(self.dialog, text='设置', font=(self.config.get('font_family'), 16, 'bold'),
                 bg=colors['bg_main'], fg=colors['fg_primary']).pack(pady=(14, 12))

        # 主题
        row1 = tk.Frame(self.dialog, bg=colors['bg_main'])
        row1.pack(fill=tk.X, padx=20, pady=(0, 10))
        tk.Label(row1, text='主题模式', font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_secondary']).pack(side=tk.LEFT)

        self.theme_var = tk.StringVar(value=self.config.get_theme_mode())
        for val, txt in [('system', '跟随系统'), ('light', '亮色'), ('dark', '暗色')]:
            tk.Radiobutton(row1, text=txt, variable=self.theme_var, value=val,
                           font=(self.config.get('font_family'), 10),
                           bg=colors['bg_main'], fg=colors['fg_primary'],
                           selectcolor=colors['bg_sidebar']).pack(side=tk.LEFT, padx=(12, 0))

        # 洛谷 Cookie
        tk.Label(self.dialog, text='洛谷 Cookie（用于搜索题目，可选）',
                 font=(self.config.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_secondary'], anchor=tk.W
                 ).pack(fill=tk.X, padx=20, pady=(8, 2))

        tk.Label(self.dialog, text='登录 luogu.com.cn 后从浏览器开发者工具复制',
                 font=(self.config.get('font_family'), 9),
                 bg=colors['bg_main'], fg=colors['fg_muted'], anchor=tk.W
                 ).pack(fill=tk.X, padx=20)

        self.cookie_text = tk.Text(self.dialog, font=(self.config.get('font_family'), 10),
                                    bg=colors['bg_input'], fg=colors['fg_primary'],
                                    relief=tk.FLAT, wrap=tk.WORD, height=4)
        self.cookie_text.pack(fill=tk.X, padx=20, pady=(4, 8))
        saved = self.config.get('luogu_cookie', '')
        if saved:
            self.cookie_text.insert('1.0', saved)

        # 按钮
        btn_row = tk.Frame(self.dialog, bg=colors['bg_main'])
        btn_row.pack(fill=tk.X, padx=20, pady=(4, 12))
        tk.Button(btn_row, text='取消', font=(self.config.get('font_family'), 11),
                  bg=colors['bg_sidebar'], fg=colors['fg_primary'],
                  relief=tk.FLAT, padx=16, pady=6,
                  command=self.dialog.destroy).pack(side=tk.RIGHT, padx=(8, 0))
        tk.Button(btn_row, text='保存', font=(self.config.get('font_family'), 11, 'bold'),
                  bg=colors['fg_accent'], fg='#ffffff', relief=tk.FLAT,
                  padx=20, pady=6, command=self._save).pack(side=tk.RIGHT)

    def _save(self):
        new_theme = self.theme_var.get()
        old_theme = self.config.get_theme_mode()

        self.config.set_theme_mode(new_theme)
        self.config.set('luogu_cookie', self.cookie_text.get('1.0', tk.END).strip())

        self.dialog.destroy()

        if new_theme != old_theme:
            self.app.apply_theme()

        self.app.set_status('设置已保存')
