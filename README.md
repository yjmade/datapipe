# DataPipe
*a framework let you build data processing procedure for production both easy and robust, and help you to deal with parallels, performancing, error handling, debugging and data reprocessing*

##What for
When building a procedure to process data, we are facing some challenges:

- Collect data from different data source and process it in real time.
- Different procedure for different type of data.
- The processing code should structured in a clean and elegant form, to make it easy to write, easy to read, and easy to extend. 
- Reprocess the data and clean up the out result easily
- Easy to debug by collecting the unhandled exception, and reprocess the data when bugs fixed.
- Do not missing one data.
- Run in parallels, and easily to scale up.
- Monitoring ongoing process status.

This framework is build to solve all these problems. It has been up and running at my company for 2 years. 

##Prerequest
1. datapipe is made as a Django reusable module
2. `Postgres` 9.4 or above is required as we need the `jsonb` field type.
3. [`Celery`](http://celeryproject.org) is required for concurrent processing.


##Installation
```bash
pip install datapipe
```
Then add `datapipe` and `django-errorlog` to `INSTALLED_APPS` of Django's settings.

Now you can write pipes at pipes.py under each apps.

To start celery worker to run pipeline in parallels, check out the [docs of Celery](http://docs.celeryproject.org/en/latest/django/first-steps-with-django.html#django-first-steps).

## Terminology
- `Pipe` is a single data processing step
- `Pipeline` is the assemble of multiple pipes. 
- `Session` is in charge of managing the running Pipelines.

##How it works
In the project of my company, there is a MQ(message queue), and the datapipe running inside Celery workers which listen to the MQ. Then when any  data source put data in the MQ, datapipe will start to processing.
Say here is a piece of code:

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

And following is the equavilent pipeline: [source](https://github.com/yjmade/datapipe/blob/master/tests/simple/pipes/__init__.py)

```python
# -*- coding: utf-8 -*-
from ..models import SourceItem, ResultItem
from datapipe.pipe import Pipe, pipeline


class GradualSum(Pipe):
    """initialize total and add number for each item to it"""

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
    """discount the total"""
    discount = 0.99

    def process(self):
        item = super(DiscountSum, self).process()

        self.context.total *= self.discount
        return item


@pipeline("discount_sum")  # register the last pipe with a name, that is the pipeline
class Save(DiscountSum):
    """save current total to result"""
    
    result_model = ResultItem

    def process(self):
        item = super(Save, self).process()

        self.add_to_save(self.result_model(number=self.total))
        return item

```
`SourceItem` is the input items, and the result will be put into `ResultItem`. Both of them are django Model with only an integer field named `number`.

In above code piece, we build a pipeline named `discount_sum`, contains three pipes, which is `GradualSum `, `DiscountSum` and `Save`.

To run the pipeline:

```python
from datapipe import get_session
sess=get_session()  # create the session instance
sess.run("discount_sum",SourceItem.objects.all())  # run discount_sum pipeline to all the SourceItems
```

Run it in parallels with celery worker:

```python
from datapipe import get_session
sess=get_session()
sess.run_in_celery("discount_sum",SourceItem.objects.all(),queue=QUEUE_NAME)
```
##Explaination

Think about a `Pipeline` as the real assembly line.

![Pipeline](https://upload.wikimedia.org/wikipedia/commons/2/29/Ford_assembly_line_-_1913.jpg)

### Execute flow

* At runtime, a list of input items will be feed into pipeline.

* Method `pipe.prepare(items)` will be called with all the input items, it returns a list of items to be processed. It's like there's person stand before the conveyor belt to do some check of the items and filter the bad input. 

* Method `pipe.process(item)` will run with the items `prepare(items)` returned one by one. 

* Non-None return of the `pipe.process(item)` will be collected, and be sent to `pipe.finish(results)` after all input item `process()` finished.

Following pseudo code shows how this processing go:

```python
def run(pipeline, items):
    prepared_item = pipeline().prepare(items)
    results=[]
    for item in prepared_items:
        result=pipeline().process(item)
        if result is not None:
            results.append(result)
    pipeline().finish(results)
           
``` 

* In `process()`,when processing one item, you can control the flow by throwing the following exceptions:
	* `PipeContinue`: stop the processing of current item, continue processing next item;
	* `PipeIgnore`:   stop the processing of current item, rollback to the beginning of this item, continue processing next item;
	* `PipeBreak`:    stop the processing of current item, rollback to the beginning of this item, stop processing the rest items;
	* `PipeError`:    stop processing, rollback all the items.

###Pipeline assemble

* The whole assembly line sequence is a `Pipeline`, numbers of worker(`Pipe`) which do specific work are included.

* The work of each worker has dependency. In datapipe, dependency relationship represented by inheritance of the pipes. 

* The side effect of pipe inheritance is that methods and properties written under each `Pipe` can be accessed by all other connected pipes. It's suggested to name the methods and properties of the pipe with 2 beginning underscores, to avoid unintention name collision.

* Python allow multiple inheritance, which perfectly emulate the branch nature of the data processing. So one `Pipe` can be inherited from multiple pipes, You have to make sure you have call the same method of the super class in the `prepare`/`process`/`finish` methods, and return the result properly. The executing order is compling to the [C3 algorithm](https://www.python.org/download/releases/2.3/mro/) of python.

* For convinience of development, each pipe can be running seperately, `output=Pipe.eval(item)`.

*At the first version of datapipe, I was using a list of Pipe classes to stand for different steps, and session instace pass the output of one pipe to the next one as the input. But soon I find it's not flexable enough, and hard to share variables.*

###Pipeline Chaining
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

The `BeingDepends` get the same items as input and puts the result in `self.context` then `Main` can access it.

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
sess.run([news1,news2],"news.link.tags")  # run standalone
# or
sess.run([raw_item_store1, raw_item_store2],"news.import") # news.link.tags will run after news.import finished
``` 

###Varible Sharing
In assembly line there are containers for people to store some half products, which will be used later. 

In datapipe, in the `Pipe`, there are three containers with different life span you can put varible by set attribute.
 
* `self` lives for only this one specific item; 
* `self.local` lives for all the items, and be cleaned at `finish()`; 
* `self.context` shared with all the chained pipeline. 
 
You can make an analogy with the assembly line, the variable put in `self` is like there is a bucket together with the item on the conveyor belt, workers can put some stuff in it and these stuff can be used by other person, but after the process of the item has finished, this bucket will gone. `self.local` is like a big table, every people can put thing on it and be shared, but it will be clean up when all the batch of items finished. `self.context` is another table next `self.local`, what different is the stuff on it will be pack together with the output and send together to the next `Pipeline` be chained.  


###Result and Error Handling

* Pipe provide a method `pipe.add_to_save(result_item)` to let you put a to be saved Django Model object in the buffer,  `Session` will periodically do the save in batch for the sake of performance. Also the object put in the `add_to_save` will be tracked for reparse.   

* Reparse: When pipeline see one input item that has been processed before, it will remove the result item tracked by add_to_save from database before do the processing again. This feature is usedful when you changed the code of pipes and the output is also changed, then you just need to run this pipeline with old items, the old results will be removed and the new results will be saved.

* Exception Handler: In assembly line, if some person gets an error, which he has no idea how to deal with in current situation(uncatched exception), he will take the item out of the conveyor belt, clean the related intermediate outputs(rollback the database to the savepoint before starting this item), and put it in some other bucket with a note of the situation(`PipelineError` Collector). **Then he moves on to the next item.** Periodically the engeneers will come to check the error colletor bucket and figure out what has happened and teach the worker how to deal with it(You fix the code). Then all the collected items will be put in the pipeline again. 

* Concurrent: `sess.run_in_celery(items,pipeline_name,[celery_chunksize=10, queue=None])` will split the input items into chunks, the size of chunk is control by celery_chunksize. Then it will send each chunk to celery worker asynchronously, and celery will run the pipeline in parallels.


##TODO
get the reparse entity in the pipe