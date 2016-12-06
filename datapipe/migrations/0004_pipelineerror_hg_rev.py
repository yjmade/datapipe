# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import extensions.utils.hg


class Migration(migrations.Migration):

    dependencies = [
        ('pipeline', '0003_pipelineerror_date_time'),
    ]

    operations = [
        migrations.AddField(
            model_name='pipelineerror',
            name='hg_rev',
            field=models.TextField(default=extensions.utils.hg.get_hg_changeset, null=True, blank=True),
        ),
    ]
