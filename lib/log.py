#!/usr/bin/env python
# coding:utf-8

"""
Copyright (c) 2017 BugScan (http://www.bugscan.net)
Copyright (C) 2024 0wnerDied <z1281552865@gmail.com>
See the file 'LICENCE' for copying permission
"""

import platform
import sys


class LOGGER(object):
    """
    @desc:   Terminal color output module
    @create: 2015/08/17
    """

    def __init__(self):
        """
        @desc: Create output function based on the current system
        """
        os_name = platform.uname()[0]
        self.IS_WIN = os_name == "Windows"
        self.IS_MAC = os_name == "Darwin"
        # colors
        if self.IS_WIN:
            # Windows
            self.RED = 0x0C
            self.GREY = 0x07
            self.BLUE = 0x09
            self.CYAN = 0x0B
            self.LINK = 0x30
            self.BLACK = 0x0
            self.GREEN = 0x0A
            self.WHITE = 0x0F
            self.PURPLE = 0x0D
            self.YELLOW = 0x0E
        else:
            # Other system(unix)
            self.RED = "\033[1;31m"
            self.GREY = "\033[38m"
            self.BLUE = "\033[1;34m"
            self.CYAN = "\033[36m"
            self.LINK = "\033[0;36;4m"
            self.BLACK = "\033[0m"
            self.GREEN = "\033[32m"
            self.WHITE = "\033[37m"
            self.PURPLE = "\033[35m"
            self.YELLOW = "\033[33m"
        # functions
        self.p = self.win_print if self.IS_WIN else self.os_print

    def win_reset(self, color):
        """
        @desc: Reset terminal color (for windows)
        """
        from ctypes import windll

        handler = windll.kernel32.GetStdHandle(-11)
        return windll.kernel32.SetConsoleTextAttribute(handler, color)

    def win_print(self, msg, color, enter=True):
        """
        @desc: Color output function (for windows)
        """
        color = color or self.BLACK
        self.win_reset(color | color | color)
        sys.stdout.write(("%s\n" if enter else "%s") % msg)
        self.win_reset(self.RED | self.GREEN | self.BLUE)
        return self

    def os_print(self, msg, color, enter=True):
        """
        @desc: Color output function (for unix[osx|linux..])
        """
        color = color or self.BLACK
        sys.stdout.write(("%s%s%s\n" if enter else "%s%s%s") % (color, msg, self.BLACK))
        return self

    def error(self, msg=""):
        """
        @desc:  Error message
        @param: String{msg} Text to output
        """
        self.p("[!] %s" % msg, self.RED)
        return self

    def warning(self, msg=""):
        """
        @desc:  Warning message
        @param: String{msg} Text to output
        """
        self.p("[-] %s" % msg, self.YELLOW)
        return self

    def info(self, msg=""):
        """
        @desc:  Information message
        @param: String{msg} Text to output
        """
        self.p("[*] %s" % msg, self.CYAN)
        return self

    def success(self, msg=""):
        """
        @desc:  Success message
        @param: String{msg} Text to output
        """
        self.p("[+] %s" % msg, self.GREEN)
        return self
