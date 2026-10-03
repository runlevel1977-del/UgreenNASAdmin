"""Create private staging files before any secret bytes are written."""
import os
from pathlib import Path
import tempfile
import uuid


def windows_security():
    import ctypes
    from ctypes import wintypes as wt
    adv = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    adv.OpenProcessToken.argtypes = [wt.HANDLE, wt.DWORD, ctypes.POINTER(wt.HANDLE)]
    adv.OpenProcessToken.restype = wt.BOOL
    adv.GetTokenInformation.argtypes = [wt.HANDLE, ctypes.c_int, wt.LPVOID, wt.DWORD, ctypes.POINTER(wt.DWORD)]
    adv.GetTokenInformation.restype = wt.BOOL
    adv.ConvertSidToStringSidW.argtypes = [wt.LPVOID, ctypes.POINTER(wt.LPWSTR)]
    adv.ConvertSidToStringSidW.restype = wt.BOOL
    kernel.GetCurrentProcess.restype = wt.HANDLE
    kernel.CloseHandle.argtypes = [wt.HANDLE]
    kernel.LocalFree.argtypes = [wt.LPVOID]
    kernel.LocalFree.restype = wt.LPVOID
    token = wt.HANDLE()
    if not adv.OpenProcessToken(kernel.GetCurrentProcess(), 0x0008, ctypes.byref(token)):
        raise ctypes.WinError(ctypes.get_last_error())
    sid_text = wt.LPWSTR()
    try:
        size = wt.DWORD()
        adv.GetTokenInformation(token, 1, None, 0, ctypes.byref(size))
        if not size.value:
            raise ctypes.WinError(ctypes.get_last_error())
        info = ctypes.create_string_buffer(size.value)
        if not adv.GetTokenInformation(token, 1, info, size, ctypes.byref(size)):
            raise ctypes.WinError(ctypes.get_last_error())
        sid = ctypes.cast(info, ctypes.POINTER(wt.LPVOID))[0]
        if not adv.ConvertSidToStringSidW(sid, ctypes.byref(sid_text)):
            raise ctypes.WinError(ctypes.get_last_error())
        # Explicit SID, protected DACL, no inherited Everyone/Users permissions.
        return "O:" + sid_text.value + "D:P(A;;FA;;;SY)(A;;FA;;;" + sid_text.value + ")"
    finally:
        if sid_text:
            kernel.LocalFree(sid_text)
        kernel.CloseHandle(token)


def private_temporary(directory):
    if os.name != "nt":
        return tempfile.mkstemp(prefix=".ugreen-settings-", suffix=".tmp", dir=directory)
    import ctypes
    from ctypes import wintypes as wt
    import msvcrt
    adv = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    class SecurityAttributes(ctypes.Structure):
        _fields_ = [("length", wt.DWORD), ("descriptor", wt.LPVOID), ("inherit", wt.BOOL)]
    adv.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [wt.LPCWSTR, wt.DWORD, ctypes.POINTER(wt.LPVOID), ctypes.POINTER(wt.DWORD)]
    adv.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = wt.BOOL
    kernel.CreateFileW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD, ctypes.POINTER(SecurityAttributes), wt.DWORD, wt.DWORD, wt.HANDLE]
    kernel.CreateFileW.restype = wt.HANDLE
    kernel.CloseHandle.argtypes = [wt.HANDLE]
    kernel.LocalFree.argtypes = [wt.LPVOID]
    descriptor = wt.LPVOID()
    if not adv.ConvertStringSecurityDescriptorToSecurityDescriptorW(windows_security(), 1, ctypes.byref(descriptor), None):
        raise ctypes.WinError(ctypes.get_last_error())
    target = str(Path(directory).resolve() / (".ugreen-settings-" + uuid.uuid4().hex + ".tmp"))
    try:
        attrs = SecurityAttributes(ctypes.sizeof(SecurityAttributes), descriptor, False)
        handle = kernel.CreateFileW(target, 0x40000000, 0, ctypes.byref(attrs), 1, 0x80, None)
        if handle == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            return msvcrt.open_osfhandle(handle, os.O_WRONLY | os.O_BINARY), target
        except BaseException:
            kernel.CloseHandle(handle)
            os.unlink(target)
            raise
    finally:
        kernel.LocalFree(descriptor)


def write_private_bytes(path, data):
    target = Path(path)
    if target.is_symlink():
        raise ValueError("Refusing symbolic-link configuration")
    fd, temporary = private_temporary(target.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if target.is_symlink():
            raise ValueError("Configuration destination changed to a symbolic link")
        os.replace(temporary, target)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
