
from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from core.file_transfer import FileTransferManager, TransferResult


class FilePushThread(QThread):
    """把本地文件推送到手机（不阻塞 UI）。"""

    finished_with_result = Signal(str, object)

    def __init__(self, manager: FileTransferManager, serial: str,
                 local_paths: list[str], remote_dir: str, parent=None) -> None:
        super().__init__(parent)
        self.manager = manager
        self.serial = serial
        self.local_paths = list(local_paths)
        self.remote_dir = remote_dir

    def run(self) -> None:
        try:
            result: TransferResult = self.manager.push_files(
                self.serial, self.local_paths, self.remote_dir
            )
        except Exception as error:
            result = TransferResult(len(self.local_paths), 0, len(self.local_paths), (str(error),))
        self.finished_with_result.emit(self.serial, result)


class FilePullThread(QThread):
    """把手机文件拉取到电脑（不阻塞 UI）。"""

    finished_with_result = Signal(str, object)

    def __init__(self, manager: FileTransferManager, serial: str,
                 remote_paths: list[str], local_dir: str, parent=None) -> None:
        super().__init__(parent)
        self.manager = manager
        self.serial = serial
        self.remote_paths = list(remote_paths)
        self.local_dir = local_dir

    def run(self) -> None:
        try:
            result = self.manager.pull_files(self.serial, self.remote_paths, self.local_dir)
        except Exception as error:
            result = TransferResult(len(self.remote_paths), 0, len(self.remote_paths), (str(error),))
        self.finished_with_result.emit(self.serial, result)
