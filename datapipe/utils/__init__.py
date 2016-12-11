# -*- coding: utf-8 -*-
from collections import defaultdict
from django.utils.functional import cached_property, SimpleLazyObject  # noqa


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


def get_ct_model_map():
    from django.contrib.contenttypes.models import ContentType
    return {ct.model_class(): ct.id for ct in ContentType.objects.all()}


ct_model_map = SimpleLazyObject(get_ct_model_map)


model_ct_map = SimpleLazyObject(
    lambda: {ct: model for model, ct in ct_model_map.iteritems()}
)


def changeStyle(string, auto=True, toCamel=False):  # noqa
    if auto:
        try:
            toCamel = string.index("_") >= 0  # noqa
        except ValueError:
            pass

    if toCamel:
        s1 = string.split("_")
        return "".join([s.capitalize() for s in s1])
    else:
        s1 = ""
        for s in string:
            if s.isupper():
                s = "_" + s.lower()
            s1 += s
        if s1[0] == "_":
            s1 = s1[1:]
        return s1


from .iter import progressbar_iter, queryset_iterator, in_chunk  # noqa
from .datastructures import *  # noqa