import re       # Regular expressions - for parsing the results
import csv      # For writing the parsed results 
import time     # For the result times

from scrapy.spider import Spider
from scrapy.selector import Selector

from tutorial.items import ResultItem, CourseItem

# Parses output from Michael Napier's software, namely COLOUR and MERCS
# 
# TODO: Somewhere have a check to determine which spider to use
# TODO: Convert time to appropriate representation
# TODO: Try to match 'E-card XXXXXX' to a competitor
# TODO: Handle 'out of order' controls and prevent assignment to name
# TODO: '&amp;' being skipped, stop this
# TODO: Handle different units for course length and climb
# 
# @author: abradbury
class NapierSpider(Spider):
    name = "napier"
    allowed_domains = ["www.southyorkshireorienteers.org.uk"]
    start_urls = [
        # "http://www.southyorkshireorienteers.org.uk/event/2013-03-10-rivelin-valley/results.htm",
        # "http://www.southyorkshireorienteers.org.uk/event/2013-12-15-canklow-woods/results.htm"
        "http://www.southyorkshireorienteers.org.uk/event/2013-05-11-millhouses-park/results_v2.htm"
    ]

    # Checks if a parsed element is an age class e.g W12 or M50 (women's 12 or 
    # men's 50) and returns true if this is the case, false otherwise.
    #
    # @param    value   The value to check
    # @return           True if the value is an age class, false otherwise
    def isAgeClass(self, value):
        firstChar = value[0]
        otherChar = value[1:]
        result = False
        
        if(firstChar == 'M') or (firstChar == 'W'):
            if otherChar.isdigit():
                result = True
        return result
    

    # Identifies the element in a row
    # 
    # @param    row                 The row to analyse
    # @param    previousPosition    The previous competitor's position
    def identify(self, row, previousPosition):
        item = ResultItem()
        missingFlag = False     # True when the competitor has missed controls
        ecardFlag = False       # True when the competitor details are unknown

        print row

        # Iterate over row elements
        for i, element in enumerate(row):
            # Match the numerical elements such as position and missed controls
            if element.rstrip('=;').isdigit():
                if i == 0:                          # Position
                    item['position'] = int(element.rstrip('='))
                    item['status'] = 'ok'
                elif missingFlag:                   # Missed controls
                    if ';' in element:
                        missingFlag = False
                    item['missed'] = [int(element.rstrip(';'))]
                elif ecardFlag:                     # E-card number
                    item['name'] = "E-card " + element
                    ecardFlag = False
        
            # Match the characters to name, club and status flags
            elif re.match("^[a-zA-Z-\']+$", element.rstrip(',')) and not missingFlag:
                if element.isupper():               # Club
                    item['club'] = element
                elif element == "Missing":          # Missing controls
                    missingFlag = True
                elif i == 0 and element == "mp":    # MP (Miss-Punched)
                    item['status'] = 'mp'
                elif element == "rtd":              # RTD (Retired)
                    item['status'] = 'rtd'
                elif element == "dns":              # DNS (Did not start)
                    item['status'] = 'dns'
                elif element == 'E-card':           # E-card (unknown competitor)
                    ecardFlag = True
                elif ';' in element:
                    missingFlag = False;
                else:                               # Name
                    try:
                        item['name'] += " " + element
                    except KeyError:
                        item['name'] = element
            
            elif missingFlag and "no" not in element:
                item['missed'] = self.parseMissedControls(element)

            elif element == "n/c":                  # N/C (Non-Competitive)
                item['status'] = 'n/c'
        
            elif self.isAgeClass(element):          # Age class (M/W number)
                item['ageClass'] = element
        
            elif ':' in element:                    # Time
                item['time'] = element

        print item
        print item.fieldsToList()

        return item
    
    
    # Parses the missed controls numbers from a string such as '1,4-6' to 
    # return a list of missed control numbers as integers e.g. [1,4,5,6].
    # 
    # @param    value   The missed controls to parse
    # @return           A list containing the missed controls
    def parseMissedControls(self, value):
        missing = []
        for group in value.split(','):
            b = group.split('-')
            if len(b) > 1:
                missing += range(int(b[0]), int(b[1])+1)
            else:
                missing += [int(b[0])]
        return missing
    

    # The main method to parse the results on a web page
    # ---ADD DETAILS--
    #
    # @param    response    ??
    # @return               A list of parsed objects?
    def parse(self, response):
        hxs = Selector(response)
        courses = hxs.xpath('//a/p')
        # Change the below to //a name = xxx to get both course and competitor info
        results = hxs.xpath('//a[@name]')
        # Select all the links that have an attribute 'name' - the course headers

        items = []      # Each result
        courses = []    # A list of all courses for the event
        courseID = 1    # A unique ID for each course

        # Set up the CSV output and write the header row
        output = csv.writer(open('output.csv', 'wb'))
        headerItem = ResultItem()
        output.writerow(headerItem.fieldNamesToList())
        
        # Iterate over each set of course results e.g. white results, yellow results etc.
        for courseResults in results:
            previousPosition = 0

            # Parse and store the course's details
            tmp = courseResults.xpath('p')[0].xpath('text()').extract()
            if len(tmp) > 0:
                courseDetails = CourseItem()
                
                # Store course details
                courseDetails['name'] = (courseResults.xpath('p')[0].xpath('strong/text()').extract())[0]
                courseDetails['uid'] = courseID

                for courseDescriptor in tmp[0].strip().split(', '):
                    print courseDescriptor
                    if 'length' in courseDescriptor:
                        courseDetails['length'] = courseDescriptor.split(' ')[1]
                    elif 'climb' in courseDescriptor:
                        courseDetails['climb'] = courseDescriptor.split(' ')[1]
                    elif 'controls' in courseDescriptor:
                        courseDetails['controls'] = int(courseDescriptor.split(' ')[0])

                courses.append(courseDetails)

                print '+++++Parsed Details+++++'
                print '\'' + courseDetails['name'] + '\''
    
                # Parse and store each competitor's result
                print courseResults.xpath('pre').extract()[0]
                for result in courseResults.xpath('pre').extract()[0].splitlines():
                    print '--' + result
                    row = result.split()

                    # Try to filter out irrelavent rows, e.g. 'green men's standard'
                    if (len(row) > 2) and ('<i>' not in row[0]):
                        item = self.identify(row, previousPosition)
                        
                        item['courseID'] = courseID

                        items.append(item)
                        output.writerow(items[-1].fieldsToList())

                        # Don't update the previous position if the current result was n/c
                        if item['status'] != 'n/c':
                            previousPosition+=1
                    else:
                        print '**** course thing'
                courseID += 1

        # Print the course details
        print 'Number of courses: ' + str(len(courses))
        for course in courses:
            print course.get('uid'), course.get('name'), course.get('length'), course.get('climb'), course.get('controls')
        
        return items
