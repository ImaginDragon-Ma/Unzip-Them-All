# -*- coding: utf-8 -*-
"""主窗口"""

import os
from pathlib import Path
from typing import List, Optional, Tuple

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QListWidget, QLabel, QLineEdit, QProgressBar,
    QFileDialog, QMessageBox, QGroupBox, QCheckBox, QComboBox,
    QDialog, QDialogButtonBox, QScrollArea
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from config.settings import Config, load_config, save_config
from config.password_manager import PasswordManager
from core.winrar_helper import WinRARHelper
from gui.worker_thread import ExtractWorker
from gui.task_widget import TaskWidget


class PasswordManagerDialog(QDialog):
    """密码管理对话框"""

    def __init__(self, password_manager: PasswordManager, parent=None):
        super().__init__(parent)
        self.password_manager = password_manager
        self.passwords = password_manager.get_all()
        self.init_ui()

    def init_ui(self) -> None:
        """初始化界面"""
        self.setWindowTitle('管理密码')
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)

        layout = QVBoxLayout(self)

        # 密码列表
        layout.addWidget(QLabel('已保存的密码:'))
        self.password_list = QListWidget()
        self.password_list.setFont(QFont('Arial', 10))
        self._update_list()
        layout.addWidget(self.password_list)

        # 输入新密码
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel('新密码:'))
        self.new_password_edit = QLineEdit()
        self.new_password_edit.setEchoMode(QLineEdit.Password)
        input_layout.addWidget(self.new_password_edit)
        layout.addLayout(input_layout)

        # 按钮布局
        btn_layout = QHBoxLayout()

        self.add_btn = QPushButton('添加密码')
        self.add_btn.clicked.connect(self.add_password)
        btn_layout.addWidget(self.add_btn)

        self.delete_btn = QPushButton('删除选中')
        self.delete_btn.clicked.connect(self.delete_password)
        btn_layout.addWidget(self.delete_btn)

        self.clear_all_btn = QPushButton('清空全部')
        self.clear_all_btn.clicked.connect(self.clear_all)
        btn_layout.addWidget(self.clear_all_btn)

        layout.addLayout(btn_layout)

        # 对话框按钮
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _update_list(self) -> None:
        """更新密码列表"""
        self.password_list.clear()
        for pwd in self.passwords:
            self.password_list.addItem('***' if pwd else '(无密码)')

    def add_password(self) -> None:
        """添加密码"""
        password = self.new_password_edit.text().strip()
        if not password:
            QMessageBox.warning(self, '警告', '请输入密码！')
            return

        if password in self.passwords:
            QMessageBox.warning(self, '警告', '密码已存在！')
            return

        self.passwords.append(password)
        self.new_password_edit.clear()
        self._update_list()

    def delete_password(self) -> None:
        """删除密码"""
        current_row = self.password_list.currentRow()
        if current_row >= 0:
            del self.passwords[current_row]
            self._update_list()
        else:
            QMessageBox.warning(self, '警告', '请选择要删除的密码！')

    def clear_all(self) -> None:
        """清空所有密码"""
        reply = QMessageBox.question(
            self,
            '确认',
            '确定要清空所有密码吗？',
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.passwords.clear()
            self._update_list()

    def get_passwords(self) -> List[str]:
        """获取密码列表"""
        return self.passwords.copy()

    def accept(self) -> None:
        """接受对话框"""
        # 更新密码管理器
        self.password_manager.passwords = self.passwords
        super().accept()


class ExtractorGUI(QMainWindow):
    """压缩文件批量解压工具 - 主窗口"""

    def __init__(self):
        super().__init__()

        self.worker: ExtractWorker = None
        self.config: Config = load_config()
        self.password_manager = PasswordManager(self.config.saved_passwords)
        self.task_widgets: List[TaskWidget] = []

        # 查找 WinRAR 路径
        self.winrar_path = self.config.winrar_path
        if not self.winrar_path:
            found_path = WinRARHelper.find_path()
            if found_path:
                self.winrar_path = str(found_path)
                self.config.winrar_path = self.winrar_path

        self.init_ui()
        self.load_saved_settings()

    def init_ui(self) -> None:
        """初始化界面"""
        self.setWindowTitle('压缩文件批量解压工具')
        self.setGeometry(300, 300, 900, 700)

        # 中央窗口
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout(central_widget)

        # WinRAR 路径选择
        winrar_layout = QHBoxLayout()
        winrar_layout.addWidget(QLabel('WinRAR 路径:'))
        self.winrar_path_edit = QLineEdit(self.winrar_path if self.winrar_path else '')
        self.winrar_path_edit.setFont(QFont('Arial', 9))
        self.winrar_path_edit.setPlaceholderText('点击浏览选择 WinRAR.exe')
        winrar_layout.addWidget(self.winrar_path_edit)

        self.browse_winrar_btn = QPushButton('浏览...')
        self.browse_winrar_btn.clicked.connect(self.browse_winrar)
        winrar_layout.addWidget(self.browse_winrar_btn)

        # WinRAR 状态
        winrar_status = '✓' if self.winrar_path else '✗ 未找到'
        self.winrar_status = QLabel(winrar_status)
        self.winrar_status.setStyleSheet('color: green' if self.winrar_path else 'color: red')
        winrar_layout.addWidget(self.winrar_status)

        main_layout.addLayout(winrar_layout)

        # 全局选项
        global_options_group = QGroupBox('全局选项')
        options_layout = QVBoxLayout()

        # 解压到原目录
        self.extract_to_source_cb = QCheckBox('解压到原目录（忽略任务中的输出目录设置）')
        self.extract_to_source_cb.setChecked(self.config.extract_to_source)
        self.extract_to_source_cb.stateChanged.connect(self.on_extract_to_source_changed)
        options_layout.addWidget(self.extract_to_source_cb)

        # 统一密码
        unified_password_layout = QHBoxLayout()
        self.use_unified_password_cb = QCheckBox('使用统一密码（忽略任务中的密码设置）')
        self.use_unified_password_cb.setChecked(self.config.use_unified_password)
        self.use_unified_password_cb.stateChanged.connect(self.on_use_unified_password_changed)
        unified_password_layout.addWidget(self.use_unified_password_cb)

        self.unified_password_combo = QComboBox()
        self.unified_password_combo.setEditable(True)
        self.unified_password_combo.setPlaceholderText('选择或输入统一密码')
        self.unified_password_combo.setEnabled(self.config.use_unified_password)
        self._update_password_combo(self.unified_password_combo)
        unified_password_layout.addWidget(self.unified_password_combo, 1)

        options_layout.addLayout(unified_password_layout)

        # 密码管理按钮
        password_manage_layout = QHBoxLayout()
        password_manage_layout.addWidget(QLabel('密码管理:'))
        self.manage_passwords_btn = QPushButton('管理密码')
        self.manage_passwords_btn.clicked.connect(self.manage_passwords)
        password_manage_layout.addWidget(self.manage_passwords_btn)
        password_manage_layout.addStretch()
        options_layout.addLayout(password_manage_layout)

        global_options_group.setLayout(options_layout)
        main_layout.addWidget(global_options_group)

        # 任务配置区域（滚动）
        tasks_label = QLabel('任务配置:')
        tasks_label.setFont(QFont('Arial', 11, QFont.Bold))
        main_layout.addWidget(tasks_label)

        # 任务按钮
        task_btn_layout = QHBoxLayout()
        self.add_task_btn = QPushButton('添加任务')
        self.add_task_btn.clicked.connect(self.add_task)
        task_btn_layout.addWidget(self.add_task_btn)
        task_btn_layout.addStretch()
        main_layout.addLayout(task_btn_layout)

        # 任务容器（滚动区域）
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(250)

        self.tasks_container = QWidget()
        self.tasks_layout = QVBoxLayout(self.tasks_container)
        self.tasks_layout.addStretch()  # 添加伸缩项
        scroll_area.setWidget(self.tasks_container)

        main_layout.addWidget(scroll_area)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.progress_bar)

        # 状态标签
        self.status_label = QLabel('准备就绪')
        self.status_label.setFont(QFont('Arial', 10))
        main_layout.addWidget(self.status_label)

        # 日志框
        log_group = QGroupBox('解压日志')
        log_layout = QVBoxLayout()
        self.log_list = QListWidget()
        self.log_list.setFont(QFont('Consolas', 9))
        log_layout.addWidget(self.log_list)
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)

        # 解压按钮
        self.extract_btn = QPushButton('开始解压')
        self.extract_btn.setMinimumHeight(40)
        self.extract_btn.setFont(QFont('Arial', 12, QFont.Bold))
        self.extract_btn.clicked.connect(self.start_extract)
        main_layout.addWidget(self.extract_btn)

    def _update_password_combo(self, combo: QComboBox) -> None:
        """更新密码下拉框"""
        current_text = combo.currentText()
        combo.clear()
        combo.addItem('')  # 空密码选项
        for pwd in self.password_manager.get_all():
            combo.addItem(pwd)

        # 如果有统一密码，设置为选中
        if self.config.unified_password:
            index = combo.findText(self.config.unified_password)
            if index >= 0:
                combo.setCurrentIndex(index)

        # 恢复之前选中的密码
        if current_text and not self.config.unified_password:
            index = combo.findText(current_text)
            if index >= 0:
                combo.setCurrentIndex(index)

    def add_task(self) -> None:
        """添加新任务"""
        task_index = len(self.task_widgets)
        task_widget = TaskWidget(
            task_index,
            self.password_manager.get_all(),
            on_delete=self.delete_task
        )
        self.task_widgets.append(task_widget)

        # 插入到伸缩项之前
        self.tasks_layout.insertWidget(
            self.tasks_layout.count() - 1,
            task_widget
        )

    def delete_task(self, task_index: int) -> None:
        """删除任务"""
        if task_index < len(self.task_widgets):
            task_widget = self.task_widgets[task_index]
            self.tasks_layout.removeWidget(task_widget)
            task_widget.deleteLater()
            self.task_widgets.pop(task_index)

            # 更新后续任务的索引
            for i in range(task_index, len(self.task_widgets)):
                self.task_widgets[i].update_task_index(i)

    def browse_winrar(self) -> None:
        """浏览 WinRAR 可执行文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            '选择 WinRAR 可执行文件',
            'C:\\Program Files',
            'WinRAR (WinRAR.exe);;所有文件 (*.*)'
        )

        if file_path:
            self.winrar_path = file_path
            self.winrar_path_edit.setText(file_path)
            self.winrar_status.setText('✓')
            self.winrar_status.setStyleSheet('color: green')

    def load_saved_settings(self) -> None:
        """加载保存的设置"""
        # 更新密码下拉框
        self._update_password_combo(self.unified_password_combo)

        # 更新输出目录的启用状态
        for task_widget in self.task_widgets:
            task_widget.output_path_edit.setEnabled(not self.config.extract_to_source)
            task_widget.browse_btn.setEnabled(not self.config.extract_to_source)

    def on_extract_to_source_changed(self, state: int) -> None:
        """解压到原目录复选框状态改变"""
        self.config.extract_to_source = (state == Qt.Checked)
        for task_widget in self.task_widgets:
            task_widget.output_path_edit.setEnabled(not self.config.extract_to_source)
            task_widget.browse_btn.setEnabled(not self.config.extract_to_source)

    def on_use_unified_password_changed(self, state: int) -> None:
        """使用统一密码复选框状态改变"""
        self.config.use_unified_password = (state == Qt.Checked)
        self.unified_password_combo.setEnabled(self.config.use_unified_password)

    def manage_passwords(self) -> None:
        """管理密码"""
        dialog = PasswordManagerDialog(self.password_manager, self)
        if dialog.exec_() == QDialog.Accepted:
            # 更新所有任务的密码下拉框
            saved_passwords = self.password_manager.get_all()
            for task_widget in self.task_widgets:
                task_widget.update_saved_passwords(saved_passwords)

    def save_settings(self) -> None:
        """保存设置"""
        self.config.winrar_path = self.winrar_path_edit.text().strip()
        self.config.extract_to_source = self.config.extract_to_source
        self.config.use_unified_password = self.config.use_unified_password
        self.config.unified_password = self.unified_password_combo.currentText().strip()
        self.config.saved_passwords = self.password_manager.get_all()
        save_config(self.config)

    def start_extract(self) -> None:
        """开始解压"""
        # 收集所有任务
        tasks = []
        for task_widget in self.task_widgets:
            files = task_widget.get_files()
            if not files:
                continue

            output_dir = task_widget.get_output_dir()
            password = task_widget.get_password()

            tasks.append({
                'files': files,
                'output_dir': output_dir,
                'password': password
            })

        if not tasks:
            QMessageBox.warning(self, '警告', '请至少添加一个任务并选择文件！')
            return

        # 检查 WinRAR 路径
        winrar_path = self.winrar_path_edit.text().strip()
        if not winrar_path or not Path(winrar_path).exists():
            QMessageBox.warning(
                self,
                '警告',
                '未找到 WinRAR！\n\n请点击"浏览..."按钮选择 WinRAR.exe 的位置。'
            )
            return

        # 确定统一密码
        unified_password = None
        if self.config.use_unified_password:
            unified_password = self.unified_password_combo.currentText().strip()
            if not unified_password:
                unified_password = None

        # 验证输出目录（如果不是解压到原目录）
        if not self.config.extract_to_source:
            for task in tasks:
                if task['output_dir'] is None:
                    QMessageBox.warning(
                        self,
                        '警告',
                        f'有一个任务的输出目录为空！\n\n请为每个任务设置输出目录或勾选"解压到原目录"。'
                    )
                    return

                if not task['output_dir'].exists():
                    QMessageBox.warning(
                        self,
                        '警告',
                        f'输出目录不存在: {task["output_dir"]}'
                    )
                    return

        # 保存设置
        self.save_settings()

        # 禁用按钮
        self._set_ui_enabled(False)

        # 清空日志
        self.log_list.clear()
        self.status_label.setText('正在解压...')

        # 启动工作线程
        self.worker = ExtractWorker(
            tasks,
            Path(winrar_path),
            extract_to_source=self.config.extract_to_source,
            unified_password=unified_password
        )
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.log_signal.connect(self.add_log)
        self.worker.finished_signal.connect(self.extract_finished)
        self.worker.start()

    def _set_ui_enabled(self, enabled: bool) -> None:
        """设置UI组件的启用状态"""
        self.add_task_btn.setEnabled(enabled)
        self.extract_btn.setEnabled(enabled)
        self.browse_winrar_btn.setEnabled(enabled)
        self.manage_passwords_btn.setEnabled(enabled)
        self.unified_password_combo.setEnabled(enabled and self.config.use_unified_password)
        self.extract_to_source_cb.setEnabled(enabled)
        self.use_unified_password_cb.setEnabled(enabled)
        self.winrar_path_edit.setEnabled(enabled)

        for task_widget in self.task_widgets:
            task_widget.delete_btn.setEnabled(enabled)
            task_widget.select_btn.setEnabled(enabled)
            task_widget.clear_btn.setEnabled(enabled)
            task_widget.browse_btn.setEnabled(enabled and not self.config.extract_to_source)
            task_widget.output_path_edit.setEnabled(enabled and not self.config.extract_to_source)
            task_widget.password_combo.setEnabled(enabled and not self.config.use_unified_password)
            task_widget.file_list.setEnabled(enabled)

    def update_progress(self, task_name: str, progress: int) -> None:
        """更新进度"""
        self.progress_bar.setValue(progress)
        self.status_label.setText(f'正在处理: {task_name}')

    def add_log(self, message: str) -> None:
        """添加日志"""
        self.log_list.addItem(message)
        self.log_list.scrollToBottom()

    def extract_finished(self, success_count: int) -> None:
        """解压完成"""
        self._set_ui_enabled(True)

        # 计算总文件数
        total_files = 0
        for task_widget in self.task_widgets:
            total_files += len(task_widget.get_files())

        self.status_label.setText(f'解压完成！成功: {success_count}/{total_files}')

        QMessageBox.information(
            self,
            '完成',
            f'解压完成！\n\n成功: {success_count}\n失败: {total_files - success_count}'
        )

        self.worker = None
