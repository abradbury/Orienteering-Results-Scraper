#!/usr/bin/env python3
#
# To ignore missing docstrings:
#     pylint: disable=C0111

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/topics/item-pipeline.html

from pymongo import MongoClient

# From http://doc.scrapy.org/en/latest/topics/item-pipeline.html#write-items-to-mongodb
class MongoPipeline(object):

    def __init__(self, mongo_uri, mongo_db):
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongo_uri=crawler.settings.get('MONGO_URI'),
            mongo_db=crawler.settings.get('MONGO_DATABASE')
        )

    def process_item(self, item, spider):
        if spider.name == "clubs":
            collection_name = "clubs"
        else:
            collection_name = "results"

        self.db[collection_name].insert(dict(item))
        return item

    def close_spider(self, spider):
        # Close DB connection
        self.client.close()
        print("Spider closed (blah)")

    def open_spider(self, spider):
        # Open DB connection
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]
        print("Spider opened (blah)")
