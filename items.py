#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# To ignore numpy missing docstrings and too many ancestors warnings:
#     pylint: disable=C0111,R0901

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/topics/items.html

from scrapy.item import Item, Field


class EventSummaryItem(Item):
    seq_id = Field()
    url = Field()
    name = Field()
    results_format = Field()
    status = Field()
    results = Field()       # [PersonItem]
    courses = Field()       # [CourseItem]


class PersonItem(Item):
    name = Field()
    club = Field()
    ageClass = Field()
    result = Field()        # ResultItem
    course = Field()        # CourseItem
    event = Field()         # EventItem
    venue = Field()         # VenueItem


class ResultItem(Item):
    position = Field()
    time = Field()
    course = Field()
    status = Field()
    missed = Field()
    out_of_order = Field()


class CourseItem(Item):
    name = Field()
    length = Field()
    climb = Field()
    controls = Field()


class VenueItem(Item):
    name = Field()
    location = Field()


class EventItem(Item):
    name = Field()
    level = Field()
    category = Field()
    date = Field()
    url = Field()
