import orjson
from django.core import serializers



class Serializer:
    fields = None

    def __init__(self, data):
        self.data = data
        self.to_json = NotImplementedError
        self.to_dict = NotImplementedError

    def serialize(self):
        self.to_json = serializers.serialize("json", self.data, fields=self.fields)
        self.to_dict = orjson.loads(self.to_json)
