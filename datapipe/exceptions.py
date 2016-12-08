# -*- coding: utf-8 -*-
class PipeBreak(Exception):

    """stop all the operation, and rollback current item"""
    pass


class PipeError(Exception):

    """停止,回滚全部"""
    pass


class PipeIgnore(Exception):

    """ignore and rollback for this item, and keep going for next item"""
    pass


class PipeContinue(Exception):

    """like continue, do not rollback the operation, but give up all the coming operation and keep going for next item"""
    pass
