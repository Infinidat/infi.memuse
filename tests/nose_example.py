import unittest

class MyTest(unittest.TestCase):
    def xsetUp(self):
        global xx
        xx = 'x' * 1024 * 1024

    def xtest_leak(self):
        global x
        x = 'x' * 1024 * 1024

    def test_success(self):
        pass

    def xtest_fail(self):
        # Make sure our plugin doesn't hide an error within the test.
        global xx
        xx = 'x' * 1024 * 1024
        self.assertEqual(1, 0)
