# -*- coding: utf-8 -*-
"""核心解压逻辑"""

import os
import shutil
from pathlib import Path
from typing import Optional, Callable, List

from core.file_analyzer import FileAnalyzer
from core.winrar_helper import WinRARHelper
from config.constants import MAX_RECURSION_DEPTH


class FileExtractor:
    """文件解压器核心类"""

    def __init__(
        self,
        winrar_path: Optional[Path] = None,
        progress_callback: Optional[Callable[[str, int], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None,
        should_stop_callback: Optional[Callable[[], bool]] = None
    ):
        """
        初始化解压器

        Args:
            winrar_path: WinRAR 可执行文件路径
            progress_callback: 进度回调函数 (文件名, 百分比)
            log_callback: 日志回调函数 (消息)
            should_stop_callback: 是否停止回调函数
        """
        self.winrar_path = winrar_path or WinRARHelper.find_path()
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        self.should_stop_callback = should_stop_callback
        self.password: Optional[str] = None

    def _log(self, message: str) -> None:
        """记录日志"""
        if self.log_callback:
            self.log_callback(message)

    def _should_stop(self) -> bool:
        """检查是否应该停止"""
        if self.should_stop_callback:
            return self.should_stop_callback()
        return False

    def _progress(self, file_name: str, percent: int) -> None:
        """更新进度"""
        if self.progress_callback:
            self.progress_callback(file_name, percent)

    def extract(
        self,
        files: List[Path],
        output_dir: Path,
        password: Optional[str] = None,
        extract_to_source: bool = False
    ) -> int:
        """
        批量解压文件

        Args:
            files: 文件路径列表
            output_dir: 输出目录
            password: 解压密码
            extract_to_source: 是否解压到原目录

        Returns:
            int: 成功解压的文件数量
        """
        # 设置密码
        self.password = password

        success_count = 0
        total_files = len(files)

        for idx, file_path in enumerate(files):
            if self._should_stop():
                break

            self._log(f"正在处理 ({idx+1}/{total_files}): {file_path.name}")
            progress = int((idx / total_files) * 100)
            self._progress(file_path.name, progress)

            try:
                # 确定输出目录
                if extract_to_source:
                    target_output_dir = file_path.parent
                else:
                    target_output_dir = output_dir

                # 递归解压
                if self._extract_recursive(file_path, target_output_dir):
                    success_count += 1
                    self._log(f"✓ 成功: {file_path.name}")
                else:
                    self._log(f"✗ 失败: {file_path.name}")
            except Exception as e:
                self._log(f"✗ 错误: {file_path.name} - {str(e)}")

        self._progress("完成", 100)
        return success_count

    def _extract_recursive(
        self,
        file_path: Path,
        output_dir: Path,
        depth: int = 0,
        final_output_dir: Optional[Path] = None
    ) -> bool:
        """
        递归解压文件

        Args:
            file_path: 文件路径
            output_dir: 当前解压输出目录
            depth: 当前递归深度
            final_output_dir: 最终根目录（所有非压缩文件的最终目的地）

        Returns:
            bool: 是否成功解压
        """
        if depth > MAX_RECURSION_DEPTH:
            self._log(f"  [警告] 达到最大递归深度: {file_path.name}")
            return False

        if not file_path.exists():
            self._log(f"  [错误] 文件不存在: {file_path}")
            return False

        # 如果没有指定 final_output_dir，使用当前的 output_dir
        if final_output_dir is None:
            final_output_dir = output_dir

        # 创建临时解压目录
        temp_dir = output_dir / f"temp_extract_{depth}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        # 修正文件扩展名
        corrected_path = FileAnalyzer.fix_extension(file_path, self._log)

        # 使用 WinRAR 解压
        success, _ = WinRARHelper.extract(
            corrected_path,
            temp_dir,
            self.winrar_path,
            password=self.password,
            log_callback=self._log
        )

        if not success:
            # 清理临时目录
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
            return False

        # 检查解压结果
        extracted_files = list(temp_dir.rglob('*'))
        extracted_files = [f for f in extracted_files if f.is_file()]

        if not extracted_files:
            self._log(f"  [警告] 解压后无文件: {corrected_path.name}")
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
            return False

        # 检查解压后的文件是否还有压缩文件
        archive_files = []
        non_archive_files = []

        for extracted_file in extracted_files:
            # 先判断是否为压缩文件
            is_archive, format_name, reason = FileAnalyzer.identify(extracted_file, self._log)

            if is_archive:
                # 只有确认是压缩文件，才尝试修正扩展名
                fixed_file = FileAnalyzer.fix_extension(extracted_file, self._log)
                archive_files.append(fixed_file)
                self._log(f"  ✓ 压缩文件: {fixed_file.name}")
                self._log(f"    格式: {format_name}")
                self._log(f"    理由: {reason}")
            else:
                # 非压缩文件，保持原文件名，不修改扩展名
                non_archive_files.append(extracted_file)
                self._log(f"  ✗ 非压缩文件: {extracted_file.name}")
                self._log(f"    识别: {format_name}")
                self._log(f"    理由: {reason}")

        # 递归解压嵌套的压缩文件
        if archive_files:
            self._log(f"  开始处理 {len(archive_files)} 个嵌套压缩文件...")
            inner_output = output_dir / corrected_path.stem
            inner_output.mkdir(parents=True, exist_ok=True)

            for archive_file in archive_files:
                self._extract_recursive(
                    archive_file, inner_output, depth + 1, final_output_dir
                )

        # 将非压缩文件/文件夹移动到最终根目录
        if non_archive_files:
            self._log(f"  移动 {len(non_archive_files)} 个非压缩文件/文件夹到根目录...")

            # 保持目录结构，使用相对路径
            for source_path in non_archive_files:
                # 获取相对于 temp_dir 的相对路径
                rel_path = source_path.relative_to(temp_dir)
                dest_path = final_output_dir / rel_path

                # 确保目标父目录存在
                dest_parent = dest_path.parent
                if dest_parent != final_output_dir:
                    dest_parent.mkdir(parents=True, exist_ok=True)

                # 如果源是目录，递归处理
                if source_path.is_dir():
                    # 处理同名目录
                    if dest_path.exists():
                        self._log(f"  [警告] 目标目录已存在: {rel_path}")
                        # 可以选择合并或重命名，这里选择重命名
                        base_name = rel_path
                        counter = 1
                        while (final_output_dir / f"{base_name}_{counter}").exists():
                            counter += 1
                        new_dest = final_output_dir / f"{base_name}_{counter}"
                        shutil.move(str(source_path), str(new_dest))
                        self._log(f"    目录重命名移动: {rel_path} → {new_dest.name}")
                    else:
                        shutil.move(str(source_path), str(dest_path))
                        self._log(f"  → 已移动目录: {rel_path}")
                else:
                    # 处理同名文件
                    if dest_path.exists():
                        base = dest_path.stem
                        ext = dest_path.suffix
                        counter = 1
                        while dest_path.with_name(f"{base}_{counter}{ext}").exists():
                            counter += 1
                        dest_path = dest_path.with_name(f"{base}_{counter}{ext}")
                        self._log(f"    同名文件重命名: {rel_path} → {dest_path.name}")

                    # 移动文件
                    if source_path.exists():
                        shutil.move(str(source_path), str(dest_path))
                        self._log(f"  → 已移动文件: {rel_path}")

        # 清理临时目录
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)

        return True

    def stop(self) -> None:
        """停止解压"""
        if self.should_stop_callback:
            self.should_stop_callback()
