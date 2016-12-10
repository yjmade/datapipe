# -*- coding: utf-8 -*-
from celery import shared_task
from . import get_pipeline
from .utils import model_ct_map
# from celery.contrib import rdb


Pipeline = get_pipeline()
Pipeline._import_pipes()


@shared_task(name="datapipe.run", bind=True)
def run_pipe(self, item_ct_id, items_id, name=None, options={}, **kwargs):
    items = model_ct_map[item_ct_id].objects.filter(id__in=items_id)
    Pipeline(**options).run(items, name, **kwargs)
