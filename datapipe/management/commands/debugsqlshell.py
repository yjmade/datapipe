# -*- coding: utf-8 -*-
from .shell import Command as ShellCommand


class Command(ShellCommand):
    def handle(self,debug_sql=False,**options):
        debug_sql=True
        super(Command, self).handle(debug_sql,**options)
