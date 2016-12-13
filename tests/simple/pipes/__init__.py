# -*- coding: utf-8 -*-
from ..models import SourceItem, ResultItem
from datapipe.pipe import Pipe, pipeline


class GradualSum(Pipe):

    def prepare(self, items):
        assert isinstance(items[0], SourceItem)
        self.context.total = 0
        return super(GradualSum, self).prepare(items)

    def process(self):
        item = super(GradualSum, self).process()
        self.context.total += item.number
        self.total = self.context.total
        return item


class DiscountSum(GradualSum):
    discount = 0.99

    def process(self):
        item = super(DiscountSum, self).process()

        self.total *= self.discount
        return item


@pipeline("discount_sum")
class Save(DiscountSum):
    result_model = ResultItem

    def process(self):
        item = super(Save, self).process()

        self.add_to_save(self.result_model(number=self.total))
        return item
