#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
压缩文件批量解压工具
支持 WinRAR API，可递归解压多层压缩文件
"""

import os
import subprocess
import shutil
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QListWidget, QLabel, QLineEdit, QProgressBar,
    QFileDialog, QMessageBox, QGroupBox, QCheckBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont


class ExtractWorker(QThread):
    """解压工作线程"""
    progress_signal = pyqtSignal(str, int)  # (文件名, 进度百分比)
    log_signal = pyqtSignal(str)  # 日志信息
    finished_signal = pyqtSignal(int)  # (成功数量)

    def __init__(self, files, output_dir, password=None):
        super().__init__()
        self.files = files
        self.output_dir = output_dir
        self.password = password
        self.running = True

    def run(self):
        success_count = 0
        total_files = len(self.files)

        for idx, file_path in enumerate(self.files):
            if not self.running:
                break

            file_name = os.path.basename(file_path)
            self.log_signal.emit(f"正在处理 ({idx+1}/{total_files}): {file_name}")
            progress = int((idx / total_files) * 100)
            self.progress_signal.emit(file_name, progress)

            try:
                # 递归解压
                if self.extract_file_recursive(file_path, self.output_dir):
                    success_count += 1
                    self.log_signal.emit(f"✓ 成功: {file_name}")
                else:
                    self.log_signal.emit(f"✗ 失败: {file_name}")
            except Exception as e:
                self.log_signal.emit(f"✗ 错误: {file_name} - {str(e)}")

        self.progress_signal.emit("完成", 100)
        self.finished_signal.emit(success_count)

    def extract_file_recursive(self, file_path, output_dir, depth=0, max_depth=10):
        """
        递归解压文件

        Args:
            file_path: 文件路径
            output_dir: 输出目录
            depth: 当前递归深度
            max_depth: 最大递归深度（防止无限循环）

        Returns:
            bool: 是否成功解压
        """
        if depth > max_depth:
            self.log_signal.emit(f"  [警告] 达到最大递归深度: {file_path}")
            return False

        if not os.path.exists(file_path):
            self.log_signal.emit(f"  [错误] 文件不存在: {file_path}")
            return False

        # 创建临时解压目录
        temp_dir = os.path.join(output_dir, f"temp_extract_{depth}")
        os.makedirs(temp_dir, exist_ok=True)

        # 修正文件扩展名
        corrected_path = self.fix_archive_extension(file_path)

        # 使用 WinRAR 解压
        success = self.extract_with_winrar(corrected_path, temp_dir)

        if not success:
            # 清理临时目录
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            return False

        # 检查解压结果
        extracted_files = []
        for root, dirs, files in os.walk(temp_dir):
            for f in files:
                extracted_files.append(os.path.join(root, f))

        if not extracted_files:
            self.log_signal.emit(f"  [警告] 解压后无文件: {corrected_path}")
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            return False

        # 检查解压后的文件是否还有压缩文件
        has_archive = False
        for extracted_file in extracted_files:
            if self.is_archive_file(extracted_file):
                has_archive = True
                # 递归解压
                self.log_signal.emit(f"  发现嵌套压缩: {os.path.basename(extracted_file)}")
                inner_output = os.path.join(output_dir, os.path.splitext(os.path.basename(corrected_path))[0])
                os.makedirs(inner_output, exist_ok=True)

                self.extract_file_recursive(
                    extracted_file, inner_output, depth + 1, max_depth
                )

        # 将非压缩文件移动到根目录
        for extracted_file in extracted_files:
            if not self.is_archive_file(extracted_file) or depth > 0:
                dest_path = os.path.join(output_dir, os.path.basename(extracted_file))
                # 处理同名文件
                if os.path.exists(dest_path):
                    base, ext = os.path.splitext(dest_path)
                    counter = 1
                    while os.path.exists(f"{base}_{counter}{ext}"):
                        counter += 1
                    dest_path = f"{base}_{counter}{ext}"

                shutil.move(extracted_file, dest_path)
                self.log_signal.emit(f"  → 已移动: {os.path.basename(dest_path)}")

        # 清理临时目录
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

        return True

    def extract_with_winrar(self, file_path, output_dir):
        """使用 WinRAR 命令行解压"""
        # WinRAR 命令行参数
        # x: 完整路径解压
        # -y: 覆盖所有确认
        # -o+: 覆盖已存在文件
        # -inul: 禁用所有消息
        # -p: 密码

        cmd = ['winrar', 'x', '-y', '-o+', '-inul']

        if self.password:
            cmd.append(f'-p{self.password}')

        cmd.extend([file_path, output_dir + os.sep])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            # WinRAR 返回码: 0=成功, 其他=失败
            if result.returncode in [0, 1]:  # 0=成功, 1=警告但成功
                return True
            else:
                self.log_signal.emit(f"  [WinRAR] 返回码: {result.returncode}")
                if result.stderr:
                    self.log_signal.emit(f"  [WinRAR] 错误: {result.stderr}")
                return False
        except FileNotFoundError:
            self.log_signal.emit("  [错误] 未找到 WinRAR，请确认已安装 WinRAR")
            return False
        except Exception as e:
            self.log_signal.emit(f"  [错误] 解压失败: {str(e)}")
            return False

    def is_archive_file(self, file_path):
        """判断文件是否为压缩文件"""
        archive_extensions = {
            '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz',
            '.001', '.002', '.003', '.004', '.005',  # 分卷压缩
        }
        return os.path.splitext(file_path)[1].lower() in archive_extensions

    def fix_archive_extension(self, file_path):
        """
        根据文件信息修正压缩文件扩展名

        检测文件头魔数（magic number）来确定实际压缩格式
        """
        # 常见压缩文件的魔数
        magic_numbers = {
            b'\x50\x4B\x03\x04': '.zip',  # ZIP
            b'\x50\x4B\x05\x06': '.zip',  # ZIP (空)
            b'\x50\x4B\x07\x08': '.zip',  # ZIP
            b'\x52\x61\x72\x21': '.rar',  # RAR v1.5
            b'\x52\x61\x72\x21\x1A\x07': '.rar',  # RAR v5.0
            b'\x37\x7A\xBC\xAF\x27\x1C': '.7z',  # 7Z
            b'\x1F\x8B': '.gz',  # GZIP
        }

        # 检查当前扩展名是否正确
        current_ext = os.path.splitext(file_path)[1].lower()
        if current_ext in ['.zip', '.rar', '.7z', '.gz', '.tar']:
            return file_path

        # 读取文件头
        try:
            with open(file_path, 'rb') as f:
                header = f.read(8)

            for magic, ext in magic_numbers.items():
                if header.startswith(magic):
                    # 文件头匹配，修正扩展名
                    new_path = os.path.splitext(file_path)[0] + ext
                    try:
                        os.rename(file_path, new_path)
                        self.log_signal.emit(f"  修正扩展名: {os.path.basename(file_path)} → {ext}")
                        return new_path
                    except Exception as e:
                        self.log_signal.emit(f"  [警告] 重命名失败: {str(e)}")
                        return file_path
        except Exception as e:
            self.log_signal.emit(f"  [警告] 无法读取文件头: {str(e)}")

        # 无法识别，默认为 .zip
        new_path = os.path.splitext(file_path)[0] + '.zip'
        try:
            os.rename(file_path, new_path)
            self.log_signal.emit(f"  默认扩展名: {os.path.basename(file_path)} → .zip")
            return new_path
        except Exception:
            return file_path


class ExtractorGUI(QMainWindow):
    """压缩文件批量解压工具 - 图形界面"""

    def __init__(self):
        super().__init__()
        self.selected_files = []
        self.worker = None
        self.init_ui()

    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle('压缩文件批量解压工具')
        self.setGeometry(300, 300, 700, 500)

        # 中央窗口
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout(central_widget)

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

    def select_files(self):
        """选择文件"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            '选择压缩文件',
            os.getcwd(),
            '压缩文件 (*.zip *.rar *.7z *.tar *.gz *.001 *.002 *.7z.001 *.part1.rar);;所有文件 (*.*)'
        )

        if files:
            for file in files:
                if file not in self.selected_files:
                    self.selected_files.append(file)
                    self.file_list.addItem(os.path.basename(file))
            self.status_label.setText(f'已选择 {len(self.selected_files)} 个文件')

    def clear_files(self):
        """清空文件列表"""
        self.selected_files.clear()
        self.file_list.clear()
        self.status_label.setText('准备就绪')

    def browse_output_dir(self):
        """浏览输出目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            '选择输出目录',
            os.getcwd()
        )

        if dir_path:
            self.output_path_edit.setText(dir_path)

    def start_extract(self):
        """开始解压"""
        if not self.selected_files:
            QMessageBox.warning(self, '警告', '请先选择要解压的文件！')
            return

        output_dir = self.output_path_edit.text()
        if not os.path.isdir(output_dir):
            QMessageBox.warning(self, '警告', '输出目录不存在！')
            return

        password = self.password_edit.text().strip()
        if not password:
            password = None

        # 禁用按钮
        self.select_btn.setEnabled(False)
        self.extract_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self.browse_btn.setEnabled(False)
        self.password_edit.setEnabled(False)
        self.output_path_edit.setEnabled(False)

        # 清空日志
        self.log_list.clear()
        self.status_label.setText('正在解压...')

        # 启动工作线程
        self.worker = ExtractWorker(self.selected_files, output_dir, password)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.log_signal.connect(self.add_log)
        self.worker.finished_signal.connect(self.extract_finished)
        self.worker.start()

    def update_progress(self, file_name, progress):
        """更新进度"""
        self.progress_bar.setValue(progress)
        self.status_label.setText(f'正在处理: {file_name}')

    def add_log(self, message):
        """添加日志"""
        self.log_list.addItem(message)
        self.log_list.scrollToBottom()

    def extract_finished(self, success_count):
        """解压完成"""
        self.select_btn.setEnabled(True)
        self.extract_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self.password_edit.setEnabled(True)
        self.output_path_edit.setEnabled(True)

        self.status_label.setText(f'解压完成！成功: {success_count}/{len(self.selected_files)}')

        QMessageBox.information(
            self,
            '完成',
            f'解压完成！\n\n成功: {success_count}\n失败: {len(self.selected_files) - success_count}'
        )


def main():
    app = QApplication([])
    app.setStyle('Fusion')  # 使用 Fusion 样式

    window = ExtractorGUI()
    window.show()

    app.exec_()


if __name__ == '__main__':
    main()
