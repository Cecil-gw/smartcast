
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
vendor = Path(__file__).resolve().parents[1] / "vendor"
if vendor.is_dir():
    sys.path.insert(0, str(vendor))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication, QGridLayout, QWidget

import ui.theme as bg
from ui.theme import BackgroundManager, BackgroundLayer
from utils.config_manager import ConfigManager


def make_png(path: Path) -> None:
    image = QImage(120, 200, QImage.Format_RGB32)
    image.fill(QColor("#3366CC"))
    image.save(str(path), "PNG")


def flush(ms: int = 2000) -> None:
    """Advance the event loop enough for short animations to finish."""
    app = QApplication.instance()
    deadline = app.property("_deadline")
    app.processEvents()


class ConfigAnimationTests(unittest.TestCase):
    def test_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = ConfigManager(Path(tmp))
            self.assertTrue(cfg.settings["animations_enabled"])
            self.assertEqual(cfg.settings["animation_duration_scale"], 1.0)

    def test_disabled_and_scale_normalized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"
            settings_path.write_text(
                '{"animations_enabled": false, "animation_duration_scale": 1.5}',
                encoding="utf-8",
            )
            cfg = ConfigManager(Path(tmp))
            self.assertFalse(cfg.settings["animations_enabled"])
            self.assertEqual(cfg.settings["animation_duration_scale"], 1.5)

    def test_invalid_scale_falls_back(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"
            settings_path.write_text('{"animation_duration_scale": "junk"}', encoding="utf-8")
            cfg = ConfigManager(Path(tmp))
            self.assertEqual(cfg.settings["animation_duration_scale"], 1.0)

    def test_out_of_range_scale_clamped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"
            settings_path.write_text('{"animation_duration_scale": 99}', encoding="utf-8")
            cfg = ConfigManager(Path(tmp))
            self.assertEqual(cfg.settings["animation_duration_scale"], 2.0)

    def test_existing_settings_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"
            settings_path.write_text(
                '{"scan_interval": 5, "animations_enabled": false}',
                encoding="utf-8",
            )
            cfg = ConfigManager(Path(tmp))
            self.assertEqual(cfg.settings["scan_interval"], 5)
            self.assertFalse(cfg.settings["animations_enabled"])


class BackgroundCrossFadeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = QApplication.instance() or QApplication([])
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.img = self.base / "background.png"
        make_png(self.img)

        self.host = QWidget()
        self.host.resize(800, 600)
        self.surface = QWidget()
        layout = QGridLayout(self.host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.surface, 0, 0)

        self.manager = BackgroundManager(self.host, self.surface)
        self.manager.layer.resize(800, 600)
        self.manager.fade_layer.resize(800, 600)
        self.manager.animations_enabled = True
        self.manager.animation_scale = 0.01  # nearly instant, still exercises code

        patcher = mock.patch(
            "ui.theme.resource_path",
            side_effect=lambda rel: self.img if rel.endswith("home/background.png") else self.base / "missing.png",
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_crossfade_ends_with_new_image_on_base(self) -> None:
        self.manager.set_background("home")
        # scale 0.01 -> duration ~4ms; pump events until finished
        for _ in range(200):
            self.app.processEvents()
            if self.manager.layer._source is not None:
                break
            import time
            time.sleep(0.005)
        self.assertTrue(self.manager.is_showing_image())
        self.assertFalse(self.manager.fade_layer._source is not None and
                         self.manager.fade_layer._opacity not in (0,))

    def test_missing_image_crossfade_degrades(self) -> None:
        self.manager.set_background("devices")  # missing
        self.assertFalse(self.manager.is_showing_image())

    def test_corrupt_image_crossfade_degrades(self) -> None:
        broken = self.base / "broken.png"
        broken.write_bytes(b"junk")
        with mock.patch("ui.theme.resource_path", return_value=broken):
            self.manager.set_background("home")
        self.assertFalse(self.manager.is_showing_image())

    def test_disabled_background_stays_clear(self) -> None:
        self.manager.set_enabled(False)
        self.manager.set_background("home")
        self.assertFalse(self.manager.is_showing_image())

    def test_rapid_switching_no_crash_and_final_key_correct(self) -> None:
        for key in ("home", "devices", "home", "devices", "home"):
            self.manager.set_background(key)
            self.app.processEvents()
        self.assertEqual(self.manager.current_key, "home")

    def test_switch_during_crossfade_promotes_correctly(self) -> None:
        # 模拟动画中途再次切换：最后以最后一次请求为准
        self.manager.animation_scale = 1.0
        self.manager.set_background("home")
        self.manager.set_background("devices")  # crossfade restarts to missing
        # 手动触发 finished 逻辑
        self.manager._on_fade_finished()
        self.assertFalse(self.manager.is_showing_image())


class MainWindowTransitionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = QApplication.instance() or QApplication([])

    def _window(self, animations: bool = True, scale: float = 1.0):
        from ui.main_window import MainWindow
        from utils.config_manager import ConfigManager

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        cfg = ConfigManager(Path(tmp.name))
        cfg.settings["animations_enabled"] = animations
        cfg.settings["animation_duration_scale"] = scale
        window = MainWindow(cfg)

        def _cleanup() -> None:
            # 必须先停线程再销毁窗口，否则连续创建/销毁窗口会在退出时崩溃
            thread = getattr(window, "device_thread", None)
            if thread is not None:
                thread.quit()
                thread.wait(3000)
            bg = getattr(window, "background", None)
            if bg is not None:
                for anim in (getattr(bg, "_fade_anim", None), getattr(bg, "_fade_out_anim", None)):
                    if anim is not None:
                        anim.stop()
            window.close()
            try:
                import shiboken6
                shiboken6.delete(window)
            except Exception:
                window.deleteLater()
            app = QApplication.instance()
            if app is not None:
                app.processEvents()

        self.addCleanup(_cleanup)
        return window

    def test_pages_reused_across_navigation(self) -> None:
        window = self._window()
        overview = window.overview_page
        device = window.device_page
        for key in ("home", "devices", "sessions", "media", "home"):
            window._navigate(key)
            self.app.processEvents()
        self.assertIs(window.overview_page, overview)
        self.assertIs(window.device_page, device)

    def test_disabled_animation_switches_immediately(self) -> None:
        window = self._window(animations=False)
        window.show()
        self.app.processEvents()
        window._navigate("devices")
        self.app.processEvents()
        self.assertIs(window.stack.currentWidget(), window.device_page)
        # 关闭动画时不应残留透明效果
        self.assertIsNone(window.page_surface.graphicsEffect())

    def test_zero_scale_switches_immediately(self) -> None:
        window = self._window(scale=0.0)
        window.show()
        self.app.processEvents()
        window._navigate("sessions")
        self.app.processEvents()
        self.assertIs(window.stack.currentWidget(), window.sessions_page)

    def test_animation_with_scale_one(self) -> None:
        window = self._window(scale=1.0)
        window.show()
        self.app.processEvents()
        window._navigate("media")
        # 动画期间页面已经是目标页
        self.assertIs(window.stack.currentWidget(), window.media_page)
        for _ in range(100):
            self.app.processEvents()
            if window.page_surface.graphicsEffect() is None:
                break
            import time
            time.sleep(0.01)
        self.assertIsNone(window.page_surface.graphicsEffect())

    def test_cast_sessions_survive_page_switches(self) -> None:
        window = self._window()
        from core.cast_session import CastSession, SESSION_RUNNING

        session = CastSession(serial="S1", model="M", state=SESSION_RUNNING)
        window.scrcpy.sessions["S1"] = session
        before = dict(window.scrcpy.sessions)
        for key in ("home", "sessions", "devices", "home"):
            window._navigate(key)
            self.app.processEvents()
        self.assertEqual(window.scrcpy.sessions, before)


if __name__ == "__main__":
    unittest.main()


def tearDownModule() -> None:
    """确保测试窗口全部销毁，避免解释器退出时 Qt 对象析构崩溃。"""
    import gc

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is not None:
        for widget in list(app.topLevelWidgets()):
            try:
                widget.close()
                widget.deleteLater()
            except RuntimeError:
                pass
        app.processEvents()
    gc.collect()
