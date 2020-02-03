import unittest
import gc
import os
from time import sleep
from infi.memuse import verify_rss, PotentialMemoryLeakError

mem_pacman = ''

def eat_memory(amount):
    global mem_pacman
    # https://stackoverflow.com/questions/7044044/
    mem_pacman = os.urandom(amount)

def clear_eat_memory():
    global mem_pacman
    mem_pacman = ''
    gc.collect()

class VerifyRSSTestCase(unittest.TestCase):
    def setUp(self):
        clear_eat_memory()

    def tearDown(self):
        clear_eat_memory()

    def test_verify_rss__wrap_class_eat_10mb(self):
        @verify_rss(rss_leftover=512*1024)
        class Foo:
            def foo(self, a, b):
                return a + b

            def leaking_foo(self, a, b):
                eat_memory(10 * 1024 * 1024)
                return a + b

        f = Foo()

        self.assertEqual(f.foo(1, 6), 7)

        with self.assertRaises(PotentialMemoryLeakError):
            f.leaking_foo(1, 6)

    def test_verify_rss__wrap_class_ignore_method(self):
        @verify_rss(rss_leftover=512*1024, ignore_methods=[ 'leaking_foo' ])
        class Foo:
            def foo(self, a, b):
                return a + b

            def leaking_foo(self, a, b):
                eat_memory(1024 * 1024)
                return a + b

        f = Foo()

        self.assertEqual(f.foo(1, 6), 7)
        self.assertEqual(f.leaking_foo(1, 6), 7)

    def test_verify_rss__wrap_func(self):
        @verify_rss(rss_leftover=512*1024)
        def good_func(a, b, c):
            return a + b + c

        self.assertEqual(good_func(1, 2, 3), 6)

    def test_verify_rss__wrap_func_eat_100mb(self):
        @verify_rss(rss_leftover=512*1024)
        def leaking_func():
            eat_memory(100 * 1024 * 1024)
            sleep(1)

        with self.assertRaises(PotentialMemoryLeakError):
            leaking_func()
