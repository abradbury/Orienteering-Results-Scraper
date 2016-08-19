#!/usr/bin/python
# -*- coding: utf-8 -*-

# To ignore numpy errors and docstrings:
#     pylint: disable=E1101,C0111

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/topics/items.html

from scrapy.item import Item, Field

class ResultItem(Item):
    position = Field()
    name = Field()
    club = Field()
    ageClass = Field()
    time = Field()
    courseID = Field()
    status = Field()
    missed = Field()
    out_of_order = Field()

    #TODO: replace with a better method that doesn't hardcode the attribute values
    def field_names_to_list(self):
        return ['position', 'name', 'club', 'ageClass', 'time', 'courseID', 'status', 'missed', 'out_of_order']

    def fields_to_list(self):
        return [self.get('position'), self.get('name'), self.get('club'), self.get('ageClass'), self.get('time'), self.get('courseID'), self.get('status'), self.get('missed'), self.get('out_of_order')]


class CourseItem(Item):
    uid = Field()
    name = Field()
    length = Field()
    climb = Field()
    controls = Field()
    competitors = Field()
    