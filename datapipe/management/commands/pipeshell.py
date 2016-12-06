# -*- coding: utf-8 -*-
# from django.core.management.commands.shell import Command as ShellCommand
from .shell import Command as ShellCommand


class Command(ShellCommand):
    def add_arguments(self,parser):
        parser.add_argument('-g', '--gevent', action='store_true', dest='gevent',help='Specify pipeline use Gevent"'),
        parser.add_argument('-w', '--worker', action='store', dest='worker',help='Specify an nuber of gevent worker number"'),
        super(Command, self).add_arguments(parser)

    def get_local(self):
        local=super(Command, self).get_local()
        if not self.gevent:
            from extensions.pipeline.pipeline import Pipeline
        else:
            from extensions.pipeline.gv import Pipeline
        local["p"]=p=Pipeline()
        local["Pipeline"]=Pipeline
        if self.worker:
            p._worker_count=int(self.worker)
        return local

    def handle(self, gevent,worker=None,**options):
        self.gevent=gevent
        self.worker=worker
        super(Command, self).handle(**options)
