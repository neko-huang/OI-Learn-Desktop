"""
OI-Learn Desktop — 信息学竞赛学习桌面助手
入口文件

运行方式：
    python main.py

打包命令：
    pyinstaller OI-Learn.spec          # 使用 spec 文件（folder 模式，推荐）

⚠️ 重要：切勿使用 --onefile 模式打包！
   config.py 的 get_app_dir() 在 onefile 模式下会指向系统临时解压目录，
   导致所有数据（数据库、配置、签到记录）写入临时目录、程序退出即丢失。
   当前 OI-Learn.spec 使用 folder 模式（COLLECT），数据随 exe 同目录存储，
   整个 dist/OI-Learn/ 文件夹可拷贝到 U 盘随身携带。
"""

import sys
import os
import traceback

# 确保程序根目录在 Python 搜索路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import App


def main():
    """程序入口"""
    app = App()
    app.mainloop()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        # 顶层异常兜底：显示友好错误对话框，避免暴露 Python 堆栈
        try:
            import tkinter.messagebox as mb
            mb.showerror(
                'InfoLearn 错误',
                f'程序启动或运行过程中发生未预期错误：\n\n{e}\n\n'
                '请查看控制台日志获取详细信息，或联系开发者。'
            )
        except Exception:
            pass
        traceback.print_exc()
        sys.exit(1)