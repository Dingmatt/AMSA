import os
import random


class UserAgentManager:
    def __init__(self, agent_file=os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/user_agents.txt'))):
        """
        Initialize a user agent.

        Args:
            self: (todo): write your description
            agent_file: (str): write your description
            os: (int): write your description
            path: (str): write your description
            abspath: (str): write your description
            os: (int): write your description
            path: (str): write your description
            join: (todo): write your description
            os: (int): write your description
            path: (str): write your description
            dirname: (str): write your description
            __file__: (str): write your description
        """
        self.agent_file = agent_file
        self.useragents = self.load_user_agents(self.agent_file)

    def load_user_agents(self, useragentsfile):
        """
        useragentfile : string
            path to text file of user agents, one per line
        """
        useragents = []
        with open(useragentsfile, 'rb') as uaf:
            for ua in uaf.readlines():
                if ua:
                    useragents.append(ua.strip()[1:-1 - 1])
        return useragents

    def get_random_user_agent(self):
        """
        useragents : string array of different user agents
        :param useragents:
        :return random agent:
        """
        user_agent = random.choice(self.useragents)
        return user_agent

    def get_first_user_agent(self):
        """
        Gets the user agent user agent.

        Args:
            self: (todo): write your description
        """
        return self.useragents[0]

    def get_last_user_agent(self):
        """
        Gets the user - agent.

        Args:
            self: (todo): write your description
        """
        return self.useragents[-1]

    def get_len_user_agent(self):
        """
        Gets the number of the user agent.

        Args:
            self: (todo): write your description
        """
        return len(self.useragents)


if __name__ == '__main__':
    ua = UserAgentManager()
    print("Number of User Agent headers: {0}".format(str(ua.get_len_user_agent)))
    print("First User Agent in file: {0}".format(ua.get_first_user_agent()))
    print("Last User Agent in file: {0}".format(ua.get_last_user_agent()))
    print("If you want one random header for a request, you may use the following header:\n")
    print("User-Agent: " + ua.get_random_user_agent() + "\n")
