import tempfile
from pathlib import Path

from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from core.device_info import DeviceInfo
from ui.components.device_card import DeviceCard
from ui.components.quick_config import QuickConfigPanel
from ui.main_window import MainWindow
from utils.config_manager import ConfigManager


app = QApplication([])

panel = QuickConfigPanel()
panel.show()
panel.resize(900, 100)
app.processEvents()
assert panel._compact_parameters is False
panel.resize(620, 100)
app.processEvents()
assert panel._compact_parameters is True
for cell, _row, _column in panel.param_cells:
    assert cell.geometry().width() > 0

device = DeviceInfo("320146588834", "device", "ZTE", "ZTE", "W201DS", "13", "33", "1200x1920", "260")
card = DeviceCard(device)
card.resize(480, card.sizeHint().height())
card.show()
app.processEvents()
assert card.start_button.geometry().bottom() <= card.rect().bottom()
assert card.stop_button.geometry().bottom() <= card.rect().bottom()
assert card.details_button.geometry().bottom() <= card.rect().bottom()
assert card.settings_button.geometry().bottom() <= card.rect().bottom()
assert card.copy_button.geometry().bottom() <= card.rect().bottom()
assert card.codec_label.geometry().bottom() <= card.rect().bottom()
assert not card.start_button.geometry().intersects(card.stop_button.geometry())
assert not card.details_button.geometry().intersects(card.settings_button.geometry())

with tempfile.TemporaryDirectory() as temp:
    window = MainWindow(ConfigManager(Path(temp)))
    window.show()
    window.resize(1200, 760)
    app.processEvents()
    assert window.header.context_label.isVisible()
    window.resize(900, 640)
    app.processEvents()
    assert not window.header.context_label.isVisible()
    window.show_cast_settings_page()
    app.processEvents()
    assert window.cast_page.quick_config._compact_parameters is True
    window.close()

print("responsive smoke passed")

