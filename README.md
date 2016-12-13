# DataPipe
*a data processing framework let you build workflow just like making building blocks, and make it run in parallels*

##Concept
In the project of the company, we are facing few challenges.

- Input data come from different sources, like spiders, logs, they are in different machine, have to have a way to collect them together, and need to be processed as soon as possible.
- The input data get different types, need different flow to process.
- For each flow, it get multiple steps to finish the work. For example, say I crawled a news website, so I need to see if the news has already existed in the database, then check if the author has already created, then check if the content is valid, then clean up the content... Finally, save the result to database. Some of the steps can be share between different flow, and some are not. Some step can be irelevent to the other steps so that it should be able to plug into the flow. So we want to build each step seperately, like a LEGO building block. Then assemble them together. If we do it right, the code should be clean, easy to read, easy to write, easy to maintain.
- The data source like spider to provide input data may get problem, processing flow itself can have bugs too. So we need to track what has been write to database after one specific input data item has been processed, and be able to erase the outcome and reprocessing when feed the flow with the same item.
- When bug happend, error and the enviroment should be logged, then rollback the database operation has been done related to this input item. After the issue has been addressed, be able to put the items which throwed the error to the flow again with one single click.
- When multiple result comes, be able to run them in parallels.
- If the speed of processing is not enough, can easily scale up the workers.
- Be able to monitor what the status of process going.
- All the boring staff just mentioned which has nothing to do with the processing flow, should be shared as much as possible, so that developer can put most attention to the building of the flow itself. 

With all these requirments, I build this module. And it has been there and running for 2 years. Now I open source it, to share it as a infrastructure.

##Prerequest
Since we love python, and the project of the company is build up of the Django, so datapipe is made as a Django reusable module.

Also, some of the feature is rely on the postgres's jsonb field, so at least you have to configure the PipelineTrack model to link to the postgres database.

##How it work
In the project, we build all the processing procedure with datapipe, and running it as a daemon. Then, have a MQ(Message Queue) to link to daemon with different data sources. And each different data source will throw raw data into the MQ, and datapipe start to process it one by one parallels.

Here is a example of how the datapipe looks like: [source](https://github.com/yjmade/datapipe/blob/master/tests/simple/pipes/__init__.py)

```python
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

```

To run it like this:

```python
from datapipe import get_session
sess=get_session()
sess.run("discount_sum",SourceItem.objects.all())
```
###Explain
`SourceItem` is the input items, and the result will be put into `ResultItem`. Both of them are django Model with only a integer field name as number.

There are three main concept in datapipe:

- `Pipe` is a single data processing step
- `Pipeline` is the assemble of multiple Pipes to one procedure. 
- `Session` in charge of manage the running Pipelines.

In the above example, we have build one `Pipeline` with 3 `Pipe`.

datapipe uses python buildin class inheritance to assemble the Pipes together. So, the 1st step pipe is a class inherit from `Pipe`, and 2nd step pipe just inherit from the 1st. 



##TODO
get the reparse entity in the pipe