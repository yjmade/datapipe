# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pipeline', '0005_pipelinetrack_created_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='pipelineerror',
            name='error_html',
            field=models.TextField(null=True),
        ),
    ]
