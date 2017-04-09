import os
import random


class UserAgentManager:
    def __init__(self, agent_file=os.path.join(os.path.dirname(__file__), '../data/user_agents.txt')):
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
        return self.useragents[0]

    def get_last_user_agent(self):
        return self.useragents[-1]

    def get_len_user_agent(self):
        return len(self.useragents)


if __name__ == '__main__':
    ua = UserAgentManager()
    print "Number of User Agent headers: " + str(ua.get_len_user_agent)
    print "First User Agent in file: " + ua.get_first_user_agent()
    print "Last User Agent in file: " + ua.get_last_user_agent()
    print "If you want one random header for a request, you may use the following header:\n"
    print "User-Agent: " + ua.get_random_user_agent() + "\n"
