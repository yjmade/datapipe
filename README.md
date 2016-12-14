# DataPipe
*a data processing framework let you build workflow just like making building blocks, and makes it run in parallels*

##Concept
In the project of my company, we are facing few challenges.

- Input data come from different sources, like spiders, logs, they are in different machine, have to have a way to collect them together, and needs to be processed as soon as possible.
- The input data get different types, need different flow to process.
- For each flow, it get multiple steps to finish the work. For example, say I crawled a news website, so I need to see if the news has already existed in the database, then check if the author has already created, then check if the content is valid, then clean up the content... Finally, save the result to database. Some of the steps can be share between different flow, and some are not. Some step can be irelevent to the other steps so that it should be able to plug into the flow. So we want to build each step seperately, like a LEGO building block. Then assemble them together. If we do it right, the code should be clean, easy to read, easy to write, easy to maintain.
- The data source like spider to provide input data may get problem, processing flow itself can have bugs too. So we need to track what has been written to database after one specific input data item has been processed, and be able to erase the outcome and reprocessing by feed the flow with the same item.
- When bug happens, error and the enviroment should be logged, then rollback the database operation related to this input item. After the issue has been addressed, you should be able to put the items which throwed the error to the flow again with one single click.
- When multiple results come, you should be able to processing them in parallels.
- If the speed of processing is not enough, can easily scale up the workers.
- Monitoring ongoing process status.
- All the boring staff just mentioned which has nothing to do with the processing flow, should be shared as much as possible, so that developer can put most attention to the building of the flow itself. 

With all these requirments, I built this module. And it has been up and running for 2 years. Now I open source it, to share it as a infrastructure.

##Prerequest
Since we love python, and the project of the company is build with Django, so datapipe is made as a Django reusable module.

Also, some of the features rely on the postgres's `jsonb` field, so the minimal requirment is to configure the `PipelineTrack` model to use the postgres database.

##How it works
In the project, we build all the processing procedure with datapipe, and run it as a daemon. Then, have a MQ(Message Queue) to link to daemon with different data sources. Each different data source will throw raw data into the MQ, then datapipe starts to process it in parallels.

Here is an example of how the datapipe looks like: [source](https://github.com/yjmade/datapipe/blob/master/tests/simple/pipes/__init__.py)

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


@pipeline("discount_sum")  # register the last pipe with a name, that is the pipeline
class Save(DiscountSum):
    result_model = ResultItem

    def process(self):
        item = super(Save, self).process()

        self.add_to_save(self.result_model(number=self.total))
        return item

```

To run it:

```python
from datapipe import get_session
sess=get_session()
sess.run("discount_sum",SourceItem.objects.all())
```

If you have celery worker running:
```python
from datapipe import get_session
sess=get_session()
sess.run_in_celery("discount_sum",SourceItem.objects.all(),queue=QUEUE_NAME)
```
###Explaination
`SourceItem` is the input items, and the result will be put into `ResultItem`. Both of them are django Model with only an integer field named `number`.

It's equivalent to this following code

```python
source_list=[...]  # a list of numbers
# prepare
results=[]
total=0
discount=0.99
for source in source_list:  # process
    total+=source  # GradulSum
    results.append(total) # Save
    total*=0.99  # DiscountSum
``` 

There are three main concepts in datapipe:

- `Pipe` is a single data processing step
- `Pipeline` is the assemble of multiple Pipes to one procedure. 
- `Session` is in charge of managing the running Pipelines.

In the above example, we have build one `Pipeline` with 3 `Pipe`.

Datapipe uses python buildin class inheritance to assemble the Pipes together. So, the 1st step pipe `GradualSum` is a class inherited from `Pipe`, and next step pipe inherits from the previous step pipe. 
<!--
Why we use inherit to connect the `Pipe`?-->

Think about a `Pipeline` as the real assembly line.

![Pipeline](https://upload.wikimedia.org/wikipedia/commons/2/29/Ford_assembly_line_-_1913.jpg)

* The whole assembly line sequence is a `Pipeline`.
* The man placed in the certain postion of the sequence is a `Pipe`, he's been taught to do specific work.
* One man's work can rely on the other's, so in datapipe, one `Pipe` inherit all the `Pipe`s it relies on, to specify the relationship of dependency. 
* For convinience of development, each pipe can be running seperately,`output=Pipe.eval(item)`.
* The worker process the item one by one, but the pipeline accepts input(raw material) in batch. So if you need to do some preparation before the formal one-by-one process, you can rewrite a method `prepare(items)`.
* The one-by-one process in running in the `pipe.process()` method, where most of your code lives in. The item is get by `item = super(GradualSum, self).process()`.
* Inherited `Pipe` has the method `pipe.finish(results)` and will be called after all processing items are finished. Results returned by the `result=pipe.process()` will go to this method. 
* At the end of the assembly line, there is a person responsible to put all products to a big box and send it out. In datapipe, the outcome of pipeline, usually is an item that will be written to database. Usually the last `Pipe` is in charge of merging all results from it's depending `Pipe`s to store them in result object, then put the result object in the buffer by `self.add_to_save(result_item)`. `Session` is responsible to save the output in batch periodically.
* There are containers for people to store some half products, which will be used later. In datapipe, in the `Pipe`, there are three different containers. The `Pipe` instance `self`, `self.local` and `self.context`. You can do `self.total=1`,`self.local.total=1` or even `self.context.total=1`. The difference between them is it's life span. `self` lives for only this one specific item; `self.local` lives for all the items but without the `chained pipeline`(will explain later); `self.context` lives all the time even with the `chained pipeline`. You can make an analogy with the assembly line, the variable put in `self` is like there is a bucket together with the item on the conveyor belt, workers can put some stuff in it and these stuff can be used by other person, but after the process of the item has finished, this bucket will gone. `self.local` is like a big table, every people can put thing on it and be shared, but it will be clean up when all the batch of items finished. `self.context` is another table next `self.local`, what different is the stuff on it will be pack together with the output and send together to the next `Pipeline` chained on this `Pipeline`.     
* All methods written under each `Pipe` can be used by all other connected pipes, like a wrench on the table. If they need to be marked as private not to be confused with others, you need to name them with 2 beginning underscores.
* Reparse: The Pipeline will record the outputs with the corresponding input item. Next time, when it will see the same input item again, it will remove the old outputs from database first and do the processing again. So if you run the above run code 2 times, the count of ResultItem will not change.
* Exception Handler: In assembly line, if some person gets an error, which he has no idea how to deal with in current situation(uncatched exception), he will take the item out of the conveyor belt, clean the related intermediate outputs(rollback the database to the savepoint before starting this item), and put it in some other bucket with a note of the situation(`PipelineError` Collector). **Then he moves on to the next item.** Periodically the engeneers will come to check the error colletor bucket and figure out what has happened and teach the worker how to deal with it(You fix the code). Then all the collected items will be put in the pipeline again in batch. 
* Parallels: If the input comes too fast, you can easily open up another `Session` to run it in parallels by increasing the number of workers or have other machines to run it at same time. ##TODO
* Chained Pipeline:
	* depends: if you need to do some pre-processing of items in batch, you can define a depends in the `Pipe`, for example

```python
@pipeline('main')
class Main(Pipe):
   depends=["being_depend"]  # **to specify the depends**
   
   def process(self):
       item=super(Main,self).process()
       print "main", item, item*1./self.context.depends_total
       

@pipeline("being_depend")
class Depends(Pipe):
	def prepare(items):
	    items=super(Depends).prepare(items)
	    self.context.depends_total=0
	    return items
	    
	def process(self):
	    item=super(Depends,self).process()
	    print "depend", item
	    self.context.depends_total+=item
	    return item
	    
sess=get_session()
sess.run([1,2],"main")
# depend 1
# depend 2
# main 1, 0.33333333
# main 2, 0.66666667
```

The BeingDepends get the same items as input and puts the result in `self.context` then `Main` can access it.

* 
	* trigger:  one pipeline needs to run right after some other pipeline finished and also has to run standalone in some time.

```python
@pipeline("news.import")
class NewsImport(Pipe):
    def process(raw_item_store):
        content=self.do_some_stuff_here(raw_item_store)
        result_news=self.add_to_save(News(content=content))
        return result_news
        

@pipeline("news.link.tags", trigger="news_import")
class NewsTag(Pipe):
	def process(news):
	    tags_text=self.do_some_stuff_here()
	    self.add_to_save(*[NewsTag(news=news,tag=tag_text) for tag_text in tags_text])
	    return news 
	    
	    
sess=get_session()
sess.run([news1,news2],"news.link.tags") 
# or
sess.run([raw_item_store1, raw_item_store2],"news.import")
# both run get "news.link.tags" run
``` 

Python class inheritance allow multiple inheritance, which perfectly emulate the branch nature of the data processing. With the [C3 algorithm](https://www.python.org/download/releases/2.3/mro/) of python, it just works.  

*At the first version of datapipe, I was using a list of Pipe classes to stand for different node, and session instace pass the output of one element to the next one as the input, but soon I find it's not flexable enough, and hard to share variables.*



##TODO
get the reparse entity in the pipe