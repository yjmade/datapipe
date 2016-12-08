# -*- coding: utf-8 -*-
class obj(dict):  # noqa

    def __new__(cls, *args, **kwargs):
        self = super(cls, obj).__new__(cls, *args, **kwargs)
        self.__dict__ = self
        return self

    def __hash__(self, *args, **kwargs):
        return hash(tuple(self.iteritems()))
