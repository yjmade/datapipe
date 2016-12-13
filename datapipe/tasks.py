# -*- coding: utf-8 -*-
from celery import shared_task
from .pipeline import Session
from .utils import model_ct_map
# from celery.contrib import rdb


Session._import_pipes()


@shared_task(name="datapipe.run", bind=True)
def run_pipe(self, item_ct_id, items_id, name=None, with_old_items={}, options={}):
    items = model_ct_map[item_ct_id].objects.filter(id__in=items_id)
    Session(**options).run(items, name, with_old_items=with_old_items)
