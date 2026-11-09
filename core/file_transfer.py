
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from utils.logger import setup_logger


DEFAULT_REMOTE_DIR = "/sdcard/Download/SmartCast"


@dataclass(frozen=True)
class TransferResult:
    total: int
    succeeded: int
    failed: int
    messages: tuple[str, ...] = ()
    succeeded_names: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.failed == 0 and self.succeeded > 0


class FileTransferManager:
    """通过 adb push/pull 在电脑与手机之间传输文件。"""

    def __init__(self, adb_path: str) -> None:
        self.adb_path = adb_path
        self.logger = setup_logger()

    # ------------------------------------------------------------------
    def push_files(
        self, serial: str, local_paths: list[str], remote_dir: str = DEFAULT_REMOTE_DIR
    ) -> TransferResult:
        paths = [Path(p) for p in local_paths if Path(p).is_file()]
        if not paths:
            return TransferResult(0, 0, 0, ("没有可发送的文件",))

        # 确保目标目录存在（失败也不阻断，push 会给出明确错误）
        self._shell(serial, f"mkdir -p {remote_dir}")

        succeeded = 0
        messages: list[str] = []
        for path in paths:
            target = f"{remote_dir.rstrip('/')}/{path.name}"
            code, output, error = self._run(
                [self.adb_path, "-s", serial, "push", str(path), target], timeout=300
            )
            if code == 0:
                succeeded += 1
                self.logger.info("已推送 %s -> %s:%s", path.name, serial, target)
            else:
                detail = (error or output or f"退出码 {code}").strip()
                messages.append(f"{path.name}: {detail}")
                self.logger.warning("推送失败 %s：%s", path.name, detail)

        return TransferResult(len(paths), succeeded, len(paths) - succeeded, tuple(messages))

    def pull_files(
        self, serial: str, remote_paths: list[str], local_dir: str
    ) -> TransferResult:
        target_dir = Path(local_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        succeeded = 0
        succeeded_names: list[str] = []
        messages: list[str] = []
        for remote in remote_paths:
            code, output, error = self._run(
                [self.adb_path, "-s", serial, "pull", remote, str(target_dir)], timeout=300
            )
            if code == 0:
                succeeded += 1
                name = remote.rstrip("/").rsplit("/", 1)[-1]
                succeeded_names.append(name)
                self.logger.info("已拉取 %s:%s -> %s", serial, remote, target_dir)
            else:
                detail = (error or output or f"退出码 {code}").strip()
                messages.append(f"{remote}: {detail}")
                self.logger.warning("拉取失败 %s：%s", remote, detail)
        return TransferResult(
            len(remote_paths), succeeded, len(remote_paths) - succeeded,
            tuple(messages), tuple(succeeded_names),
        )

    def list_dir(self, serial: str, remote_dir: str) -> list[dict]:
        """列出手机目录内容，返回 [{name, is_dir, size}]，目录排在前面。"""
        code, output, error = self._run(
            [self.adb_path, "-s", serial, "shell", f"ls -l {remote_dir}"], timeout=20
        )
        if code != 0:
            raise RuntimeError((error or output or f"退出码 {code}").strip())

        entries: list[dict] = []
        for line in (output or "").splitlines():
            line = line.rstrip()
            if not line or line.startswith("total "):
                continue
            parts = line.split(None, 7)
            if len(parts) < 8:
                continue
            perms, size_text = parts[0], parts[4]
            name = parts[7]
            is_dir = perms.startswith("d")
            if name in (".", ".."):
                continue
            try:
                size = int(size_text)
            except ValueError:
                size = 0
            entries.append({"name": name, "is_dir": is_dir, "size": size})

        entries.sort(key=lambda e: (not e["is_dir"], e["name"].lower()))
        return entries

    def pull_to_dir(self, serial: str, remote_paths: list[str], local_dir: str) -> TransferResult:
        """把手机上的多个路径取回到本地目录。"""
        return self.pull_files(serial, remote_paths, local_dir)

    # ------------------------------------------------------------------
    def _shell(self, serial: str, command: str) -> None:
        self._run([self.adb_path, "-s", serial, "shell", command], timeout=10)

    @staticmethod
    def _run(command: list[str], timeout: float) -> tuple[int, str, str]:
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return completed.returncode, completed.stdout or "", completed.stderr or ""
        except subprocess.TimeoutExpired:
            return 124, "", "传输超时"
        except FileNotFoundError:
            return 127, "", "找不到 ADB"
        except Exception as exc:
            return 1, "", str(exc)
