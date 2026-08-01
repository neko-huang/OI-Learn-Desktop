"""
代码编辑器组件（占位模块）
为 PyInstaller 打包提供模块引用
后续可扩展为带语法高亮的代码编辑器
"""
import tkinter as tk
from config import Config


class CodeEditor(tk.Frame):
    """代码编辑器组件（基础版本）"""
    
    def __init__(self, parent, language='cpp', **kwargs):
        super().__init__(parent, **kwargs)
        self.config_obj = Config()
        self._language = language
        
        colors = self.config_obj.get_colors()
        self.configure(bg=colors['bg_input'])
        
        # 行号区域
        self._line_numbers = tk.Text(self, width=4,
                                      font=(self.config_obj.get('code_font_family'), 
                                            self.config_obj.get('code_font_size', 11)),
                                      bg=colors['bg_sidebar'], fg=colors['fg_muted'],
                                      relief=tk.FLAT, state=tk.DISABLED,
                                      padx=4, pady=4)
        self._line_numbers.pack(side=tk.LEFT, fill=tk.Y)
        
        # 代码编辑区
        self._code_text = tk.Text(self,
                                   font=(self.config_obj.get('code_font_family'),
                                         self.config_obj.get('code_font_size', 11)),
                                   bg=colors['bg_input'], fg=colors['fg_primary'],
                                   relief=tk.FLAT, wrap=tk.NONE, undo=True,
                                   padx=8, pady=4)
        self._code_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 滚动条
        from tkinter import ttk
        scroll_y = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self._code_text.yview)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self._code_text.configure(yscrollcommand=scroll_y.set)
        
        scroll_x = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self._code_text.xview)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self._code_text.configure(xscrollcommand=scroll_x.set)
        
        # 绑定行号更新
        self._code_text.bind('<KeyRelease>', self._update_line_numbers)
        self._code_text.bind('<MouseWheel>', self._update_line_numbers)
    
    def _update_line_numbers(self, event=None):
        """更新行号"""
        lines = self._code_text.get('1.0', tk.END).count('\n')
        self._line_numbers.configure(state=tk.NORMAL)
        self._line_numbers.delete('1.0', tk.END)
        for i in range(1, lines + 1):
            self._line_numbers.insert(tk.END, f'{i}\n')
        self._line_numbers.configure(state=tk.DISABLED)
    
    def get_code(self) -> str:
        return self._code_text.get('1.0', tk.END).strip()
    
    def set_code(self, code: str):
        self._code_text.delete('1.0', tk.END)
        self._code_text.insert('1.0', code)
        self._update_line_numbers()
    
    def set_language(self, language: str):
        self._language = language
