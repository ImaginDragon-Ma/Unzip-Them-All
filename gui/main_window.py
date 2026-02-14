# -*- coding: utf-8 -*-
"""主窗口"""

import os
from pathlib import Path
from typing import List

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QListWidget, QLabel, QLineEdit, QProgressBar,
    QFileDialog, QMessageBox, QGroupBox, QCheckBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from config.settings import Config, load_config, save_config
from core.winrar_helper import WinRARHelper
from gui.worker_thread import ExtractWorker


class ExtractorGUI(QMainWindow):
    """压缩文件批量解压工具 - 主窗口"""

    def __init__(self):
        super().__init__()
        self.selected_files: List[Path] = []
        self.worker: ExtractWorker = None
        self.config: Config = load_config()

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
        self.setGeometry(300, 300, 700, 500)

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

        # 文件选择组
        file_group = QGroupBox('文件选择')
        file_layout = QVBoxLayout()

        # 文件列表
        self.file_list = QListWidget()
        self.file_list.setFont(QFont('Arial', 10))
        file_layout.addWidget(self.file_list)

        # 按钮布局
        btn_layout = QHBoxLayout()

        self.select_btn = QPushButton('选择文件')
        self.select_btn.clicked.connect(self.select_files)
        btn_layout.addWidget(self.select_btn)

        self.clear_btn = QPushButton('清空列表')
        self.clear_btn.clicked.connect(self.clear_files)
        btn_layout.addWidget(self.clear_btn)

        file_layout.addLayout(btn_layout)
        file_group.setLayout(file_layout)
        main_layout.addWidget(file_group)

        # 输出目录
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel('输出目录:'))
        self.output_path_edit = QLineEdit(os.getcwd())
        self.output_path_edit.setFont(QFont('Arial', 10))
        output_layout.addWidget(self.output_path_edit)

        self.browse_btn = QPushButton('浏览...')
        self.browse_btn.clicked.connect(self.browse_output_dir)
        output_layout.addWidget(self.browse_btn)

        main_layout.addLayout(output_layout)

        # 密码输入
        password_layout = QHBoxLayout()
        password_layout.addWidget(QLabel('解压密码:'))
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText('无密码可留空')
        password_layout.addWidget(self.password_edit)
        main_layout.addLayout(password_layout)

        # 记住密码
        self.remember_password_cb = QCheckBox('记住密码')
        self.remember_password_cb.setChecked(self.config.remember_password)
        self.remember_password_cb.stateChanged.connect(self.on_remember_password_changed)
        main_layout.addWidget(self.remember_password_cb)

        # 解压到原目录
        self.extract_to_source_cb = QCheckBox('解压到原目录（忽略上面的输出目录设置）')
        self.extract_to_source_cb.setChecked(self.config.extract_to_source)
        self.extract_to_source_cb.stateChanged.connect(self.on_extract_to_source_changed)
        main_layout.addWidget(self.extract_to_source_cb)

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

    def select_files(self) -> None:
        """选择文件"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            '选择压缩文件',
            os.getcwd(),
            '压缩文件 (*.zip *.rar *.7z *.tar *.gz *.001 *.002 *.7z.001 *.part1.rar);;所有文件 (*.*)'
        )

        if files:
            for file_str in files:
                file_path = Path(file_str)
                if file_path not in self.selected_files:
                    self.selected_files.append(file_path)
                    self.file_list.addItem(file_path.name)
            self.status_label.setText(f'已选择 {len(self.selected_files)} 个文件')

    def clear_files(self) -> None:
        """清空文件列表"""
        self.selected_files.clear()
        self.file_list.clear()
        self.status_label.setText('准备就绪')

    def browse_output_dir(self) -> None:
        """浏览输出目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            '选择输出目录',
            os.getcwd()
        )

        if dir_path:
            self.output_path_edit.setText(dir_path)

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
        # 加载保存的密码
        if self.config.password and self.config.remember_password:
            self.password_edit.setText(self.config.password)

        # 更新输出目录的启用状态
        self.output_path_edit.setEnabled(not self.config.extract_to_source)
        self.browse_btn.setEnabled(not self.config.extract_to_source)

    def on_remember_password_changed(self, state: int) -> None:
        """记住密码复选框状态改变"""
        self.config.remember_password = (state == Qt.Checked)
        if not self.config.remember_password:
            # 取消记住时清除保存的密码
            self.config.password = ''

    def on_extract_to_source_changed(self, state: int) -> None:
        """解压到原目录复选框状态改变"""
        self.config.extract_to_source = (state == Qt.Checked)
        self.output_path_edit.setEnabled(not self.config.extract_to_source)
        self.browse_btn.setEnabled(not self.config.extract_to_source)

    def save_settings(self) -> None:
        """保存设置"""
        self.config.winrar_path = self.winrar_path_edit.text().strip()
        self.config.output_dir = self.output_path_edit.text().strip()
        self.config.extract_to_source = self.config.extract_to_source
        self.config.remember_password = self.config.remember_password
        self.config.password = self.password_edit.text().strip() if self.config.remember_password else ''
        save_config(self.config)

    def start_extract(self) -> None:
        """开始解压"""
        if not self.selected_files:
            QMessageBox.warning(self, '警告', '请先选择要解压的文件！')
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

        output_dir = self.output_path_edit.text()
        # 如果是解压到原目录模式，不需要检查输出目录
        if not self.config.extract_to_source and not Path(output_dir).is_dir():
            QMessageBox.warning(self, '警告', '输出目录不存在！')
            return

        password = self.password_edit.text().strip()
        if not password:
            password = None

        # 保存设置
        self.save_settings()

        # 禁用按钮
        self.select_btn.setEnabled(False)
        self.extract_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self.browse_btn.setEnabled(False)
        self.browse_winrar_btn.setEnabled(False)
        self.password_edit.setEnabled(False)
        self.output_path_edit.setEnabled(False)
        self.winrar_path_edit.setEnabled(False)
        self.extract_to_source_cb.setEnabled(False)
        self.remember_password_cb.setEnabled(False)

        # 清空日志
        self.log_list.clear()
        self.status_label.setText('正在解压...')

        # 启动工作线程
        self.worker = ExtractWorker(
            self.selected_files,
            Path(output_dir),
            password,
            Path(winrar_path),
            self.config.extract_to_source
        )
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.log_signal.connect(self.add_log)
        self.worker.finished_signal.connect(self.extract_finished)
        self.worker.start()

    def update_progress(self, file_name: str, progress: int) -> None:
        """更新进度"""
        self.progress_bar.setValue(progress)
        self.status_label.setText(f'正在处理: {file_name}')

    def add_log(self, message: str) -> None:
        """添加日志"""
        self.log_list.addItem(message)
        self.log_list.scrollToBottom()

    def extract_finished(self, success_count: int) -> None:
        """解压完成"""
        self.select_btn.setEnabled(True)
        self.extract_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self.browse_winrar_btn.setEnabled(True)
        self.password_edit.setEnabled(True)
        self.output_path_edit.setEnabled(not self.config.extract_to_source)
        self.browse_btn.setEnabled(not self.config.extract_to_source)
        self.winrar_path_edit.setEnabled(True)
        self.extract_to_source_cb.setEnabled(True)
        self.remember_password_cb.setEnabled(True)

        self.status_label.setText(f'解压完成！成功: {success_count}/{len(self.selected_files)}')

        QMessageBox.information(
            self,
            '完成',
            f'解压完成！\n\n成功: {success_count}\n失败: {len(self.selected_files) - success_count}'
        )

        self.worker = None
