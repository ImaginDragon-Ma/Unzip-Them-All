#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
压缩文件批量解压工具
支持 WinRAR API，可递归解压多层压缩文件
"""

import sys

from PyQt5.QtWidgets import QApplication

from gui import ExtractorGUI
from gui.app_icon import create_app_icon


def main() -> None:
    """程序入口"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # 使用 Fusion 样式

    # 设置应用程序图标
    app_icon = create_app_icon()
    app.setWindowIcon(app_icon)

    window = ExtractorGUI()
    window.setWindowIcon(app_icon)
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
