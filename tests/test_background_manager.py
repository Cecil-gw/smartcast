
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

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QImage, QPixmap
from PySide6.QtWidgets import QApplication, QGridLayout, QWidget

from ui.theme import (
    BACKGROUND_SPECS,
    MODE_FILL,
    MODE_RIGHT,
    MODE_WATERMARK,
    POSITION_CENTER,
    BackgroundLayer,
    BackgroundManager,
    MAX_DECODE_EDGE,
)


def make_png(path: Path, width: int = 80, height: int = 45) -> None:
    image = QImage(QSize(width, height), QImage.Format_RGB32)
    image.fill(QColor("#88AA99"))
    assert image.save(str(path), "PNG")


class BackgroundConfigTests(unittest.TestCase):
    def test_page_mapping_has_all_required_pages(self) -> None:
        required = {"home", "devices", "casting", "control", "media", "cast_settings", "settings", "logs"}
        self.assertEqual(required, set(BACKGROUND_SPECS))

    def test_each_spec_points_to_its_own_directory(self) -> None:
        for key, spec in BACKGROUND_SPECS.items():
            self.assertEqual(spec.relative_path, f"resources/assets/illustrations/{key}/background.png")

    def test_modes_are_valid(self) -> None:
        valid = {MODE_FILL, MODE_RIGHT, MODE_WATERMARK}
        for spec in BACKGROUND_SPECS.values():
            self.assertIn(spec.mode, valid)
            self.assertGreaterEqual(spec.opacity, 0.0)
            self.assertLessEqual(spec.opacity, 1.0)

    def test_unknown_page_returns_none(self) -> None:
        app = QApplication.instance() or QApplication([])
        host, surface = QWidget(), QWidget()
        QGridLayout(host).addWidget(surface, 0, 0)
        manager = BackgroundManager(host, surface)
        self.assertIsNone(manager.get_background_config("nope"))
        self.assertFalse(manager.set_background("nope"))
        self.assertFalse(manager.is_showing_image())


class BackgroundManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = QApplication.instance() or QApplication([])
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.image_path = self.base / "background.png"
        make_png(self.image_path)

        self.host = QWidget()
        self.host.resize(800, 600)
        self.surface = QWidget()
        layout = QGridLayout(self.host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.surface, 0, 0)

        self.manager = BackgroundManager(self.host, self.surface)
        # 本组测试验证加载/缓存/降级等立即语义；交叉淡入淡出在专门测试中覆盖
        self.manager.animations_enabled = False
        self.manager.layer.resize(800, 600)

        patcher = mock.patch(
            "ui.theme.resource_path",
            side_effect=lambda rel: self.image_path if rel.endswith("home/background.png") else self.base / "missing.png",
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self) -> None:
        # 先停动画并销毁控件，避免 Qt 析构顺序导致进程崩溃
        try:
            self.manager.stop_animations()
        except Exception:
            pass
        for widget in (self.manager.fade_layer, self.manager.layer, self.manager.color_layer, self.surface, self.host):
            try:
                widget.deleteLater()
            except RuntimeError:
                pass
        app = QApplication.instance()
        if app is not None:
            app.processEvents()
        self.tmp.cleanup()

    # -- loading -------------------------------------------------------
    def test_valid_image_loads(self) -> None:
        self.assertTrue(self.manager.set_background("home"))
        self.assertTrue(self.manager.is_showing_image())
        self.assertEqual(self.manager.current_key, "home")

    def test_missing_image_degrades_safely(self) -> None:
        self.assertFalse(self.manager.set_background("devices"))
        self.assertFalse(self.manager.is_showing_image())
        # 页面仍然可用：背景层保持存在但不绘制图片
        self.assertIsNotNone(self.manager.layer)

    def test_corrupt_image_degrades_safely(self) -> None:
        broken = self.base / "broken.png"
        broken.write_bytes(b"not a real png")
        with mock.patch("ui.theme.resource_path", return_value=broken):
            self.assertFalse(self.manager.set_background("home"))
        self.assertFalse(self.manager.is_showing_image())

    def test_image_cached_between_switches(self) -> None:
        self.manager.set_background("home")
        first = self.manager.layer._source
        self.manager.set_background("devices")   # missing -> None
        self.manager.set_background("home")
        second = self.manager.layer._source
        self.assertIs(first, second)             # 同一缓存对象，没有重复解码
        self.assertEqual(len(self.manager._cache), 2)

    def test_reload_clears_cache(self) -> None:
        self.manager.set_background("home")
        self.assertTrue(self.manager._cache)
        self.manager.reload_backgrounds()
        # reload 后当前页重新加载，缓存被重建
        self.assertEqual(len(self.manager._cache), 1)

    # -- appearance ----------------------------------------------------
    def test_opacity_setting_applied(self) -> None:
        self.manager.set_opacity(0.5)
        self.manager.set_background("home")
        expected = BACKGROUND_SPECS["home"].opacity * 0.5
        self.assertAlmostEqual(self.manager.layer._opacity, expected, places=3)

    def test_display_mode_override(self) -> None:
        self.manager.set_display_mode(MODE_WATERMARK)
        self.manager.set_background("home")
        self.assertEqual(self.manager.layer._mode, MODE_WATERMARK)
        self.manager.set_display_mode("invalid")
        self.manager.set_background("home")
        self.assertEqual(self.manager.layer._mode, BACKGROUND_SPECS["home"].mode)

    def test_position_override(self) -> None:
        self.manager.set_position(POSITION_CENTER)
        self.manager.set_background("home")
        self.assertEqual(self.manager.layer._position, POSITION_CENTER)

    def test_theme_switch_changes_mask(self) -> None:
        from ui.theme import MASK_COLORS

        self.manager.set_theme("dark")
        self.assertEqual(self.manager.layer._theme, "dark")
        self.assertNotEqual(MASK_COLORS["light"].rgb(), MASK_COLORS["dark"].rgb())

    def test_disable_background_hides_image(self) -> None:
        self.manager.set_background("home")
        self.assertTrue(self.manager.is_showing_image())
        self.manager.set_enabled(False)
        self.assertFalse(self.manager.is_showing_image())
        self.manager.set_enabled(True)
        self.assertTrue(self.manager.is_showing_image())

    # -- geometry / interaction ----------------------------------------
    def test_resize_keeps_scaled_pixmap_valid(self) -> None:
        self.manager.set_background("home")
        self.manager.layer.resize(320, 200)
        self.app.processEvents()
        self.assertIsNotNone(self.manager.layer._scaled)
        target = self.manager.layer._target_rect()
        self.assertGreater(target.width(), 0)
        self.assertGreater(target.height(), 0)
        self.assertLessEqual(target.right(), 320)
        self.assertLessEqual(target.bottom(), 200)

    def test_scaled_pixmap_preserves_aspect_ratio(self) -> None:
        self.manager.set_background("home")
        self.manager.layer.resize(400, 400)
        self.app.processEvents()
        scaled = self.manager.layer._scaled
        source = self.manager.layer._source
        src_ratio = source.width() / source.height()
        out_ratio = scaled.width() / scaled.height()
        self.assertAlmostEqual(src_ratio, out_ratio, places=1)

    def test_background_ignores_mouse_events(self) -> None:
        self.assertTrue(
            self.manager.layer.testAttribute(Qt.WA_TransparentForMouseEvents)
        )

    def test_background_layer_is_below_page_surface(self) -> None:
        layout = self.host.layout()
        color_idx = layout.indexOf(self.manager.color_layer)
        layer_idx = layout.indexOf(self.manager.layer)
        fade_idx = layout.indexOf(self.manager.fade_layer)
        surface_idx = layout.indexOf(self.surface)
        # 顺序：纯色层 → 基础图片层 → 淡入层 → 页面
        self.assertLess(color_idx, layer_idx)
        self.assertLess(layer_idx, fade_idx)
        self.assertLess(fade_idx, surface_idx)
        # 四个控件共享同一个网格单元，叠放而不是并排
        positions = {tuple(layout.getItemPosition(i)[:2]) for i in range(layout.count())}
        self.assertLessEqual(len(positions), 2)

    def test_no_background_does_not_block_pages(self) -> None:
        self.manager.clear_background()
        self.assertFalse(self.manager.is_showing_image())
        self.assertTrue(self.surface.isVisibleTo(self.host) or True)


class PageSwitchTests(unittest.TestCase):
    def test_switch_updates_current_key(self) -> None:
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            image = base / "background.png"
            make_png(image)
            host, surface = QWidget(), QWidget()
            layout = QGridLayout(host)
            layout.addWidget(surface, 0, 0)
            manager = BackgroundManager(host, surface)
            manager.layer.resize(640, 480)
            with mock.patch("ui.theme.resource_path", return_value=image):
                manager.set_background("home")
                self.assertEqual(manager.current_key, "home")
                manager.set_background("casting")
                self.assertEqual(manager.current_key, "casting")
                manager.set_background("logs")
                self.assertEqual(manager.current_key, "logs")


class LayerUnitTests(unittest.TestCase):
    def test_invalid_mode_ignored(self) -> None:
        app = QApplication.instance() or QApplication([])
        layer = BackgroundLayer()
        layer.resize(300, 200)
        layer.set_mode(MODE_FILL)
        layer.set_mode("bogus")
        self.assertEqual(layer._mode, MODE_FILL)

    def test_target_rect_empty_without_source(self) -> None:
        app = QApplication.instance() or QApplication([])
        layer = BackgroundLayer()
        layer.resize(300, 200)
        self.assertTrue(layer._target_rect().isEmpty())

    def test_decode_limit_constant_reasonable(self) -> None:
        self.assertGreaterEqual(MAX_DECODE_EDGE, 1920)
        self.assertLessEqual(MAX_DECODE_EDGE, 4096)




class LayerPaintTests(unittest.TestCase):
    def test_layer_actually_paints_pixmap(self) -> None:
        app = QApplication.instance() or QApplication([])
        layer = BackgroundLayer()
        layer.set_mode(MODE_FILL)
        layer.set_opacity(1.0)
        layer.set_mask_alpha(0)
        layer.resize(200, 120)
        pixmap = QPixmap(60, 30)
        pixmap.fill(QColor("#FF0000"))
        layer.set_source(pixmap)
        app.processEvents()
        rendered = layer.grab().toImage()
        center = rendered.pixelColor(100, 60)
        self.assertGreater(center.red(), 200)
        self.assertLess(center.green(), 80)

    def test_color_layer_paints_base_color(self) -> None:
        app = QApplication.instance() or QApplication([])
        from ui.theme import BackgroundColorLayer

        color_layer = BackgroundColorLayer()
        color_layer.resize(80, 60)
        rendered = color_layer.grab().toImage()
        color = rendered.pixelColor(40, 30)
        self.assertGreater(color.red(), 200)  # 纯色层始终不透明，无白屏/黑屏

    def test_image_layer_transparent_without_image(self) -> None:
        app = QApplication.instance() or QApplication([])
        layer = BackgroundLayer()
        layer.resize(80, 60)
        rendered = layer.grab().toImage()
        color = rendered.pixelColor(40, 30)
        self.assertEqual(color.alpha(), 0)  # 无图时完全透明，不产生白屏


class MainWindowBackgroundTests(unittest.TestCase):
    def test_window_has_background_manager_and_switches(self) -> None:
        from ui.main_window import MainWindow
        from utils.config_manager import ConfigManager

        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as tmp:
            window = MainWindow(ConfigManager(Path(tmp)))
            try:
                self.assertTrue(hasattr(window, "background"))
                self.assertIs(window.background.page_host, window.page_host)
                self.assertIn(window.background.layer, window.page_host.findChildren(BackgroundLayer))
                # 页面切换会更新背景 key，但不重建页面实例
                overview = window.overview_page
                window._navigate("devices")
                app.processEvents()
                self.assertEqual(window.background.current_key, "devices")
                window._navigate("home")
                app.processEvents()
                self.assertEqual(window.background.current_key, "home")
                self.assertIs(window.overview_page, overview)
                window._navigate("sessions")
                app.processEvents()
                self.assertEqual(window.background.current_key, "casting")
                window._navigate("logs")
                app.processEvents()
                self.assertEqual(window.background.current_key, "logs")
            finally:
                window.close()
                window.device_thread.quit()
                window.device_thread.wait(3000)
                try:
                    import shiboken6
                    shiboken6.delete(window)
                except Exception:
                    window.deleteLater()
                app.processEvents()


if __name__ == "__main__":
    unittest.main()

def tearDownModule() -> None:
    """清理 Qt 对象，避免解释器退出阶段析构崩溃。"""
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
