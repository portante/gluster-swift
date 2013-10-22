# Copyright (c) 2012-2013 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import os
import errno
import stat
import random
import ctypes
import os.path as _os_path
from eventlet import sleep
from swift.common.utils import load_libc_function
from gluster.swift.common.exceptions import FileOrDirNotFoundError, \
    NotDirectoryError, GlusterFileSystemOSError


os_path = _os_path


def do_walk(*args, **kwargs):
    return os.walk(*args, **kwargs)


def do_write(fd, buf):
    try:
        cnt = os.write(fd, buf)
    except OSError as err:
        raise GlusterFileSystemOSError(
            err.errno, '%s, os.write("%s", ...)' % (err.strerror, fd))
    return cnt


def do_read(fd, n):
    try:
        buf = os.read(fd, n)
    except OSError as err:
        raise GlusterFileSystemOSError(
            err.errno, '%s, os.write("%s", ...)' % (err.strerror, fd))
    return buf


def do_ismount(path):
    """
    Test whether a path is a mount point.

    This is code hijacked from C Python 2.6.8, adapted to remove the extra
    lstat() system call.
    """
    try:
        s1 = os.lstat(path)
    except os.error as err:
        if err.errno == errno.ENOENT:
            # It doesn't exist -- so not a mount point :-)
            return False
        else:
            raise GlusterFileSystemOSError(
                err.errno, '%s, os.lstat("%s")' % (err.strerror, path))

    if stat.S_ISLNK(s1.st_mode):
        # A symlink can never be a mount point
        return False

    try:
        s2 = os.lstat(os.path.join(path, '..'))
    except os.error as err:
        raise GlusterFileSystemOSError(
            err.errno, '%s, os.lstat("%s")' % (err.strerror,
                                               os.path.join(path, '..')))

    dev1 = s1.st_dev
    dev2 = s2.st_dev
    if dev1 != dev2:
        # path/.. on a different device as path
        return True

    ino1 = s1.st_ino
    ino2 = s2.st_ino
    if ino1 == ino2:
        # path/.. is the same i-node as path
        return True

    return False


def do_mkdir(path):
    try:
        os.mkdir(path)
    except OSError as err:
        if err.errno == errno.EEXIST:
            logging.warn("fs_utils: os.mkdir - path %s already exists", path)
        else:
            raise GlusterFileSystemOSError(
                err.errno, '%s, os.mkdir("%s")' % (err.strerror, path))


def do_listdir(path):
    try:
        buf = os.listdir(path)
    except OSError as err:
        raise GlusterFileSystemOSError(
            err.errno, '%s, os.listdir("%s")' % (err.strerror, path))
    return buf


def dir_empty(path):
    """
    Return true if directory is empty (or does not exist), false otherwise.

    :param path: Directory path
    :returns: True/False
    """
    try:
        files = do_listdir(path)
        return not files
    except GlusterFileSystemOSError as err:
        if err.errno == errno.ENOENT:
            raise FileOrDirNotFoundError()
        if err.errno == errno.ENOTDIR:
            raise NotDirectoryError()
        raise


def do_rmdir(path):
    try:
        os.rmdir(path)
    except OSError as err:
        raise GlusterFileSystemOSError(
            err.errno, '%s, os.rmdir("%s")' % (err.strerror, path))


def do_chown(path, uid, gid):
    try:
        os.chown(path, uid, gid)
    except OSError as err:
        raise GlusterFileSystemOSError(
            err.errno, '%s, os.chown("%s", %s, %s)' % (
                err.strerror, path, uid, gid))


def do_fchown(fd, uid, gid):
    try:
        os.fchown(fd, uid, gid)
    except OSError as err:
        raise GlusterFileSystemOSError(
            err.errno, '%s, os.fchown(%s, %s, %s)' % (
                err.strerror, fd, uid, gid))


_STAT_ATTEMPTS = 10


def do_stat(path):
    serr = None
    for i in range(0, _STAT_ATTEMPTS):
        try:
            stats = os.stat(path)
        except OSError as err:
            if err.errno == errno.EIO:
                # Retry EIO assuming it is a transient error from FUSE after a
                # short random sleep
                serr = err
                sleep(random.uniform(0.001, 0.005))
                continue
            if err.errno == errno.ENOENT:
                stats = None
            else:
                raise GlusterFileSystemOSError(
                    err.errno, '%s, os.stat("%s")[%d attempts]' % (
                        err.strerror, path, i))
        if i > 0:
            logging.warn("fs_utils.do_stat():"
                         " os.stat('%s') retried %d times (%s)",
                         path, i, 'success' if stats else 'failure')
        return stats
    else:
        raise GlusterFileSystemOSError(
            serr.errno, '%s, os.stat("%s")[%d attempts]' % (
                serr.strerror, path, _STAT_ATTEMPTS))


def do_fstat(fd):
    try:
        stats = os.fstat(fd)
    except OSError as err:
        raise GlusterFileSystemOSError(
            err.errno, '%s, os.fstat(%s)' % (err.strerror, fd))
    return stats


def do_open(path, flags, **kwargs):
    try:
        fd = os.open(path, flags, **kwargs)
    except OSError as err:
        raise GlusterFileSystemOSError(
            err.errno, '%s, os.open("%s", %x, %r)' % (
                err.strerror, path, flags, kwargs))
    return fd


def do_close(fd):
    try:
        os.close(fd)
    except OSError as err:
        raise GlusterFileSystemOSError(
            err.errno, '%s, os.close(%s)' % (err.strerror, fd))


def do_unlink(path, log=True):
    try:
        os.unlink(path)
    except OSError as err:
        if err.errno != errno.ENOENT:
            raise GlusterFileSystemOSError(
                err.errno, '%s, os.unlink("%s")' % (err.strerror, path))
        elif log:
            logging.warn("fs_utils: os.unlink failed on non-existent path: %s",
                         path)


def do_rename(old_path, new_path):
    try:
        os.rename(old_path, new_path)
    except OSError as err:
        raise GlusterFileSystemOSError(
            err.errno, '%s, os.rename("%s", "%s")' % (
                err.strerror, old_path, new_path))


def do_fsync(fd):
    try:
        os.fsync(fd)
    except OSError as err:
        raise GlusterFileSystemOSError(
            err.errno, '%s, os.fsync("%s")' % (err.strerror, fd))


def do_fdatasync(fd):
    try:
        os.fdatasync(fd)
    except AttributeError:
        do_fsync(fd)
    except OSError as err:
        raise GlusterFileSystemOSError(
            err.errno, '%s, os.fsync("%s")' % (err.strerror, fd))


_posix_fadvise = None


def do_fadvise64(fd, offset, length):
    global _posix_fadvise
    if _posix_fadvise is None:
        _posix_fadvise = load_libc_function('posix_fadvise64')
    # 4 means "POSIX_FADV_DONTNEED"
    _posix_fadvise(fd, ctypes.c_uint64(offset),
                   ctypes.c_uint64(length), 4)


def do_lseek(fd, pos, how):
    try:
        os.lseek(fd, pos, how)
    except OSError as err:
        raise GlusterFileSystemOSError(
            err.errno, '%s, os.fsync("%s")' % (err.strerror, fd))


def mkdirs(path):
    """
    Ensures the path is a directory or makes it if not. Errors if the path
    exists but is a file or on permissions failure.

    :param path: path to create
    """
    try:
        os.makedirs(path)
    except OSError as err:
        if err.errno == errno.EEXIST and os.path.isdir(path):
            return
        raise GlusterFileSystemOSError(
            err.errno, '%s, os.makedirs("%s")' % (err.strerror, path))
