import http.client
import threading
import unittest
from voice2txt.mobile_server import MobileServer


class MobileServerTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        def transcribe(data, mode, refine):
            self.calls.append((data, mode, refine))
            return {'text': '測試成功', 'source': '', 'backend': 'Whisper'}
        self.server = MobileServer(('127.0.0.1', 0), 'test-pairing-key', transcribe)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection(*self.server.server_address, timeout=3)
        connection.request(method, path, body, headers or {})
        response = connection.getresponse()
        result = (response.status, response.read(), dict(response.getheaders()))
        connection.close()
        return result

    def test_shell_and_manifest_are_available_without_key(self):
        self.assertEqual(self.request('GET', '/')[0], 200)
        status, body, headers = self.request('GET', '/manifest.webmanifest')
        self.assertEqual(status, 200)
        self.assertIn(b'"standalone"', body)
        self.assertNotIn(b'test-pairing-key', body)
        self.assertEqual(headers['Referrer-Policy'], 'no-referrer')

    def test_private_routes_require_key(self):
        self.assertEqual(self.request('GET', '/api/status')[0], 401)
        self.assertEqual(self.request('POST', '/api/transcribe?mode=zh', b'audio')[0], 401)
        self.assertEqual(self.calls, [])

    def test_audio_and_mode_reach_decoder(self):
        status, body, _ = self.request('POST', '/api/transcribe?mode=translate&refine=1', b'audio',
                                      {'Authorization': 'Bearer test-pairing-key'})
        self.assertEqual(status, 200)
        self.assertIn('測試成功', body.decode())
        self.assertEqual(self.calls, [(b'audio', 'translate', True)])

    def test_bad_mode_empty_and_oversized_audio_are_rejected(self):
        auth = {'Authorization': 'Bearer test-pairing-key'}
        self.assertEqual(self.request('POST', '/api/transcribe?mode=ask', b'audio', auth)[0], 400)
        self.assertEqual(self.request('POST', '/api/transcribe?mode=zh', b'', auth)[0], 400)
        self.assertEqual(self.request('POST', '/api/transcribe?mode=zh', b'',
                         dict(auth, **{'Content-Length': str(16 * 1024 * 1024)}))[0], 413)
        self.assertEqual(self.calls, [])

    def test_busy_decoder_does_not_queue_audio(self):
        self.server.inference_lock.acquire()
        try:
            self.assertEqual(self.request('POST', '/api/transcribe?mode=zh', b'audio',
                             {'Authorization': 'Bearer test-pairing-key'})[0], 429)
        finally:
            self.server.inference_lock.release()

    def test_files_outside_web_root_are_not_served(self):
        for path in ('/../README.md', '/mobile-runtime/pairing.json', '/api/unknown'):
            self.assertEqual(self.request('GET', path)[0], 404)


if __name__ == '__main__':
    unittest.main()
