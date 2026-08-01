"""
统一弹窗基类
提供居中显示、ESC 关闭、主题适配等通用功能
"""
import tkinter as tk
from config import Config


class BaseDialog(tk.Toplevel):
    """弹窗基类，所有对话框继承此类"""
    
    def __init__(self, parent, title='', width=450, height=350):
        super().__init__(parent)
        self.config_obj = Config()
        colors = self.config_obj.get_colors()
        
        self.title(title)
        self.geometry(f'{width}x{height}')
        self.transient(parent)
        self.configure(bg=colors['bg_main'])
        
        # ESC 关闭
        self.bind('<Escape>', lambda e: self._on_close())
        
        # 居中显示
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - width) // 2
        y = parent.winfo_y() + (parent.winfo_height() - height) // 2
        self.geometry(f'+{x}+{y}')
        
        # 模态
        self.grab_set()
        
        self._build_content()
    
    def _build_content(self):
        """子类重写此方法来构建内容"""
        pass
    
    def _on_close(self):
        self.grab_release()
        self.destroy()
    
    def get_colors(self):
        return self.config_obj.get_colors()


class ConfirmDialog(BaseDialog):
    """确认对话框"""
    
    def __init__(self, parent, title='确认', message='确定要执行此操作吗？',
                 confirm_text='确定', cancel_text='取消', on_confirm=None):
        self._on_confirm = on_confirm
        self._message = message
        self._confirm_text = confirm_text
        self._cancel_text = cancel_text
        super().__init__(parent, title=title, width=380, height=180)
    
    def _build_content(self):
        colors = self.get_colors()
        
        tk.Label(self, text=self._message,
                 font=(self.config_obj.get('font_family'), 12),
                 bg=colors['bg_main'], fg=colors['fg_primary'],
                 wraplength=320, justify=tk.LEFT
                 ).pack(pady=(24, 16))
        
        btn_frame = tk.Frame(self, bg=colors['bg_main'])
        btn_frame.pack(fill=tk.X, padx=24, pady=(0, 16))
        
        tk.Button(btn_frame, text=self._cancel_text,
                  font=(self.config_obj.get('font_family'), 11),
                  bg=colors['bg_sidebar'], fg=colors['fg_primary'],
                  relief=tk.FLAT, padx=20, pady=6, cursor='hand2',
                  command=self._on_close
                  ).pack(side=tk.RIGHT, padx=(8, 0))
        
        tk.Button(btn_frame, text=self._confirm_text,
                  font=(self.config_obj.get('font_family'), 11),
                  bg=colors['fg_accent'], fg='#ffffff',
                  relief=tk.FLAT, padx=20, pady=6, cursor='hand2',
                  command=self._do_confirm
                  ).pack(side=tk.RIGHT)
    
    def _do_confirm(self):
        if self._on_confirm:
            self._on_confirm()
        self._on_close()


class InputDialog(BaseDialog):
    """输入对话框"""
    
    def __init__(self, parent, title='输入', label='请输入：', 
                 default_value='', on_submit=None):
        self._label = label
        self._default = default_value
        self._on_submit = on_submit
        self._entry_var = None
        super().__init__(parent, title=title, width=420, height=200)
    
    def _build_content(self):
        colors = self.get_colors()
        
        tk.Label(self, text=self._label,
                 font=(self.config_obj.get('font_family'), 11),
                 bg=colors['bg_main'], fg=colors['fg_secondary'],
                 anchor=tk.W
                 ).pack(fill=tk.X, padx=24, pady=(16, 4))
        
        self._entry_var = tk.StringVar(value=self._default)
        entry = tk.Entry(self, textvariable=self._entry_var,
                         font=(self.config_obj.get('font_family'), 12),
                         bg=colors['bg_input'], fg=colors['fg_primary'],
                         relief=tk.FLAT, bd=0)
        entry.pack(fill=tk.X, padx=24, pady=(0, 12), ipady=6)
        entry.focus_set()
        entry.bind('<Return>', lambda e: self._do_submit())
        
        btn_frame = tk.Frame(self, bg=colors['bg_main'])
        btn_frame.pack(fill=tk.X, padx=24, pady=(0, 16))
        
        tk.Button(btn_frame, text='取消',
                  font=(self.config_obj.get('font_family'), 11),
                  bg=colors['bg_sidebar'], fg=colors['fg_primary'],
                  relief=tk.FLAT, padx=20, pady=6, cursor='hand2',
                  command=self._on_close
                  ).pack(side=tk.RIGHT, padx=(8, 0))
        
        tk.Button(btn_frame, text='确定',
                  font=(self.config_obj.get('font_family'), 11),
                  bg=colors['fg_accent'], fg='#ffffff',
                  relief=tk.FLAT, padx=20, pady=6, cursor='hand2',
                  command=self._do_submit
                  ).pack(side=tk.RIGHT)
    
    def _do_submit(self):
        value = self._entry_var.get().strip() if self._entry_var else ''
        if self._on_submit:
            self._on_submit(value)
        self._on_close()
    
    def get_value(self):
        return self._entry_var.get().strip() if self._entry_var else ''
