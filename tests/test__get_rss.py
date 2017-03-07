import unittest
import gc
import sys
from contextlib import contextmanager

from infi.memuse import get_rss

class GetRSSTestCase(unittest.TestCase):
    PYTHON_OVERHEAD_MAX_SIZE = 40 * 1024 * 1024

    def test_get_rss__simple_program(self):
        # We assume here that our very simplistic Python program's RSS is in the range of 
        # (1MB, PYTHON_OVERHEAD_MAX_SIZE)
        mem_usage = get_rss()
        self.assertGreater(mem_usage, 1 * 1024 * 1024)
        self.assertLess(mem_usage, self.PYTHON_OVERHEAD_MAX_SIZE)

    def test_get_rss__eat_1mb(self):
        gc.collect()
        block_size = 1 * 1024 * 1024
        with self.gc_disabled():
            baseline_mem_usage = get_rss()
            eat_memory = 'x' * block_size
            delta = get_rss() - baseline_mem_usage

        # Since Python's memory allocator pre-allocates physical memory so it can create objects more quickly, the
        # delta we'll see will be less than the amount of memory we allocated for the object. As a safety precaution,
        # we check for an increase half the size of the memory we consumed.
        self.assertGreater(delta, block_size / 2)

        # Here we make sure the delta isn't too much - because there's no reason Python will allocate another 1MB.
        self.assertLess(delta, block_size * 2)

    def test_get_rss__free_10mb(self):
        gc.collect()
        block_size = 10 * 1024 * 1024
        with self.gc_disabled():
            baseline_mem_usage = get_rss()
            eat_memory = 'x' * block_size
            delta = get_rss() - baseline_mem_usage
            del eat_memory
            gc.collect()
            delta2 = get_rss() - baseline_mem_usage

        self.assertGreater(delta, block_size / 2)
        self.assertLess(delta, block_size * 2)
        self.assertLess(delta2, block_size / 2)

    def test_get_rss__one_child(self):
        block_size = 5 * 1024 * 1024
        gc.collect()
        with self.gc_disabled():
            baseline_mem_usage = get_rss()

            child = self.create_memory_eating_child(block_size)

            # We need to wait here for the process to write to us so we can be sure it's up and allocated.
            self.wait_for_child_to_be_ready(child)

            # Now we are sure the child has initialized and allocated the memory, we can now test it.
            delta = get_rss() - baseline_mem_usage

            self.wait_for_child_to_exit(child)
            gc.collect()

            delta2 = get_rss() - baseline_mem_usage
            
        self.assertGreater(delta, block_size)
        self.assertLess(delta, self.PYTHON_OVERHEAD_MAX_SIZE + block_size)
        self.assertLess(delta2, block_size)

    def test_get_rss__two_children(self):
        block_size = 5 * 1024 * 1024
        gc.collect()
        with self.gc_disabled():
            baseline_mem_usage = get_rss()

            child1 = self.create_memory_eating_child(block_size)
            child2 = self.create_memory_eating_child(block_size)

            # We need to wait here for the process to write to us so we can be sure it's up and allocated.
            self.wait_for_child_to_be_ready(child1)
            self.wait_for_child_to_be_ready(child2)

            # Now we are sure the child has initialized and allocated the memory, we can now test it.
            delta = get_rss() - baseline_mem_usage

            self.wait_for_child_to_exit(child1)
            self.wait_for_child_to_exit(child2)
            gc.collect()

            delta2 = get_rss() - baseline_mem_usage
            
        self.assertGreater(delta, block_size * 2)
        self.assertLess(delta, (self.PYTHON_OVERHEAD_MAX_SIZE + block_size) * 2)
        self.assertLess(delta2, (block_size * 2))

    def create_memory_eating_child(self, block_size):
        from psutil import Popen
        from subprocess import PIPE
        return Popen([ sys.executable,  '-c', 
                       'eat_memory = "x" * %d ; ' % (block_size,) +
                       'import sys ; ' + 
                       'sys.stdout.write("x") ; ' +
                       'sys.stdout.flush() ; ' + 
                       'sys.stdin.read(1)' ], stdin=PIPE, stdout=PIPE)

    def wait_for_child_to_be_ready(self, child):
        # Our child writes 'x' to its stdout pipe when it's ready - read it.
        child_output = child.stdout.read(1)
        self.assertEqual(child_output, 'x')

    def wait_for_child_to_exit(self, child):
        # Our child waits for a single byte from stdin to exit.
        child.communicate('x')
        self.assertEqual(child.returncode, 0)
            
    @contextmanager
    def gc_disabled(self):
        try:
            gc.disable()
            yield
        finally:
            gc.enable()
