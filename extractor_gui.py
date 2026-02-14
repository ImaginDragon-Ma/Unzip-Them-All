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
        archive_files = []
        non_archive_files = []

        for extracted_file in extracted_files:
            # 先判断是否为压缩文件
            is_archive, format_name, reason = self.check_and_identify_archive(extracted_file)

            file_basename = os.path.basename(extracted_file)

            if is_archive:
                # 只有确认是压缩文件，才尝试修正扩展名
                fixed_file = self.fix_archive_extension(extracted_file)
                archive_files.append(fixed_file)
                fixed_basename = os.path.basename(fixed_file)
                self.log_signal.emit(f"  ✓ 压缩文件: {fixed_basename}")
                self.log_signal.emit(f"    格式: {format_name}")
                self.log_signal.emit(f"    理由: {reason}")
            else:
                # 非压缩文件，保持原文件名，不修改扩展名
                non_archive_files.append(extracted_file)
                self.log_signal.emit(f"  ✗ 非压缩文件: {file_basename}")
                self.log_signal.emit(f"    识别: {format_name}")
                self.log_signal.emit(f"    理由: {reason}")

        # 递归解压嵌套的压缩文件
        if archive_files:
            self.log_signal.emit(f"  开始处理 {len(archive_files)} 个嵌套压缩文件...")
            inner_output = os.path.join(output_dir, os.path.splitext(os.path.basename(corrected_path))[0])
            os.makedirs(inner_output, exist_ok=True)

            for archive_file in archive_files:
                self.extract_file_recursive(
                    archive_file, inner_output, depth + 1, max_depth
                )

        # 将非压缩文件移动到根目录
        if non_archive_files:
            self.log_signal.emit(f"  移动 {len(non_archive_files)} 个非压缩文件到根目录...")
            for non_archive_file in non_archive_files:
                dest_path = os.path.join(output_dir, os.path.basename(non_archive_file))
                # 处理同名文件
                if os.path.exists(dest_path):
                    base, ext = os.path.splitext(dest_path)
                    counter = 1
                    while os.path.exists(f"{base}_{counter}{ext}"):
                        counter += 1
                    dest_path = f"{base}_{counter}{ext}"
                    self.log_signal.emit(f"    同名文件重命名: {os.path.basename(non_archive_file)} → {os.path.basename(dest_path)}")

                # 移动文件（保持原文件名）
                if os.path.exists(non_archive_file):
                    shutil.move(non_archive_file, dest_path)
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
        """判断文件是否为压缩文件（简单版，只检查扩展名）"""
        archive_extensions = {
            '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz',
            '.001', '.002', '.003', '.004', '.005',  # 分卷压缩
        }
        return os.path.splitext(file_path)[1].lower() in archive_extensions

    def check_and_identify_archive(self, file_path):
        """
        检查文件是否为压缩文件，并返回详细信息

        Returns:
            tuple: (是否为压缩文件, 压缩格式, 理由)
        """
        # 常见压缩文件的魔数
        magic_numbers = {
            b'\x50\x4B\x03\x04': ('ZIP', '.zip'),
            b'\x50\x4B\x05\x06': ('ZIP', '.zip'),
            b'\x50\x4B\x07\x08': ('ZIP', '.zip'),
            b'\x52\x61\x72\x21': ('RAR', '.rar'),
            b'\x52\x61\x72\x21\x1A\x07': ('RAR v5', '.rar'),
            b'\x37\x7A\xBC\xAF\x27\x1C': ('7Z', '.7z'),
            b'\x1F\x8B': ('GZIP', '.gz'),
            b'\x42\x5A\x68': ('BZIP2', '.bz2'),
            b'\xFD\x37\x7A\x58\x5A\x00': ('XZ', '.xz'),
            # 其他可能的可识别文件
            b'\x25\x50\x44\x46': ('PDF', '.pdf'),
            b'\x50\x33\x52\x33': ('MP3', '.mp3'),
            b'\x00\x00\x00': ('MP4/RAR', None),  # 需要进一步判断
        }

        filename = os.path.basename(file_path)
        file_size = 0

        # 检查文件是否存在和大小
        if not os.path.exists(file_path):
            return (False, None, f"文件不存在")

        try:
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                return (False, None, f"文件大小为 0 字节")
        except Exception:
            pass

        # 读取文件头
        header = b''
        try:
            with open(file_path, 'rb') as f:
                header = f.read(16)  # 读取更多字节以便更准确判断
        except Exception as e:
            return (False, None, f"无法读取文件头: {str(e)}")

        if len(header) < 4:
            return (False, None, f"文件头长度不足 ({len(header)} 字节)")

        # 1. 通过文件头魔数判断
        for magic, (format_name, ext) in magic_numbers.items():
            if header.startswith(magic):
                # 找到了魔数匹配
                current_ext = os.path.splitext(file_path)[1].lower()

                # 如果是 MP4（和 RAR v5 的开头可能冲突）
                if magic == b'\x00\x00\x00':
                    if header.startswith(b'\x00\x00\x00\x18ftypmp42') or \
                       header.startswith(b'\x00\x00\x00\x20ftypisom'):
                        return (False, 'MP4', f"文件头识别为 MP4 视频文件，不是压缩文件")

                # 检查扩展名是否匹配
                if ext and current_ext != ext:
                    if ext in ['.zip', '.rar', '.7z', '.gz']:
                        return (True, format_name,
                               f"文件头识别为 {format_name} 格式，但扩展名是 {current_ext}")

                if ext in ['.zip', '.rar', '.7z', '.gz', '.bz2', '.xz', '.tar']:
                    return (True, format_name,
                           f"文件头识别为 {format_name} 格式")

                return (False, format_name,
                       f"文件头识别为 {format_name} 格式，不是压缩文件")

        # 2. 通过扩展名判断（文件头无法识别的情况）
        current_ext = os.path.splitext(file_path)[1].lower()
        archive_extensions = {
            '.zip': 'ZIP', '.rar': 'RAR', '.7z': '7Z',
            '.tar': 'TAR', '.gz': 'GZIP', '.bz2': 'BZIP2',
            '.xz': 'XZ'
        }

        if current_ext in archive_extensions:
            # 检查是否可能是文件头伪装的压缩文件（比如把 .exe 改名为 .zip）
            # 如果扩展名是压缩格式，但文件头不匹配，给出警告
            return (True, archive_extensions[current_ext],
                   f"扩展名为 {current_ext}，但文件头无法识别（可能是损坏或加密的压缩文件）")

        # 3. 分卷压缩判断
        if current_ext in ['.001', '.002', '.003', '.004', '.005', '.006', '.007', '.008', '.009']:
            return (True, '分卷压缩',
                   f"扩展名为 {current_ext}，可能是分卷压缩文件")

        # 4. 常见非压缩文件格式（通过扩展名排除）
        non_archive_exts = {
            '.txt': '文本文件', '.doc': 'Word', '.docx': 'Word',
            '.xls': 'Excel', '.xlsx': 'Excel', '.ppt': 'PowerPoint',
            '.pdf': 'PDF', '.jpg': 'JPEG', '.jpeg': 'JPEG',
            '.png': 'PNG', '.gif': 'GIF', '.bmp': 'BMP',
            '.mp3': 'MP3', '.mp4': 'MP4', '.avi': 'AVI',
            '.mkv': 'MKV', '.flv': 'FLV', '.wmv': 'WMV',
            '.exe': '可执行文件', '.dll': '动态链接库',
            '.iso': 'ISO 镜像', '.img': 'IMG 镜像'
        }

        if current_ext in non_archive_exts:
            return (False, non_archive_exts[current_ext],
                   f"扩展名为 {current_ext}，识别为 {non_archive_exts[current_ext]}")

        # 5. 无法识别
        return (False, '未知格式',
               f"无法识别文件格式（扩展名: {current_ext}, 文件大小: {file_size} 字节）")

    def fix_archive_extension(self, file_path):
        """
        根据文件信息修正压缩文件扩展名

        只在确认文件是压缩格式时才修改扩展名，避免破坏非压缩文件
        """
        # 先判断是否为压缩文件
        is_archive, format_name, reason = self.check_and_identify_archive(file_path)

        # 如果不是压缩文件，直接返回原路径，不修改扩展名
        if not is_archive:
            self.log_signal.emit(f"  [跳过扩展名修改] 不是压缩文件: {os.path.basename(file_path)}")
            self.log_signal.emit(f"    原因: {reason}")
            return file_path

        # 是压缩文件，检查是否需要修正扩展名
        # 常见压缩文件的魔数
        magic_numbers = {
            b'\x50\x4B\x03\x04': ('ZIP', '.zip'),  # ZIP
            b'\x50\x4B\x05\x06': ('ZIP', '.zip'),  # ZIP (空)
            b'\x50\x4B\x07\x08': ('ZIP', '.zip'),  # ZIP
            b'\x52\x61\x72\x21': ('RAR', '.rar'),  # RAR v1.5
            b'\x52\x61\x72\x21\x1A\x07': ('RAR v5', '.rar'),  # RAR v5.0
            b'\x37\x7A\xBC\xAF\x27\x1C': ('7Z', '.7z'),  # 7Z
            b'\x1F\x8B': ('GZIP', '.gz'),  # GZIP
            b'\x42\x5A\x68': ('BZIP2', '.bz2'),  # BZIP2
            b'\xFD\x37\x7A\x58\x5A\x00': ('XZ', '.xz'),  # XZ
        }

        # 检查当前扩展名是否已经是正确的压缩格式
        current_ext = os.path.splitext(file_path)[1].lower()
        valid_extensions = {'.zip', '.rar', '.7z', '.gz', '.bz2', '.xz', '.tar'}
        if current_ext in valid_extensions:
            # 扩展名已经是压缩格式，不修改
            return file_path

        # 读取文件头，获取正确的扩展名
        try:
            with open(file_path, 'rb') as f:
                header = f.read(16)

            for magic, (format_name, ext) in magic_numbers.items():
                if header.startswith(magic):
                    # 文件头匹配，修正扩展名
                    if ext:  # 确保有有效的扩展名
                        new_path = os.path.splitext(file_path)[0] + ext
                        try:
                            os.rename(file_path, new_path)
                            self.log_signal.emit(f"  ✓ 修正扩展名: {os.path.basename(file_path)} → {ext}")
                            self.log_signal.emit(f"    格式: {format_name}")
                            return new_path
                        except Exception as e:
                            self.log_signal.emit(f"  [警告] 重命名失败: {str(e)}")
                            return file_path
        except Exception as e:
            self.log_signal.emit(f"  [警告] 无法读取文件头: {str(e)}")

        # 无法识别文件头，但通过扩展名判断是压缩文件的情况
        # 保持原扩展名不变，只记录日志
        self.log_signal.emit(f"  [保持原扩展名] {os.path.basename(file_path)}")
        self.log_signal.emit(f"    原因: 文件头无法识别，但扩展名表明是压缩文件")
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
