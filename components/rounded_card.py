"""
圆角卡片组件
使用 Canvas 绘制圆角矩形背景，支持主题适配
"""
import tkinter as tk
from config import Config


class RoundedCard(tk.Frame):
    """圆角卡片容器，内部可放置任意子组件"""
    
    def __init__(self, parent, radius=12, bg_color=None, border_color=None, 
                 border_width=1, padding=16, **kwargs):
        self.config_obj = Config()
        colors = self.config_obj.get_colors()
        
        self._radius = radius
        self._bg_color = bg_color or colors['bg_card']
        self._border_color = border_color or colors['border_card']
        self._border_width = border_width
        self._padding = padding
        
        # 外层 Frame（透明，用于 pack/grid 布局）
        super().__init__(parent, bg=parent.cget('bg') if hasattr(parent, 'cget') else colors['bg_main'], **kwargs)
        
        # Canvas 绘制圆角背景
        self._canvas = tk.Canvas(self, bg=self._get_parent_bg(), 
                                  highlightthickness=0, borderwidth=0)
        self._canvas.pack(fill=tk.BOTH, expand=True)
        
        # 内部内容 Frame
        self._inner = tk.Frame(self._canvas, bg=self._bg_color)
        self._canvas_window = None
        
        # 绑定事件
        self._canvas.bind('<Configure>', self._on_configure)
    
    def _get_parent_bg(self):
        try:
            return self.master.cget('bg')
        except:
            return self.config_obj.get_colors()['bg_main']
    
    def _draw_rounded_rect(self, width, height):
        """在 Canvas 上绘制圆角矩形"""
        self._canvas.delete('all')
        r = self._radius
        bg = self._bg_color
        border = self._border_color
        bw = self._border_width
        
        # 绘制圆角矩形
        points = [
            r, 0, width-r, 0,
            width, 0, width, r,
            width, height-r, width-r, height,
            r, height, 0, height-r,
            0, r, 0, 0
        ]
        
        # 填充
        self._canvas.create_polygon(points, fill=bg, outline=border, 
                                     smooth=True, width=bw)
        
        # 更新内部 Frame 位置和大小
        inner_x = self._padding
        inner_y = self._padding
        inner_w = width - 2 * self._padding
        inner_h = height - 2 * self._padding
        
        if self._canvas_window:
            self._canvas.coords(self._canvas_window, inner_x, inner_y)
            self._canvas.itemconfig(self._canvas_window, width=inner_w, height=inner_h)
        else:
            self._canvas_window = self._canvas.create_window(
                inner_x, inner_y, window=self._inner, anchor=tk.NW,
                width=inner_w, height=inner_h
            )
    
    def _on_configure(self, event):
        self._draw_rounded_rect(event.width, event.height)
    
    def get_inner(self) -> tk.Frame:
        """获取内部内容 Frame，往里面放子组件"""
        return self._inner
    
    def update_colors(self, bg_color=None, border_color=None):
        """更新颜色（主题切换时调用）"""
        if bg_color:
            self._bg_color = bg_color
        if border_color:
            self._border_color = border_color
        self._canvas.configure(bg=self._get_parent_bg())
        self._inner.configure(bg=self._bg_color)
        w = self._canvas.winfo_width()
        h = self._canvas.winfo_height()
        if w > 1 and h > 1:
            self._draw_rounded_rect(w, h)


class ShadowCard(tk.Frame):
    """带阴影效果的卡片（简化版：底部偏移绘制阴影）"""
    
    def __init__(self, parent, radius=10, shadow_color=None, bg_color=None,
                 shadow_offset=3, padding=14, **kwargs):
        self.config_obj = Config()
        colors = self.config_obj.get_colors()
        
        self._radius = radius
        self._shadow_color = shadow_color or ('#D0CCE0' if colors['bg_main'] != '#13111A' else '#0A0910')
        self._bg_color = bg_color or colors['bg_card']
        self._shadow_offset = shadow_offset
        self._padding = padding
        
        super().__init__(parent, bg=parent.cget('bg') if hasattr(parent, 'cget') else colors['bg_main'], **kwargs)
        
        self._canvas = tk.Canvas(self, bg=self._get_parent_bg(),
                                  highlightthickness=0, borderwidth=0)
        self._canvas.pack(fill=tk.BOTH, expand=True)
        
        self._inner = tk.Frame(self._canvas, bg=self._bg_color)
        self._canvas_window = None
        self._canvas.bind('<Configure>', self._on_configure)
    
    def _get_parent_bg(self):
        try:
            return self.master.cget('bg')
        except:
            return self.config_obj.get_colors()['bg_main']
    
    def _draw(self, width, height):
        self._canvas.delete('all')
        r = self._radius
        off = self._shadow_offset
        so = self._shadow_offset
        
        # 阴影
        shadow_points = [
            r, so, width-r+so, so,
            width+so, so, width+so, r+so,
            width+so, height-r+so, width-r+so, height+so,
            r, height+so, 0-so, height-r+so,
            0-so, r+so, 0-so, so
        ]
        self._canvas.create_polygon(shadow_points, fill=self._shadow_color, 
                                     outline='', smooth=True)
        
        # 卡片
        card_points = [
            r, 0, width-r, 0,
            width, 0, width, r,
            width, height-r, width-r, height,
            r, height, 0, height-r,
            0, r, 0, 0
        ]
        self._canvas.create_polygon(card_points, fill=self._bg_color,
                                     outline='', smooth=True)
        
        # 内部 Frame
        inner_x = self._padding
        inner_y = self._padding
        inner_w = max(1, width - 2 * self._padding)
        inner_h = max(1, height - 2 * self._padding)
        
        if self._canvas_window:
            self._canvas.coords(self._canvas_window, inner_x, inner_y)
            self._canvas.itemconfig(self._canvas_window, width=inner_w, height=inner_h)
        else:
            self._canvas_window = self._canvas.create_window(
                inner_x, inner_y, window=self._inner, anchor=tk.NW,
                width=inner_w, height=inner_h
            )
    
    def _on_configure(self, event):
        self._draw(event.width, event.height)
    
    def get_inner(self) -> tk.Frame:
        return self._inner
    
    def update_colors(self, bg_color=None, shadow_color=None):
        if bg_color:
            self._bg_color = bg_color
        if shadow_color:
            self._shadow_color = shadow_color
        self._canvas.configure(bg=self._get_parent_bg())
        self._inner.configure(bg=self._bg_color)
        w = self._canvas.winfo_width()
        h = self._canvas.winfo_height()
        if w > 1 and h > 1:
            self._draw(w, h)
