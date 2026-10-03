"""Execute generated Linux code against an inode/descriptor model, without sudo."""
import io
import stat
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from nas_ssh import _atomic_root_write_code


def directory(mode=0o755,uid=0):
    return dict(mode=stat.S_IFDIR|mode,uid=uid,children={})


class DescriptorOS:
    O_RDONLY=0; O_WRONLY=1; O_CREAT=2; O_EXCL=4; O_DIRECTORY=8; O_NOFOLLOW=16
    def __init__(self):
        self.root=directory();self.var=directory();self.lib=directory();self.private=directory(0o700)
        self.root['children']['var']=self.var;self.var['children']['lib']=self.lib
        self.lib['children']['ugreen-nas-admin']=self.private
        self.private['children']['helper']=dict(mode=stat.S_IFREG|0o600,uid=0,data=b'old')
        self.handles={};self.number=100;self.replacements=[];self.fail_write=False
    def open(self,name,flags,mode=None,dir_fd=None):
        if name=='/':node=self.root
        else:
            children=self.handles[dir_fd]['children']
            if flags & self.O_CREAT:
                if name in children:raise FileExistsError(name)
                children[name]=dict(mode=stat.S_IFREG|mode,uid=0,data=b'')
            if name not in children:raise FileNotFoundError(name)
            node=children[name]
        if stat.S_ISLNK(node['mode']):raise OSError('nofollow')
        self.number+=1;self.handles[self.number]=node;return self.number
    def mkdir(self,name,mode,dir_fd):
        children=self.handles[dir_fd]['children']
        if name in children:raise FileExistsError(name)
        children[name]=directory(mode)
    def fstat(self,fd):return SimpleNamespace(st_uid=self.handles[fd]['uid'],st_mode=self.handles[fd]['mode'])
    def stat(self,name,dir_fd,follow_symlinks):
        try:node=self.handles[dir_fd]['children'][name]
        except KeyError:raise FileNotFoundError(name)
        return SimpleNamespace(st_mode=node['mode'])
    def close(self,fd):del self.handles[fd]
    def fdopen(self,fd,mode):
        fs=self
        class Output(io.BytesIO):
            def fileno(self):return fd
            def write(self,data):
                if fs.fail_write:raise OSError('synthetic disk full')
                return super().write(data)
            def close(self):
                if not self.closed:fs.handles[fd]['data']=self.getvalue();fs.close(fd)
                super().close()
        return Output()
    def fchown(self,fd,uid,gid):self.handles[fd]['uid']=uid
    def fchmod(self,fd,mode):self.handles[fd]['mode']=stat.S_IFREG|mode
    def fsync(self,fd):pass
    def replace(self,src,dst,src_dir_fd,dst_dir_fd):
        self.replacements.append((self.handles[src_dir_fd],self.handles[dst_dir_fd]))
        self.handles[dst_dir_fd]['children'][dst]=self.handles[src_dir_fd]['children'].pop(src)
    def unlink(self,name,dir_fd):
        try:del self.handles[dir_fd]['children'][name]
        except KeyError:raise FileNotFoundError(name)
    def rmdir(self,name,dir_fd):self.unlink(name,dir_fd)


class RootPathBindingTests(unittest.TestCase):
    def execute(self,fs,data="data=b'new'",**context):
        try:
            with patch.dict(sys.modules,{'os':fs}):
                exec(_atomic_root_write_code('/var/lib/ugreen-nas-admin/helper',0o640,data),context)
        finally:
            self.assertEqual(fs.handles,{})

    def test_success_uses_original_directory_handle_and_root_owned_file(self):
        fs=DescriptorOS();self.execute(fs)
        self.assertEqual(fs.private['children']['helper']['data'],b'new')
        self.assertEqual(fs.private['children']['helper']['uid'],0)
        self.assertEqual(fs.private['children']['helper']['mode']&0o777,0o640)
        self.assertIs(fs.replacements[0][1],fs.private)
        self.assertEqual(list(fs.private['children']),['helper'])

    def test_path_replacement_after_check_does_not_redirect_write(self):
        fs=DescriptorOS();replacement=directory(0o700)
        def swap():fs.lib['children']['ugreen-nas-admin']=replacement
        self.execute(fs,"swap()\ndata=b'new'",swap=swap)
        self.assertEqual(replacement['children'],{})
        self.assertEqual(fs.private['children']['helper']['data'],b'new')

    def test_untrusted_parent_aborts_before_reading_data(self):
        fs=DescriptorOS();fs.var['uid']=1000
        with self.assertRaises(PermissionError):self.execute(fs,"raise AssertionError('payload read')")

    def test_write_error_preserves_old_file_and_removes_only_staging(self):
        fs=DescriptorOS();fs.fail_write=True
        with self.assertRaisesRegex(OSError,'disk full'):self.execute(fs)
        self.assertEqual(fs.private['children']['helper']['data'],b'old')
        self.assertEqual(list(fs.private['children']),['helper'])

    def test_data_read_failure_closes_pinned_directory(self):
        fs=DescriptorOS()
        with self.assertRaisesRegex(OSError,'source'):self.execute(fs,"raise OSError('source')")
        self.assertEqual(fs.replacements,[])

    def test_symbolic_link_destination_rejected(self):
        fs=DescriptorOS();fs.private['children']['helper']['mode']=stat.S_IFLNK|0o777
        with self.assertRaises(ValueError):self.execute(fs)
        self.assertEqual(fs.replacements,[])


if __name__=='__main__':unittest.main()
