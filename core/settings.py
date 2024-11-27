from flask import g
from configparser import ConfigParser

def get_conf():
    if 'conf' not in g:
        conf = ConfigParser()
        conf.read("conf.ini")
        g.conf = conf

    return g.conf