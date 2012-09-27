__import__("pkg_resources").declare_namespace(__name__)

from psutil import Process
from os import getpid
import inspect
import gc

from infi.pyutils.decorators import wraps

DEFAULT_ALLOWED_LEFTOVER = 512 * 1024 * 1024

class PotentialMemoryLeakError(AssertionError):
    __MESSAGE__ =  \
        "\nPotential memory leak detected in {0}:\n" \
        "Baseline RSS was {1} bytes before test started, " \
        "but growed to be {2} bytes after test ended (delta={3} bytes).\n" \
        "Allowed memory leftover was {4} bytes - consider increasing it if there is no leak."

    def __init__(self, where, baseline_rss, current_rss, rss_leftover):
        super(PotentialMemoryLeakError, self).__init__(self.__MESSAGE__.format(where,
                                                                               baseline_rss, current_rss, 
                                                                               current_rss - baseline_rss,
                                                                               rss_leftover))

def get_rss():
    return get_self_rss() + get_children_rss()

def get_self_rss():
    pid = getpid()
    return Process(pid).get_memory_info().rss

def get_children_rss():
    pid = getpid()
    return sum([ child.get_memory_info().rss for child in Process(pid).get_children() ], 0)

def verify_rss(rss_leftover=DEFAULT_ALLOWED_LEFTOVER, ignore_methods=[]):
    def _decorator(func_or_class):
        if inspect.isclass(func_or_class):
            return __verify_rss_wrap_class(func_or_class, ignore_methods, rss_leftover)
        else:
            return __verify_rss_wrap_func(func_or_class, rss_leftover)
    return _decorator

def __verify_rss_wrap_class(cls, ignore_methods, rss_leftover):
    for attr_name in dir(cls):
        if not attr_name.startswith('__') and attr_name not in ignore_methods:
            attr = getattr(cls, attr_name)
            if inspect.isfunction(attr) or inspect.ismethod(attr):
                setattr(cls, attr_name, __verify_rss_wrap_func(attr, rss_leftover))
    return cls

def __verify_rss_wrap_func(func, rss_leftover):
    @wraps(func)
    def new_func(*args, **kwargs):
        gc.disable()
        gc.collect()
        rss_baseline = get_rss()
        gc.enable()
        try:
            result = func(*args, **kwargs)
        except:
            # Don't shadow the original exception if happened - we don't test for leak in this case.
            raise
        else:
            gc.disable()
            gc.collect()
            rss_current = get_rss()
            gc.enable()
            if (rss_current - rss_baseline) > rss_leftover:
                try:
                    where = 'file %s, function %s' % (inspect.getfile(func), func)
                except:
                    where = 'function %s' % (func,)
                raise PotentialMemoryLeakError(where, rss_baseline, rss_current, rss_leftover)
            
        return result
    return new_func
