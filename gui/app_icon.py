#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
应用程序图标生成器
使用代码生成压缩工具图标
"""

from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QFont
from PyQt5.QtCore import Qt, QSize


def create_app_icon() -> QIcon:
    """
    创建应用程序图标

    Returns:
        QIcon: 应用程序图标
    """
    # 创建16x16的图标用于任务栏
    sizes = [16, 32, 48, 64, 128, 256]
    icon = QIcon()

    for size in sizes:
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # 计算缩放比例
        scale = size / 48.0

        # 绘制压缩包图标背景
        rect_x = int(8 * scale)
        rect_y = int(6 * scale)
        rect_w = int(32 * scale)
        rect_h = int(36 * scale)

        # 背景渐变
        gradient_rect_x = rect_x
        gradient_rect_y = rect_y
        gradient_rect_w = rect_w
        gradient_rect_h = rect_h

        # 背景颜色
        bg_color = QColor(66, 133, 244)  # 蓝色

        painter.setBrush(bg_color)
        painter.setPen(QPen(QColor(51, 103, 214), 2 * scale))
        painter.drawRoundedRect(rect_x, rect_y, rect_w, rect_h, 4 * scale, 4 * scale)

        # 绘制文件折角效果
        corner_x = rect_x + rect_w - int(10 * scale)
        corner_y = rect_y
        corner_w = int(10 * scale)
        corner_h = int(10 * scale)

        from PyQt5.QtGui import QPolygonF
        from PyQt5.QtCore import QPointF
        corner = QPolygonF([
            QPointF(corner_x, corner_y),
            QPointF(rect_x + rect_w, corner_y),
            QPointF(corner_x, corner_y + corner_h)
        ])
        painter.setBrush(QColor(103, 149, 249))
        painter.drawPolygon(corner)

        # 绘制向下箭头
        arrow_center_x = rect_x + rect_w / 2
        arrow_top_y = rect_y + int(14 * scale)
        arrow_bottom_y = rect_y + int(26 * scale)
        arrow_size = int(8 * scale)
        arrow_thick = int(3 * scale)

        painter.setBrush(QColor(255, 255, 255))
        painter.setPen(Qt.NoPen)

        # 箭头三角形
        arrow = QPolygonF([
            QPointF(arrow_center_x - arrow_size, arrow_top_y),
            QPointF(arrow_center_x + arrow_size, arrow_top_y),
            QPointF(arrow_center_x, arrow_bottom_y)
        ])
        painter.drawPolygon(arrow)

        # 箭头线条
        painter.setBrush(QColor(255, 255, 255))
        painter.drawRoundedRect(
            int(arrow_center_x - arrow_thick / 2),
            arrow_bottom_y - int(2 * scale),
            arrow_thick,
            arrow_bottom_y - arrow_top_y + int(4 * scale),
            1,
            1
        )

        # 绘制文字 "ZIP"
        if size >= 32:
            font = QFont('Arial', int(8 * scale), QFont.Bold)
            painter.setFont(font)
            painter.setPen(QColor(255, 255, 255))
            text = "ZIP"
            text_width = painter.fontMetrics().width(text)
            painter.drawText(
                int(rect_x + (rect_w - text_width) / 2),
                int(rect_y + rect_h - int(6 * scale)),
                text
            )

        painter.end()
        icon.addPixmap(pixmap)

    return icon
