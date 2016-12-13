# -*- coding: utf-8 -*-
import sys
import gevent
from gevent.queue import Queue, Empty
from .pipeline import Session as NormalSession, queryset_iterator, PipeIgnore, PipeBreak
from django.db import close_old_connections


class Session(NormalSession):
    _mode = "gevent"

    def __init__(self, worker=100, *args, **kwargs):
        super(Session, self).__init__(*args, **kwargs)
        self._worker_count = worker

    def _process_atomic(self, items, name, debug, chunksize, count, error_items, direct_save, pg):
        self.queue = Queue(maxsize=chunksize)
        gs = [gevent.spawn(self.dispatch, items, name, chunksize)]
        gs += [gevent.spawn(self.worker, pg, debug, error_items, chunksize, direct_save, i) for i in xrange(self._worker_count)]
        try:
            gevent.joinall(gs, raise_error=True)
        except PipeBreak:
            pass

    _process = _process_atomic

    def dispatch(self, items, name, chunksize):
        # print "dispatch:start"
        for item in queryset_iterator(items, chunksize):
            # print "dispatch:put in queue",item,name
            self.queue.put((item, name))
            # print "dispatch:puted in queue",item,name

    def worker(self, pg, debug, error_items, chunksize, direct_save, id):
        # print id,"worker:start"
        try:
            while True:
                # print id,"worker:to get"
                item, name = self.queue.get(timeout=1)
                # print id,"worker:geted",item
                try:
                    self.process_each(item, name, direct_save)
                    pg.send({})
                    self.bulk_save_to_database(chunksize=chunksize)
                    # print id,"worker:success",item
                except PipeIgnore:
                    pg.send({"ignore": 1})
                except (KeyboardInterrupt, PipeBreak):
                    raise
                except Exception:
                    error_class, error_obj, traceback = sys.exc_info()
                    if debug:
                        raise error_class, error_obj, traceback
                    error_items.append((item, error_obj, traceback))
                    pg.send({"error": 1})
                    # print id,"worker:error",item,error_obj
                finally:
                    close_old_connections()
                    gevent.sleep(0)
        except Empty:
            return
