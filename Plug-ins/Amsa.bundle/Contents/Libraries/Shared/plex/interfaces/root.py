from plex.core.idict import idict
from plex.interfaces.core.base import Interface


class RootInterface(Interface):
    def detail(self):
        """
        Retrieve the detail

        Args:
            self: (todo): write your description
        """
        response = self.http.get()

        return self.parse(response, idict({
            'MediaContainer': ('Detail', idict({
                'Directory': 'Directory'
            }))
        }))

    def version(self):
        """
        Return the version of the database.

        Args:
            self: (todo): write your description
        """
        detail = self.detail()

        if not detail:
            return None

        return detail.version

    def clients(self):
        """
        Retrieve all clients

        Args:
            self: (todo): write your description
        """
        response = self.http.get('clients')

        return self.parse(response, idict({
            'MediaContainer': ('ClientContainer', idict({
                'Server': 'Client'
            }))
        }))

    def players(self):
        """
        Add a set of packages.

        Args:
            self: (todo): write your description
        """
        pass

    def servers(self):
        """
        Returns a list of servers

        Args:
            self: (todo): write your description
        """
        response = self.http.get('servers')

        return self.parse(response, idict({
            'MediaContainer': ('Container', idict({
                'Server': 'Server'
            }))
        }))

    def agents(self):
        """
        Retrieve agents

        Args:
            self: (todo): write your description
        """
        response = self.http.get('system/agents')

        return self.parse(response, idict({
            'MediaContainer': ('Container', idict({
                'Agent': 'Agent'
            }))
        }))

    def primary_agent(self, guid, media_type):
        """
        Gets the primary agent.

        Args:
            self: (todo): write your description
            guid: (int): write your description
            media_type: (str): write your description
        """
        response = self.http.get('/system/agents/%s/config/%s' % (guid, media_type))
        return self.parse(response, idict({
            'MediaContainer': ('Container', idict({
                'Agent': 'Agent'
            }))
        }))
