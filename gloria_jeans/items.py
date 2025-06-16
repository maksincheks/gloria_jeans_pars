from scrapy import Field, Item

class ProductItem(Item):
    url = Field()
    categories = Field()
    timestamp = Field()
    name = Field()
    price = Field()
    code = Field()
    description = Field()
    images = Field()
    specifications = Field()