# -*- coding: utf-8 -*-
import sys
from itertools import chain
from collections import OrderedDict, defaultdict
from django.db import models
from django.conf import settings
from django.db.transaction import atomic
from django.utils.module_loading import autodiscover_modules
from .utils import group_by, queryset_iterator, changeStyle, progressbar_iter, in_chunk, ct_model_map, obj
from .models import PipelineTrack, PipelineError
from .exceptions import PipeIgnore, PipeContinue, PipeBreak
from . import get_session
try:
    from mptt.models import MPTTModel
except ImportError:
    MPTTModel = None

import logging
logger = logging.getLogger("pipeline")

PIPE_IMPORTED = False


class Session(object):
    _mode = "seq"  # or gevent
    pipes = defaultdict(OrderedDict)
    triggers = defaultdict(list)
    _pipe_cache = {}
    ct_model_map = ct_model_map

    def __init__(self, context=None, debug=None, chunksize=2000, direct_save=False, atomic=True, trigger_from_name=None):
        self._import_pipes()
        self.context = obj() if context is None else context
        self.debug = settings.DEBUG if debug is None else debug
        self.chunksize = chunksize
        self.direct_save = direct_save
        self.atomic = atomic
        self.trigger_from_name = trigger_from_name

    @classmethod
    def _import_pipes(cls):
        global PIPE_IMPORTED
        if PIPE_IMPORTED:
            return
        autodiscover_modules("pipes")
        PIPE_IMPORTED = True

    def _get_default_name(self, items):
        if isinstance(items, models.QuerySet):
            if hasattr(items, "get_default_pipe_name"):
                return items.get_default_pipe_name()

        try:
            item = items[0]
        except IndexError:
            return None

        if hasattr(item, "get_default_pipe_name"):
            return item.get_default_pipe_name()
        return None

    def run_in_celery(self, items, name=None, with_old_items={}, celery_chunksize=10, queue=None):
        if isinstance(items, models.QuerySet):
            ids = list(items.values_list("id", flat=True))
            model = items.model
        else:
            ids = [item.id for item in items]
            model = type(item)
        from celery import current_app as celery
        for chunk_ids in in_chunk(ids, celery_chunksize):
            celery.send_task("datapipe.run", kwargs={
                "item_ct_id": ct_model_map[model],
                "items_id": chunk_ids,
                "name": name,
                "with_old_items": with_old_items,
                "options": {
                    "debug": self.debug,
                    "chunksize": self.chunksize,
                    "direct_save": self.direct_save,
                    "atomic": self.atomic,
                    "trigger_from_name": self.trigger_from_name,
                }
            }, queue=queue)

    def run(self, items, name=None, with_old_items={}, pipe=None):
        assert not (name and pipe), "Pipe and name can be specify only one of them"
        if pipe:
            name = pipe.__name__
            pipe.name = name
            self.pipe = pipe
            return_results = True
        else:
            name = name + ".default" if name and "." not in name else name
            if name is None:
                name = self._get_default_name(items)
            assert name, "Must define which pipeline to run"
            self.pipe = self.get_pipe(name)
            return_results = False

        self.process_start(name)

        items = items if isinstance(items, (list, tuple, models.QuerySet)) else [items]

        if self.debug and self.atomic:
            with atomic():
                self._to_process(items, with_old_items=with_old_items)
        else:
            self._to_process(items, with_old_items=with_old_items)
        if not self.results:
            return
        self.fire_trigger(name)
        if return_results:
            return self.results[0]

    def _to_process(self, items, with_old_items=None):
        # multi level pipeline
        for depend in self.pipe.depends:
            depend_pipe = self.get_pipe(depend)
            # if depend_pipe.mode not in ("auto", self._mode):
            # pp_cls = get_session(depend_pipe.mode)
            # else:
            # pp_cls = type(self)

            print("running dependancy:%s" % depend)
            get_session(mode=depend_pipe.mode, context=self.context, debug=self.debug, chunksize=self.chunksize, atomic=False)\
                .run(items, name=depend)
        # prepare items
        print "preparing %s" % self.pipe.__name__
        self.local.with_old_items = with_old_items
        with self.pipe(context=self.context, local=self.local, direct_save=self.direct_save).set_context(items) as items:
            count = items.count() if isinstance(items, models.QuerySet) else len(items)
            if not count:
                self.process_end()
                return

            # with Progressbar(count) as pg:
            self._process_atomic(items, count)
            self.process_end()

    def _process_atomic(self, items, count):
        for item in progressbar_iter(queryset_iterator(items, self.chunksize), count):
            # for item in items:
            error_class, error_obj, error_tb = None, None, None
            try:
                with atomic():
                    self.process_each(item)
                    # pg.send({})
                    if self.should_save_now():
                        self.bulk_save_to_database()
            except PipeIgnore as e:
                if e.message:
                    print "Ignore %s:%s" % (item, e.message)
                # pg.send({"ignore": 1})
                continue
            except PipeBreak:
                break
            except Exception:
                error_class, error_obj, error_tb = sys.exc_info()
                if self.debug:
                    raise error_class, error_obj, error_tb
                else:
                    self.process_exception(item, error_tb, error_obj)
                self.errors.append((item, error_obj, error_tb))
            finally:
                del error_class, error_obj, error_tb
                # pg.send({"error": 1})

    def process_exception(self, item, error_tb, error_obj):
        logger.exception("<%s:%s> %s", type(item).__name__, item.id if isinstance(item, models.Model) else id(item), item)
        PipelineError.from_except(self.pipe.name, item, error_tb, error_obj).save()

    def process_each(self, item):
        pipe = self.pipe(item=item, session=self, context=self.context, local=self.local, direct_save=self.direct_save)
        try:
            res = pipe.process()
        except PipeContinue as e:
            res = e.message  # continue as valid result
        pipe.contribute_to_session(res)

    def get_pipe(self, name):
        name = name + ".default" if "." not in name else name
        try:
            pipe_cls = self._pipe_cache[name]
        except KeyError:
            assert name in self.pipes, "no %s pipes found" % name
            pipes = self.pipes[name].keys()
            pipes.reverse()
            pipe_cls = self._pipe_cache[name] = type(
                str("%sPipe" % changeStyle(name.replace(".", "_"))),
                tuple(pipes),
                {"name": name}
            )
        return pipe_cls

    def process_start(self, name):
        self.to_save = {}
        self.to_save_size = 0
        self.saved_items = {}
        self.items_result = {}
        self.need_rebuild = {}
        self.local = obj(_name=name)
        self.errors = []
        self.old_results = []
        self.results = []

    def process_end(self):
        self.bulk_save_to_database()
        self.old_results = dict(self.old_results)
        del self.local
        del self.items_result
        del self.saved_items
        del self.to_save
        # self.context=None
        # self._clear_pipe_cache()

    def fire_trigger(self, name):
        triggers = self.triggers.get(name, [])

        if self.old_results:
            old_results = self.old_results.values()
            result_cls = type(old_results[0])
            if issubclass(result_cls, models.Model):
                trackers = PipelineTrack.objects.filter(
                    trigger_from_name=name,
                    item_content_type_id=ct_model_map[result_cls],
                    item_id__in=[item.id for item in old_results]
                )
                if trackers.exsits():
                    deleted_trackers = trackers.exclude(pipeline_name__in=triggers) if triggers else trackers

        if triggers:
            p = type(self)(context=self.context, debug=self.debug, chunksize=self.chunksize, atomic=True, trigger_from_name=name)
            for trigger_name in triggers:
                p.run(self.results, with_old_items=self.old_results, name=trigger_name)

        if "deleted_trackers" in locals():
            for tracker in deleted_trackers:
                tracker.revert()

    def _clear_pipe_cache(self):
        self._pipe_cache = {}

    def should_save_now(self):
        if self.debug:
            return self.to_save_size >= self.chunksize
        else:
            return True

    def bulk_save_to_database(self):
        to_save, self.to_save, self.to_save_size, = self.to_save, {}, 0
        saved_items, self.saved_items = self.saved_items, {}
        items_result, self.items_result = self.items_result, {}
        grouped_to_save = group_by(chain(*to_save.itervalues()), lambda x: type(x))
        for cls, items in grouped_to_save.iteritems():
            if MPTTModel and issubclass(cls, MPTTModel):
                with cls.objects.disable_mptt_updates():
                    for item in items:
                        item.lft = item.rght = item.level = item.tree_id = 0
                    cls.objects.bulk_create(items)
                if self.need_rebuild.get(cls):
                    cls.objects.rebuild()
            else:
                cls.objects.bulk_create(items)
        if self.local._enable_reparse:
            PipelineTrack.objects.bulk_create(filter(
                None,
                (
                    PipelineTrack.by_objects(
                        name=self.local._name,
                        item=item,
                        objects=chain(to_save.get(item, []), saved_items.get(item, [])),
                        result=items_result.get(item),
                        trigger_from_name=self.trigger_from_name
                    )
                    # for item,to_save_objs in to_save.iteritems()
                    for item in set(chain(saved_items.keys(), to_save.keys(), items_result.keys()))
                )
            ))
