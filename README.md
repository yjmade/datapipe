# django-celery-errorlog
Reuseable app for django to collect the unexpted exception and generate comprehansive report just like what you get in debug mode and store in database from celery task

Introduction
============
This is a extension of [django-errorlog](https://pypi.python.org/pypi/django-errorlog) to bring support of celery task with some other features.
I love Celery, but sometimes when there are bugs hiding in the celery tasks code, and the code has already running as deamon in the background of the production server, you will find it's hard to track and debug the error. More importantly, when a unhandled exception happened, that's also means the task failed, and the arguments send to this task will be losed.
To solve this problem, this app wrap you task function inside a database transaction, when unhandled exception been catched by the wrapper, it will do this following stuff:

1. rollback this transaction
2. get the exception and traceback to generate a HTML error report as same as the Django buildin 500 page when `DEBUG=True`, which contains the stack trace also the varibles in each stack. That make it much easier to debug.
3. record the arguments of this task
4. get the error categorized

So, after error happened, you can check the `CeleryError.unfixed_errors`, then fix the code, restart the worker, then run `error.fix()` to send this task back to the queue again to make sure all task will be run.

If you do `error.fix()` before you fixed code in place, it's doesn't matter, because even the old error has been mark as fixed, since the same error will be raised again, so you will get new error with same parameters.  

Change Logs
===========
2016-12-04: 0.1.0
Initial submit. Split the code from the online project. Write the documents, and add the tests. 


Install
=======
 
```bash
pip install django-celery-errorlog
```
Then modify the settings
 
1. Follow the instruction of [django-errorlog](https://pypi.python.org/pypi/django-errorlog) to set it up properly 
2. set up djcelery properly
3. Add `djcelery-errorlog` into `INSTALLED_APPS` after `errorlog`

Then do `python manage.py migrate` to setup the database table.



Usage
=====
In tasks.py, you have to change the import of `shared_task` and `periodic_task` from `celery` to `djcelery_errorlog` to make errorlog work, here is the example

```python
# -*- coding: utf-8 -*-
from djcelery_errorlog import shared_task


@shared_task(name="tests")
def tests(**kwargs):
    raise ValueError(kwargs)

```
That's it, now when there is uncatched exception been throwed, CeleryError will record the invoke parameter and stack trace.


 buildin shell command(same as django-errorlog)
------------------
```python
>>> from djcelery_errorlog.models import CeleryError
>>> CeleryError.unfixed_errors
{0: <CeleryError:     1 - test1 - ValueError: A>,
 1: <CeleryError:     4 - test2 - ValueError: B>}
>>> error = CeleryError.unfixed_errors[1]
>>> error
 1: <CeleryError:     4 - test1 - ValueError: B>
>>> # in this repr, the first number is the index to make it easy to select; 
>>> # the second number 4 is the the count of the same error happened;
>>> # test1 is the name of the task;
>>> # ValueError is the exception type; 
>>> # B is the args in the exception.
>>> error.vcs_rev # the git/hg version of error, for hg, it's the incremental number that is orderable
"1"
>>> error.ignore() # this command ignore the whole 4 error logs
```

Fix the error
------
After you fixed the code base on the error been tracked, you can do `error.fix([queue="queue_name"])` to get the task with same parameter run again. Remember, when you run fix on one error, all same errors will be send to the celery worker and marked as fixed.


