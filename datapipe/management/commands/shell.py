# -*- coding: utf-8 -*-
from django.core.management.commands.shell import Command as ShellCommand
import six
import sys


class Command(ShellCommand):
    def add_arguments(self,parser):
        # parser.add_argument('-g', '--gevent', action='store_true', dest='gevent',help='Specify pipeline use Gevent"'),
        # parser.add_argument('-w', '--worker', action='store', dest='worker',help='Specify an nuber of gevent worker number"'),
        parser.add_argument('-d', '--debug_sql', action='store_true', dest='debug_sql',help='debugsqlshell'),
        super(Command, self).add_arguments(parser)

    def _ipython(self):
        try:
            from IPython import embed
            local=self.get_local()
            local["embed"]=embed
            eval("embed()", {"__name__":"__main__"}, local)
        except Exception as e:
            import sys
            error_class, error_obj, tb = sys.exc_info()
            raise TypeError,TypeError(e),tb

    def get_local(self):
        from django.conf import settings
        local={}
        for app in settings.INSTALLED_APPS:
            try:
                exec("from {app}.models import *".format(app=app),{},local)
            except ImportError as e:
                if e.message=="No module named models":
                    continue
                six.reraise(*sys.exc_info())
        return local

    def handle(self,debug_sql=False,**options):
        if debug_sql:
            from . import sqlshell
        super(Command, self).handle(**options)
