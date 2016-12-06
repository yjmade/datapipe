from __future__ import absolute_import, print_function, unicode_literals

from time import time
from ....utils import time_limit
# 'debugsqlshell' is the same as the 'shell'.
from django.core.management.commands.shell import Command               # noqa
try:
    from django.db.backends import utils
except ImportError:
    from django.db.backends import util as utils

import sqlparse


class PrintQueryWrapper(utils.CursorDebugWrapper):
    def execute(self, sql, params=()):
        raw_sql = sql % tuple("'%s'" % p if isinstance(p,basestring) else p for p in params)
        try:
            with time_limit(1):
                print(sqlparse.format(raw_sql, reindent=True))
        except time_limit.Timeout:
            print(raw_sql)
        try:
            start_time = time()
            return self.cursor.execute(sql, params)
        finally:
            end_time = time()
            duration = (end_time - start_time) * 1000
            # formatted_sql = sqlparse.format(raw_sql, reindent=True)
            print('[%.2fms]' % (duration))


utils.CursorDebugWrapper = PrintQueryWrapper
