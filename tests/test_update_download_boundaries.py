"""Download bytes are synthetic; no network or installer is used."""
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import urllib.request

from ugreen_app import update_check as updates

URL = 'https://github.com/runlevel1977-del/UgreenNASAdmin/releases/download/v23.8.57/UgreenNASAdmin_setup_23.8.57.exe'


class Response(io.BytesIO):
    def __init__(self, data, length=None, url=URL):
        super().__init__(data)
        self.headers = {} if length is None else {'Content-Length':str(length)}
        self.url = url
    def geturl(self):
        return self.url


class UpdateDownloadTests(unittest.TestCase):
    def download(self, destination, response, **kwargs):
        opener = Mock()
        opener.open.return_value = response
        with patch.object(updates.urllib.request, 'build_opener', return_value=opener):
            return updates.download_release_asset(URL, destination, **kwargs)

    def test_safe_flat_installer_name_required(self):
        self.assertEqual(updates.safe_installer_name('UgreenNASAdmin_setup_23.8.57.exe'),'UgreenNASAdmin_setup_23.8.57.exe')
        for name in ('../UgreenNASAdmin_setup_1.exe','C:\\UgreenNASAdmin_setup_1.exe',
                     'UgreenNASAdmin_setup_1.exe:stream','UgreenNASAdmin_setup_1.exe/other','setup.exe'):
            with self.assertRaises(ValueError):
                updates.safe_installer_name(name)

    def test_rejects_http_credentials_ports_and_unrelated_hosts(self):
        for url in ('http://github.com/x','https://github.com.evil.invalid/x','https://user@github.com/x',
                    'https://github.com:444/x','file:///tmp/setup.exe'):
            with self.assertRaises(ValueError):
                updates._validate_download_url(url)

    def test_redirect_checked_before_contacting_target(self):
        handler=updates._ReleaseRedirectHandler()
        request=urllib.request.Request(URL)
        for target in ('http://github.com/setup.exe','https://example.invalid/setup.exe'):
            with self.assertRaises(ValueError):
                handler.redirect_request(request,None,302,'found',{},target)
        redirect=handler.redirect_request(request,None,302,'found',{},'https://release-assets.githubusercontent.com/example')
        self.assertEqual(redirect.full_url,'https://release-assets.githubusercontent.com/example')

    def test_other_repository_rejected_before_any_download(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(updates.urllib.request,'build_opener') as opener:
            ok,_=updates.download_release_asset(URL.replace('/runlevel1977-del/','/different/'),Path(directory)/'test.exe')
            self.assertFalse(ok)
            opener.assert_not_called()
            self.assertEqual(list(Path(directory).iterdir()),[])

    def test_truncated_oversized_and_empty_download_keep_previous_file(self):
        for content,length,size in ((b'part',9,9),(b'extra!',3,3),(b'',None,None),(b'part',None,9)):
            with self.subTest(size=size),tempfile.TemporaryDirectory() as directory:
                path=Path(directory)/'test.exe'; path.write_bytes(b'previous')
                ok,_=self.download(path,Response(content,length),expected_size=size)
                self.assertFalse(ok)
                self.assertEqual(path.read_bytes(),b'previous')
                self.assertEqual([p.name for p in Path(directory).iterdir()],['test.exe'])

    def test_bounded_signature_download(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'test.sig'
            ok,_=self.download(path,Response(b'x'*4097),max_bytes=4096)
            self.assertFalse(ok)
            self.assertFalse(path.exists())

    def test_callback_failure_also_cleans_only_owned_temporary_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'test.exe';path.write_bytes(b'previous')
            ok,_=self.download(path,Response(b'new',3),expected_size=3,log=Mock(side_effect=RuntimeError('UI unavailable')))
            self.assertFalse(ok)
            self.assertEqual(path.read_bytes(),b'previous')
            self.assertEqual(len(list(Path(directory).iterdir())),1)

    def test_valid_download_publishes_complete_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'test.exe'
            ok,_=self.download(path,Response(b'synthetic',9),expected_size=9)
            self.assertTrue(ok)
            self.assertEqual(path.read_bytes(),b'synthetic')
            self.assertEqual(len(list(Path(directory).iterdir())),1)

    def test_final_response_url_rechecked(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'test.exe'
            ok,_=self.download(path,Response(b'abc',3,'https://unrelated.invalid/asset'),expected_size=3)
            self.assertFalse(ok)
            self.assertFalse(path.exists())


if __name__ == '__main__':
    unittest.main()
