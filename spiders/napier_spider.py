#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Parses output from Michael Napier's software, namely COLOUR and MERCS

Usage:
    scrapy crawl napier

TODOs:
    TODO: Write a parser for MERCS, OEVENTS, COCOA etc.
    TODO: Try to match 'E-card XXXXXX' to a competitor
    TODO: Find case of multiple 'out of order' and handle this
    TODO: Handle different units for course length and climb

@author: abradbury
"""

import re           # Regular expressions - for parsing the results
import datetime     # For storing time information
import scrapy
from urlparse import urlparse

from Orienteering_Scraper.items import ResultItem, CourseItem, PersonItem, \
    EventItem, VenueItem, EventSummaryItem


class NapierSpider(scrapy.Spider):
    """
    Some class-level description
    """

    name = "napier"
    allowed_domains = ["www.southyorkshireorienteers.org.uk"]
    start_urls = ["https://www.southyorkshireorienteers.org.uk/results"]

    discovered_events_count = 0
    processed_events_count = 0

    def parse(self, response):
        """
        The main entry into the parsing process, starts at the results page
        of an orienteering website and works through the results pages,
        yeilding to another parser for each event found on the pages
        """

        # Process each event on the current results page
        events = response.css(
            'table.eventtable tr td[headers=jem_title] a::attr(href)')\
            .extract()

        if len(events) == 0:
            print "Error - no events found on " + response.url

        for event in events:
            yield scrapy.Request(response.urljoin(event),
                                 callback=self.parse_event_page)

        # Parse the next results page
        # next_page = response\
        #     .css('nav ul.pagination li a[title=Next]::attr(href)')\
        #     .extract_first()
        # if next_page is not None:
        #     next_page = response.urljoin(next_page)
        #     yield scrapy.Request(next_page, callback=self.parse)

    def parse_event_page(self, response):
        """
        Parses a single event page on the orienteering website to identify the
        link to the evens results page. Currently, only local event
        result pages are parsed.

        Args:
            response: the Scrapy HTTP Response object
        """

        event = EventSummaryItem(seq_id=self.discovered_events_count + 1)
        self.discovered_events_count += 1
        event['name'] = response.url

        # From an event's page, get the link to its results & send for parsing
        results_url = response.css(
            'dl.event_info dd.custom4 a::attr(href)').extract_first()
        if results_url is not None:
            url_path_parts = urlparse(results_url).path.split('.')
            file_type = url_path_parts[-1] if len(url_path_parts) > 1 else None

            if "http" not in results_url or "southyorkshireorienteers" in results_url:
                if file_type is None or "htm" in file_type:
                    yield scrapy.Request(response.urljoin(results_url),
                                         meta={'event_object': event},
                                         callback=self.parse_result)
                else:
                    event['status'] = str(file_type.upper()) + " not supported"
                    NapierSpider.printSummary(event)
                    yield event
            else:
                event['status'] = "Not following external link '" + results_url + "'"
                NapierSpider.printSummary(event)
                yield event
        else:
            event['status'] = "No results link found"
            NapierSpider.printSummary(event)
            yield event

    def update_event_results_format(self, event, results_format):
        """
        Updates the result format of an event such that the actual result
        format is not lost when an event is able to be parsed using an
        existing parser e.g. MERCS simple events can be parsed by Colour
        """
        if 'results_format' in event:
            event['results_format'] = event['results_format'] + \
                ' (parsed as ' + results_format + ')'
        else:
            event['results_format'] = results_format

    def parse_result(self, response):
        """
        Parses and identifies the type of the event results pages
        """

        event = response.meta['event_object']
        results_format = self.identify_results_page(response)

        if "Napier - Colour" in results_format:
            self.update_event_results_format(event, "Napier - Colour")
            yield self.parse_napier_common(response, event)

        elif "MERCS" in results_format:
            text = response.css("::text").extract()

            if "Relay" in text or "relay" in text:
                self.update_event_results_format(event, "MERCS relay")
                event['status'] = "MERCS relay events not supported"
                NapierSpider.printSummary(event)
                yield event

            # elif ???
            #     self.update_event_results_format(event, "MERCS multi-day")
            #     event['status'] = "MERCS multi-day events not supported"
            #     NapierSpider.printSummary(event)
            #     yield event

            # elif ???
            #     self.update_event_results_format(event, "MERCS class-split")
            #     event['status'] = "MERCS class-split events not supported"
            #     NapierSpider.printSummary(event)
            #     yield event

            else:
                links = response.css("p a::attr(href)").extract()

                if "results.htm" in links:
                    mercs_result_page = links[links.index("results.htm")]
                    self.update_event_results_format(event, "MERCS simple")
                    yield scrapy.Request(response.urljoin(mercs_result_page),
                                         meta={'event_object': event},
                                         callback=self.parse_result)
                else:
                    event['status'] = "MERCS no results link found"
                    NapierSpider.printSummary(event)
                    yield event
        else:
            event['status'] = "Unsupported results format: " + results_format
            self.update_event_results_format(event, results_format)
            NapierSpider.printSummary(event)
            yield event

    @staticmethod
    def identify_results_page(response):
        """
        Identifies the format of a results page based on the response.

        Args:
            response: the Scrapy HTTP Response object
        """
        napier_raw = response.css('address p::text')
        mercs_raw = response.css('address p a::text')
        stephan_raw = response.css('table tr td small a::text')
        cocoa_raw = response.css('head meta[name=Generator]::attr(content)')

        if napier_raw and "Napier" in napier_raw.extract_first():
            return "Napier - Colour"
        elif mercs_raw and "MERCS" in mercs_raw.extract_first():
            return "Napier - MERCS"
        elif stephan_raw and "Stephan" in stephan_raw.extract_first():
            return "Stephan"
        elif cocoa_raw and "Cocoa" in cocoa_raw.extract_first():
            return "Cocoa"
        else:
            return "--Unknown--"

    @staticmethod
    def get_napier_courses(response, event):
        # TODO: Ignore score courses that can be mixed up in the results

        # Select all the links that have an attribute 'name' - course headers
        # Change the below to //a name = xxx to get course & competitor info
        courses = results = response.css('a:not([name=TOP])[name]')

        # If no courses found, assume simple Napier format (no links)
        if len(courses) == 0:
            event['results_format'] += " (simple)"
            courses = response.css('p')
            results = response.css('pre')
            courses = [course for course in courses
                       if "Results for " not in course.extract() and
                       "Results software provided by" not in course.extract()]

        return (courses, results)

    def parse_napier_common(self, response, event):
        (courses, course_results) = NapierSpider.get_napier_courses(response,
                                                                    event)

        if len(courses) != len(course_results):
            event['status'] = (str(event.get('status', "")) +
                               ("**Mismatch between number of courses and " +
                                "course results - investigate parser**"))

        raw_event_info = response.css('a[name=TOP] p strong::text')
        event_info, venue_info = NapierSpider.parse_event_info(
            raw_event_info, response)

        items = []      # Each result
        processed_courses = []    # A list of all courses for the event

        # Iterate over each set of course results e.g. white results
        for course, results in zip(courses, course_results):
            if course.css('p::text').extract_first():
                course_info = self.parse_course_info(course)
                parsed_results = self.parse_course_results(results,
                                                           course_info,
                                                           venue_info,
                                                           event_info)

                items.extend(parsed_results)
                processed_courses.append(dict(course_info))

        if (len(items) == 0):
            event['status'] = (str(event.get('status', "")) +
                               ("**No results detected - " +
                                "investigate parser**"))
        else:
            self.processed_events_count += 1
            event['status'] = "OK"

        event['name'] = event_info['name'] + " at " + venue_info['name']
        event['results'] = items
        event['courses'] = processed_courses
        NapierSpider.printSummary(event)

        return event

    @staticmethod
    def parse_event_info(event_info, response):
        event = EventItem()
        venue = VenueItem()

        split_event_info = event_info.extract_first().split(', ')

        event['date'] = split_event_info[-1]
        event['name'] = split_event_info[0].replace('Results for ', '')
        event['url'] = response.url

        venue['name'] = split_event_info[1]

        return event, venue

    def parse_course_results(self, course, course_info, venue_info, event_info):
        # Parse and store each competitor's result
        course_results = course.css('pre').extract_first().splitlines()
        parsed_results = []

        for result in course_results:
            split_row = result.split()

            # Try to filter out irrelavent rows, e.g. 'green men's standard'
            if (len(split_row) > 2) and ('<i>' not in split_row[0]):
                parsed_result = self.parse_result_row(result)
                parsed_result['course'] = dict(course_info)
                parsed_result['venue'] = dict(venue_info)
                parsed_result['event'] = dict(event_info)
                parsed_results.append(parsed_result)

                # print "Raw: '" + str(result) + "'"
                # print "Parsed: " + str(parsed_result)
                # print

        return parsed_results

    @staticmethod
    def parse_course_info(raw_course):
        """
        Extracts the course information (such as name, length etc.)

        Args:
            raw_course: ??
        Returns:
            ??
        """
        course = CourseItem()

        course['name'] = raw_course.css('p strong::text').extract_first()

        course_text = raw_course.css('p::text').extract_first()
        stripped_course_detailed = course_text.strip().replace('(', '')\
            .replace(')', '').split(', ')

        for course_descriptor in stripped_course_detailed:
            if 'length' in course_descriptor:
                course['length'] = course_descriptor.split(' ')[1]
            elif 'climb' in course_descriptor:
                course['climb'] = course_descriptor.split(' ')[1]
            elif 'controls' in course_descriptor:
                course['controls'] = int(
                    course_descriptor.split(' ')[0])

        return course

    @staticmethod
    def is_age_class(value):
        """
        Checks if a parsed element is an age class e.g W12 or M50 (women's 12
        or men's 50) and returns true if this is the case, false otherwise.

        Args:
            value: the value to check
        Returns:
            true if the value is an age class, false otherwise
        """
        first_char = value[0]
        other_char = value[1:]
        result = False

        if(first_char == 'M') or (first_char == 'W'):
            if other_char.isdigit():
                result = True
        return result

    @staticmethod
    def parse_result_row(raw_row):
        """
        Identifies the element in a row
        TODO: Separate person and result item parsing into two methods

        Args:
            row: the row to analyse
        """
        person = PersonItem()
        result = ResultItem()

        missing_flag = False     # True when the competitor has missed controls
        ecard_flag = False       # True when the competitor details are unknown

        if "out of order" in raw_row:
            result['out_of_order'] = int(raw_row.split("out of order")[0]
                                         .strip().split()[-1])
            raw_row = raw_row.replace("out of order", "")

        split_row = raw_row.split()

        # Iterate over row elements
        for i, element in enumerate(split_row):
            # Match the numerical elements such as position and missed controls
            if element.rstrip('=;').isdigit():
                if i == 0:                          # Position
                    result['position'] = int(element.rstrip('='))
                    result['status'] = 'ok'
                elif missing_flag:                   # Missed controls
                    if ';' in element:
                        missing_flag = False
                    result['missed'] = [int(element.rstrip(';'))]
                elif ecard_flag:                     # E-card number
                    person['name'] = "E-card " + element
                    ecard_flag = False

            # Match the characters to name, club and status flags
            elif re.match("^[a-zA-Z-\']+$", element.rstrip(',')) and not missing_flag:
                if element.isupper():               # Club
                    person['club'] = element
                elif element == "Missing":          # Missing controls
                    missing_flag = True
                elif i == 0 and element == "mp":    # MP (Miss-Punched)
                    result['status'] = 'mp'
                elif element == "rtd":              # RTD (Retired)
                    result['status'] = 'rtd'
                elif element == "dns":              # DNS (Did not start)
                    result['status'] = 'dns'
                # E-card (unknown competitor)
                elif element == 'E-card':
                    ecard_flag = True
                elif ';' in element:
                    missing_flag = False
                else:                               # Name
                    try:
                        person['name'] += " " + element
                    except KeyError:
                        person['name'] = element

            elif missing_flag and "no" not in element:
                result['missed'] = NapierSpider.parse_missed_controls(element)
                missing_flag = False
                if ";" in element:
                    ooo_flag = True

            elif element == "n/c":                  # N/C (Non-Competitive)
                result['status'] = 'n/c'

            elif NapierSpider.is_age_class(element):  # Age class (M/W number)
                person['ageClass'] = element

            elif ':' in element:                    # Time
                time_parts = element.split(':')
                full_minutes = int(time_parts[0])
                hours = full_minutes / 60
                minutes = full_minutes % 60
                seconds = int(time_parts[1])
                result['time'] = datetime.time(
                    hours, minutes, seconds).isoformat()

        person['result'] = dict(result)

        return person

    @staticmethod
    def parse_missed_controls(value):
        """
        Parses the missed controls numbers from a string such as '1,4-6' to
        return a list of missed control numbers as integers e.g. [1,4,5,6].

        Args:
            value: the missed controls to parse
        Returns:
            a list containing the missed controls
        """
        missing = []
        for group in value.replace(";", "").split(','):
            split_group = group.split('-')
            if len(split_group) > 1:
                missing += range(int(split_group[0]), int(split_group[1]) + 1)
            else:
                missing += [int(split_group[0])]
        return missing

    def closed(self, reason):
        print "{:d}% of events processed ({:d} of {:d})"\
            .format(int((self.processed_events_count /
                    float(self.discovered_events_count)) * 100),
                    self.processed_events_count, self.discovered_events_count)

    @staticmethod
    def printSummary(event):
        """
        event is of type Item and because courses could be empty, the .get method 
        with a default value is neede instead of event['courses']
        """
        print "/" + ("=" * 163) + "\\"
        print "| {0:<4} {1:<156} |".format(str(event['seq_id']) + ")", event['name'])
        print "| " + ("-" * 162) + "|"
        print "| {0:<10} {1:<150} |".format("Status:", event.get("status", ""))
        print "| {0:<10} {1:<150} |".format("Format:", event.get("results_format", ""))
        print "| {0:<10} {1:<150} |".format("Courses:", len(event.get("courses", "")))
        print "| {0:<10} {1:<150} |".format("Results:", len(event.get("results", "")))
        print "\\" + ("=" * 163) + "/"
        print ""
