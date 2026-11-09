"""Qt bridge policy tests without requiring FontLab or Qt on the test runner."""
from pathlib import Path
import sys
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'manager'))
import mwsm_core
from mwsm_core import Downloader, ManagerError, Cancelled
from mwsm_host import QtHttpsBridge


class Reply:
    def __init__(self, status=200, error=0, redirect=None):
        self.status, self.code, self.redirect = status, error, redirect
        self.deleted = False
    def attribute(self, key):
        return self.status if key == 'status' else self.redirect
    def error(self):
        return self.code
    def errorString(self):
        return 'TLS certificate verification failed'
    def url(self):
        return self
    def resolved(self, target):
        return SimpleNamespace(toString=lambda: target)
    def deleteLater(self):
        self.deleted = True


class HttpsTests(unittest.TestCase):
    def bridge(self):
        b = QtHttpsBridge.__new__(QtHttpsBridge)
        b.network = SimpleNamespace(QNetworkRequest=SimpleNamespace(HttpStatusCodeAttribute='status', RedirectionTargetAttribute='redirect'), QNetworkReply=SimpleNamespace(NoError=0))
        b.read = lambda job: None
        b.active = []
        return b

    def finish(self, reply):
        bridge = self.bridge()
        job = {'reply': reply, 'error': None, 'done': threading.Event()}
        bridge.active.append(job)
        bridge.finish(job)
        self.assertTrue(job['done'].is_set())
        self.assertTrue(reply.deleted)
        self.assertEqual(bridge.active, [])
        return job

    def test_ssl_error_is_not_ignored(self):
        job = self.finish(Reply(error=6))
        self.assertIn('certificate', str(job['error']))

    def test_http_failure(self):
        job = self.finish(Reply(status=404))
        self.assertIn('404', str(job['error']))

    def test_redirect_host_checked_before_following(self):
        for url in ('https://evil.test/file', 'http://github.com/file'):
            job = self.finish(Reply(status=302, redirect=url))
            self.assertIsInstance(job['error'], ManagerError)
            self.assertNotIn('redirect', job)

    def test_valid_redirect(self):
        url = mwsm_core.CATALOG_URL
        self.assertEqual(self.finish(Reply(status=302, redirect=url))['redirect'], url)

    def test_read_limit_aborts(self):
        bridge = self.bridge()
        aborted = []
        reply = SimpleNamespace(readAll=lambda: SimpleNamespace(data=lambda: b'12345'), abort=lambda: aborted.append(True))
        job = {'reply': reply, 'data': bytearray(), 'limit': 4, 'progress': lambda x: None, 'error': None}
        QtHttpsBridge.read(bridge, job)
        self.assertTrue(aborted)
        self.assertIsInstance(job['error'], ManagerError)
        self.assertEqual(job['data'], bytearray())

    def test_ui_thread_cannot_block_on_download(self):
        bridge = self.bridge()
        bridge.owner_thread = threading.get_ident()
        with self.assertRaisesRegex(ManagerError, '작업자'):
            bridge(mwsm_core.CATALOG_URL, 10, threading.Event(), lambda x: None)

    def test_dispatches_only_when_python_https_unavailable(self):
        original = mwsm_core.urllib.request.HTTPSHandler
        calls = []
        def fallback(url, limit, cancel, progress):
            calls.append((url, limit))
            return b'qt'
        try:
            del mwsm_core.urllib.request.HTTPSHandler
            with patch.object(mwsm_core, 'HTTPS_FALLBACK', fallback):
                self.assertEqual(Downloader()(mwsm_core.CATALOG_URL, 42), b'qt')
                self.assertEqual(calls, [(mwsm_core.CATALOG_URL, 42)])
                cancel = threading.Event(); cancel.set()
                with self.assertRaises(Cancelled):
                    Downloader(cancel)(mwsm_core.CATALOG_URL)
                self.assertEqual(len(calls), 1)
        finally:
            mwsm_core.urllib.request.HTTPSHandler = original
