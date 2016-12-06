# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.serializers.json
import decimal
import django_pgjsonb.fields


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='PipelineTrack',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('pipeline_name', models.TextField(null=True, db_index=True)),
                ('item_id', models.PositiveIntegerField(null=True, blank=True)),
                ('created_info', django_pgjsonb.fields.JSONField(default=dict, encode_kwargs={'cls': django.core.serializers.json.DjangoJSONEncoder}, decode_kwargs={'parse_float': decimal.Decimal})),
                ('trigger_from_name', models.TextField(null=True, db_index=True)),
                ('result_id', models.PositiveIntegerField(null=True, blank=True)),
                ('item_content_type', models.ForeignKey(related_name='+', to='contenttypes.ContentType')),
                ('result_content_type', models.ForeignKey(related_name='+', blank=True, to='contenttypes.ContentType', null=True)),
            ],
        ),
        migrations.AlterIndexTogether(
            name='pipelinetrack',
            index_together=set([('item_content_type', 'item_id')]),
        ),
    ]
