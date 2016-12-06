# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('pipeline', '0004_pipelineerror_hg_rev'),
    ]

    operations = [
        migrations.AddField(
            model_name='pipelinetrack',
            name='created_date',
            field=models.DateTimeField(default=datetime.datetime(2015, 9, 23, 4, 7, 21, 388916, tzinfo=utc), auto_now_add=True),
            preserve_default=False,
        ),
    ]
