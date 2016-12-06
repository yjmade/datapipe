# -*- coding: utf-8 -*-
from collections import defaultdict


class cached_property(object):  # noqa

    """
    Decorator that converts a method with a single self argument into a
    property cached on the instance.

    Optional ``name`` argument allows you to make cached properties of other
    methods. (e.g.  url = cached_property(get_absolute_url, name='url') )
    """

    def __init__(self, func, name=None):
        self.func = func
        self.__doc__ = getattr(func, '__doc__')
        self.name = name or func.__name__

    def __get__(self, instance, type=None):
        if instance is None:
            return self
        res = instance.__dict__[self.name] = self.func(instance)
        return res


class GroupIgnore(object):
    pass


def group_by(obj_list, prop, obj_func=lambda obj: obj):
    prop_func = (lambda obj: getattr(obj, prop)) if isinstance(
        prop, basestring) else prop
    obj_dict = defaultdict(list)
    for obj in obj_list:
        obj_dict[prop_func(obj)].append(obj_func(obj))
    obj_dict.pop(GroupIgnore, None)
    return obj_dict


class cached_class_property(property):  # noqa

    """
    Decorator that creates converts a class method with a single
    cls argument into a property cached on the class.

    class C(object):
    @cached_class_property
    @classmethod
    def x(cls):
        return self._x
    """

    def __get__(self, obj, cls):
        cache_name = "_cache_%s_%s" % (cls.__name__, self.name)
        try:
            return getattr(cls, cache_name) if obj is None else getattr(obj, cache_name)
        except AttributeError:
            res = self.fget.__get__(None, cls)()
            setattr(cls, cache_name, res)
            return getattr(cls, cache_name) if obj is None else getattr(obj, cache_name)

    def __init__(self, fget):
        self.name = fget.__func__.__name__
        super(cached_class_property, self).__init__(fget)

    def __set__(self, obj, value):
        cache_name = "_cache_%s_%s" % (obj.__class__.__name__, self.name)
        setattr(obj, cache_name, value)
