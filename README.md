# OI-Learn Desktop

信息学竞赛学习桌面助手 —— 一站式 OI 学习管理工具。

<kbd>Windows</kbd>　<kbd>Python 3.12</kbd>　<kbd>tkinter</kbd>　<kbd>SQLite</kbd>

---

## 目录

- [快速开始](#快速开始)
- [功能模块](#功能模块)
  - [首页 — 签到 + 赛事 + 学习规划](#1-首页)
  - [大纲 — 算法知识树](#2-大纲)
  - [百科 — 算法知识库](#3-百科)
  - [刷题 — 题目记录](#4-刷题)
  - [模板 — 代码模板库](#5-模板)
  - [易错集 — 错误复盘](#6-易错集)
  - [练习 — 题单 + 智能生成](#7-练习)
  - [统计 — 数据分析](#8-统计)
- [架构设计](#架构设计)
- [数据存储](#数据存储)
- [外部数据源](#外部数据源)
- [主题系统](#主题系统)
- [快捷键](#快捷键)
- [开发](#开发)
- [打包](#打包)
- [项目结构](#项目结构)

---

## 快速开始

### 方式一：运行可执行文件

下载 `dist/OI-Learn/` 文件夹，双击 `OI-Learn.exe` 即可运行。整个文件夹可放到 U 盘随身携带。

### 方式二：从源码运行

```bash
pip install -r requirements.txt
python main.py
```

---

## 功能模块

### 1. 首页

签到打卡 + 赛事日历 + 学习规划 + 便签，一站式仪表盘。

| 功能 | 说明 |
|------|------|
| **每日签到** | 点击签到按钮打卡，连续天数自动累计。月历上已签到日期高亮显示 |
| **近期赛事** | 从 Codeforces API 和 AtCoder(kenkoooo) 实时拉取未来 90 天赛事。NOI 系列赛事从 `data/noi_events.json` 读取（可自行编辑修正）。点击赛事名称跳转官网，刷新按钮后台异步更新不卡 UI |
| **学习规划** | 添加/勾选/删除学习任务，数据存储在 `settings.json`，重启不丢失 |
| **便签** | 右下角 Markdown 便签，自动保存至 `settings.json` |

**实现细节**：
- 签到数据通过 `Config` 单例持久化到 `data/settings.json`（键：`last_checkin_date`、`checkin_streak`）
- 赛事缓存 6 小时（`services/contests.py`），`fetch_cf_contests()` → `codeforces.com/api/contest.list`，`fetch_atcoder_contests()` → `kenkoooo.com/atcoder/resources/contests.json`
- 刷新使用 `threading.Thread(daemon=True)` 后台拉取，`parent.after(0, callback)` 回调 UI 更新
- 规划数据以 JSON 数组存入 Config `study_plan` 键

---

### 2. 大纲

22 大类算法知识树，支持掌握度追踪、自定义条目、关联百科。

| 功能 | 说明 |
|------|------|
| **树形大纲** | 左侧 `Treeview` 展示 22 大类 → 主题 → 知识点（~147 个叶子节点），每个节点带掌握度标记 ○◐◉● |
| **详情面板** | 选中知识点显示 Markdown 描述、难度星级、等级、掌握度下拉框 |
| **掌握度** | 未学 → 学习中 → 熟悉 → 已掌握，选择即保存到 `outline_progress` 表 |
| **自定义条目** | 右键菜单：添加子知识点（名称/难度/等级/描述）、编辑、删除 |
| **关联百科** | 详情面板「关联百科」按钮 → 弹出百科条目选择器 → 搜索并关联 |
| **搜索文章** | 「搜索文章」→ 浏览器打开百度搜索 "{知识点} 算法" |
| **导出进度** | `Ctrl+E` 导出大纲进度为 JSON |

**实现细节**：
- 种子数据 `db/seed.py` → `ALGORITHM_CATEGORIES`（22 大类，每类含多个 topic，每个 topic 含多个 subtopic）
- subtopic 格式：`(id, name, desc, difficulty_1to8, level)` 5 元组
- 自定义条目存 `custom_topics` 表，通过 `LOAD/INSERT/UPDATE/DELETE` 操作
- 树节点掌握度符号：`_progress[topic_id]` → `MASTERY_MAP` 映射 ○/◐/◉/●
- 关联百科：`UPDATE encyclopedia SET topic_id=?` 建立外键关联

---

### 3. 百科

内置算法百科知识库，支持 Markdown 编辑和全文搜索。

| 功能 | 说明 |
|------|------|
| **左栏列表** | 搜索框 + 分类筛选（20 个预定义类别） + 条目列表 |
| **右栏查看** | Markdown 渲染，代码高亮（Pygments） |
| **编辑模式** | 标题 + 分类 + Markdown 编辑器，`Ctrl+S` 保存 |
| **删除** | 底部删除按钮，确认后移除 |
| **导出** | `Ctrl+E` 导出为 Markdown，按分类分组 |

**实现细节**：
- 数据库表 `encyclopedia`（`id, title, content, category, tags, topic_id`）
- 查看模式使用 `components.markdown_view.MarkdownView`（封装 tkinterweb HtmlFrame）
- 编辑模式使用 `tk.Text` 多行编辑
- `_save_entry()`：INSERT 或 UPDATE，自动设置 `updated_at`
- 导出 `services/exporter.py` → `export_encyclopedia_to_md()`

---

### 4. 刷题

刷题记录管理，含分屏 Markdown 编辑器和知识标签系统。

| 功能 | 说明 |
|------|------|
| **题目列表** | 搜索 + 状态筛选（待做/已做/复习）+ 难度筛选，左侧可折叠面板 |
| **详情查看** | 题号、平台、难度、状态、题目描述（Markdown）、题解 |
| **编辑模式** | 题号、标题、难度下拉框、状态单选、平台选择、标签 chip、分屏 Markdown 编辑器（编辑/分屏/预览）、题解区 |
| **标签系统** | 弹出标签选择器（18 大类，5 列网格），多选 chip 展示 |
| **自动保存** | 离开编辑模式或切换模块时自动保存脏数据 |

**实现细节**：
- 数据库表 `problems`（`id, title, platform, platform_id, difficulty, tags(JSON), description, status, solution, url`）
- 标签以 JSON 数组存入数据库，使用 `json.dumps/loads` 处理
- 标签选择器 `_open_tag_picker()`：Toplevel 对话框，按 `PROBLEM_CATEGORIES` 分组，grid 布局
- 分屏编辑器 `_build_md_editor()`：三个子 Frame（edit/split/preview），Split 模式左右分屏
- 自动保存 `_auto_save()`：检查表单脏标记，INSERT 或 UPDATE

---

### 5. 模板

算法代码模板管理，支持收藏和代码高亮。

| 功能 | 说明 |
|------|------|
| **模板列表** | 搜索 + 分类筛选 + 语言筛选，收藏模板置顶 |
| **查看模式** | Markdown 渲染的代码块（含语言标记用于语法高亮） |
| **编辑模式** | 名称、分类（8 个选项）、语言（cpp/python/java）、备注、代码编辑器 |
| **收藏** | ⭐ 按钮切换，SQL `1 - is_starred`，收藏模板自动置顶 |
| **导出** | 导出为 Markdown，按分类分组 |

**实现细节**：
- 数据库表 `templates`（`id, name, category, language, code, note, is_starred`）
- 种子数据含 5 个预置模板：快读、DSU、BIT、Dijkstra、快速幂
- 仅首次运行时 `seed_database()` 插入（`SELECT COUNT(*) FROM templates` 判断）
- 收藏切换 `_toggle_star()`：`UPDATE templates SET is_starred = 1 - is_starred`

---

### 6. 易错集

错误代码与正确代码对比管理的复盘工具。

| 功能 | 说明 |
|------|------|
| **条目列表** | 搜索框 + 条目列表 |
| **查看模式** | Markdown 渲染：错误原因 + ❌ 错误代码 + ✅ 正确代码（并列对比） |
| **编辑模式** | 标题 + 左侧错误代码 + 右侧正确代码 + 错误原因（Markdown） |

**实现细节**：
- 数据库表 `mistakes`（`id, problem_id, title, wrong_code, correct_code, reason, tags`）
- 查看模式渲染为含语言标记的代码围栏块（```python / ```cpp）
- 编辑模式左右双 `tk.Text`，红色标签"错误代码"，绿色标签"正确代码"

---

### 7. 练习

题单创建 + 智能生成 + VP 模拟赛，支持多来源题目获取。

| 功能 | 说明 |
|------|------|
| **新建练习** | 名称 + 自由练习/定时模拟（含倒计时器），定时模式自动隐藏时长选择 |
| **手动添加** | 输入题目标题直接加入 |
| **智能生成** | 选择知识点标签（147 个中文 tag）+ 难度筛选 + 数量 + 来源（CF/AT/Luogu/本地），后台线程搜索 → 随机采样 → 去重 → 展示 |
| **不重复机制** | 全局题目池缓存（CF 5000 题，AT 5000 题），`random.sample()` 随机采样，`_used_ids` 追踪已用避免重复 |
| **导入题单** | 粘贴洛谷训练链接（`luogu.com.cn/training/{id}`），后台调用 API 获取题目列表，确认后批量插入 |
| **从本地添加** | 弹窗列出所有本地刷题记录（支持搜索），多选后加入 |
| **练习中模式** | 进度条 + 可勾选题目列表（待做 ↔ 已完成），定时模式倒计时 HH:MM:SS，到时间弹窗提示 |
| **题目链接** | 标题可点击跳转洛谷/CF/AT 原题页，自动构建 URL |

**实现细节**：
- 数据库表 `practice_plans`（`id, name, description, practice_mode, duration, status`）+ `plan_problems`（`id, plan_id, problem_id, platform, platform_id, title, difficulty, sort_order, status, note`）
- 智能生成 `_do_gen_search()`：后台线程，根据来源调用不同 fetcher
  - CF：`search_codeforces(limit=5000)` → 全局池 → `random.sample(available, count)`
  - AT：`search_atcoder(keyword='', limit=5000)` → 同上
  - Luogu：`search_luogu(keyword=tag, limit=...)` → 需配置 Cookie
  - Local：`search_local()` → 全局池
- 已用 ID 追踪 `_used_ids`（set），池子用完自动 `clear()` 重置
- 导入洛谷题单：`requests.get(training/{id}?_contentOnly=1)` → 解析 `training.problems[].problem` → 批量 INSERT
- 倒计时器 `_update_timer()`：`after(1000, ...)` 递归循环

---

### 8. 统计

纯 Canvas 绘制的可视化分析面板。

| 功能 | 说明 |
|------|------|
| **概览卡片** | 4 个卡片：大纲进度、刷题总数、已掌握算法、易错记录 |
| **大纲柱状图** | 前 10 个大类的掌握度水平柱状图（已学/总数） |
| **刷题分布** | 按难度的水平柱状图（8 级，8 种颜色）+ 按状态的颜色标签 |

**实现细节**：
- 卡片组件 `_make_card(parent, title, value)`：Frame + 两个 Label
- 所有图表使用 `tk.Canvas` 绘制，无外部图表库依赖
- 数据通过 SQL 聚合查询获取
- `_draw_outline_bars()`：Canvas 紫色填充条，动态计算宽度
- `_draw_problem_stats()`：8 种难度颜色渐变

---

## 架构设计

### 模块懒加载

模块仅在首次导航到时才被导入和实例化，降低启动时间：

```python
_MODULE_LOADER = {
    'home': ('modules.home', 'HomeModule'),
    'outline': ('modules.outline', 'OutlineModule'),
    # ...
}

def _load_module(self, module_id):
    import_path, class_name = _MODULE_LOADER[module_id]
    mod = __import__(import_path, fromlist=[class_name])
    cls = getattr(mod, class_name)
    instance = cls(self, frame)
    self._loaded_modules[module_id] = instance
```

### 生命周期钩子

每个模块可实现以下钩子：

| 钩子 | 触发时机 |
|------|---------|
| `on_before_leave()` | 切换模块前（自动保存） |
| `on_new()` | `Ctrl+N` |
| `on_save()` | `Ctrl+S` |
| `on_search()` | `Ctrl+F` |
| `on_export()` | `Ctrl+E` |
| `apply_theme()` | 主题切换 |

### 主题级联

`App.apply_theme()` → 遍历所有加载的模块 → 调用 `module.apply_theme()`，确保主题切换全局生效。

### 线程安全

所有网络请求和耗时操作使用 `threading.Thread(daemon=True)`，通过 `parent.after(0, callback)` 回到 GUI 线程更新 UI。

### 单例配置

`Config` 类使用 `__new__` 单例模式，全局唯一实例，`set()` 自动持久化到 `data/settings.json`。

---

## 数据存储

### 数据库（SQLite）

文件：`data/info-learn.db`，WAL 模式，启用外键

> ⚠️ **迁移 / 备份须知（WAL 模式）**：数据库以 WAL 模式运行，除 `info-learn.db` 外还会生成 `info-learn.db-wal` 和 `info-learn.db-shm` 两个附属文件。近期未「落盘」的写操作记录在 `-wal` 中。
> - **复制或迁移时务必连同整个 `data/` 目录一起拷贝**，只拷 `info-learn.db` 会丢失 `-wal` 里尚未合并的改动。
> - 正常退出应用后 SQLite 会自动把 WAL 合并回主库；若担心残留，可在退出前执行一次 `PRAGMA wal_checkpoint(TRUNCATE)`。

| 表 | 用途 | 关键字段 |
|----|------|---------|
| `outline_progress` | 大纲掌握度 | topic_id(UNIQUE), mastery |
| `encyclopedia` | 算法百科 | title, content, category, topic_id |
| `problems` | 刷题记录 | title, platform, platform_id, difficulty, tags(JSON), description, status, solution, url |
| `templates` | 代码模板 | name, category, language, code, note, is_starred |
| `mistakes` | 易错集 | title, wrong_code, correct_code, reason |
| `practice_plans` | 练习计划 | name, practice_mode, duration, status |
| `plan_problems` | 计划内题目 | plan_id(FK), platform, platform_id, title, difficulty, sort_order, status |
| `custom_topics` | 自定义大纲条目 | topic_id(UNIQUE), parent_id, name, desc, difficulty, level, category_name |

### 配置文件

文件：`data/settings.json`

| 键 | 用途 |
|----|------|
| `theme_mode` | light/dark/system |
| `window_width/height/x/y` | 窗口几何信息 |
| `font_family/size` | 字体配置 |
| `last_checkin_date` | 最后签到日期 |
| `checkin_streak` | 连续签到天数 |
| `luogu_cookie` | 洛谷登录 Cookie |
| `home_note` | 首页便签内容 |
| `study_plan` | 学习规划 JSON 数组 |

### 种子数据

文件：`data/noi_events.json` — NOI 系列赛历

文件：`db/seed.py` — `ALGORITHM_CATEGORIES`（22 大类 ~147 个子知识点）+ `SEED_TEMPLATES`（5 个预置模板）

---

## 外部数据源

| 来源 | API 端点 | 用途 |
|------|---------|------|
| Codeforces | `codeforces.com/api/contest.list` | 赛事日历 |
| Codeforces | `codeforces.com/api/problemset.problems` | 题目搜索（智能生成） |
| AtCoder | `kenkoooo.com/atcoder/resources/problems.json` | 题目搜索（智能生成） |
| AtCoder | `kenkoooo.com/atcoder/resources/contests.json` | 赛事日历 |
| 洛谷 | `luogu.com.cn/problem/list?_contentOnly=1` | 题目搜索（需 Cookie） |
| 洛谷 | `luogu.com.cn/training/{id}?_contentOnly=1` | 题单导入 |

---

## 主题系统

双主题方案，约 50 种颜色 token：

| 类别 | 亮色（Light） | 暗色（Dark） |
|------|-------------|-------------|
| 主背景 | `#F5F2FF` 浅紫白 | `#13111A` 深紫黑 |
| 面板 | `#F0ECFF` 淡紫 | `#1A1725` |
| 卡片 | `#FFFFFF` 纯白 | `#1E1B2E` |
| 导航 | `#FFFFFF` | `#1A1725` |
| 强调色 | `#7C3AED` 紫色 | `#A78BFA` |
| 成功 | `#059669` 翠绿 | `#34D399` |
| 警告 | `#D97706` 琥珀 | `#FBBF24` |
| 危险 | `#DC2626` 红色 | `#F87171` |

主题检测：Windows 读注册表、macOS 读 defaults、Linux 读 gsettings。

---

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+1~8` | 切换模块 |
| `Ctrl+,` | 打开设置 |
| `Ctrl+N` | 新建（刷题/模板/易错/百科） |
| `Ctrl+S` | 保存当前编辑 |
| `Ctrl+F` | 聚焦搜索框 |
| `Ctrl+E` | 导出 |

---

## 开发

### 依赖

```
markdown>=3.4
Pygments>=2.14
tkinterweb>=3.24
requests>=2.28
PyInstaller>=6.0
katex>=0.10
```

### 运行

```bash
python main.py
```

### 添加新模块

1. 在 `modules/` 下创建 `{name}.py`，定义 `{Name}Module` 类
2. 在 `app.py` 的 `MODULES` 列表中添加条目
3. 在 `_MODULE_LOADER` 字典中注册导入路径

---

## 打包

```bash
pyinstaller --onedir --windowed --name "OI-Learn" \
  --add-data "data;data" \
  --hidden-import modules.home \
  --hidden-import modules.outline \
  --hidden-import modules.plan \
  --hidden-import modules.problems \
  --hidden-import modules.templates \
  --hidden-import modules.mistakes \
  --hidden-import modules.encyclopedia \
  --hidden-import modules.stats \
  --hidden-import modules.settings \
  --hidden-import modules.problem_meta \
  --hidden-import components.markdown_view \
  --hidden-import db.database \
  --hidden-import db.seed \
  --hidden-import services.fetcher \
  --hidden-import services.contests \
  --hidden-import services.exporter \
  --hidden-import services.markdown_engine \
  --hidden-import markdown --hidden-import pygments \
  --hidden-import requests --hidden-import certifi \
  main.py
```

输出在 `dist/OI-Learn/`，整个文件夹拷贝到 U 盘即可运行。

> **重要**：项目模块使用动态导入（`__import__`），必须用 `--hidden-import` 显式声明，否则打包后的 exe 无法加载模块。

---

## 项目结构

```
oi-learn-desktop/
├── main.py                      # 入口
├── app.py                       # 主窗口（导航/快捷键/主题）
├── config.py                    # 配置单例（主题/设置/持久化）
├── OI-Learn.spec                # PyInstaller 配置
├── requirements.txt             # Python 依赖
│
├── modules/
│   ├── home.py                  # 签到+赛事+规划+便签
│   ├── outline.py               # 算法大纲树
│   ├── encyclopedia.py          # Markdown 百科
│   ├── problems.py              # 刷题记录
│   ├── templates.py             # 代码模板
│   ├── mistakes.py              # 易错集
│   ├── plan.py                  # 练习计划+智能生成
│   ├── stats.py                 # Canvas 图表
│   ├── settings.py              # 设置对话框
│   └── problem_meta.py          # 难度/分类常量
│
├── services/
│   ├── fetcher.py               # 外部题目获取（CF/AT/洛谷/本地）
│   ├── contests.py              # 赛事聚合（6h缓存）
│   ├── exporter.py              # 导出 Markdown/JSON
│   └── markdown_engine.py       # MD→HTML（Pygments高亮+数学公式）
│
├── db/
│   ├── database.py              # SQLite 连接（8表+dict_factory+迁移）
│   └── seed.py                  # 22大类算法数据+模板种子
│
├── components/
│   └── markdown_view.py         # 可复用 Markdown 渲染组件
│
└── data/
    ├── settings.json            # 应用配置
    ├── noi_events.json          # NOI 赛历
    ├── contests_cache.json      # 赛事缓存（运行时生成）
    └── info-learn.db            # 主数据库（运行时生成）
```
