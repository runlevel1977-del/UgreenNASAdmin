import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from ugreen_app import private_file


class PrivateFileTests(unittest.TestCase):
    def test_security_initialization_failure_never_replaces_previous_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'fixture.json'; path.write_bytes(b'old')
            with patch.object(private_file, 'private_temporary', side_effect=OSError('ACL failure')):
                with self.assertRaises(OSError): private_file.write_private_bytes(path, b'new')
            self.assertEqual(path.read_bytes(), b'old')

    @unittest.skipUnless(os.name == 'nt', 'Native Windows DACL test')
    def test_native_windows_file_has_protected_current_user_and_system_acl(self):
        import ctypes
        from ctypes import wintypes as wt
        adv=ctypes.WinDLL('advapi32',use_last_error=True)
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        adv.GetNamedSecurityInfoW.argtypes=[wt.LPWSTR,ctypes.c_int,wt.DWORD,wt.LPVOID,wt.LPVOID,wt.LPVOID,wt.LPVOID,ctypes.POINTER(wt.LPVOID)]
        adv.GetNamedSecurityInfoW.restype=wt.DWORD
        adv.ConvertSecurityDescriptorToStringSecurityDescriptorW.argtypes=[wt.LPVOID,wt.DWORD,wt.DWORD,ctypes.POINTER(wt.LPWSTR),wt.LPVOID]
        adv.ConvertSecurityDescriptorToStringSecurityDescriptorW.restype=wt.BOOL
        kernel.LocalFree.argtypes=[wt.LPVOID]
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'fixture.json'
            path.write_bytes(b'old inherited permissions')
            private_file.write_private_bytes(path,b'synthetic-only')
            descriptor=wt.LPVOID(); text=wt.LPWSTR()
            self.assertEqual(adv.GetNamedSecurityInfoW(str(path),1,5,None,None,None,None,ctypes.byref(descriptor)),0)
            try:
                self.assertTrue(adv.ConvertSecurityDescriptorToStringSecurityDescriptorW(descriptor,1,5,ctypes.byref(text),None))
                current_sid=private_file.windows_security().split('D:',1)[0][2:]
                self.assertIn('D:P',text.value)
                self.assertEqual(text.value.count('(A;'),2)
                self.assertIn('(A;;FA;;;SY)',text.value)
                self.assertIn('(A;;FA;;;'+current_sid+')',text.value)
            finally:
                if text: kernel.LocalFree(text)
                kernel.LocalFree(descriptor)


if __name__ == '__main__': unittest.main()
