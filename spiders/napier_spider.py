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
    TODO: Handle 'dnf' and 'No finish time' e.g. 2017-03-18-norfolk-park
    TODO: Handle non-latin names e.g. Jimena Calvo SÃ¡enz at above

Data source problems:
 - Sometimes there can be no space between name and club e.g. https://www.southyorkshireorienteers.org.uk/event/2017-04-29-parkwood-springs/results_v2.htm
 - Some events have mixed courses (e.g. score and normal...) https://www.southyorkshireorienteers.org.uk/event/2016-12-03-Christmas-event/results.htm

@author: abradbury
"""

# Definitions: 
# Homepage              https://www.southyorkshireorienteers.org.uk/
# Results List Page     https://www.southyorkshireorienteers.org.uk/results
# Event Page            https://www.southyorkshireorienteers.org.uk/events/event/642-outdoor-city-weekender-middle-distance-race
# Event Results Page    https://www.southyorkshireorienteers.org.uk/event/2017-01-22-big-moor/index.htm

# Useful MongoDB queries:
# db.results.find({ 'results.name': 'Bob Smith' }, { 'name': 1 })
# { "_id" : ObjectId("87y"), "name" : "Night Event at Bowden Houstead" }

import datetime                     # For storing time information
import scrapy                       # For scraping the web pages
from urlparse import urlparse       # For determining file type of web page
import itertools                    # For parsing course results in pre
from collections import Counter     # For parsing course results in pre
import math

from Orienteering_Scraper.items import ResultItem, CourseItem, PersonItem, EventItem, VenueItem, EventSummaryItem


class NapierSpider(scrapy.Spider):
    """
    Some class-level description
    """

    name = "napier"
    allowed_domains = ["www.southyorkshireorienteers.org.uk"]
    start_urls = ["https://www.southyorkshireorienteers.org.uk/results"]

    # Counters used in end of scraping summary output
    discovered_events_count = 0
    discovered_courses_count = 0
    processed_events_count = 0
    processed_courses_count = 0
    processed_results_count = 0

    # ======================================================================= #
    # Page parsers ---------------------------------------------------------- #
    # ======================================================================= #

    def parse(self, response):
        """
        The main entry into the parsing process, starts at the results list 
        page of an orienteering website and works through the results pages,
        yielding to another parser for each event found on these pages.

        Example URL: 
            https://www.southyorkshireorienteers.org.uk/results
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
        link to the event results page. Currently, only local event result 
        pages are parsed.

        Args:
            response: the Scrapy HTTP Response object

        Example URL:
            https://www.southyorkshireorienteers.org.uk/events/event/622-local-and-schools-event
        """

        event = EventSummaryItem(seq_id=self.discovered_events_count + 1)
        self.discovered_events_count += 1
        event['name'] = response.url

        # From an event's page, get the link to its results & send for parsing
        results_url = response.css('dl.event_info dd.custom4 a::attr(href)').extract_first()
        if results_url is not None:
            url_path_parts = urlparse(results_url).path.split('.')
            file_type = url_path_parts[-1] if len(url_path_parts) > 1 else None

            if "http" not in results_url or "southyorkshireorienteers" in results_url:
                if file_type is None or "htm" in file_type:
                    yield scrapy.Request(response.urljoin(results_url),
                                         meta={'event_object': event},
                                         callback=self.parse_event_results_page)
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

    def parse_event_results_page(self, response):
        """
        Parses and identifies the type of the event results pages

        Example URL:
            https://www.southyorkshireorienteers.org.uk/event/2017-04-29-parkwood-springs/results_v2.htm
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
                                         callback=self.parse_event_results_page)
                else:
                    event['status'] = "MERCS no results link found"
                    NapierSpider.printSummary(event)
                    yield event
        else:
            event['status'] = "Unsupported results format: " + results_format
            self.update_event_results_format(event, results_format)
            NapierSpider.printSummary(event)
            yield event

    # ======================================================================= #
    # Other functions ------------------------------------------------------- #
    # ======================================================================= #

    @staticmethod
    def update_event_results_format(event, results_format):
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
    def identify_course_data(response, event):
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

        return courses, results

    def parse_napier_common(self, response, event):
        (courses, course_results) = NapierSpider.identify_course_data(response, event)
        (event_info, venue_info) = NapierSpider.identify_event_info(response)

        if len(courses) != len(course_results):
            event['status'] = (str(event.get('status', "")) +
                               ("**Mismatch between number of courses and " +
                                "course results - investigate parser**"))

        event_results = []      # Each result
        processed_courses = []  # A list of all courses for the event

        # Identify the columns by looking at all course results as a whole
        column_indices = NapierSpider.identify_columns(course_results)

        # Iterate over each set of course results e.g. white results
        for course, results in zip(courses, course_results):
            if course.css('p::text').extract_first():
                self.discovered_courses_count += 1
                course_info = NapierSpider.parse_course_info(course)
                parsed_results = NapierSpider.parse_course_results(results,
                                                                   course_info,
                                                                   venue_info,
                                                                   event_info,
                                                                   column_indices)

                if len(parsed_results) > 0:
                    self.processed_courses_count += 1
                    self.processed_results_count += len(parsed_results)

                event_results.extend(parsed_results)
                processed_courses.append(dict(course_info))

        if len(event_results) == 0:
            event['status'] = (str(event.get('status', "")) +
                               ("**No results detected - " +
                                "investigate parser**"))
        else:
            self.processed_events_count += 1
            event['status'] = "OK"

        event['name'] = event_info['name'] + " at " + venue_info['name']
        event['results'] = event_results
        event['courses'] = processed_courses
        NapierSpider.printSummary(event)

        return event

    @staticmethod
    def identify_event_info(response):
        event = EventItem()
        venue = VenueItem()

        raw_event_info = response.css('a[name=TOP] p strong::text')
        split_event_info = raw_event_info.extract_first().split(', ')

        event['date'] = split_event_info[-1]
        event['name'] = split_event_info[0].replace('Results for ', '')
        event['url'] = response.url

        venue['name'] = split_event_info[1]

        return event, venue

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

    # ======================================================================= #
    # Extract individual results data --------------------------------------- #
    # ======================================================================= #

    @staticmethod
    def parse_course_results(course_results, course_info, venue_info, event_info, column_indices):
        """
        Takes the raw results for a given course and extracts the results into 
        a list of result objects. 

        Rather than splitting each row by spaces, this function finds the 
        indices of the common spaces across all rows for a given set of 
        course results. These indices are then used to extract the data. 

        Args:
            course_results  the raw course results
            course_info     a
            venue_info      a
            event_info      a 
        """

        # Extract data to list based on common space indices
        extracted_data = NapierSpider.extract_data(NapierSpider.get_valid_rows(course_results), column_indices)

        # Process extracted data into list of objects
        parsed_results = []
        for result_row in extracted_data:
            parsed_result = NapierSpider.parse_result_row(result_row)
            
            parsed_result['course'] = dict(course_info)
            parsed_result['venue'] = dict(venue_info)
            parsed_result['event'] = dict(event_info)

            parsed_results.append(parsed_result)

        return parsed_results

    @staticmethod
    def get_valid_rows(data):
        extracted_course_results = "".join(data.css('pre::text').extract())
        return [line for line in extracted_course_results.split('\n') if len(line) > 0 and '<i>' not in line and not line.isspace()]

    @staticmethod
    def identify_columns(data):
        filtered_event_results = NapierSpider.get_valid_rows(data)
        space_indices = [NapierSpider.find_space_indices(line) for line in filtered_event_results]
        max_line_length = max([len(line) for line in filtered_event_results])
        popular_space_indices = sorted(list(set([0] + NapierSpider.find_popular_space_indices(space_indices, len(filtered_event_results)) + [max_line_length])))

        return NapierSpider.identify_column_indices(popular_space_indices)

    @staticmethod
    def find_space_indices(line):
        """
        Returns a list of the indices where there is a space in the input line
        """
        return [i for i, x in enumerate(line) if x == ' ']

    @staticmethod
    def find_popular_space_indices(space_indices, course_results_count):
        """
        Returns a list of most popular indices from the input list of lists 
        of indices where there are spaces on a given line. Popularity is 
        defined as if more than 90% of the course results have this space. 
        """
        totals = Counter(i for i in list(itertools.chain.from_iterable(space_indices))).most_common()
        return sorted([x[0] for x in totals if x[1] > int(math.floor(course_results_count * 0.95))])

    @staticmethod
    def identify_column_indices(common_space_indices):
        """
        Returns a list of tuples where each tuple is the bounding indices 
        for a given column, identified through common spaces indices
        """
        pairs = [(x, common_space_indices[i+1]) for i, x in enumerate(common_space_indices) if i < len(common_space_indices) - 1]
        return [x for x in pairs if x[1] - x[0] > 1]

    @staticmethod
    def extract_data(data, column_indices):
        """
        Uses the supplied list of column indices to split the raw course
        result data into a list of list
        """
        parsed_data = []
        for line in data:
            parsed_line = []
            for column in column_indices:
                parsed_line += [line[column[0]:column[1]].strip()]
            parsed_data.append(parsed_line)
        return parsed_data

    @staticmethod
    def parse_result_row(input_row):
        """
        Identifies the element in a row
        TODO: Separate person and result item parsing into two methods

        Args:
            row: the row to analyse
        """
        person = PersonItem()
        result = ResultItem()

        # Position
        raw_position = input_row[0].rstrip('=;')
        if raw_position.isdigit():
            result['status'] = 'ok'
        else:
            result['status'] = raw_position

        # Name
        person['name'] = input_row[1]

        # Club
        person['club'] = input_row[2]

        # Age Class
        person['ageClass'] = input_row[3]

        # Time
        raw_time = input_row[4]
        if ':' in raw_time:
            time_parts = raw_time.split(':')
            full_minutes = int(time_parts[0])
            hours = full_minutes / 60
            minutes = full_minutes % 60
            seconds = int(time_parts[1])
            result['time'] = datetime.time(hours, minutes, seconds).isoformat()
        else:
            result['status'] = raw_time

        # Comments
        # NapierSpider.parse_missed_controls(input_row[5])

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

    # ======================================================================= #
    # Miscellaneous functions  ---------------------------------------------- #
    # ======================================================================= #

    def closed(self, reason):
        """
        Called when the Scrapy crawler has completed and it being closed down
        """

        print "{:d}% of events processed ({:d} of {:d})"\
            .format(int((self.processed_events_count /
                    float(self.discovered_events_count)) * 100),
                    self.processed_events_count, self.discovered_events_count)

        print "{:d}% of courses processed ({:d} of {:d})" \
            .format(int((self.processed_courses_count /
                         float(self.discovered_courses_count)) * 100),
                    self.processed_courses_count, self.discovered_courses_count)

        print "{:d} results found over {:d} processed courses of {:d} processed events)"\
            .format(int(self.processed_results_count), 
                    int(self.processed_courses_count),
                    int(self.processed_events_count))

    @staticmethod
    def printSummary(event):
        """
        event is of type Item and because courses could be empty, the .get method 
        with a default value is needed instead of event['courses']
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
