import ctypes
from ctypes import wintypes
u=ctypes.windll.user32
E=ctypes.WINFUNCTYPE(ctypes.c_bool,wintypes.HWND,wintypes.LPARAM)
def cb(h,l):
    n=u.GetWindowTextLengthW(h); t=ctypes.create_unicode_buffer(n+1); u.GetWindowTextW(h,t,n+1)
    c=ctypes.create_unicode_buffer(256); u.GetClassNameW(h,c,256)
    p=wintypes.DWORD(); u.GetWindowThreadProcessId(h,ctypes.byref(p))
    if 'SDL' in c.value or 'scrcpy' in t.value.lower() or 'W201DS' in t.value:
        print('TOP',h,c.value,repr(t.value),p.value,bool(u.IsWindowVisible(h)))
    return True
u.EnumWindows(E(cb),0)
