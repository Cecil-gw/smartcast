from core.device_info import DeviceInfo
from core.encoder_detector import EncoderDetector

class FakeAdb:
    def shell(self, serial, command, timeout=5):
        return "name=c2.unisoc.avc.encoder\n  is-encoder=true\n  mime=video/avc\nname=c2.qti.hevc.encoder\n  is-encoder=true\n  mime=video/hevc\nname=c2.android.vp9.encoder\n  is-encoder=true\n  mime=video/x-vnd.on2.vp9"

device = DeviceInfo("serial", "device")
items = EncoderDetector(FakeAdb()).detect(device)
assert items[0].codec == "H.265" and items[0].hardware
assert any(item.codec == "H.264" and item.hardware for item in items)
assert any(item.codec == "VP9" for item in items)
print("encoder parser test passed")
