from plex.interfaces.core.base import Interface


class PluginInterface(Interface):
    path = ':/plugins'

    def reload_services(self, plugin_id):
        """
        Reloads a specific plugin.

        Args:
            self: (todo): write your description
            plugin_id: (str): write your description
        """
        response = self.http.get(plugin_id, 'services/reload')
        return response.status_code == 200

    def restart(self, plugin_id):
        """
        Restart a single plugin.

        Args:
            self: (todo): write your description
            plugin_id: (str): write your description
        """
        response = self.http.get(plugin_id, 'restart')
        return response.status_code == 200
