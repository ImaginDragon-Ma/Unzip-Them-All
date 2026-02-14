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
from config.i18n import I18N
from core.winrar_helper import WinRARHelper
from gui.worker_thread import ExtractWorker
from gui.task_widget import TaskWidget


class PasswordManagerDialog(QDialog):
    """密码管理对话框"""

    def __init__(self, password_manager: PasswordManager, i18n: I18N, parent=None):
        super().__init__(parent)
        self.password_manager = password_manager
        self.passwords = password_manager.get_all()
        self.i18n = i18n
        self.init_ui()
        self._apply_translation()

    def init_ui(self) -> None:
        """初始化界面"""
        self.setWindowTitle('')
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)

        layout = QVBoxLayout(self)

        # 密码列表
        self.saved_passwords_label = QLabel('')
        layout.addWidget(self.saved_passwords_label)
        self.password_list = QListWidget()
        self.password_list.setFont(QFont('Arial', 10))
        self._update_list()
        layout.addWidget(self.password_list)

        # 输入新密码
        input_layout = QHBoxLayout()
        self.new_password_label = QLabel('')
        input_layout.addWidget(self.new_password_label)
        self.new_password_edit = QLineEdit()
        self.new_password_edit.setEchoMode(QLineEdit.Password)
        input_layout.addWidget(self.new_password_edit)
        layout.addLayout(input_layout)

        # 按钮布局
        btn_layout = QHBoxLayout()

        self.add_btn = QPushButton('')
        self.add_btn.clicked.connect(self.add_password)
        btn_layout.addWidget(self.add_btn)

        self.delete_btn = QPushButton('')
        self.delete_btn.clicked.connect(self.delete_password)
        btn_layout.addWidget(self.delete_btn)

        self.clear_all_btn = QPushButton('')
        self.clear_all_btn.clicked.connect(self.clear_all)
        btn_layout.addWidget(self.clear_all_btn)

        layout.addLayout(btn_layout)

        # 对话框按钮
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _apply_translation(self) -> None:
        """应用翻译"""
        self.setWindowTitle(self.i18n.get('manage_passwords_title'))
        self.saved_passwords_label.setText(self.i18n.get('saved_passwords'))
        self.new_password_label.setText(self.i18n.get('new_password'))
        self.add_btn.setText(self.i18n.get('add_password'))
        self.delete_btn.setText(self.i18n.get('delete_selected'))
        self.clear_all_btn.setText(self.i18n.get('clear_all'))

    def _update_list(self) -> None:
        """更新密码列表"""
        self.password_list.clear()
        for pwd in self.passwords:
            display = pwd if pwd else '(无密码)'
            self.password_list.addItem(display)

    def add_password(self) -> None:
        """添加密码"""
        password = self.new_password_edit.text().strip()
        if not password:
            QMessageBox.warning(self, self.i18n.get('warning'), self.i18n.get('input_password'))
            return

        if password in self.passwords:
            QMessageBox.warning(self, self.i18n.get('warning'), self.i18n.get('password_exists'))
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
            QMessageBox.warning(self, self.i18n.get('warning'), self.i18n.get('select_password'))

    def clear_all(self) -> None:
        """清空所有密码"""
        reply = QMessageBox.question(
            self,
            self.i18n.get('confirm'),
            self.i18n.get('clear_all_passwords'),
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
        # 更新密码管理器 - 先清空再重新添加
        self.password_manager.clear()
        for pwd in self.passwords:
            if pwd:  # 不添加空密码
                self.password_manager.add_password(pwd)
        super().accept()


class ExtractorGUI(QMainWindow):
    """压缩文件批量解压工具 - 主窗口"""

    def __init__(self):
        super().__init__()

        self.worker: ExtractWorker = None
        self.config: Config = load_config()
        self.i18n = I18N(self.config.language)
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
        self._apply_translation()
        self.load_saved_settings()
        self._update_task_disable_state()

    def init_ui(self) -> None:
        """初始化界面"""
        self.setWindowTitle('')
        self.setGeometry(300, 300, 1200, 700)
        self.setMinimumWidth(1100)

        # 中央窗口
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout(central_widget)

        # WinRAR 路径选择
        winrar_layout = QHBoxLayout()
        self.winrar_path_label = QLabel('')
        winrar_layout.addWidget(self.winrar_path_label)
        self.winrar_path_edit = QLineEdit(self.winrar_path if self.winrar_path else '')
        self.winrar_path_edit.setFont(QFont('Arial', 9))
        self.winrar_path_edit.setPlaceholderText('')
        winrar_layout.addWidget(self.winrar_path_edit)

        self.browse_winrar_btn = QPushButton('')
        self.browse_winrar_btn.clicked.connect(self.browse_winrar)
        winrar_layout.addWidget(self.browse_winrar_btn)

        # WinRAR 状态
        self.winrar_status = QLabel('')
        winrar_layout.addWidget(self.winrar_status)

        main_layout.addLayout(winrar_layout)

        # 全局选项
        global_options_group = QGroupBox('')
        options_layout = QVBoxLayout()

        # 语言切换
        language_layout = QHBoxLayout()
        language_layout.addWidget(QLabel('Language:'))
        self.language_combo = QComboBox()
        self.language_combo.addItem('中文', 'zh_CN')
        self.language_combo.addItem('English', 'en')
        self.language_combo.setCurrentIndex(0 if self.config.language == 'zh_CN' else 1)
        self.language_combo.currentIndexChanged.connect(self.change_language)
        language_layout.addWidget(self.language_combo, 1)
        options_layout.addLayout(language_layout)

        # 解压到原目录
        self.extract_to_source_cb = QCheckBox('')
        self.extract_to_source_cb.setChecked(self.config.extract_to_source)
        self.extract_to_source_cb.stateChanged.connect(self.on_extract_to_source_changed)
        options_layout.addWidget(self.extract_to_source_cb)

        # 统一密码
        unified_password_layout = QHBoxLayout()
        self.use_unified_password_cb = QCheckBox('')
        self.use_unified_password_cb.setChecked(self.config.use_unified_password)
        self.use_unified_password_cb.stateChanged.connect(self.on_use_unified_password_changed)
        unified_password_layout.addWidget(self.use_unified_password_cb)

        self.unified_password_combo = QComboBox()
        self.unified_password_combo.setEditable(True)
        self.unified_password_combo.setPlaceholderText('')
        self.unified_password_combo.setEnabled(self.config.use_unified_password)
        self._update_password_combo(self.unified_password_combo)
        unified_password_layout.addWidget(self.unified_password_combo, 1)

        options_layout.addLayout(unified_password_layout)

        # 密码管理按钮
        password_manage_layout = QHBoxLayout()
        self.password_management_label = QLabel('')
        password_manage_layout.addWidget(self.password_management_label)
        self.manage_passwords_btn = QPushButton('')
        self.manage_passwords_btn.clicked.connect(self.manage_passwords)
        password_manage_layout.addWidget(self.manage_passwords_btn)
        password_manage_layout.addStretch()
        options_layout.addLayout(password_manage_layout)

        global_options_group.setLayout(options_layout)
        main_layout.addWidget(global_options_group)

        # 任务配置区域（滚动）
        self.tasks_label = QLabel('')
        self.tasks_label.setFont(QFont('Arial', 11, QFont.Bold))
        main_layout.addWidget(self.tasks_label)

        # 任务按钮
        task_btn_layout = QHBoxLayout()
        self.add_task_btn = QPushButton('')
        self.add_task_btn.clicked.connect(self.add_task)
        task_btn_layout.addWidget(self.add_task_btn)
        task_btn_layout.addStretch()
        main_layout.addLayout(task_btn_layout)

        # 任务容器（滚动区域）
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(250)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.tasks_container = QWidget()
        self.tasks_container.setMinimumWidth(1000)
        self.tasks_layout = QVBoxLayout(self.tasks_container)
        self.tasks_layout.setSpacing(8)
        self.tasks_layout.addStretch()  # 添加伸缩项
        scroll_area.setWidget(self.tasks_container)

        main_layout.addWidget(scroll_area)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.progress_bar)

        # 状态标签
        self.status_label = QLabel('')
        self.status_label.setFont(QFont('Arial', 10))
        main_layout.addWidget(self.status_label)

        # 日志框
        log_group = QGroupBox('')
        log_layout = QVBoxLayout()
        self.log_list = QListWidget()
        self.log_list.setFont(QFont('Consolas', 9))
        log_layout.addWidget(self.log_list)
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)

        # 解压按钮
        self.extract_btn = QPushButton('')
        self.extract_btn.setMinimumHeight(40)
        self.extract_btn.setFont(QFont('Arial', 12, QFont.Bold))
        self.extract_btn.clicked.connect(self.start_extract)
        main_layout.addWidget(self.extract_btn)

    def _apply_translation(self) -> None:
        """应用翻译"""
        self.setWindowTitle(self.i18n.get('window_title'))
        self.winrar_path_label.setText(self.i18n.get('winrar_path'))
        self.winrar_path_edit.setPlaceholderText(self.i18n.get('browse'))
        self.browse_winrar_btn.setText(self.i18n.get('browse'))
        winrar_status = self.i18n.get('winrar_found') if self.winrar_path else self.i18n.get('winrar_not_found')
        self.winrar_status.setText(winrar_status)
        self.winrar_status.setStyleSheet('color: green' if self.winrar_path else 'color: red')

        # 全局选项
        self.findChild(QGroupBox).setTitle(self.i18n.get('global_options'))
        self.extract_to_source_cb.setText(self.i18n.get('extract_to_source'))
        self.use_unified_password_cb.setText(self.i18n.get('use_unified_password'))
        self.unified_password_combo.setPlaceholderText(self.i18n.get('select_or_input_password'))
        self.password_management_label.setText(self.i18n.get('password_management'))
        self.manage_passwords_btn.setText(self.i18n.get('manage_passwords'))

        # 任务配置
        self.tasks_label.setText(self.i18n.get('task_config'))
        self.add_task_btn.setText(self.i18n.get('add_task'))

        # 状态和日志
        self.status_label.setText(self.i18n.get('ready'))
        log_group = self.findChild(QGroupBox, 'log_group')
        if log_group:
            log_group.setTitle(self.i18n.get('extraction_log'))

        self.extract_btn.setText(self.i18n.get('start_extract'))

        # 更新任务组件
        self._update_task_widgets_translation()

    def _update_task_widgets_translation(self) -> None:
        """更新所有任务组件的翻译"""
        for task_widget in self.task_widgets:
            task_widget._apply_translation(self.i18n)

    def change_language(self, index: int) -> None:
        """切换语言"""
        language = self.language_combo.itemData(index)
        self.config.language = language
        self.i18n.set_language(language)
        self._apply_translation()
        save_config(self.config)

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
        task_widget._apply_translation(self.i18n)
        self.task_widgets.append(task_widget)

        # 插入到伸缩项之前
        self.tasks_layout.insertWidget(
            self.tasks_layout.count() - 1,
            task_widget
        )

        # 应用禁用状态
        self._update_task_disable_state()

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

    def _update_task_disable_state(self) -> None:
        """更新任务的禁用状态"""
        output_enabled = not self.config.extract_to_source
        password_enabled = not self.config.use_unified_password

        for task_widget in self.task_widgets:
            task_widget.set_output_enabled(output_enabled)
            task_widget.set_password_enabled(password_enabled)

    def browse_winrar(self) -> None:
        """浏览 WinRAR 可执行文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            '',
            'C:\\Program Files',
            'WinRAR (WinRAR.exe);;所有文件 (*.*)'
        )

        if file_path:
            self.winrar_path = file_path
            self.winrar_path_edit.setText(file_path)
            self.winrar_status.setText(self.i18n.get('winrar_found'))
            self.winrar_status.setStyleSheet('color: green')

    def load_saved_settings(self) -> None:
        """加载保存的设置"""
        # 设置统一密码
        if self.config.unified_password:
            # 确保统一密码在密码列表中
            if self.config.unified_password not in self.password_manager.get_all():
                # 如果不在列表中，添加到密码管理器
                self.password_manager.add_password(self.config.unified_password)
            self.unified_password_combo.setCurrentText(self.config.unified_password)

        # 更新密码下拉框
        self._update_password_combo(self.unified_password_combo)

        # 更新输出目录的启用状态
        self._update_task_disable_state()

    def on_extract_to_source_changed(self, state: int) -> None:
        """解压到原目录复选框状态改变"""
        self.config.extract_to_source = (state == Qt.Checked)
        self._update_task_disable_state()

    def on_use_unified_password_changed(self, state: int) -> None:
        """使用统一密码复选框状态改变"""
        self.config.use_unified_password = (state == Qt.Checked)
        self.unified_password_combo.setEnabled(self.config.use_unified_password)
        self._update_task_disable_state()

    def manage_passwords(self) -> None:
        """管理密码"""
        dialog = PasswordManagerDialog(self.password_manager, self.i18n, self)
        if dialog.exec_() == QDialog.Accepted:
            # 更新所有任务的密码下拉框
            saved_passwords = self.password_manager.get_all()
            for task_widget in self.task_widgets:
                task_widget.update_saved_passwords(saved_passwords)
            # 更新统一密码下拉框
            self._update_password_combo(self.unified_password_combo)
            # 立即保存设置
            self.save_settings()

    def save_settings(self) -> None:
        """保存设置"""
        self.config.winrar_path = self.winrar_path_edit.text().strip()
        self.config.extract_to_source = self.config.extract_to_source
        self.config.use_unified_password = self.config.use_unified_password
        self.config.unified_password = self.unified_password_combo.currentText().strip()
        self.config.saved_passwords = self.password_manager.get_all()
        self.config.language = self.config.language
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
            QMessageBox.warning(self, self.i18n.get('warning'), self.i18n.get('no_tasks'))
            return

        # 检查 WinRAR 路径
        winrar_path = self.winrar_path_edit.text().strip()
        if not winrar_path or not Path(winrar_path).exists():
            QMessageBox.warning(
                self,
                self.i18n.get('warning'),
                self.i18n.get('no_winrar')
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
                        self.i18n.get('warning'),
                        self.i18n.get('empty_output_dir')
                    )
                    return

                if not task['output_dir'].exists():
                    QMessageBox.warning(
                        self,
                        self.i18n.get('warning'),
                        self.i18n.get('output_dir_not_exist', str(task['output_dir']))
                    )
                    return

        # 保存设置
        self.save_settings()

        # 禁用按钮
        self._set_ui_enabled(False)

        # 清空日志
        self.log_list.clear()
        self.status_label.setText(self.i18n.get('extracting'))

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
        self.language_combo.setEnabled(enabled)

        output_enabled = enabled and not self.config.extract_to_source
        password_enabled = enabled and not self.config.use_unified_password

        for task_widget in self.task_widgets:
            task_widget.delete_btn.setEnabled(enabled)
            task_widget.select_btn.setEnabled(enabled)
            task_widget.clear_btn.setEnabled(enabled)
            task_widget.browse_btn.setEnabled(output_enabled)
            task_widget.output_path_edit.setEnabled(output_enabled)
            task_widget.password_combo.setEnabled(password_enabled)

    def update_progress(self, task_name: str, progress: int) -> None:
        """更新进度"""
        self.progress_bar.setValue(progress)
        self.status_label.setText(f'{self.i18n.get("extracting")} {task_name}')

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

        failed = total_files - success_count
        self.status_label.setText(
            self.i18n.get('extraction_complete', success_count, failed)
        )

        QMessageBox.information(
            self,
            self.i18n.get('complete'),
            self.i18n.get('extraction_complete', success_count, failed)
        )

        self.worker = None
