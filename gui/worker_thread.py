# -*- coding: utf-8 -*-
"""解压工作线程"""

from pathlib import Path
from typing import List, Optional

from PyQt5.QtCore import QThread, pyqtSignal

from core.extractor import FileExtractor


class ExtractWorker(QThread):
    """解压工作线程"""

    # 信号定义
    progress_signal = pyqtSignal(str, int)  # (文件名, 进度百分比)
    log_signal = pyqtSignal(str)  # 日志信息
    finished_signal = pyqtSignal(int)  # (成功数量)

    def __init__(
        self,
        files: List[Path],
        output_dir: Path,
        password: Optional[str] = None,
        winrar_path: Optional[Path] = None,
        extract_to_source: bool = False
    ):
        """
        初始化工作线程

        Args:
            files: 要解压的文件列表
            output_dir: 输出目录
            password: 解压密码
            winrar_path: WinRAR 路径
            extract_to_source: 是否解压到原目录
        """
        super().__init__()
        self.files = files
        self.output_dir = output_dir
        self.password = password
        self.winrar_path = winrar_path
        self.extract_to_source = extract_to_source
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

        # 执行解压
        success_count = self._extractor.extract(
            self.files,
            self.output_dir,
            password=self.password,
            extract_to_source=self.extract_to_source
        )

        # 发送完成信号
        self.progress_signal.emit("完成", 100)
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
