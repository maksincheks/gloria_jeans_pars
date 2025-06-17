from scrapy import Item, Field

class ProductItem(Item):
    url = Field()
    categories = Field()
    timestamp = Field()
    name = Field()
    price = Field()
    old_price = Field()
    code = Field()
    color = Field()
    sizes = Field()
    composition = Field()
    description = Field()
    images = Field()
    attributes = Field()