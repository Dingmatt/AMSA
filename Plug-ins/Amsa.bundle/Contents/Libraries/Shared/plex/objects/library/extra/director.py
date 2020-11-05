from plex.objects.core.base import Descriptor, Property


class Director(Descriptor):
    id = Property(type=int)
    tag = Property

    @classmethod
    def from_node(cls, client, node):
        """
        Create an instance from a node.

        Args:
            cls: (todo): write your description
            client: (todo): write your description
            node: (todo): write your description
        """
        return cls.construct(client, cls.helpers.find(node, 'Director'), child=True)
