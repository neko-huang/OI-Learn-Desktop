"""
增强搜索框组件
支持搜索图标、placeholder 文字、清除按钮、聚焦高亮
"""
import tkinter as tk
from config import Config


class SearchBar(tk.Frame):
    """增强搜索框：搜索图标 + placeholder + 清除按钮"""
    
    def __init__(self, parent, placeholder='搜索...', on_change=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.config_obj = Config()
        self._placeholder = placeholder
        self._on_change = on_change
        self._has_focus = False
        self._has_text = False
        
        colors = self.config_obj.get_colors()
        self.configure(bg=colors['bg_input'])
        
        # 搜索图标
        self._search_icon = tk.Label(self, text='🔍',
                                      font=(self.config_obj.get('font_family'), 10),
                                      bg=colors['bg_input'], fg=colors['fg_muted'],
                                      padx=(8, 2))
        self._search_icon.pack(side=tk.LEFT)
        
        # 输入框
        self._var = tk.StringVar()
        self._entry = tk.Entry(self, textvariable=self._var,
                                font=(self.config_obj.get('font_family'), 11),
                                bg=colors['bg_input'], fg=colors['fg_primary'],
                                relief=tk.FLAT, bd=0, insertbackground=colors['fg_primary'])
        self._entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)
        
        # 清除按钮
        self._clear_btn = tk.Label(self, text='✕',
                                    font=(self.config_obj.get('font_family'), 9),
                                    bg=colors['bg_input'], fg=colors['fg_muted'],
                                    cursor='hand2', padx=(2, 8))
        # 初始不显示清除按钮
        # self._clear_btn.pack(side=tk.RIGHT)
        
        # 绑定事件
        self._var.trace_add('write', self._on_text_change)
        self._entry.bind('<FocusIn>', self._on_focus_in)
        self._entry.bind('<FocusOut>', self._on_focus_out)
        self._clear_btn.bind('<Button-1>', self._clear_text)
        
        # 显示 placeholder
        self._show_placeholder()
    
    def _show_placeholder(self):
        """显示 placeholder 文字"""
        colors = self.config_obj.get_colors()
        self._entry.delete(0, tk.END)
        self._entry.insert(0, self._placeholder)
        self._entry.configure(fg=colors['fg_muted'])
        self._has_text = False
    
    def _hide_placeholder(self):
        """隐藏 placeholder"""
        colors = self.config_obj.get_colors()
        self._entry.delete(0, tk.END)
        self._entry.configure(fg=colors['fg_primary'])
        self._has_text = True
    
    def _on_text_change(self, *args):
        text = self._var.get()
        if text == self._placeholder:
            return
        
        # 显示/隐藏清除按钮
        if text and text != self._placeholder:
            if not self._clear_btn.winfo_ismapped():
                self._clear_btn.pack(side=tk.RIGHT)
        else:
            self._clear_btn.pack_forget()
        
        if self._on_change and self._has_text:
            self._on_change(text)
    
    def _on_focus_in(self, event):
        self._has_focus = True
        if not self._has_text:
            self._hide_placeholder()
    
    def _on_focus_out(self, event):
        self._has_focus = False
        text = self._var.get()
        if not text:
            self._show_placeholder()
    
    def _clear_text(self, event=None):
        self._var.set('')
        self._show_placeholder()
        self._entry.focus_set()
        if self._on_change:
            self._on_change('')
    
    def get(self) -> str:
        """获取当前输入文本"""
        text = self._var.get()
        if text == self._placeholder:
            return ''
        return text
    
    def set(self, text: str):
        """设置文本"""
        if text:
            colors = self.config_obj.get_colors()
            self._entry.configure(fg=colors['fg_primary'])
            self._has_text = True
        self._var.set(text)
    
    def focus(self):
        """聚焦输入框"""
        self._entry.focus_set()
    
    @property
    def var(self):
        return self._var
