"""
Markdown 渲染引擎
负责：Markdown → HTML 转换，含代码语法高亮、数学公式渲染、主题适配

技术路线：
  - markdown 库：核心 Markdown → HTML 转换
  - Pygments：代码块语法高亮，生成内联 CSS 的 <pre> 块
  - 数学公式（默认分支，离线零依赖）：把 $...$ / $$...$$ 里的内容
        先做「LaTeX 命令 → Unicode」转换（\\frac \\sqrt \\sum … 都能识别），
        再用「数学专用字体 + 浅色背景」的 span/div 包装显示。
        内容本身是 Unicode（√、∑ 等）时基本原样保留，只顺手美化。
  - 真实 KaTeX（可选，默认关闭）：assets/katex/ 已本地化打包，不依赖 CDN。
        但 tkinterweb 的 HtmlFrame 默认不执行 JS，需开启 ENABLE_KATEX_JS
        并安装 pythonmonkey 后端后才会启用，详见 ENABLE_KATEX_JS 注释。
"""

import os
import re
import markdown
from markdown.extensions import fenced_code, codehilite, tables, toc
from config import get_app_dir


# 是否启用「本地 KaTeX 真实渲染」。
# ⚠️ 重要前提：tkinterweb 的 HtmlFrame 默认【不执行 JavaScript】
#    （javascript_enabled 默认 False，且需要额外安装 pythonmonkey 后端才能跑 JS）。
#    因此把 katex.min.js 注入 <script> 默认不会运行，
#    renderMathInElement 不会触发，$...$ 会原样显示成文本（反而更难看）。
# 当前渲染走下面的「字体模拟」分支：离线、零依赖，U 盘直接能用，
# 且已支持把常见 LaTeX 命令（\frac \sqrt \sum …）转成 Unicode 显示。
# 若日后确实要真实 KaTeX 排版：
#   1) pip install pythonmonkey
#   2) 在 components/markdown_view.py 创建 HtmlFrame 时设 javascript_enabled=True
#   3) 把下面这个开关改成 True
# 届时本引擎会自动改用 assets/katex/ 里的本地 KaTeX 资源渲染，无需任何 CDN。
ENABLE_KATEX_JS = False

# 常见 LaTeX 数学命令 → Unicode 的映射（仅用于「字体模拟」离线降级显示）
_LATEX_UNICODE = [
    # 先处理内层 \sqrt，再处理 \frac，避免 \frac 的参数里带花括号时匹配失败
    (r'\\sqrt\{([^{}]*)\}', r'√(\1)'),
    (r'\\frac\{([^{}]*)\}\{([^{}]*)\}', r'(\1)/(\2)'),
    (r'\\cdot', '·'), (r'\\times', '×'), (r'\\div', '÷'),
    (r'\\pm', '±'), (r'\\mp', '∓'),
    (r'\\leq|\\le', '≤'), (r'\\geq|\\ge', '≥'),
    (r'\\neq|\\ne', '≠'), (r'\\approx', '≈'), (r'\\equiv', '≡'),
    (r'\\sum', '∑'), (r'\\int', '∫'), (r'\\prod', '∏'),
    (r'\\infty', '∞'), (r'\\partial', '∂'), (r'\\nabla', '∇'),
    (r'\\alpha', 'α'), (r'\\beta', 'β'), (r'\\gamma', 'γ'), (r'\\delta', 'δ'),
    (r'\\theta', 'θ'), (r'\\lambda', 'λ'), (r'\\mu', 'μ'), (r'\\pi', 'π'),
    (r'\\sigma', 'σ'), (r'\\phi', 'φ'), (r'\\omega', 'ω'),
    (r'\\Delta', 'Δ'), (r'\\Theta', 'Θ'), (r'\\Lambda', 'Λ'), (r'\\Pi', 'Π'),
    (r'\\Sigma', 'Σ'), (r'\\Phi', 'Φ'), (r'\\Omega', 'Ω'),
    (r'\\rightarrow|\\Rightarrow|\\to|\\longrightarrow', '→'),
    (r'\\leftarrow', '←'),
    (r'\\in', '∈'), (r'\\notin', '∉'), (r'\\subset', '⊂'), (r'\\subseteq', '⊆'),
    (r'\\forall', '∀'), (r'\\exists', '∃'), (r'\\cup', '∪'), (r'\\cap', '∩'),
    (r'\\emptyset', '∅'),
    (r'\\mathbb\{R\}', 'ℝ'), (r'\\mathbb\{N\}', 'ℕ'), (r'\\mathbb\{Z\}', 'ℤ'),
    (r'\\mathbb\{Q\}', 'ℚ'), (r'\\mathbb\{C\}', 'ℂ'),
    (r'\\left', ''), (r'\\right', ''),
    (r'\\\{', '{'), (r'\\\}', '}'),
    (r'\\,|\\;|\\ ', ' '),
]

# 上下标用的 Unicode 字符（让 x^2、a_n 这类更美观）
_SUP = {'0':'⁰','1':'¹','2':'²','3':'³','4':'⁴','5':'⁵','6':'⁶','7':'⁷','8':'⁸','9':'⁹',
        '+':'⁺','-':'⁻','n':'ⁿ','i':'ⁱ',')':')'}
_SUB = {'0':'₀','1':'₁','2':'₂','3':'₃','4':'₄','5':'₅','6':'₆','7':'₇','8':'₈','9':'₉',
        '+':'₊','-':'₋','n':'ₙ','i':'ᵢ',')':')'}


def _latex_to_unicode(latex: str) -> str:
    """
    把常见 LaTeX 数学写法转成 Unicode，用于「没有 JS 引擎」时的离线降级显示。
    内容本来就是 Unicode（√、∑ 等）时基本原样保留，只是顺手清理命令、处理上下标。
    """
    s = latex
    for pat, repl in _LATEX_UNICODE:
        s = re.sub(pat, repl, s)
    # 上标 ^x / ^{...}
    s = re.sub(r'\^\{([^{}]*)\}', lambda m: ''.join(_SUP.get(c, c) for c in m.group(1)), s)
    s = re.sub(r'\^(\w)', lambda m: _SUP.get(m.group(1), m.group(0)), s)
    # 下标 _x / _{...}
    s = re.sub(r'_\{([^{}]*)\}', lambda m: ''.join(_SUB.get(c, c) for c in m.group(1)), s)
    s = re.sub(r'_(\w)', lambda m: _SUB.get(m.group(1), m.group(0)), s)
    return s


def _render_math_inline(content: str, dark: bool = False) -> str:
    """
    处理 $...$ 内联数学公式（字体模拟分支）
    把内容转成 Unicode 后用带样式的 span 包装，使用数学专用字体
    """
    text = _latex_to_unicode(content.strip())
    text = re.sub(r'\s+', ' ', text)
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
            f'">{text}</span>'
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
        f'">{text}</span>'
    )


def _render_math_block(content: str, dark: bool = False) -> str:
    """
    处理 $$...$$ 块级数学公式（字体模拟分支）
    渲染为居中、带背景的高亮块，使用数学专用字体
    """
    text = _latex_to_unicode(content.strip())
    # 对换行和空格做简单清理
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    text = ' '.join(lines)
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
            f'">{text}</div>'
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
        f'">{text}</div>'
    )


def _katex_asset_urls() -> dict:
    """
    返回本地 vendored KaTeX 资源的 file:// URL。
    资源缺失（例如未下载或未打包）时返回 None，调用方应降级为字体模拟。
    """
    kdir = os.path.join(get_app_dir(), 'assets', 'katex')
    js = os.path.join(kdir, 'katex.min.js')
    css = os.path.join(kdir, 'katex.min.css')
    auto = os.path.join(kdir, 'contrib', 'auto-render.min.js')
    if not (os.path.exists(js) and os.path.exists(css) and os.path.exists(auto)):
        return None
    # Windows 路径反斜杠转为正斜杠，构造 file:/// 绝对路径
    to_url = lambda p: 'file:///' + p.replace('\\', '/')
    return {'css': to_url(css), 'js': to_url(js), 'auto': to_url(auto)}


def _preprocess_math(text: str, dark: bool = False) -> tuple:
    """
    预处理：在 Markdown 渲染之前，保护数学公式不被 Markdown 解析器破坏
    策略：占位符中同时保存「原始 $...$ 文本」和「字体模拟 HTML」，
          后续根据是否启用 KaTeX 决定还原成哪种形式。
    """
    # 用占位符保护公式
    placeholders = []

    # 1. 块级公式 $$...$$
    def save_block(match):
        latex = match.group(1)
        placeholders.append({
            'raw': f'$${latex}$$',                       # 交给 KaTeX 渲染
            'sim': _render_math_block(latex, dark=dark),  # 降级：字体模拟
        })
        return f'\u0000MATHBLOCK{len(placeholders)-1}\u0000'

    text = re.sub(r'\$\$(.+?)\$\$', save_block, text, flags=re.DOTALL)

    # 2. 内联公式 $...$
    def save_inline(match):
        # 跳过 $$ 的情况（已在上面处理）
        content = match.group(1)
        if content.strip():
            placeholders.append({
                'raw': f'${content}$',
                'sim': _render_math_inline(content, dark=dark),
            })
            return f'\u0000MATHINLINE{len(placeholders)-1}\u0000'
        return match.group(0)

    text = re.sub(r'\$(.+?)\$', save_inline, text)

    return text, placeholders


def _restore_math(html: str, placeholders: list, use_katex: bool = False) -> str:
    """
    将占位符替换回公式 HTML。
    use_katex=True  → 还原为原始 $...$ 文本，由页面内 KaTeX 渲染；
    use_katex=False → 还原为字体模拟 HTML（无 KaTeX 资源时的降级）。
    """
    for i, ph in enumerate(placeholders):
        val = ph['raw'] if use_katex else ph['sim']
        html = html.replace(f'\u0000MATHBLOCK{i}\u0000', val)
        html = html.replace(f'\u0000MATHINLINE{i}\u0000', val)
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

    # 1. 预处理数学公式（占位符保护）
    text, placeholders = _preprocess_math(md_text, dark=(theme == 'dark'))

    # 2. 是否启用本地 KaTeX 真实渲染（默认关闭，原因见 ENABLE_KATEX_JS 注释）
    katex = _katex_asset_urls() if ENABLE_KATEX_JS else None
    use_katex = katex is not None

    # 3. Markdown → HTML
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

    # 4. 手动处理代码块高亮（因为 markdown.codehilite 需要额外配置）
    html_body = _highlight_code_blocks(html_body, theme)

    # 5. 恢复数学公式（KaTeX 模式还原为 $...$，降级模式还原为字体模拟）
    html_body = _restore_math(html_body, placeholders, use_katex=use_katex)

    # 6. 组装完整 HTML 页面（注入 KaTeX 资源）
    full_html = _build_html_page(html_body, theme, katex=katex)

    return full_html


def _wrap_bare_text(highlighted: str) -> str:
    """
    将 Pygments 高亮输出中 <pre> 内未被 <span> 包裹的裸文本节点
    包进中性 <span> 中，消除 tkinterweb 对裸文本渲染红框的伪影。
    只处理 <pre>...</pre> 内部内容，不触碰外层 div 等标签。
    """
    def wrap_inner(pre_content: str) -> str:
        """只对 pre 内部的裸文本做 span 包裹"""
        parts = []
        i = 0
        while i < len(pre_content):
            if pre_content[i:].startswith('<span'):
                close = pre_content.find('</span>', i)
                if close == -1:
                    parts.append(pre_content[i:])
                    break
                end = close + len('</span>')
                parts.append(pre_content[i:end])
                i = end
            else:
                next_span = pre_content.find('<span', i)
                if next_span == -1:
                    text = pre_content[i:]
                    if text.strip():
                        parts.append(f'<span>{text}</span>')
                    else:
                        parts.append(text)
                    break
                text = pre_content[i:next_span]
                if text.strip():
                    parts.append(f'<span>{text}</span>')
                else:
                    parts.append(text)
                i = next_span
        return ''.join(parts)

    # 仅替换 <pre>...</pre> 内部
    return re.sub(
        r'(<pre[^>]*>)(.*?)(</pre>)',
        lambda m: m.group(1) + wrap_inner(m.group(2)) + m.group(3),
        highlighted,
        flags=re.DOTALL,
    )


def _highlight_code_blocks(html: str, theme: str = 'light') -> str:
    """
    用 Pygments 为 <pre><code> 块添加语法高亮
    """
    try:
        import html as html_module
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
            code = html_module.unescape(match.group(2) or '')

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
            # tkinterweb 对 <pre> 内裸文本节点（如 { } 等未被 Pygments 包裹的字符）
            # 会渲染出红框伪影；将所有裸文本包进中性 span 消除此问题
            highlighted = _wrap_bare_text(highlighted)
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


def _build_html_page(body: str, theme: str = 'light', katex: dict = None) -> str:
    """
    将 HTML body 包装成完整页面，添加主题样式。
    katex 非空时注入本地 KaTeX 的 CSS/JS 并对 $...$ / $$...$$ 自动渲染。
    """
    # KaTeX 注入片段（资源缺失时为空字符串，自动降级为字体模拟）
    if katex:
        katex_head = (
            f'<link rel="stylesheet" href="{katex["css"]}">\n'
        )
        katex_script = (
            f'<script src="{katex["js"]}"></script>\n'
            f'<script src="{katex["auto"]}"></script>\n'
            f'<script>\n'
            f'if (window.renderMathInElement) {{\n'
            f'  renderMathInElement(document.body, {{\n'
            f'    delimiters: [\n'
            f'      {{left: "$$", right: "$$", display: true}},\n'
            f'      {{left: "$", right: "$", display: false}}\n'
            f'    ],\n'
            f'    ignoredTags: ["script", "noscript", "style", "textarea", "pre", "code"],\n'
            f'    throwOnError: false\n'
            f'  }});\n'
            f'}}\n'
            f'</script>\n'
        )
    else:
        katex_head = ''
        katex_script = ''

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
    border: none;
    outline: none;
  }}
  pre span {{
    border: none !important;
    outline: none !important;
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
{katex_head}</head>
<body>
{body}
{katex_script}</body>
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
