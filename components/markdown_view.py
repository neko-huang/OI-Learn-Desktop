"""
Markdown 视图组件
基于 tkinterweb.HtmlFrame，将 Markdown 渲染为可交互的 HTML 视图

使用方式：
    view = MarkdownView(parent)
    view.render("# Hello\n\nThis is **markdown**.")
"""

import tkinter as tk
from tkinter import ttk
from tkinterweb import HtmlFrame

from config import Config
from services.markdown_engine import render_markdown


class MarkdownView(tk.Frame):
    """
    Markdown 渲染视图组件
    封装 HtmlFrame，自动处理主题适配、滚动、内容更新
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        self.config = Config()
        self._markdown_text = ''

        # --- HtmlFrame（HTML 渲染核心） ---
        self.html_frame = HtmlFrame(
            self,
            messages_enabled=False,  # 不显示 HtmlFrame 自己的调试消息
        )
        self.html_frame.pack(fill=tk.BOTH, expand=True)

        # 初始渲染空内容
        self._render_html('')

    # ============================================================
    # 公共接口
    # ============================================================

    def render(self, markdown_text: str):
        """
        渲染 Markdown 文本
        如果文本没变则跳过渲染（性能优化）
        """
        if markdown_text == self._markdown_text:
            return

        self._markdown_text = markdown_text or ''
        self._render_html(self._markdown_text)

    def clear(self):
        """清空视图"""
        self._markdown_text = ''
        self._render_html('')

    def apply_theme(self):
        """响应主题切换，重新渲染当前内容"""
        if self._markdown_text:
            self._render_html(self._markdown_text)

    # ============================================================
    # 内部方法
    # ============================================================

    def _render_html(self, md_text: str):
        """将 Markdown 转换为 HTML 并加载到 HtmlFrame"""
        theme = self.config.get_effective_theme()

        if md_text:
            html = render_markdown(md_text, theme=theme)
        else:
            html = self._empty_html(theme)

        try:
            self.html_frame.load_html(html)
        except Exception:
            # 如果 HtmlFrame 加载失败，显示纯文本后备
            self._fallback_display(md_text, theme)

    def _empty_html(self, theme: str) -> str:
        """生成空内容占位 HTML"""
        if theme == 'dark':
            return '<html><body style="background:#1e1e1e;color:#666;"></body></html>'
        return '<html><body style="background:#fff;color:#999;"></body></html>'

    def _fallback_display(self, md_text: str, theme: str):
        """HtmlFrame 失败时的纯文本后备方案"""
        fg = '#cccccc' if theme == 'dark' else '#1a1a1a'
        bg = '#1e1e1e' if theme == 'dark' else '#ffffff'
        escaped = (md_text
                   .replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('\n', '<br>'))
        fallback = f'<html><body style="background:{bg};color:{fg};padding:16px;"><pre>{escaped}</pre></body></html>'
        self.html_frame.load_html(fallback)
