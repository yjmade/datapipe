# -*- coding: utf-8 -*-
class PipeBreak(Exception):

    u"停止,回滚当前item"
    pass


class PipeError(Exception):

    u"停止,回滚全部"


class PipeIgnore(Exception):

    u"忽略当前item,回滚当前item的sql,继续下一个"
    pass


class PipeContinue(Exception):

    u"""忽略后面操作,不回滚,继续下一个"""
    pass
