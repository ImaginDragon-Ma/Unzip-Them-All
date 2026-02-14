# -*- coding: utf-8 -*-
"""任务配置小组件"""

import os
from pathlib import Path
from typing import List, Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QListWidget, QComboBox, QFileDialog, QGroupBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from config.task_config import TaskConfig


class TaskWidget(QWidget):
    """任务配置小组件"""

    def __init__(self, task_index: int, saved_passwords: List[str], on_delete=None):
        super().__init__()

        self.task_index = task_index
        self.saved_passwords = saved_passwords
        self.on_delete = on_delete
        self.task_config = TaskConfig()

        self.init_ui()

    def init_ui(self) -> None:
        """初始化界面"""
        layout = QVBoxLayout(self)

        # 任务标题
        title_layout = QHBoxLayout()
        title_label = QLabel(f'任务 {self.task_index + 1}')
        title_label.setFont(QFont('Arial', 11, QFont.Bold))
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        # 删除任务按钮
        self.delete_btn = QPushButton('删除任务')
        self.delete_btn.setMaximumWidth(80)
        if self.on_delete:
            self.delete_btn.clicked.connect(lambda: self.on_delete(self.task_index))
        title_layout.addWidget(self.delete_btn)

        layout.addLayout(title_layout)

        # 输出目录
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel('输出目录:'))
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setFont(QFont('Arial', 9))
        self.output_path_edit.setPlaceholderText('选择输出目录或留空使用默认')
        output_layout.addWidget(self.output_path_edit)

        self.browse_btn = QPushButton('浏览...')
        self.browse_btn.setMaximumWidth(60)
        self.browse_btn.clicked.connect(self.browse_output_dir)
        output_layout.addWidget(self.browse_btn)

        layout.addLayout(output_layout)

        # 密码选择
        password_layout = QHBoxLayout()
        password_layout.addWidget(QLabel('解压密码:'))

        # 密码下拉框
        self.password_combo = QComboBox()
        self.password_combo.setEditable(True)
        self.password_combo.setPlaceholderText('无密码可留空')
        self._update_password_combo()
        password_layout.addWidget(self.password_combo, 1)

        layout.addLayout(password_layout)

        # 文件选择
        file_group = QGroupBox('文件列表')
        file_layout = QVBoxLayout()

        # 文件列表
        self.file_list = QListWidget()
        self.file_list.setFont(QFont('Arial', 9))
        file_layout.addWidget(self.file_list)

        # 按钮布局
        btn_layout = QHBoxLayout()

        self.select_btn = QPushButton('选择文件')
        self.select_btn.setMaximumWidth(80)
        self.select_btn.clicked.connect(self.select_files)
        btn_layout.addWidget(self.select_btn)

        self.clear_btn = QPushButton('清空')
        self.clear_btn.setMaximumWidth(60)
        self.clear_btn.clicked.connect(self.clear_files)
        btn_layout.addWidget(self.clear_btn)

        file_layout.addLayout(btn_layout)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

    def _update_password_combo(self) -> None:
        """更新密码下拉框"""
        current_text = self.password_combo.currentText()
        self.password_combo.clear()
        self.password_combo.addItem('')  # 空密码选项
        for pwd in self.saved_passwords:
            self.password_combo.addItem(pwd)

        # 恢复之前选中的密码
        index = self.password_combo.findText(current_text)
        if index >= 0:
            self.password_combo.setCurrentIndex(index)

    def update_saved_passwords(self, saved_passwords: List[str]) -> None:
        """
        更新保存的密码列表

        Args:
            saved_passwords: 新的密码列表
        """
        self.saved_passwords = saved_passwords
        self._update_password_combo()

    def browse_output_dir(self) -> None:
        """浏览输出目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            f'选择输出目录 (任务 {self.task_index + 1})',
            os.getcwd()
        )

        if dir_path:
            self.output_path_edit.setText(dir_path)

    def select_files(self) -> None:
        """选择文件"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            f'选择压缩文件 (任务 {self.task_index + 1})',
            os.getcwd(),
            '压缩文件 (*.zip *.rar *.7z *.tar *.gz *.001 *.002 *.7z.001 *.part1.rar);;所有文件 (*.*)'
        )

        if files:
            for file_str in files:
                file_path = Path(file_str)
                if file_path not in self.task_config.get_file_paths():
                    self.task_config.add_file(file_path)
                    self.file_list.addItem(file_path.name)

    def clear_files(self) -> None:
        """清空文件列表"""
        self.task_config.files.clear()
        self.file_list.clear()

    def get_output_dir(self) -> Optional[Path]:
        """获取输出目录"""
        path = self.output_path_edit.text().strip()
        return Path(path) if path else None

    def get_password(self) -> Optional[str]:
        """获取密码"""
        pwd = self.password_combo.currentText().strip()
        return pwd if pwd else None

    def get_files(self) -> List[Path]:
        """获取文件列表"""
        return self.task_config.get_file_paths()

    def set_output_dir(self, path: str) -> None:
        """设置输出目录"""
        self.output_path_edit.setText(path)

    def set_password(self, password: str) -> None:
        """设置密码"""
        if password:
            self.password_combo.setCurrentText(password)

    def update_task_index(self, new_index: int) -> None:
        """
        更新任务索引

        Args:
            new_index: 新的索引
        """
        self.task_index = new_index
        # 更新标题
        title_label = self.layout().itemAt(0).layout().itemAt(0).widget()
        title_label.setText(f'任务 {self.task_index + 1}')
