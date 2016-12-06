# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django_pgjsonb.fields
import decimal
import django.core.serializers.json


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('pipeline', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PipelineError',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('fixed', models.BooleanField(default=False)),
                ('occur_time', models.DateField(auto_now_add=True)),
                ('fix_time', models.DateField(null=True)),
                ('error_type', models.TextField()),
                ('error_args', django_pgjsonb.fields.JSONField(null=True, encode_kwargs={'cls': django.core.serializers.json.DjangoJSONEncoder}, decode_kwargs={'parse_float': decimal.Decimal})),
                ('stack_list', django_pgjsonb.fields.JSONField(default=list, encode_kwargs={'cls': django.core.serializers.json.DjangoJSONEncoder}, decode_kwargs={'parse_float': decimal.Decimal})),
                ('stack_hash', models.TextField(db_index=True)),
                ('item_id', models.PositiveIntegerField(null=True, blank=True)),
                ('item_repr', models.TextField(null=True, blank=True)),
                ('pipeline_name', models.TextField(null=True, blank=True)),
                ('item_content_type', models.ForeignKey(related_name='+', blank=True, to='contenttypes.ContentType', null=True)),
            ],
            options={
                'db_table': 'pipeline_error',
            },
        ),
    ]
