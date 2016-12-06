# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
import requests
from six.moves.urllib_parse import urlparse,urljoin
import re
uuid_re=re.compile(r'^\w{8}-\w{4}-\w{4}-\w{4}-\w{12}')
import os
from ....utils import cached_property,progressbar_iter


class Command(BaseCommand):
    def handle(self,*args,**options):
        i=0
        for queue in progressbar_iter(self.list_queues()):
            self.delete_queues(queue)
            i+=1
        print("DONE DELETE %d" % i)

    @cached_property
    def base_url(self):
        from django.conf import settings
        url_parsed=urlparse(settings.BROKER_URL)
        path=os.path.split(url_parsed.path)[0][1:].replace("/","%2F")
        port=getattr(settings, "MQ_MANAGEMENT_PORT", "15672")
        return url_parsed.hostname,port,path,url_parsed.username,url_parsed.password

    def run(self,uri,method="get"):
        host,port,path,user,password=self.base_url
        return getattr(requests, method)(
            urljoin("http://{host}:{port}".format(host=host,port=port),uri),
            auth=requests.auth.HTTPBasicAuth(user,password),
            headers={"content-type":"application/json"}
        )

    def list_queues(self):
        return [queues_info["name"] for queues_info in self.run("/api/queues/?columns=name,consumers").json() if uuid_re.match(queues_info["name"]) and not queues_info["consumers"]]

    def delete_queues(self,name):
        if self.run(os.path.join("/api/queues/",self.base_url[2],name), method="delete").content:
            return False
        return True
