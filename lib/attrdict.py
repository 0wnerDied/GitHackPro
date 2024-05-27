#!/usr/bin/env python
# coding:utf-8

"""
Copyright (c) 2017 BugScan (http://www.bugscan.net)
Copyright (C) 2024 0wnerDied <z1281552865@gmail.com>
See the file 'LICENCE' for copying permission
"""

import copy
import types


class AttribDict(dict):
    """
    >>> foo = AttribDict()
    >>> foo.bar = 1
    >>> foo.bar
    1
    """

    def __init__(self, indict=None, attribute=None):
        if indict is None:
            indict = {}

        self.attribute = attribute
        super().__init__(indict)
        self.__initialised = True

    def __getattr__(self, item):
        """
        Maps values to attributes
        Only called if there *is NOT* an attribute with this name
        """
        try:
            return self[item]
        except KeyError:
            raise AttributeError(f"unable to access item '{item}'")

    def __setattr__(self, item, value):
        """
        Maps attributes to values
        Only if we are initialised
        """
        # This test allows attributes to be set in the __init__ method
        if "_AttribDict__initialised" not in self.__dict__:
            super().__setattr__(item, value)

        # Any normal attributes are handled normally
        elif item in self.__dict__:
            super().__setattr__(item, value)

        else:
            self[item] = value

    def __getstate__(self):
        return self.__dict__

    def __setstate__(self, state):
        self.__dict__ = state

    def __deepcopy__(self, memo):
        retVal = self.__class__()
        memo[id(self)] = retVal

        for attr in dir(self):
            if not attr.startswith("_"):
                value = getattr(self, attr)
                if not isinstance(
                    value,
                    (types.BuiltinFunctionType, types.FunctionType, types.MethodType),
                ):
                    setattr(retVal, attr, copy.deepcopy(value, memo))

        for key, value in self.items():
            retVal[key] = copy.deepcopy(value, memo)

        return retVal
