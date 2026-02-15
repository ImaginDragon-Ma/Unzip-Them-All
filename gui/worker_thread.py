# -*- coding: utf-8 -*-
"""解压工作线程"""

from pathlib import Path
from typing import List, Optional, Dict, Any

from PyQt5.QtCore import QThread, pyqtSignal

from core.extractor import FileExtractor


class ExtractWorker(QThread):
    """解压工作线程"""

    # 信号定义
    progress_signal = pyqtSignal(str, int)  # (任务名, 进度百分比)
    log_signal = pyqtSignal(str)  # 日志信息
    finished_signal = pyqtSignal(int)  # (成功数量)
    task_status_signal = pyqtSignal(int, str)  # (任务索引, 状态: pending/success/failed/processing)

    def __init__(
        self,
        tasks: List[Dict[str, Any]],
        winrar_path: Path,
        extract_to_source: bool = False,
        unified_password: Optional[str] = None
    ):
        """
        初始化工作线程

        Args:
            tasks: 任务列表，每个任务包含 files, output_dir, password
            winrar_path: WinRAR 路径
            extract_to_source: 是否解压到原目录
            unified_password: 统一密码（如果启用）
        """
        super().__init__()
        self.tasks = tasks
        self.winrar_path = winrar_path
        self.extract_to_source = extract_to_source
        self.unified_password = unified_password
        self._running = True
        self._extractor: Optional[FileExtractor] = None

    def run(self) -> None:
        """运行解压任务"""
        # 创建解压器并设置回调
        self._extractor = FileExtractor(
            winrar_path=self.winrar_path,
            progress_callback=self._on_progress,
            log_callback=self._on_log,
            should_stop_callback=self._should_stop
        )

        # 统计总文件数和成功数
        total_files = 0
        success_count = 0

        # 计算总文件数
        for task in self.tasks:
            total_files += len(task['files'])

        current_file = 0

        # 逐个处理任务
        for task_idx, task in enumerate(self.tasks):
            if not self._running:
                break

            files = task['files']
            output_dir = task['output_dir']
            password = task['password']

            # 如果使用统一密码，覆盖任务的密码
            if self.unified_password:
                password = self.unified_password

            task_name = f'任务 {task_idx + 1} ({len(files)} 个文件)'

            # 如果解压到原目录，使用每个文件的父目录作为输出目录
            if self.extract_to_source:
                # 为每个文件单独解压
                for file_path in files:
                    if not self._running:
                        break

                    self._log(f"正在处理 ({current_file+1}/{total_files}): {file_path.name} (任务 {task_idx + 1})")
                    progress = int((current_file / total_files) * 100)
                    self._progress(task_name, progress)

                    try:
                        target_output_dir = file_path.parent
                        if self._extractor._extract_recursive(file_path, target_output_dir):
                            success_count += 1
                            self._log(f"✓ 成功: {file_path.name}")
                            # 发送任务状态：成功
                            self.task_status_signal.emit(task_idx, 'success')
                        else:
                            self._log(f"✗ 失败: {file_path.name}")
                            # 发送任务状态：失败
                            self.task_status_signal.emit(task_idx, 'failed')

                    except Exception as e:
                        self._log(f"✗ 错误: {file_path.name} - {str(e)}")
                        # 发送任务状态：错误
                        self.task_status_signal.emit(task_idx, 'error')

                    current_file += 1
            else:
                # 如果有统一的输出目录，解压所有文件到该目录
                if output_dir:
                    # 使用 FileExtractor 的 _extract_batch 方法批量解压
                    if password:
                        self._extractor.password = password

                    task_success = self._extractor._extract_batch(
                        files,
                        output_dir,
                        current_file,
                        total_files,
                        task_name
                    )
                    success_count += task_success

                    # 更新任务状态
                    if task_success == len(files):
                        self.task_status_signal.emit(task_idx, 'success')
                    elif task_success > 0:
                        self.task_status_signal.emit(task_idx, 'partial')
                    else:
                        self.task_status_signal.emit(task_idx, 'failed')

                    current_file += len(files)

        # 发送完成信号
        self._progress("完成", 100)
        self.finished_signal.emit(success_count)

    def stop(self) -> None:
        """停止解压"""
        self._running = False

    def _should_stop(self) -> bool:
        """检查是否应该停止"""
        return not self._running

    def _on_progress(self, file_name: str, percent: int) -> None:
        """进度回调"""
        self.progress_signal.emit(file_name, percent)

    def _on_log(self, message: str) -> None:
        """日志回调"""
        self.log_signal.emit(message)

    def _progress(self, task_name: str, percent: int) -> None:
        """发送进度信号"""
        self.progress_signal.emit(task_name, percent)

    def _log(self, message: str) -> None:
        """发送日志信号"""
        self.log_signal.emit(message)
