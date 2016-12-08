# -*- coding: utf-8 -*-
import sys
from pip.utils import ui
from django.conf import settings
from django.db import models
from itertools import cycle

__all__ = ["progressbar_iter", "queryset_iterator", "in_chunk"]


class ProgressMixin(object):

    def iter(self, it, n=1):
        for x in it:
            yield x
            self.next(n)
        self.finish()

    @property
    def pretty_eta(self):
        if self.eta:
            return "eta %s" % self.eta_td
        return ""

    @property
    def speed(self):
        # Avoid zero division errors...
        try:
            return "%.2f" % (1 / self.avg) + "/s"
        except ZeroDivisionError:
            return "..."

    @property
    def done(self):
        return str(self.index)

    file = sys.stdout
    hide_cursor = not settings.DEBUG


class ProgressBar(ui.WindowsMixin, ProgressMixin, ui._BaseBar):
    message = "%(percent)3d%%"
    suffix = "[%(done)s/%(max)s] %(speed)s %(pretty_eta)s"


class ProgressSpinner(ui.WindowsMixin, ui.InterruptibleMixin, ProgressMixin, ui.WritelnMixin, ui.Spinner):
    suffix = "%(done)s %(speed)s"

    def next_phase(self):
        if not hasattr(self, "_phaser"):
            self._phaser = cycle(self.phases)
        return next(self._phaser)

    def update(self):
        message = self.message % self
        phase = self.next_phase()
        suffix = self.suffix % self
        line = ''.join([
            message,
            " " if message else "",
            phase,
            " " if suffix else "",
            suffix,
        ])

        self.writeln(line)


def progressbar_iter(iterable, all_count=None):
    try:
        all_count = all_count or len(iterable)
        progressbar = ProgressBar(max=all_count)
    except TypeError:
        progressbar = ProgressSpinner()
    try:
        for i in progressbar.iter(iterable):
            yield i
    finally:
        progressbar.finish()


def queryset_iterator(objs, chunksize=None, reverse=False):
    if not chunksize or not isinstance(objs, models.QuerySet):
        return objs

    def _iter():
        ordering = '-' if reverse else ''
        queryset = objs.order_by(ordering + 'pk')
        last_pk = None
        new_items = True
        while new_items:
            new_items = False
            chunk = queryset
            if last_pk is not None:
                func = 'lt' if reverse else 'gt'
                chunk = chunk.filter(**{'pk__' + func: last_pk})
            chunk = chunk[:chunksize]
            row = None
            for row in chunk:
                yield row
            if row is not None:
                last_pk = row.pk
                new_items = True
    return _iter()


def in_chunk(iterable, chunksize):
    try:
        return _in_chunk(iterable, chunksize, iterable[0:chunksize])
    except TypeError:
        return _in_chunk_generator(iterable, chunksize, [])


def _in_chunk(iterable, chunksize, chunk):
    i = 0
    while chunk:
        yield chunk
        i += 1
        chunk = iterable[i * chunksize:(i + 1) * chunksize]


def _in_chunk_generator(iterable, chunksize, chunk):
    chunk = []
    for i, item in enumerate(iterable, 1):
        chunk.append(item)
        if not i % chunksize:
            yield chunk
            chunk = []
    if chunk:
        yield chunk
