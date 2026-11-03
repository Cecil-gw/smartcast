from PySide6.QtWidgets import QApplication

from ui.components.sidebar import Sidebar
from ui.pages.overview_page import OverviewPage


app = QApplication([])
page = OverviewPage()
events = {"scan": 0, "manage": 0, "cast": 0, "help": 0}
page.scan_requested.connect(lambda: events.__setitem__("scan", events["scan"] + 1))
page.manage_requested.connect(lambda: events.__setitem__("manage", events["manage"] + 1))
page.cast_requested.connect(lambda: events.__setitem__("cast", events["cast"] + 1))
page.help_requested.connect(lambda: events.__setitem__("help", events["help"] + 1))
page.set_adb(True, "ADB 已连接")
page.set_devices(2, 2)
page.set_casting(1)
page.set_scan("扫描完成")
assert page.adb_tile[1].text() == "ADB 已连接"
assert page.device_tile[1].text() == "2 / 2 台"
assert page.casting_tile[1].text() == "1 路"
assert page.scan_tile[1].text() == "扫描完成"
page.scan_button = page.findChild(__import__("PySide6.QtWidgets", fromlist=["QPushButton"]).QPushButton)
assert events == {"scan": 0, "manage": 0, "cast": 0, "help": 0}

sidebar = Sidebar(page)
assert sidebar.buttons["home"].isChecked()
assert sidebar.buttons["devices"].text() == "设备管理"
print("overview smoke passed")
