import os

from errno import EEXIST, EPERM
from unittest import TestCase

from mock import Mock, patch

from pulp.server.content.storage import mkdir, ContentStorage, FileStorage, SharedStorage


class TestMkdir(TestCase):

    @patch('os.makedirs')
    def test_succeeded(self, _mkdir):
        path = 'path-123'
        mkdir(path)
        _mkdir.assert_called_once_with(path)

    @patch('os.makedirs')
    def test_already_exists(self, _mkdir):
        path = 'path-123'
        mkdir(path)
        _mkdir.assert_called_once_with(path)
        _mkdir.side_effect = OSError(EEXIST, path)

    @patch('os.makedirs')
    def test_other_exception(self, _mkdir):
        path = 'path-123'
        mkdir(path)
        _mkdir.side_effect = OSError(EPERM, path)
        self.assertRaises(OSError, mkdir, path)


class TestContentStorage(TestCase):

    def test_abstract(self):
        storage = ContentStorage()
        self.assertRaises(NotImplementedError, storage.put, None, None)
        self.assertRaises(NotImplementedError, storage.get, None)

    def test_open(self):
        storage = ContentStorage()
        storage.open()

    def test_close(self):
        storage = ContentStorage()
        storage.close()

    def test_enter(self):
        storage = ContentStorage()
        storage.open = Mock()
        inst = storage.__enter__()
        storage.open.assert_called_once_with()
        self.assertEqual(inst, storage)

    def test_exit(self):
        storage = ContentStorage()
        storage.close = Mock()
        storage.__exit__()
        storage.close.assert_called_once_with()


class TestFileStorage(TestCase):

    @patch('pulp.server.content.storage.sha256')
    @patch('pulp.server.content.storage.config')
    def test_get_path(self, config, sha256):
        storage_dir = '/tmp/storage'
        digest = '0123456789'
        config.get = lambda s, p: {'server': {'storage_dir': storage_dir}}[s][p]
        unit = Mock(type_id='ABC')
        unit.unit_key_as_digest.return_value = digest

        # test
        path = FileStorage.get_path(unit)

        # validation
        unit.unit_key_as_digest.assert_called_once_with(sha256.return_value)
        self.assertEqual(
            path,
            os.path.join(storage_dir, 'content', 'units',
                         unit.type_id,
                         digest[0:2],
                         digest[2:]))

    @patch('pulp.server.content.storage.shutil')
    @patch('pulp.server.content.storage.mkdir')
    def test_put_file(self, _mkdir, shutil):
        path_in = '/tmp/test'
        unit = Mock(id='123', storage_path='/tmp/storage')
        storage = FileStorage()

        # test
        storage.put(unit, path_in)

        # validation
        _mkdir.assert_called_once_with(os.path.dirname(unit.storage_path))
        shutil.copy.assert_called_once_with(path_in, unit.storage_path)

    @patch('pulp.server.content.storage.shutil')
    @patch('pulp.server.content.storage.mkdir')
    def test_put_file_with_location(self, _mkdir, shutil):
        path_in = '/tmp/test'
        location = '/a/b/'
        unit = Mock(id='123', storage_path='/tmp/storage')
        storage = FileStorage()

        # test
        storage.put(unit, path_in, location)

        # validation
        destination = os.path.join(unit.storage_path, location.lstrip('/'))
        _mkdir.assert_called_once_with(os.path.dirname(destination))
        shutil.copy.assert_called_once_with(path_in, destination)

    def test_get(self):
        storage = FileStorage()
        storage.get(None)  # just for coverage


class TestSharedStorage(TestCase):

    @patch('pulp.server.content.storage.sha256')
    def test_init(self, sha256):
        provider = 'git'
        storage_id = '1234'
        storage = SharedStorage(provider, storage_id)
        sha256.assert_called_once_with(storage_id)
        self.assertEqual(storage.storage_id, sha256.return_value.hexdigest.return_value)
        self.assertEqual(storage.provider, provider)

    @patch('pulp.server.content.storage.mkdir')
    @patch('pulp.server.content.storage.SharedStorage.content_dir', 'abcd/')
    @patch('pulp.server.content.storage.SharedStorage.links_dir', 'xyz/')
    def test_open(self, _mkdir):
        storage = SharedStorage('git', '1234')
        storage.open()
        self.assertEqual(
            _mkdir.call_args_list,
            [
                ((storage.content_dir,), {}),
                ((storage.links_dir,), {}),
            ])

    @patch('pulp.server.content.storage.config')
    def test_shared_dir(self, config):
        storage_dir = '/tmp/storage'
        config.get = lambda s, p: {'server': {'storage_dir': storage_dir}}[s][p]
        storage = SharedStorage('git', '1234')
        self.assertEqual(
            storage.shared_dir,
            os.path.join(storage_dir, 'content', 'shared', storage.provider, storage.storage_id))

    @patch('pulp.server.content.storage.SharedStorage.shared_dir', 'abcd/')
    def test_content_dir(self):
        storage = SharedStorage('git', '1234')
        self.assertEqual(
            storage.content_dir,
            os.path.join(storage.shared_dir, 'content'))

    @patch('pulp.server.content.storage.SharedStorage.shared_dir', 'abcd/')
    def test_links_dir(self):
        storage = SharedStorage('git', '1234')
        self.assertEqual(
            storage.links_dir,
            os.path.join(storage.shared_dir, 'links'))

    def test_put(self):
        unit = Mock()
        storage = SharedStorage('git', '1234')
        storage.link = Mock()
        storage.put(unit)
        storage.link.assert_called_once_with(unit)

    def test_get(self):
        storage = SharedStorage('git', '1234')
        storage.get(None)  # just for coverage

    @patch('os.symlink')
    @patch('pulp.server.content.storage.SharedStorage.content_dir', 'abcd/')
    @patch('pulp.server.content.storage.SharedStorage.links_dir', 'xyz/')
    def test_link(self, symlink):
        unit = Mock(id='0123456789')
        storage = SharedStorage('git', '1234')

        # test
        path = storage.link(unit)

        # validation
        expected_path = os.path.join(storage.links_dir, unit.id)
        symlink.assert_called_once_with(storage.content_dir, expected_path)
        self.assertEqual(path, expected_path)

    @patch('os.symlink')
    @patch('os.readlink')
    @patch('os.path.islink')
    @patch('pulp.server.content.storage.SharedStorage.content_dir', 'abcd/')
    @patch('pulp.server.content.storage.SharedStorage.links_dir', 'xyz/')
    def test_duplicate_link(self, islink, readlink, symlink):
        unit = Mock(id='0123456789')
        storage = SharedStorage('git', '1234')

        islink.return_value = True
        symlink.side_effect = OSError()
        symlink.side_effect.errno = EEXIST
        readlink.return_value = storage.content_dir

        # test
        path = storage.link(unit)
        # note: not exception raised

        # validation
        expected_path = os.path.join(storage.links_dir, unit.id)
        symlink.assert_called_once_with(storage.content_dir, expected_path)
        self.assertEqual(path, expected_path)

    @patch('os.symlink')
    @patch('os.readlink')
    @patch('os.path.islink')
    @patch('pulp.server.content.storage.SharedStorage.content_dir', 'abcd/')
    @patch('pulp.server.content.storage.SharedStorage.links_dir', 'xyz/')
    def test_duplicate_nonlink(self, islink, readlink, symlink):
        unit = Mock(id='0123456789')
        storage = SharedStorage('git', '1234')

        islink.return_value = False  # not a link
        symlink.side_effect = OSError()
        symlink.side_effect.errno = EEXIST
        readlink.return_value = storage.content_dir

        # test
        self.assertRaises(OSError, storage.link, unit)

        # validation
        expected_path = os.path.join(storage.links_dir, unit.id)
        symlink.assert_called_once_with(storage.content_dir, expected_path)

    @patch('os.symlink')
    @patch('os.readlink')
    @patch('os.path.islink')
    @patch('pulp.server.content.storage.SharedStorage.content_dir', 'abcd/')
    @patch('pulp.server.content.storage.SharedStorage.links_dir', 'xyz/')
    def test_different_link_target(self, islink, readlink, symlink):
        unit = Mock(id='0123456789')
        storage = SharedStorage('git', '1234')

        islink.return_value = True
        symlink.side_effect = OSError()
        symlink.side_effect.errno = EEXIST
        readlink.return_value = 'different link target'

        # test
        self.assertRaises(OSError, storage.link, unit)

        # validation
        expected_path = os.path.join(storage.links_dir, unit.id)
        symlink.assert_called_once_with(storage.content_dir, expected_path)

    @patch('os.symlink')
    @patch('pulp.server.content.storage.SharedStorage.content_dir', 'abcd/')
    @patch('pulp.server.content.storage.SharedStorage.links_dir', 'xyz/')
    def test_link_failed(self, symlink):
        unit = Mock(id='0123456789')
        storage = SharedStorage('git', '1234')
        symlink.side_effect = OSError()
        symlink.side_effect.errno = EPERM
        self.assertRaises(OSError, storage.link, unit)
