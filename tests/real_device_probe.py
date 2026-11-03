from core.adb_manager import AdbManager
from core.device_info import DeviceInfoReader
from core.encoder_detector import EncoderDetector
from utils.config_manager import ConfigManager
config = ConfigManager()
adb = AdbManager(config.settings["adb_path"])
adb.start_server()
raw = adb.devices()[0]
device = DeviceInfoReader(adb).read(raw)
print(device)
codecs = EncoderDetector(adb).detect(device)
for item in codecs:
    print(item)
print("optimized:", EncoderDetector(adb).optimize(device, "auto", codecs))
