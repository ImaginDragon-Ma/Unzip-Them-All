# -*- coding: utf-8 -*-
"""任务配置小组件"""

import os
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QFileDialog, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from config.task_config import TaskConfig

if TYPE_CHECKING:
    from config.i18n import I18N


class TaskWidget(QFrame):
    """任务配置小组件 - 单行紧凑形式"""

    def __init__(self, task_index: int, saved_passwords: List[str], on_delete=None):
        super().__init__()
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setLineWidth(1)

        self.task_index = task_index
        self.saved_passwords = saved_passwords
        self.on_delete = on_delete
        self.task_config = TaskConfig()
        self.i18n = None

        # UI 组件引用
        self.task_label = None
        self.output_label = None
        self.password_label = None

        self.init_ui()

    def init_ui(self) -> None:
        """初始化界面"""
        layout = QHBoxLayout(self)
        layout.setSpacing(6)

        # 任务号
        self.task_label = QLabel(f'#{self.task_index + 1}')
        self.task_label.setFont(QFont('Arial', 10, QFont.Bold))
        self.task_label.setMinimumWidth(35)
        layout.addWidget(self.task_label)

        # 输出目录
        self.output_label = QLabel('输出:')
        self.output_label.setMinimumWidth(40)
        layout.addWidget(self.output_label)

        self.output_path_edit = QLineEdit()
        self.output_path_edit.setFont(QFont('Arial', 9))
        self.output_path_edit.setPlaceholderText('选择输出目录...')
        self.output_path_edit.setMinimumWidth(300)
        self.output_path_edit.setMaximumWidth(400)
        layout.addWidget(self.output_path_edit, 1)

        self.browse_btn = QPushButton('...')
        self.browse_btn.setMaximumWidth(35)
        self.browse_btn.setToolTip('浏览输出目录')
        self.browse_btn.clicked.connect(self.browse_output_dir)
        layout.addWidget(self.browse_btn)

        # 密码
        self.password_label = QLabel('密码:')
        self.password_label.setMinimumWidth(40)
        layout.addWidget(self.password_label)

        self.password_combo = QComboBox()
        self.password_combo.setEditable(True)
        self.password_combo.setPlaceholderText('无密码')
        self.password_combo.setMinimumWidth(150)
        self._update_password_combo()
        layout.addWidget(self.password_combo, 1)

        # 文件信息
        self.file_info_label = QLabel('文件: 0')
        self.file_info_label.setMinimumWidth(70)
        layout.addWidget(self.file_info_label)

        # 选择文件按钮
        self.select_btn = QPushButton('选择文件')
        self.select_btn.setMinimumWidth(80)
        self.select_btn.clicked.connect(self.select_files)
        layout.addWidget(self.select_btn)

        # 清空按钮
        self.clear_btn = QPushButton('清空')
        self.clear_btn.setMinimumWidth(55)
        self.clear_btn.clicked.connect(self.clear_files)
        layout.addWidget(self.clear_btn)

        # 删除任务按钮
        self.delete_btn = QPushButton('×')
        self.delete_btn.setMaximumWidth(35)
        self.delete_btn.setToolTip('删除此任务')
        self.delete_btn.setStyleSheet('QPushButton { color: red; font-weight: bold; }')
        if self.on_delete:
            self.delete_btn.clicked.connect(lambda: self.on_delete(self.task_index))
        layout.addWidget(self.delete_btn)

        layout.addStretch()

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
            self._update_file_info()

    def clear_files(self) -> None:
        """清空文件列表"""
        self.task_config.files.clear()
        self._update_file_info()

    def _update_file_info(self) -> None:
        """更新文件信息显示"""
        count = len(self.task_config.files)
        if self.i18n:
            self.file_info_label.setText(self.i18n.get('file_count', count))
        else:
            self.file_info_label.setText(f'文件: {count}')

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
        # 更新任务号标签
        task_label = self.layout().itemAt(0).widget()
        task_label.setText(f'#{self.task_index + 1}')

    def set_output_enabled(self, enabled: bool) -> None:
        """设置输出目录是否可编辑"""
        self.output_path_edit.setEnabled(enabled)
        self.browse_btn.setEnabled(enabled)

    def set_password_enabled(self, enabled: bool) -> None:
        """设置密码是否可编辑"""
        self.password_combo.setEnabled(enabled)

    def set_file_buttons_enabled(self, enabled: bool) -> None:
        """设置文件按钮是否可点击"""
        self.select_btn.setEnabled(enabled)
        self.clear_btn.setEnabled(enabled)

    def _apply_translation(self, i18n: 'I18N') -> None:
        """应用翻译"""
        if self.i18n == i18n:
            return
        self.i18n = i18n

        self.task_label.setText(f'#{self.task_index + 1}')
        self.output_label.setText(i18n.get('output'))
        self.password_label.setText(i18n.get('password'))

        # 根据语言调整宽度
        if i18n.language == 'en':
            self.output_path_edit.setMinimumWidth(280)
            self.password_combo.setMinimumWidth(130)
            self.select_btn.setMinimumWidth(75)
        else:
            self.output_path_edit.setMinimumWidth(300)
            self.password_combo.setMinimumWidth(150)
            self.select_btn.setMinimumWidth(80)

        self.output_path_edit.setPlaceholderText(i18n.get('select_output_dir'))
        self.password_combo.setPlaceholderText(i18n.get('no_password'))
        self.file_info_label.setText(i18n.get('file_count', len(self.task_config.files)))
        self.select_btn.setText(i18n.get('select_files'))
        self.clear_btn.setText(i18n.get('clear'))
        self.delete_btn.setText(i18n.get('delete_task'))
        self.delete_btn.setToolTip(i18n.get('delete_task_tooltip'))
        self.browse_btn.setToolTip(i18n.get('browse'))

        # 更新文件信息
        self._update_file_info()
