#!/usr/bin/env python
# coding:utf-8

"""
Copyright (c) 2017 BugScan (http://www.bugscan.net)
Copyright (C) 2024 0wnerDied <z1281552865@gmail.com>
See the file 'LICENCE' for copying permission
"""

import os
import sys
from lib.common import (
    banner,
    checkdepends,
    initAgents,
    initDirs,
    setPaths,
    usage,
)
from lib.controler import start
from lib.data import paths


def main():
    init()


def init():
    try:
        paths.GITHACK_ROOT_PATH = os.path.dirname(os.path.realpath(__file__))
        banner()
        if len(sys.argv) < 2:
            usage()
            sys.exit(1)
        checkdepends()
        setPaths(sys.argv[-1])
        initAgents()
        initDirs()
        start()
    except Exception as e:
        raise e


if __name__ == "__main__":
    main()
