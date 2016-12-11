from __future__ import unicode_literals
import random
from django.db import models


# Create your models here.


class SourceItem(models.Model):
    number = models.FloatField(default=random.random)

    @classmethod
    def generate_random_data(cls, count):
        cls.objects.bulk_create(cls() for i in xrange(count))


class ResultItem(models.Model):
    number = models.FloatField()
