# -*- coding: utf-8 -*-
def get_session(mode=None, **options):
    if mode == "gevent":
        from .gv import Session
    else:
        from .pipeline import Session
    return Session(**options)

from .pipe import Pipe, pipeline, ct_model_map  # noqa
