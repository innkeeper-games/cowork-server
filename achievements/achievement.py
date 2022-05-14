from abc import ABC

class Achievement(ABC):

    def __init__(self, stats_database_connector):
        self.reward = 0
        self.title = ""
        self.description = ""
        self.id_ = 0
        self.stats_database_connector = stats_database_connector

    def get_progress(self, account_id):
        pass

    def get_title(self):
        return self.title

    def get_description(self):
        return self.description

    def get_id(self):
        return self.id_

    def get_reward(self):
        return self.reward