from .achievement import Achievement

class FiveHoursFocusedAchievement(Achievement):

    def __init__(self, stats_database_connector):
        super().__init__(stats_database_connector)
        self.reward = 100
        self.title = "Dedicated"
        self.description = "Focus for five hours total"
        self.id_ = 1
    
    def get_progress(self, account_id):
        return self.stats_database_connector.get_time_in_sessions(account_id) / float(5 * 3600)
    
