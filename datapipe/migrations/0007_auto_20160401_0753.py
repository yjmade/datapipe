# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-04-01 07:53
from __future__ import unicode_literals

import django.core.serializers.json
from django.db import migrations
import django_pgjsonb.fields


class Migration(migrations.Migration):

    dependencies = [
        ('pipeline', '0006_pipelineerror_error_html'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pipelineerror',
            name='error_args',
            field=django_pgjsonb.fields.JSONField(decode_kwargs={}, encode_kwargs={'cls': django.core.serializers.json.DjangoJSONEncoder}, null=True),
        ),
        migrations.AlterField(
            model_name='pipelineerror',
            name='stack_list',
            field=django_pgjsonb.fields.JSONField(decode_kwargs={}, default=list, encode_kwargs={'cls': django.core.serializers.json.DjangoJSONEncoder}),
        ),
        migrations.AlterField(
            model_name='pipelinetrack',
            name='created_info',
            field=django_pgjsonb.fields.JSONField(decode_kwargs={}, default=dict, encode_kwargs={'cls': django.core.serializers.json.DjangoJSONEncoder}),
        ),
    ]
