"""Inventory every bundled Windows executable/DLL without loading or running it."""
import hashlib
import os
from pathlib import Path


def file_version(path):
    if os.name != 'nt': return None
    import ctypes
    from ctypes import wintypes as wt
    api=ctypes.WinDLL('version', use_last_error=True)
    api.GetFileVersionInfoSizeW.argtypes=[wt.LPCWSTR,wt.LPVOID]
    api.GetFileVersionInfoSizeW.restype=wt.DWORD
    api.GetFileVersionInfoW.argtypes=[wt.LPCWSTR,wt.DWORD,wt.DWORD,wt.LPVOID]
    api.GetFileVersionInfoW.restype=wt.BOOL
    api.VerQueryValueW.argtypes=[wt.LPVOID,wt.LPCWSTR,ctypes.POINTER(wt.LPVOID),ctypes.POINTER(wt.UINT)]
    api.VerQueryValueW.restype=wt.BOOL
    size=api.GetFileVersionInfoSizeW(str(path),None)
    if not size or size > 1024*1024: return None
    data=ctypes.create_string_buffer(size)
    if not api.GetFileVersionInfoW(str(path),0,size,data): return None
    value=wt.LPVOID(); length=wt.UINT()
    if not api.VerQueryValueW(data,'\\',ctypes.byref(value),ctypes.byref(length)) or length.value < 52: return None
    fixed=ctypes.cast(value,ctypes.POINTER(wt.DWORD))
    if fixed[0] != 0xFEEF04BD: return None
    return '.'.join(str(v) for v in (fixed[2]>>16, fixed[2]&65535, fixed[3]>>16, fixed[3]&65535))


def native_inventory(directory, packages):
    root=Path(directory)
    files=[]
    for path in sorted(root.rglob('*')):
        if path.is_symlink(): raise ValueError('Symlinks are not release artifacts')
        if not path.is_file() or path.suffix.lower() not in ('.dll','.pyd','.exe'): continue
        digest=hashlib.sha256()
        with path.open('rb') as source:
            for block in iter(lambda:source.read(1024*1024),b''): digest.update(block)
        version=file_version(path)
        files.append({'file':path.relative_to(root).as_posix(),'size':path.stat().st_size,
                      'sha256':digest.hexdigest(),'file_version':version,
                      'review':'map-to-component-and-advisories' if version else 'version-unknown-review-required'})
    return {'schema':1,'python_packages':dict(sorted(packages.items())),'native_files':files,
            'scope':'Complete DLL/PYD/EXE file inventory; hashes and resource versions do not identify every statically linked component or prove vulnerability freedom'}
