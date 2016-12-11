# -*- coding: utf-8 -*-
from .pipe import Pipe, pipe, ct_model_map  # noqa


def get_pipeline(mode=None, **options):
    if mode == "gevent":
        from .gv import Pipeline
    else:
        from .pipeline import Pipeline
    return Pipeline(**options)
