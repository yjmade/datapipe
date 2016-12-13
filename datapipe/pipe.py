# -*- coding: utf-8 -*-
from collections import OrderedDict
from itertools import chain
from contextlib import contextmanager
from django.db import models
from .utils import group_by, cached_class_property, ct_model_map
from .exceptions import PipeIgnore, PipeContinue, PipeBreak
from . import get_session


class PipeMeta(type):

    def __new__(meta, name, bases, attrs):  # noqa
        depends = set(attrs.setdefault("depends", []))
        for base in bases:
            if hasattr(base, "depends"):
                depends.update(base.depends)

        attrs["depends"] = depends
        return super(PipeMeta, meta).__new__(meta, name, bases, attrs)


class BasePipe(object):
    __metaclass__ = PipeMeta
    depends = []
    mode = "auto"
    # mode can be "seq","gevent" or "auto"

    def __init__(self, item=None, session=None, context=None, local=None, direct_save=False):
        self.item = item
        self.session = session
        self.context = context if context is not None else {}
        self.local = local if local is not None else {}
        self.direct_save = getattr(self, "force_direct_save", direct_save)
        self.to_save = []
        self.saved_items = []

    def prepare(self, items):
        return items

    def process(self):
        return self.item

    def finish(self, commited, exceptions):
        del self.local

    def add_to_save(self, *items, **kwargs):
        if self.direct_save or kwargs.get("direct_save"):
            [item.save(force_insert=True) for item in items]
            self.saved_items += items
        else:
            self.to_save += items
        return_list = kwargs.get("return_list", None)
        if return_list is None:
            return items[0] if len(items) == 1 else items
        elif return_list:
            return items
        else:
            return items[0]

    track = True

    def contribute_to_session(self, result):
        if self.to_save:
            self.session.to_save[self.item] = self.to_save
            self.session.to_save_size += len(self.to_save)
        if self.saved_items:
            self.session.saved_items[self.item] = self.saved_items
        if result and isinstance(result, models.Model):
            self.session.results.append(result)
            self.session.items_result[self.item] = result

    Ignore = PipeIgnore
    Break = PipeBreak
    Continue = PipeContinue

    def _continue(self, *args, **kwargs):
        ignore = kwargs.get("ignore", False)
        if ignore:
            raise self.Continue(None)
        if args:
            # assert len(args)==1,u"No more than one value continue"
            arg, = args
            raise self.Continue(arg)
        raise self.Continue(self.item)

    def ignore(self, message=None):
        raise self.Ignore(message)

    def _break(self):
        raise self.Break()

    @contextmanager
    def set_context(self, items):
        error_info = self.session.errors if self.session else None
        commited = False
        try:
            yield self.prepare(items)
            commited = True
        # except Exception as e:
        #     commited=False
        #     print "Exception happend",e
        #     error_info= [sys.exc_info()]
        #     raise error_info[0]
        finally:
            print "finishing"
            self.finish(commited, error_info or None)

    @classmethod
    def register(cls, route, sequence=None, trigger=None, triggers=None):
        triggers = triggers if triggers else [trigger] if trigger else []
        route_elements = route.split(".")
        if len(route_elements) == 1:
            route += ".default"

        def warper(klass):
            from .pipeline import Session
            assert issubclass(klass, Pipe), "klass must be type of Pipe"
            # route
            seq = sequence or (Session.pipes[route].values()[-1] + 1 if Session.pipes[route] else 0)
            Session.pipes[route][klass] = seq
            filter_list = Session.pipes[route].items()
            filter_list.sort(key=lambda x: x[1])
            Session.pipes[route] = OrderedDict(filter_list)
            # trigger
            for trigger in triggers:
                if route not in Session.triggers[trigger]:
                    Session.triggers[trigger].append(route)
            return klass

        return warper

    @classmethod
    def eval(cls, item):
        # self.name=self.__name__
        # local=obj()
        # context=obj()
        # with cls(context=context,local=local).set_context(items) as items:
        #     for item in items:
        #         cls(item=item,context=context,local=local).process()
        return get_session().run([item], pipe=cls)


class Pipe(BasePipe):

    """add ability to reparse"""
    _enable_reparse = True

    @cached_class_property
    @classmethod
    def tracker_cls(cls):
        from .models import PipelineTrack
        return PipelineTrack

    def prepare_repocessing(self, items):
        if not self._enable_reparse or (isinstance(items, (list, tuple)) and not isinstance(items[0], models.Model)):
            self.local._enable_reparse = False
            return items
        cls = items.model if isinstance(items, models.QuerySet) else type(items[0])
        self.local._enable_reparse = True
        ids = list(items.values_list("id", flat=True)) if isinstance(items, models.QuerySet) else [item.id for item in items]  # 不能用pk
        self.local._track_logs = group_by(
            self.tracker_cls.objects.filter(pipeline_name=self.name, item_content_type_id=ct_model_map[cls], item_id__in=ids),
            "item_id"
        )

        if self.local.with_old_items:
            old_results_grouped_by_type = group_by(
                self.local.with_old_items.itervalues(),
                lambda old: old[0],
                lambda old: old[1]
            )
            query = self.tracker_cls.objects.none()
            for model_ct_id, ids in old_results_grouped_by_type.iteritems():
                # self.local._track_logs[model_ct_id]=
                query |= self.tracker_cls.objects.filter(pipeline_name=self.name, item_content_type_id=model_ct_id, item_id__in=ids)
            self.local._track_logs.update({
                (tracker.item_content_type_id, tracker.item_id): [tracker]
                for tracker in query
            })

    def process(self):
        item = super(Pipe, self).process()
        if self.local._enable_reparse:
            if self.local.get("with_old_items") and self.item in self.local.with_old_items:
                tracker_key = self.local.with_old_items[self.item]
            else:
                tracker_key = item.id
            if tracker_key in self.local._track_logs:
                trackers = self.local._track_logs.pop(tracker_key)  # TODO
                self._old_result = (trackers[0].result_content_type_id, trackers[0].result_id)
                self.tracker_cls.revert_batch(*trackers)
                # transaction will take care of the revert
        return item

    def prepare(self, items):
        items = super(Pipe, self).prepare(items)
        self.prepare_repocessing(items)
        return items

    def contribute_to_session(self, result):
        super(Pipe, self).contribute_to_session(result)
        if self.local._enable_reparse and hasattr(self, "_old_result"):
            self.session.old_results.append((result, self._old_result))

    def finish(self, commited, exceptions):
        if commited and self.local._enable_reparse and self.local._track_logs:
            self.tracker_cls.revert_batch(*chain(*(trackers for trackers in self.local._track_logs.itervalues())))
        super(Pipe, self).finish(commited, exceptions)

pipeline = Pipe.register
