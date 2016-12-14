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

        self.context.total *= self.discount
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

It's equivalent to this following code

```python
source_list=[...]  # a list of numbers
results=[]
total=0
discount=0.99
for source in source_list:
    total+=source  # GradulSum
    results.append(total) # Save
    total*=0.99  # DiscountSum
``` 

There are three main concept in datapipe:

- `Pipe` is a single data processing step
- `Pipeline` is the assemble of multiple Pipes to one procedure. 
- `Session` is in charge of manage the running Pipelines.

In the above example, we have build one `Pipeline` with 3 `Pipe`.

Datapipe uses python buildin class inheritance to assemble the Pipes together. So, the 1st step pipe `GradualSum` is a class inherit from `Pipe`, and next step pipe inherit from the previous step pipe. 
<!--
Why we use inherit to connect the `Pipe`?-->

Think about a `Pipeline` as the real assembly line.

![Pipeline](https://upload.wikimedia.org/wikipedia/commons/2/29/Ford_assembly_line_-_1913.jpg)

* The whole assembly line sequence is a `Pipeline`.
* The man placed in the certain postion of the sequence is a `Pipe`, it's been trained/designed to do specific works.
* One man's work most times is rely on the other's work, so in datapipe, one `Pipe` inherit all the `Pipe` is rely on to specify the relationship of dependency. 
* People process the item one by one, but the pipeline accept input(raw material) in batch,  In datapipe, when run the `Pipeline`, you feed a batch of input items to the `Session`, then each `Pipe` inside the `Pipeline` process the item one by one. Each `Pipe` can rewrite a method `prepare`, all items will be feed into this method as a batch preparation before the formal one-by-one process. 
* In the end of the assembly line, there is a person to put multiple product to a big box then send it out. In datapipe, the output of pipeline, usually is an item will be write to the database. Most time the last `Pipe` is in charge of to merge all result of it's depends `Pipe` to the output object to save, then put it in the buffer. `Session` will responsible to save the output in batch periodically.
* There are spaces for people to put some intermediate product, will be used to shared to the later procedure. In datapipe, in the `Pipe`, there are there different containers. The `Pipe` instance `self`, `self.local` and `self.context`. You can do `self.total=1`,`self.local.total=1` or even `self.context.total=1`. The different between them is it's life span. `self` lives for only this one specific item; `self.local` lives for all the items but without the `chained pipeline`(will explain later); `self.context` lives all the time even with the `chained pipeline`. You can make an analogy with the assembly line, the varible put in `self` is as the man put some stuff in the bucket which on the conveyor belt next to the item to process, it can be used by next people, but when this item finished processing, this bucket will gone. `self.local` is like a big table, every people can put thing on it and be shared, but it will be clean up when all the batch of items finished. `self.context` is another table next `self.local`, what different is the stuff on it will be pack together with the output and send together to the next `Pipeline` chained on this `Pipeline`.     
* All methods write under each `Pipe` can be used by all other connected pipes, like a wrench on the table. If it need to be mark as private to not confuse with others, you need to have it name starts with 2 underscores.


Python class inheritance allow multiple inheritance, which perfectly emulate the branch nature of the data processing. With the [C3 algorithm](https://www.python.org/download/releases/2.3/mro/) of python, it just works.  

*At the first version of datapipe, I was using a list of Pipe classes to stand for different node, and session instace pass the output of one element to the next one as the input, but soon I find it's not flexable enough, and hard to share variables.*



##TODO
get the reparse entity in the pipe