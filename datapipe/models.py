# -*- coding: utf-8 -*-
from django.db import models
from django.utils.functional import curry, cached_property
from django_pgjsonb import JSONField
from collections import defaultdict

from django.contrib.contenttypes.models import ContentType
from .utils import group_by, ct_model_map, model_ct_map

from errorlog.models import BaseError


class PipelineError(BaseError):
    pipeline_name = models.TextField(null=True, blank=True)
    item_id = models.PositiveIntegerField(null=True, blank=True)
    item_content_type = models.ForeignKey(ContentType, null=True, blank=True, related_name='+')
    item_repr = models.TextField(null=True, blank=True)

    name_property = "pipeline_name"

    @cached_property
    def model(self):
        return model_ct_map[self.item_content_type_id]

    @cached_property
    def item(self):
        return self.model.objects.get(id=self.item_id)

    @cached_property
    def same_error_items(self):
        return self.model.objects.filter(id__in=list(self.same_errors.values_list("item_id", flat=True).distinct()))

    @classmethod
    def from_except(cls, name, item, tb, exception):
        data = {}
        if isinstance(item, models.Model):
            data.update(
                item_id=item.id,
                item_content_type_id=ct_model_map[type(item)],
                item_repr=repr(item),
            )

        return super(PipelineError, cls).from_except(name, tb, exception, **data)

    def do_fix_it(self, items, in_celery=True, queue=None, **options):
        from . import get_session
        sess = get_session(**options)
        if in_celery:
            sess.run_in_celery(items, self.pipeline_name, queue=queue)
        else:
            sess.run(items, self.pipeline_name)


class PipelineTrack(models.Model):
    pipeline_name = models.TextField(db_index=True, null=True)
    item_content_type = models.ForeignKey(ContentType, related_name='+')
    item_id = models.PositiveIntegerField(null=True, blank=True)
    created_info = JSONField(default=dict)
    trigger_from_name = models.TextField(db_index=True, null=True)
    result_content_type = models.ForeignKey(ContentType, null=True, blank=True, related_name='+')
    result_id = models.PositiveIntegerField(null=True, blank=True)
    created_date = models.DateTimeField(auto_now_add=True)

    def get_item(self, key_attr):
        print key_attr
        item_id = getattr(self, key_attr + "_id")
        item_ct = getattr(self, key_attr + "_content_type_id")
        if not item_id or not item_ct:
            return None
        return model_ct_map[item_ct].objects.get(id=item_id)

    item = cached_property(curry(get_item, key_attr="item"))
    result = cached_property(curry(get_item, key_attr="result"))

    class Meta(object):
        index_together = [
            ("item_content_type", "item_id")
        ]

    @classmethod
    def by_objects(cls, name, item, objects, result=None, trigger_from_name=None):
        if not objects:
            return None
        data = dict(
            pipeline_name=name,
            created_info=group_by(objects, lambda obj: ct_model_map[obj.__class__], lambda obj: obj.id).items(),
            trigger_from_name=trigger_from_name
        )
        data["item_content_type_id"], data["item_id"] = cls._get_generic_info(item)
        data["result_content_type_id"], data["result_id"] = cls._get_generic_info(result)
        return cls(**data)

    @classmethod
    def _get_generic_info(cls, obj):
        if isinstance(obj, models.Model):
            return ct_model_map[obj.__class__], obj.id
        elif isinstance(obj, type) and issubclass(obj, models.Model):
            return ct_model_map[obj], None
        return None, None

    @classmethod
    def _revert(cls, created_info):
        for ct, ids in created_info:
            try:
                model = model_ct_map[ct]
            except KeyError:
                continue
            objs_queryset = model.objects.filter(id__in=ids)
            objs_queryset._raw_delete(objs_queryset.db)

    def revert(self):
        self._revert(self.created_info)
        self.delete()

    @classmethod
    def revert_batch(cls, *trackers):
        created_infos = defaultdict(list)
        tracker_ids = [tracker.id for tracker in trackers]
        for tracker in trackers:
            for item_content_type_id, ids in tracker.created_info:
                created_infos[item_content_type_id] += ids
        if created_infos:
            cls._revert(created_infos.items())

        cls.objects.filter(id__in=tracker_ids).delete()

    def keep_and_delete(self):
        items = {}
        for ct, ids in self.created_info:
            model = model_ct_map[ct]
            objs_queryset = model.objects.filter(id__in=ids)
            items[model] = list(objs_queryset)
            objs_queryset._raw_delete(objs_queryset.db)
        self.old_data = items
        PipelineTrack.objects.filter(id=self.id).update(reverted=True)
        return self

    def re_insert(self):
        for model, data in self.old_data.iteritems():
            if not data:
                continue
            model.objects.bulk_create(data)
