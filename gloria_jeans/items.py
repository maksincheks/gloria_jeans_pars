from scrapy import Field, Item

class DynamicItem(Item):
    feed_name = "wrapper"

    def __setitem__(self, key, value):
        self.fields.update({key: Field()})
        self._values.update({key: value})

    def __getitem__(self, key):
        return super().__getitem__(key)

class ProductItem(DynamicItem):
    feed_name = "products"
    url = Field()
    categories = Field()
    timestamp = Field()
    name = Field()
    price = Field()
    code = Field()
    description = Field()
    images = Field()
    specifications = Field()  # Добавлено новое поле для характеристик