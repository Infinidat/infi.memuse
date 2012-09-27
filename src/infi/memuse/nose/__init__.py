__import__("pkg_resources").declare_namespace(__name__)

import gc
import nose
from infi.memuse import get_rss, PotentialMemoryLeakError, DEFAULT_ALLOWED_LEFTOVER

class NosePlugin(nose.plugins.Plugin):
    name = 'infi-memuse'

    def __init__(self, *args, **kwargs):
        super(NosePlugin, self).__init__(*args, **kwargs)
        self.allowed_leftover = DEFAULT_ALLOWED_LEFTOVER

    def help(self):
        return "Checks tests for memory leaks"

    def configure(self, options, conf):
        nose.plugins.Plugin.configure(self, options, conf)
        if options.memuseLeftover:
            self.allowed_leftover = options.memuseLeftover

    def options(self, parser, env):
        nose.plugins.Plugin.options(self, parser, env)
        parser.add_option('--memuse-leftover', action='store', dest='memuseLeftover', 
                          default=DEFAULT_ALLOWED_LEFTOVER,
                          help=('Size in bytes of allowed memory footprint "leftover" after the test ends (default=%d)'
                                % DEFAULT_ALLOWED_LEFTOVER))

    def startTest(self, test):
        gc.disable()
        gc.collect()
        self.rss_baseline = get_rss()
        gc.enable()

    def stopTest(self, test):
        gc.disable()
        gc.collect()
        rss_current = get_rss()
        rss_delta = rss_current - self.rss_baseline
        gc.enable()

        if rss_delta > self.allowed_leftover:
            raise PotentialMemoryLeakError("test [%s]" % test, self.rss_baseline, rss_current, self.allowed_leftover)

    def prepareTestResult(self, result):
        # Monkey-patch the result object to convert errors created by us to failures.
        prev = result.addError
        
        def monkey_patched_addError(test, err):
            if isinstance(err[1], PotentialMemoryLeakError):
                result.addFailure(test, err)
            else:
                prev(test, err)

        result.addError = monkey_patched_addError
