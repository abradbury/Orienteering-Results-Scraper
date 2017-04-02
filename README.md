Orienteering Results Scraper
============================

Scrapes results from orienteering websites and stores to a MongoDB database. Currently only handles results pages using the Napier format (Colour or MERCS). Code needs a tidy-up. Work in progress.

The results on orienteering website are typically presented as unstructured data (e.g. a text structured with whitespace in a HTML <code>\<pre\></code> element to visually look like a table). 

Usage
-----
`scrapy crawl napier`

Example Debug Output
--------------------
```
/=========================================================================================\
| 1)   Local & Schools Event 1 at Endcliffe Park                                          |
| ----------------------------------------------------------------------------------------|
| Status:    OK                                                                           |
| Format:    Napier - Colour                                                              |
| Courses:   5                                                                            |
| Results:   423                                                                          |
\=========================================================================================/

/=========================================================================================\
| 10)  Regional Event at Baslow Edge and Big Moor                                         |
| ----------------------------------------------------------------------------------------|
| Status:    OK                                                                           |
| Format:    MERCS simple (parsed as Napier - Colour)                                     |
| Courses:   9                                                                            |
| Results:   273                                                                          |
\=========================================================================================/

/=========================================================================================\
| 15)  https://www.southyorkshireorienteers.org.uk/events/event/643-social-and-night-event|
| ----------------------------------------------------------------------------------------|
| Status:    No results link found                                                        |
| Format:                                                                                 |
| Courses:   0                                                                            |
| Results:   0                                                                            |
\=========================================================================================/
```
