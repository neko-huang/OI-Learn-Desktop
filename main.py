"""
InfoLearn Desktop — 信息学竞赛学习桌面助手
入口文件

运行方式：
    python main.py

打包命令（M9 阶段使用）：
    pyinstaller --onefile --windowed --name InfoLearn --add-data "data;data" main.py
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