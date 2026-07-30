"""
InfoLearn Desktop — ���息学竞赛学习桌面助手
入口文件

运行方式：
    python main.py

打包命令（M9 阶段使用）：
    pyinstaller --onefile --windowed --name InfoLearn --add-data "data;data" main.py
"""

import sys
import os

# 确保程序根目录在 Python 搜索路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import App


def main():
    """程序入口"""
    app = App()
    app.mainloop()


if __name__ == '__main__':
    main()
