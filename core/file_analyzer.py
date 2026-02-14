# -*- coding: utf-8 -*-
"""文件分析器：识别压缩格式、修正扩展名"""

import os
from pathlib import Path
from typing import Optional, Tuple, Callable

from config.constants import (
    ARCHIVE_EXTENSIONS,
    VOLUME_EXTENSIONS,
    NON_ARCHIVE_EXTENSIONS
)


class FileAnalyzer:
    """文件分析器：通过魔数和扩展名识别文件类型"""

    # 常见压缩文件的魔数
    MAGIC_NUMBERS = {
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
        b'\x00\x00\x00': ('MP4/RAR', None),
    }

    # 有效的压缩文件扩展名
    VALID_ARCHIVE_EXTENSIONS = {'.zip', '.rar', '.7z', '.gz', '.bz2', '.xz', '.tar'}

    @staticmethod
    def is_archive_by_extension(file_path: Path) -> bool:
        """
        通过扩展名简单判断文件是否为压缩文件

        Args:
            file_path: 文件路径

        Returns:
            bool: 是否为压缩文件
        """
        return file_path.suffix.lower() in ARCHIVE_EXTENSIONS

    @staticmethod
    def identify(
        file_path: Path,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Tuple[bool, str, str]:
        """
        检查文件是否为压缩文件，并返回详细信息

        Args:
            file_path: 文件路径
            log_callback: 日志回调函数

        Returns:
            Tuple[bool, str, str]: (是否为压缩文件, 压缩格式, 理由)
        """
        filename = file_path.name
        file_size = 0

        # 检查文件是否存在和大小
        if not file_path.exists():
            return False, None, "文件不存在"

        try:
            file_size = file_path.stat().st_size
            if file_size == 0:
                return False, None, f"文件大小为 0 字节"
        except OSError:
            pass

        # 读取文件头
        header = b''
        try:
            with open(file_path, 'rb') as f:
                header = f.read(16)  # 读取更多字节以便更准确判断
        except Exception as e:
            return False, None, f"无法读取文件头: {str(e)}"

        if len(header) < 4:
            return False, None, f"文件头长度不足 ({len(header)} 字节)"

        # 1. 通过文件头魔数判断
        for magic, (format_name, ext) in FileAnalyzer.MAGIC_NUMBERS.items():
            if header.startswith(magic):
                # 找到了魔数匹配
                current_ext = file_path.suffix.lower()

                # 如果是 MP4（和 RAR v5 的开头可能冲突）
                if magic == b'\x00\x00\x00':
                    if header.startswith(b'\x00\x00\x00\x18ftypmp42') or \
                       header.startswith(b'\x00\x00\x00\x20ftypisom'):
                        return False, 'MP4', "文件头识别为 MP4 视频文件，不是压缩文件"

                # 检查扩展名是否匹配
                if ext and current_ext != ext:
                    if ext in FileAnalyzer.VALID_ARCHIVE_EXTENSIONS:
                        return True, format_name, \
                               f"文件头识别为 {format_name} 格式，但扩展名是 {current_ext}"

                if ext in FileAnalyzer.VALID_ARCHIVE_EXTENSIONS:
                    return True, format_name, \
                           f"文件头识别为 {format_name} 格式"

                return False, format_name, \
                       f"文件头识别为 {format_name} 格式，不是压缩文件"

        # 2. 通过扩展名判断（文件头无法识别的情况）
        current_ext = file_path.suffix.lower()
        archive_extensions = {
            '.zip': 'ZIP', '.rar': 'RAR', '.7z': '7Z',
            '.tar': 'TAR', '.gz': 'GZIP', '.bz2': 'BZIP2',
            '.xz': 'XZ'
        }

        if current_ext in archive_extensions:
            # 检查是否可能是文件头伪装的压缩文件
            return True, archive_extensions[current_ext], \
                   f"扩展名为 {current_ext}，但文件头无法识别（可能是损坏或加密的压缩文件）"

        # 3. 分卷压缩判断
        if current_ext in VOLUME_EXTENSIONS:
            return True, '分卷压缩', \
                   f"扩展名为 {current_ext}，可能是分卷压缩文件"

        # 4. 常见非压缩文件格式（通过扩展名排除）
        if current_ext in NON_ARCHIVE_EXTENSIONS:
            return False, NON_ARCHIVE_EXTENSIONS[current_ext], \
                   f"扩展名为 {current_ext}，识别为 {NON_ARCHIVE_EXTENSIONS[current_ext]}"

        # 5. 无法识别
        return False, '未知格式', \
               f"无法识别文件格式（扩展名: {current_ext}, 文件大小: {file_size} 字节）"

    @staticmethod
    def fix_extension(
        file_path: Path,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Path:
        """
        根据文件信息修正压缩文件扩展名

        Args:
            file_path: 文件路径
            log_callback: 日志回调函数

        Returns:
            Path: 修正后的文件路径
        """
        # 先判断是否为压缩文件
        is_archive, format_name, reason = FileAnalyzer.identify(file_path, log_callback)

        # 如果不是压缩文件，直接返回原路径，不修改扩展名
        if not is_archive:
            if log_callback:
                log_callback(f"  [跳过扩展名修改] 不是压缩文件: {file_path.name}")
                log_callback(f"    原因: {reason}")
            return file_path

        # 是压缩文件，检查是否需要修正扩展名
        current_ext = file_path.suffix.lower()
        if current_ext in FileAnalyzer.VALID_ARCHIVE_EXTENSIONS:
            # 扩展名已经是压缩格式，不修改
            return file_path

        # 读取文件头，获取正确的扩展名
        try:
            with open(file_path, 'rb') as f:
                header = f.read(16)

            for magic, (fmt_name, ext) in FileAnalyzer.MAGIC_NUMBERS.items():
                if header.startswith(magic):
                    # 文件头匹配，修正扩展名
                    if ext:  # 确保有有效的扩展名
                        new_path = file_path.with_suffix(ext)
                        try:
                            file_path.rename(new_path)
                            if log_callback:
                                log_callback(f"  ✓ 修正扩展名: {file_path.name} → {ext}")
                                log_callback(f"    格式: {fmt_name}")
                            return new_path
                        except Exception as e:
                            if log_callback:
                                log_callback(f"  [警告] 重命名失败: {str(e)}")
                            return file_path
        except Exception as e:
            if log_callback:
                log_callback(f"  [警告] 无法读取文件头: {str(e)}")

        # 无法识别文件头，但通过扩展名判断是压缩文件的情况
        # 保持原扩展名不变，只记录日志
        if log_callback:
            log_callback(f"  [保持原扩展名] {file_path.name}")
            log_callback(f"    原因: 文件头无法识别，但扩展名表明是压缩文件")
        return file_path
