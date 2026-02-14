#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
压缩文件批量解压工具
支持 WinRAR API，可递归解压多层压缩文件
"""

import os
import subprocess
import shutil
import json
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QListWidget, QLabel, QLineEdit, QProgressBar,
    QFileDialog, QMessageBox, QGroupBox, QCheckBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont


# 配置文件路径
CONFIG_FILE = 'extractor_config.json'


def load_config():
    """加载配置"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_config(config):
    """保存配置"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存配置失败: {e}")


def find_winrar_path():
    """
    查找 WinRAR 可执行文件的路径

    Returns:
        str: WinRAR 完整路径，如果找不到返回 None
    """
    import glob

    # 1. 尝试从 PATH 环境变量查找
    winrar_path = shutil.which('winrar')
    if winrar_path:
        return winrar_path

    # 2. 尝试从 PATH 环境变量查找 winrar.exe
    winrar_path = shutil.which('winrar.exe')
    if winrar_path:
        return winrar_path

    # 3. 尝试常见的安装路径
    common_paths = [
        r'C:\Program Files\WinRAR\WinRAR.exe',
        r'C:\Program Files (x86)\WinRAR\WinRAR.exe',
        r'C:\WinRAR\WinRAR.exe',
        r'D:\Program Files\WinRAR\WinRAR.exe',
        r'D:\Program Files (x86)\WinRAR\WinRAR.exe',
        r'D:\WinRAR\WinRAR.exe',
        os.path.join(os.environ.get('ProgramFiles', ''), 'WinRAR', 'WinRAR.exe'),
        os.path.join(os.environ.get('ProgramFiles(x86)', ''), 'WinRAR', 'WinRAR.exe'),
    ]

    for path in common_paths:
        if os.path.exists(path):
            return path

    # 4. 使用 glob 搜索多个驱动器
    for drive in ['C', 'D', 'E', 'F']:
        try:
            # 搜索 Program Files 和 Program Files (x86)
            matches = glob.glob(f'{drive}:\\Program Files*\\WinRAR\\WinRAR.exe')
            for match in matches:
                if os.path.exists(match):
                    return match
        except Exception:
            pass

    # 5. 尝试从系统环境变量 PATH 搜索
    path_env = os.environ.get('PATH', '')
    for dir_path in path_env.split(os.pathsep):
        try:
            potential_path = os.path.join(dir_path, 'winrar.exe')
            if os.path.exists(potential_path):
                return potential_path
            potential_path = os.path.join(dir_path, 'winrar')
            if os.path.exists(potential_path):
                return potential_path
        except Exception:
            pass

    return None


class ExtractWorker(QThread):
    """解压工作线程"""
    progress_signal = pyqtSignal(str, int)  # (文件名, 进度百分比)
    log_signal = pyqtSignal(str)  # 日志信息
    finished_signal = pyqtSignal(int)  # (成功数量)

    def __init__(self, files, output_dir, password=None, winrar_path=None,
                 extract_to_source=False):
        super().__init__()
        self.files = files
        self.output_dir = output_dir
        self.password = password
        self.winrar_path = winrar_path
        self.extract_to_source = extract_to_source
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
                # 确定输出目录
                if self.extract_to_source:
                    # 解压到文件所在目录
                    target_output_dir = os.path.dirname(file_path)
                else:
                    # 解压到指定目录
                    target_output_dir = self.output_dir

                # 递归解压
                if self.extract_file_recursive(file_path, target_output_dir):
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
            # 先修正扩展名，再检查是否为压缩文件
            fixed_file = self.fix_archive_extension(extracted_file)

            if self.is_archive_file(fixed_file):
                has_archive = True
                # 递归解压
                self.log_signal.emit(f"  发现嵌套压缩: {os.path.basename(fixed_file)}")
                inner_output = os.path.join(output_dir, os.path.splitext(os.path.basename(corrected_path))[0])
                os.makedirs(inner_output, exist_ok=True)

                self.extract_file_recursive(
                    fixed_file, inner_output, depth + 1, max_depth
                )

        # 将非压缩文件移动到根目录
        for extracted_file in extracted_files:
            # 先修正扩展名
            fixed_file = self.fix_archive_extension(extracted_file)
            if not self.is_archive_file(fixed_file) or depth > 0:
                dest_path = os.path.join(output_dir, os.path.basename(fixed_file))
                # 处理同名文件
                if os.path.exists(dest_path):
                    base, ext = os.path.splitext(dest_path)
                    counter = 1
                    while os.path.exists(f"{base}_{counter}{ext}"):
                        counter += 1
                    dest_path = f"{base}_{counter}{ext}"

                # 移动文件（使用修正后的路径，如果修正成功的话）
                src_file = fixed_file if os.path.exists(fixed_file) else extracted_file
                if os.path.exists(src_file):
                    shutil.move(src_file, dest_path)
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

        # 方法1: 使用完整路径
        if self.winrar_path and os.path.exists(self.winrar_path):
            cmd = [self.winrar_path, 'x', '-y', '-o+', '-inul']
            if self.password:
                cmd.append(f'-p{self.password}')
            cmd.extend([file_path, output_dir + os.sep])

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    encoding='gbk',
                    errors='ignore'
                )

                if result.returncode in [0, 1]:
                    return True
                else:
                    self.log_signal.emit(f"  [WinRAR] 返回码: {result.returncode}")
                    if result.stderr:
                        self.log_signal.emit(f"  [WinRAR] 错误: {result.stderr}")
                    if result.stdout:
                        self.log_signal.emit(f"  [WinRAR] 输出: {result.stdout}")
                    return False
            except FileNotFoundError:
                self.log_signal.emit(f"  [警告] 无法使用路径: {self.winrar_path}")
            except Exception as e:
                self.log_signal.emit(f"  [错误] 解压失败: {str(e)}")

        # 方法2: 使用 shell=True 后备方案
        self.log_signal.emit("  [尝试] 使用 shell 方式调用 WinRAR...")
        cmd_str = f'winrar x -y -o+ -inul'
        if self.password:
            cmd_str += f' -p{self.password}'
        cmd_str += f' "{file_path}" "{output_dir}\\"'

        try:
            result = subprocess.run(
                cmd_str,
                shell=True,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                encoding='gbk',
                errors='ignore'
            )

            if result.returncode in [0, 1]:
                self.log_signal.emit("  [成功] shell 方式调用成功")
                return True
            else:
                self.log_signal.emit(f"  [WinRAR] 返回码: {result.returncode}")
                if result.stderr:
                    self.log_signal.emit(f"  [WinRAR] 错误: {result.stderr}")
                if result.stdout:
                    self.log_signal.emit(f"  [WinRAR] 输出: {result.stdout}")
                return False
        except Exception as e:
            self.log_signal.emit(f"  [错误] shell 方式调用失败: {str(e)}")
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
        self.winrar_path = find_winrar_path()

        # 加载配置
        config = load_config()
        self.saved_password = config.get('password', '')
        self.remember_password = config.get('remember_password', False)
        self.extract_to_source = config.get('extract_to_source', False)

        self.init_ui()
        self.load_saved_settings()

    def init_ui(self):
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
        self.winrar_status = QLabel('✓' if self.winrar_path else '✗ 未找到')
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
        self.remember_password_cb.setChecked(self.remember_password)
        self.remember_password_cb.stateChanged.connect(self.on_remember_password_changed)
        main_layout.addWidget(self.remember_password_cb)

        # 解压到原目录
        self.extract_to_source_cb = QCheckBox('解压到原目录（忽略上面的输出目录设置）')
        self.extract_to_source_cb.setChecked(self.extract_to_source)
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

    def browse_winrar(self):
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

    def load_saved_settings(self):
        """加载保存的设置"""
        # 加载保存的密码
        if self.saved_password and self.remember_password:
            self.password_edit.setText(self.saved_password)

        # 更新输出目录的启用状态
        self.output_path_edit.setEnabled(not self.extract_to_source)
        self.browse_btn.setEnabled(not self.extract_to_source)

    def on_remember_password_changed(self, state):
        """记住密码复选框状态改变"""
        self.remember_password = (state == Qt.Checked)
        if not self.remember_password:
            # 取消记住时清除保存的密码
            self.saved_password = ''

    def on_extract_to_source_changed(self, state):
        """解压到原目录复选框状态改变"""
        self.extract_to_source = (state == Qt.Checked)
        self.output_path_edit.setEnabled(not self.extract_to_source)
        self.browse_btn.setEnabled(not self.extract_to_source)

    def save_settings(self):
        """保存设置"""
        config = {
            'winrar_path': self.winrar_path_edit.text().strip(),
            'output_dir': self.output_path_edit.text().strip(),
            'extract_to_source': self.extract_to_source,
            'remember_password': self.remember_password,
            'password': self.password_edit.text().strip() if self.remember_password else ''
        }
        save_config(config)

    def start_extract(self):
        """开始解压"""
        if not self.selected_files:
            QMessageBox.warning(self, '警告', '请先选择要解压的文件！')
            return

        # 检查 WinRAR 路径
        winrar_path = self.winrar_path_edit.text().strip()
        if not winrar_path or not os.path.exists(winrar_path):
            QMessageBox.warning(
                self,
                '警告',
                '未找到 WinRAR！\n\n请点击"浏览..."按钮选择 WinRAR.exe 的位置。'
            )
            return

        output_dir = self.output_path_edit.text()
        # 如果是解压到原目录模式，不需要检查输出目录
        if not self.extract_to_source and not os.path.isdir(output_dir):
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
            output_dir,
            password,
            winrar_path,
            self.extract_to_source
        )
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
        self.browse_winrar_btn.setEnabled(True)
        self.password_edit.setEnabled(True)
        self.output_path_edit.setEnabled(not self.extract_to_source)
        self.browse_btn.setEnabled(not self.extract_to_source)
        self.winrar_path_edit.setEnabled(True)
        self.extract_to_source_cb.setEnabled(True)
        self.remember_password_cb.setEnabled(True)

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
