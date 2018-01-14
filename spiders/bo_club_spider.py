#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Parses the list of orienteering clubs on the British Orienteering website 
to populate a list of the orienteering clubs in the UK

Usage:
    scrapy crawl clubs

@author: abradbury
"""

import pprint
import scrapy                       # For scraping the web pages

from Orienteering_Scraper.items import ClubItem

class OrienteeringClubsSpider(scrapy.Spider):
    """
    Scrapes the current list of orienteering clubs in the UK and details about
    them from the British Orienteering website
    """

    name = "clubs"
    allowed_domains = ["www.britishorienteering.org.uk/"]
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
            https://www.southyorkshireorienteers.org.uk/results
        """

        raw_club_listing = response.css('table#clubwebsites td:not([class="assoc"])')

        if raw_club_listing == 0:
            print("Error - no clubs found at " + response.url)
            exit()

        clubs = []

        for raw_club in raw_club_listing:
            club = ClubItem()

            raw_name = raw_club.css('::text').extract_first()
            if raw_name.isalpha():
                club['name'] = raw_name
                club['website'] = raw_club.css('a::attr(href)').extract_first()
                clubs.append(club)

        pprint.pprint(clubs)
