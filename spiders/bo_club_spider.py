#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Parses the list of orienteering clubs on the British Orienteering website
to populate a list of the orienteering clubs in the UK

Usage:
    scrapy crawl clubs

@author: abradbury
"""

import scrapy                       # For scraping the web pages

from Orienteering_Scraper.items import ClubItem

class OrienteeringClubsSpider(scrapy.Spider):
    """
    Scrapes the current list of orienteering clubs in the UK and details about
    them from the British Orienteering website
    """

    name = "clubs"
    start_urls = ["https://www.britishorienteering.org.uk/find_a_club"]

    # ======================================================================= #
    # Page parsers ---------------------------------------------------------- #
    # ======================================================================= #

    def parse(self, response):
        """
        The main entry into the parsing process, starts at the results list
        page of an orienteering website and works through the results pages,
        yielding to another parser for each event found on these pages.

        Example URL:
            https://www.britishorienteering.org.uk/find_a_club
        """

        raw_club_listing = response.css('table#clubwebsites td:not([class="assoc"])')

        if raw_club_listing == 0:
            print("Error - no clubs found at " + response.url)
            exit()

        for raw_club in raw_club_listing:
            club = ClubItem()

            raw_name = raw_club.css('::text').extract_first()
            if raw_name.isalpha():
                club['name'] = raw_name
                raw_website = raw_club.css('a::attr(href)').extract_first()

                if raw_website:
                    club['website'] = raw_website
                    yield scrapy.Request(raw_website, meta={'club': club}, callback=self.parse_club)
                else:
                    yield club

    def parse_club(self, response):
        """
        Parses the website of an orienteering club to extract details about the
        club such as the full name of the club

        Args:
            response: the Scrapy HTTP Response object

        Example URL:
            http://derwentvalleyorienteers.org.uk
        """

        club = response.meta['club']
        raw_full_name = response.css('head title::text').extract_first()

        if raw_full_name:
            # Split by, | - »
            # Some sites don't have a title
            # Most are before delimiter, except:
            #   BAOC Online | British Army Orienteering Club
            #   Home - Cambridge University Orienteering Club (CUOC)
            parsed_full_name = raw_full_name.split('|')[0].split("-")[0].lower()\
                .replace("welcome to", "").replace("home page", "").strip().title()

            if parsed_full_name.upper() != club['name'].upper():
                club['fullName'] = parsed_full_name

        yield club
