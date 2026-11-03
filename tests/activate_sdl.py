import ctypes
import sys
from ctypes import wintypes
pid = int(sys.argv[1])
u = ctypes.windll.user32
found = []
E = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
def cb(h, l):
    p = wintypes.DWORD(); u.GetWindowThreadProcessId(h, ctypes.byref(p))
    c = ctypes.create_unicode_buffer(64); u.GetClassNameW(h, c, 64)
    if p.value == pid and c.value == 'SDL_app' and u.IsWindowVisible(h):
        found.append(h)
    return True
u.EnumWindows(E(cb), 0)
if not found:
    print('no SDL window')
    sys.exit(1)
h = found[0]
if u.IsIconic(h):
    u.ShowWindow(h, 9)
u.BringWindowToTop(h)
print('foreground', bool(u.SetForegroundWindow(h)), 'hwnd', h)
