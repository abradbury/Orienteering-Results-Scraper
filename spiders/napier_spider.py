#!/usr/bin/python
# -*- coding: utf-8 -*-

# To ignore numpy errors and docstrings:
#     pylint: disable=E1101,C0111

import re       # Regular expressions - for parsing the results
import csv      # For writing the parsed results
import datetime # For storing time information

from scrapy.spiders import Spider
from scrapy.selector import Selector

from Orienteering_Scraper.items import ResultItem, CourseItem

# Parses output from Michael Napier's software, namely COLOUR and MERCS
#
# TODO: Somewhere have a check to determine which spider to use
# TODO: Try to match 'E-card XXXXXX' to a competitor
# TODO: Find case of multiple 'out of order' and handle this
# TODO: Handle different units for course length and climb
#
# @author: abradbury
class NapierSpider(Spider):
    name = "napier"
    allowed_domains = ["http://www.southyorkshireorienteers.org.uk"]
    start_urls = [
        # "http://www.southyorkshireorienteers.org.uk/event/2013-03-10-rivelin-valley/results.htm"
        # "http://www.southyorkshireorienteers.org.uk/event/2013-12-15-canklow-woods/results.htm"
        # "http://www.southyorkshireorienteers.org.uk/event/"
        "http://www.southyorkshireorienteers.org.uk/event/2013-05-11-millhouses-park/results_v2.htm"
    ]


    # The entry point for parsing details from a web page
    #
    # @param    response    The HTTP response object for a URL
    # @return   A list of parsed objects?
    def parse(self, response):
        hxs = Selector(response)

        # Select all the links that have an attribute 'name' - the course headers
        # Change the below to //a name = xxx to get both course and competitor info
        results = hxs.xpath('//a[@name]')

        items = []      # Each result
        courses = []    # A list of all courses for the event
        course_id = 1   # A unique ID for each course

        # Set up the CSV output and write the header row
        with open('output.csv', 'wb') as csvfile:
            output = csv.writer(csvfile)
            header_item = ResultItem()
            output.writerow(header_item.field_names_to_list())

            # Iterate over each set of course results e.g. white results, yellow results etc.
            for course in results:
                course_header = course.xpath('p')[0]

                if len(course_header.xpath('text()').extract()) > 0:
                    course_info = self.parse_course_info(course_header, course_id)
                    parsed_results, count = self.parse_course_results(course, course_id)

                    course_info['competitors'] = count

                    items.extend(parsed_results)
                    courses.append(course_info)

                    course_id += 1
                    for parsed_result in parsed_results:
                        output.writerow(parsed_result.fields_to_list())

            # Print the course details
            print 'Number of courses: ' + str(len(courses))
            for course in courses:
                print course.get('uid'), course.get('name'), course.get('length'), \
                course.get('climb'), course.get('controls'), course.get('competitors')

        return items


    # Something
    #
    # @param    course      m
    # @param    course_id   m
    # @return               m
    def parse_course_results(self, course, course_id):
        # Parse and store each competitor's result
        course_results = course.xpath('pre').extract()[0].splitlines()
        parsed_results = []
        competitor_count = 0

        for result in course_results:
            split_row = result.split()

            # Try to filter out irrelavent rows, e.g. 'green men's standard'
            if (len(split_row) > 2) and ('<i>' not in split_row[0]):
                parsed_result = self.parse_result_row(result)
                parsed_result['courseID'] = course_id
                parsed_results.append(parsed_result)
                competitor_count += 1

                print parsed_result
                print

        return parsed_results, competitor_count


    # Extracts the course information (such as name, length etc.)
    #
    # @param    course_header   m
    # @param    course_id       m
    # @return                   m
    @staticmethod
    def parse_course_info(course_header, course_id):
        course_details = CourseItem()

        course_details['name'] = (course_header.xpath('strong/text()').extract())[0]
        course_details['uid'] = course_id

        raw_course_details = course_header.xpath('text()').extract()[0].strip().split(', ')

        for course_descriptor in raw_course_details:
            if 'length' in course_descriptor:
                course_details['length'] = course_descriptor.split(' ')[1]
            elif 'climb' in course_descriptor:
                course_details['climb'] = course_descriptor.split(' ')[1]
            elif 'controls' in course_descriptor:
                course_details['controls'] = int(course_descriptor.split(' ')[0])

        print '+++++Parsed Details+++++'
        print '\'' + course_details['name'] + '\''
        print course_details

        return course_details


    # Checks if a parsed element is an age class e.g W12 or M50 (women's 12 or
    # men's 50) and returns true if this is the case, false otherwise.
    #
    # @param    value   The value to check
    # @return           True if the value is an age class, false otherwise
    @staticmethod
    def is_age_class(value):
        first_char = value[0]
        other_char = value[1:]
        result = False

        if(first_char == 'M') or (first_char == 'W'):
            if other_char.isdigit():
                result = True
        return result


    # Identifies the element in a row
    #
    # @param    row                 The row to analyse
    @staticmethod
    def parse_result_row(raw_row):
        item = ResultItem()
        missing_flag = False     # True when the competitor has missed controls
        ecard_flag = False       # True when the competitor details are unknown

        if "out of order" in raw_row:
            item['out_of_order'] = int(raw_row.split("out of order")[0].strip().split()[-1])
            raw_row = raw_row.replace("out of order", "")

        split_row = raw_row.split()

        # Iterate over row elements
        for i, element in enumerate(split_row):
            # Match the numerical elements such as position and missed controls
            if element.rstrip('=;').isdigit():
                if i == 0:                          # Position
                    item['position'] = int(element.rstrip('='))
                    item['status'] = 'ok'
                elif missing_flag:                   # Missed controls
                    if ';' in element:
                        missing_flag = False
                    item['missed'] = [int(element.rstrip(';'))]
                elif ecard_flag:                     # E-card number
                    item['name'] = "E-card " + element
                    ecard_flag = False

            # Match the characters to name, club and status flags
            elif re.match("^[a-zA-Z-\']+$", element.rstrip(',')) and not missing_flag:
                if element.isupper():               # Club
                    item['club'] = element
                elif element == "Missing":          # Missing controls
                    missing_flag = True
                elif i == 0 and element == "mp":    # MP (Miss-Punched)
                    item['status'] = 'mp'
                elif element == "rtd":              # RTD (Retired)
                    item['status'] = 'rtd'
                elif element == "dns":              # DNS (Did not start)
                    item['status'] = 'dns'
                elif element == 'E-card':           # E-card (unknown competitor)
                    ecard_flag = True
                elif ';' in element:
                    missing_flag = False
                else:                               # Name
                    try:
                        item['name'] += " " + element
                    except KeyError:
                        item['name'] = element

            elif missing_flag and "no" not in element:
                item['missed'] = NapierSpider.parse_missed_controls(element)

            elif element == "n/c":                  # N/C (Non-Competitive)
                item['status'] = 'n/c'

            elif NapierSpider.is_age_class(element):# Age class (M/W number)
                item['ageClass'] = element

            elif ':' in element:                    # Time
                time_parts = element.split(':')
                full_minutes = int(time_parts[0])
                hours = full_minutes / 60
                minutes = full_minutes % 60
                seconds = int(time_parts[1])
                item['time'] = datetime.time(hours, minutes, seconds).isoformat()

        return item


    # Parses the missed controls numbers from a string such as '1,4-6' to
    # return a list of missed control numbers as integers e.g. [1,4,5,6].
    #
    # @param    value   The missed controls to parse
    # @return           A list containing the missed controls
    @staticmethod
    def parse_missed_controls(value):
        missing = []
        for group in value.split(','):
            split_group = group.split('-')
            if len(split_group) > 1:
                missing += range(int(split_group[0]), int(split_group[1])+1)
            else:
                missing += [int(split_group[0])]
        return missing
