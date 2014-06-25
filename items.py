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
    
    #TODO: replace with a better method that doesn't hardcode the attribute values
    def fieldNamesToList(self):
        return ['position', 'name', 'club', 'ageClass', 'time', 'courseID', 'status', 'missed'];

    # 
    def fieldsToList(self):
        return [self.get('position'), self.get('name'), self.get('club'), self.get('ageClass'), self.get('time'), self.get('courseID'), self.get('status'), self.get('missed')]

    
class CourseItem(Item):
    uid = Field()
    name = Field()
    length = Field()
    climb = Field()
    controls = Field()
    
    