# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pipeline', '0002_pipelineerror'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pipelineerror',
            name='fix_time',
            field=models.DateTimeField(null=True),
        ),
        migrations.AlterField(
            model_name='pipelineerror',
            name='occur_time',
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]
