"""
Markdown 渲染引擎
负责：Markdown → HTML 转换，含代码语法高亮、数学公式渲染、主题适配

技术路线：
  - markdown 库：核心 Markdown → HTML 转换
  - Pygments：代码块语法高亮，生成内联 CSS 的 <pre> 块
  - 数学公式：$...$ 内联公式处理（用 HTML/CSS 模拟样式）
  - 完全不依赖 Node.js / KaTeX JS，保证便携性
"""

import re
import markdown
from markdown.extensions import fenced_code, codehilite, tables, toc


def _render_math_inline(match: re.Match, dark: bool = False) -> str:
    """
    处理 $...$ 内联数学公式
    用带样式的 span 包装，使用数学专用字体和浅色背景
    """
    latex = match.group(1).strip()
    # 简单美化：移除多余空格
    latex = re.sub(r'\s+', ' ', latex)
    if dark:
        return (
            f'<span class="math-inline" '
            f'style="font-family: \'Cambria Math\', \'STIX Two Math\', \'Latin Modern Math\', Georgia, serif; '
            f'font-style:italic; '
            f'background:rgba(175, 169, 236, 0.15); '
            f'color:#C4BEF0; '
            f'padding:1px 5px; '
            f'border-radius:3px; '
            f'white-space:nowrap;'
            f'">{latex}</span>'
        )
    return (
        f'<span class="math-inline" '
        f'style="font-family: \'Cambria Math\', \'STIX Two Math\', \'Latin Modern Math\', Georgia, serif; '
        f'font-style:italic; '
        f'background:rgba(83, 74, 183, 0.08); '
        f'color:#534AB7; '
        f'padding:1px 5px; '
        f'border-radius:3px; '
        f'white-space:nowrap;'
        f'">{latex}</span>'
    )


def _render_math_block(match: re.Match, dark: bool = False) -> str:
    """
    处理 $$...$$ 块级数学公式
    渲染为居中、带背景的高亮块，使用数学专用字体
    """
    latex = match.group(1).strip()
    # 对换行和空格做简单清理
    lines = [l.strip() for l in latex.split('\n') if l.strip()]
    latex = ' \\\\ '.join(lines)
    if dark:
        return (
            f'<div class="math-block" style="'
            f'text-align:center; '
            f'padding:20px 16px; '
            f'margin:16px 0; '
            f'background:#2A2545; '
            f'border:1px solid #3E3860; '
            f'border-radius:8px; '
            f'font-family: \'Cambria Math\', \'STIX Two Math\', \'Latin Modern Math\', Georgia, serif; '
            f'font-size:17px; '
            f'font-style:italic; '
            f'color:#C4BEF0; '
            f'line-height:1.6; '
            f'overflow-x:auto;'
            f'">{latex}</div>'
        )
    return (
        f'<div class="math-block" style="'
        f'text-align:center; '
        f'padding:20px 16px; '
        f'margin:16px 0; '
        f'background:#F5F0FF; '
        f'border:1px solid #E8E0F5; '
        f'border-radius:8px; '
        f'font-family: \'Cambria Math\', \'STIX Two Math\', \'Latin Modern Math\', Georgia, serif; '
        f'font-size:17px; '
        f'font-style:italic; '
        f'color:#3C3489; '
        f'line-height:1.6; '
        f'overflow-x:auto;'
        f'">{latex}</div>'
    )


def _preprocess_math(text: str, dark: bool = False) -> tuple:
    """
    预处理：在 Markdown 渲染之前，保护数学公式不被 Markdown 解析器破坏
    策略：先替换为占位符，Markdown 渲染后再换回来
    """
    # 用占位符保护公式
    placeholders = []

    # 1. 块级公式 $$...$$
    def save_block(match):
        placeholders.append(_render_math_block(match, dark=dark))
        return f'\u0000MATHBLOCK{len(placeholders)-1}\u0000'

    text = re.sub(r'\$\$(.+?)\$\$', save_block, text, flags=re.DOTALL)

    # 2. 内联公式 $...$
    def save_inline(match):
        # 跳过 $$ 的情况（已在上面处理）
        content = match.group(1)
        if content.strip():
            placeholders.append(_render_math_inline(match, dark=dark))
            return f'\u0000MATHINLINE{len(placeholders)-1}\u0000'
        return match.group(0)

    text = re.sub(r'\$(.+?)\$', save_inline, text)

    return text, placeholders


def _restore_math(html: str, placeholders: list) -> str:
    """将占位符替换回渲染后的数学公式 HTML"""
    for i, ph in enumerate(placeholders):
        html = html.replace(f'\u0000MATHBLOCK{i}\u0000', ph)
        html = html.replace(f'\u0000MATHINLINE{i}\u0000', ph)
    return html


def render_markdown(md_text: str, theme: str = 'light') -> str:
    """
    将 Markdown 文本渲染为完整 HTML

    参数：
        md_text: Markdown 源文本
        theme: 'light' 或 'dark'，影响代码高亮样式

    返回：
        完整的 HTML 字符串（可直接放入 HtmlFrame）
    """
    if not md_text:
        return '<p></p>'

    # 1. 预处理数学公式
    text, placeholders = _preprocess_math(md_text, dark=(theme == 'dark'))

    # 2. Markdown → HTML
    extensions = [
        'fenced_code',     # ``` 代码块
        'tables',          # 表格支持
    ]

    # 代码高亮扩展
    extension_configs = {
        'fenced_code': {},
    }

    # 使用 Pygments 做代码高亮
    md = markdown.Markdown(
        extensions=extensions,
        extension_configs=extension_configs,
    )

    html_body = md.convert(text)

    # 3. 手动处理代码块高亮（因为 markdown.codehilite 需要额外配置）
    html_body = _highlight_code_blocks(html_body, theme)

    # 4. 恢复数学公式
    html_body = _restore_math(html_body, placeholders)

    # 5. 组装完整 HTML 页面
    full_html = _build_html_page(html_body, theme)

    return full_html


def _highlight_code_blocks(html: str, theme: str = 'light') -> str:
    """
    用 Pygments 为 <pre><code> 块添加语法高亮
    """
    try:
        from pygments import highlight
        from pygments.lexers import get_lexer_by_name, guess_lexer
        from pygments.formatters import HtmlFormatter

        # 获取 Pygments CSS（内联样式更好兼容 tkinterweb）
        formatter = HtmlFormatter(
            noclasses=True,       # 使用内联样式而非 CSS 类
            style='default' if theme == 'light' else 'monokai',
        )

        def replace_code_block(match):
            # group(1)=语言, group(2)=代码内容
            lang = match.group(1) or ''
            code = match.group(2) or ''

            # 尝试按指定语言高亮
            try:
                if lang:
                    lexer = get_lexer_by_name(lang, stripall=True)
                else:
                    lexer = guess_lexer(code)
            except Exception:
                # 如果无法识别，用纯文本
                from pygments.lexers import TextLexer
                lexer = TextLexer()

            highlighted = highlight(code, lexer, formatter)
            return highlighted

        # 匹配 <pre><code> 或 <pre><code class="language-xxx">
        html = re.sub(
            r'<pre><code(?:\s+class="language-(\w+)")?>(.*?)</code></pre>',
            replace_code_block,
            html,
            flags=re.DOTALL,
        )

    except ImportError:
        pass  # 如果 Pygments 不可用，保持原样

    return html


def _build_html_page(body: str, theme: str = 'light') -> str:
    """
    将 HTML body 包装成完整页面，添加主题样式
    """
    if theme == 'dark':
        bg = '#1e1e1e'
        fg = '#cccccc'
        code_bg = '#2d2d30'
        border = '#3e3e42'
        link = '#85B7EB'
        heading = '#AFA9EC'
    else:
        bg = '#ffffff'
        fg = '#1a1a1a'
        code_bg = '#f5f5f5'
        border = '#e0e0e0'
        link = '#185FA5'
        heading = '#534AB7'

    html = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{
    font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
    font-size: 14px;
    line-height: 1.8;
    color: {fg};
    background: {bg};
    margin: 16px 20px;
    padding: 0;
  }}
  h1 {{ font-size: 22px; color: {heading}; margin: 20px 0 12px; border-bottom: 1px solid {border}; padding-bottom: 6px; }}
  h2 {{ font-size: 18px; color: {heading}; margin: 16px 0 10px; }}
  h3 {{ font-size: 15px; color: {heading}; margin: 14px 0 8px; }}
  h4 {{ font-size: 14px; color: {fg}; margin: 12px 0 6px; }}
  p {{ margin: 8px 0; }}
  ul, ol {{ padding-left: 24px; margin: 8px 0; }}
  li {{ margin: 4px 0; }}
  a {{ color: {link}; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  code {{
    font-family: "Consolas", "Courier New", monospace;
    font-size: 13px;
    background: {code_bg};
    padding: 2px 5px;
    border-radius: 3px;
  }}
  pre {{
    background: {code_bg};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 12px 16px;
    overflow-x: auto;
    font-size: 13px;
    line-height: 1.5;
    margin: 10px 0;
  }}
  pre code {{
    background: none;
    padding: 0;
    border-radius: 0;
  }}
  table {{
    border-collapse: collapse;
    width: 100%;
    margin: 10px 0;
  }}
  th, td {{
    border: 1px solid {border};
    padding: 8px 12px;
    text-align: left;
  }}
  th {{
    background: {code_bg};
    font-weight: 500;
  }}
  blockquote {{
    border-left: 3px solid {heading};
    padding: 6px 14px;
    margin: 10px 0;
    background: {code_bg};
    border-radius: 0 6px 6px 0;
  }}
  hr {{ border: none; border-top: 1px solid {border}; margin: 16px 0; }}
  img {{ max-width: 100%; }}
  .math-inline {{ }}
  .math-block {{ }}
</style>
</head>
<body>
{body}
</body>
</html>'''

    return html


def render_markdown_plain(md_text: str) -> str:
    """
    将 Markdown 渲染为纯文本（不包含 HTML 标签）
    用于搜索、预览等场景
    """
    # 最简单的方式：移除所有 Markdown 语法标记
    text = md_text
    # 移除代码块
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    # 移除标题符号
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # 移除加粗/斜体
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    # 移除行内代码
    text = re.sub(r'`(.+?)`', r'\1', text)
    # 移除链接 [...](...)
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
    # 移除图片
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    # 移除数学公式
    text = re.sub(r'\$\$.*?\$\$', '', text, flags=re.DOTALL)
    text = re.sub(r'\$(.+?)\$', r'\1', text)
    # 合并多余空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()
