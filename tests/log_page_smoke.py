import tempfile
from pathlib import Path

from PySide6.QtWidgets import QApplication

from ui.pages.log_page import LogPage


app = QApplication([])
page = LogPage()
page.append_log("12:00:01 INFO  SmartCast UI ready")
page.append_log("12:00:02 WARNING  Device scan slow")
page.append_log("12:00:03 ERROR  scrcpy exited")
assert page.count_label.text() == "3 条"
page.level_filter.setCurrentIndex(3)
assert page.visible_lines() and "ERROR" in page.visible_lines()[0]
page.search_edit.setText("scrcpy")
assert len(page.visible_lines()) == 1
assert "scrcpy" in page.to_plain_text()
page.clear_log()
assert page.count_label.text() == "0 条"

with tempfile.TemporaryDirectory() as temp:
    log = Path(temp) / "smartcast.log"
    log.write_text("2026-10-31 22:00:00 INFO smartcast: ok\n", encoding="utf-8")
    page.level_filter.setCurrentIndex(0)
    page.search_edit.clear()
    page.load_recent(log)
    assert page.to_plain_text().endswith("ok")

print("log page smoke passed")


