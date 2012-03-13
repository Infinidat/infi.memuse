__import__("pkg_resources").declare_namespace(__name__)

from psutil import Process
from os import getpid

def get_rss():
    return get_self_rss() + get_children_rss()

def get_self_rss():
    pid = getpid()
    return Process(pid).get_memory_info().rss

def get_children_rss():
    pid = getpid()
#    p = Process(pid)
#    if len(p.get_children()) > 0:
#        print(p.get_children()[0].get_memory_info())
    return sum([ child.get_memory_info().rss for child in Process(pid).get_children() ], 0)
