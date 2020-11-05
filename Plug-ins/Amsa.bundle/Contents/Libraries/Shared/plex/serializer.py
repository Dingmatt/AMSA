import jsonpickle


class Serializer(object):
    @classmethod
    def encode(cls, value):
        """
        Encode the given value.

        Args:
            cls: (todo): write your description
            value: (todo): write your description
        """
        return jsonpickle.encode(value)

    @classmethod
    def decode(cls, value, client=None):
        """
        Decode the given value.

        Args:
            cls: (todo): write your description
            value: (str): write your description
            client: (todo): write your description
        """
        try:
            result = jsonpickle.decode(value)
            result.client = client

            return result
        except:
            return None
