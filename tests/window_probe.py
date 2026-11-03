import ctypes
import sys
from ctypes import wintypes

pid = int(sys.argv[1])
user32 = ctypes.windll.user32
results = []
EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

def callback(hwnd, lparam):
    owner = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
    if owner.value != pid:
        return True
    length = user32.GetWindowTextLengthW(hwnd)
    title = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, title, length + 1)
    cls = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, cls, 256)
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    results.append((hwnd, cls.value, title.value, bool(user32.IsWindowVisible(hwnd)), (rect.left, rect.top, rect.right, rect.bottom)))
    return True

user32.EnumWindows(EnumProc(callback), 0)
for item in results:
    print(item)
