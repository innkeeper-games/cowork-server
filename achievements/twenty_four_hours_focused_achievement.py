from .achievement import Achievement

class TwentyFourHoursFocusedAchievement(Achievement):

    def __init__(self, stats_database_connector):
        super().__init__(stats_database_connector)
        self.reward = 800
        self.title = "Champion"
        self.description = "Focus for 24 hours total"
        self.id_ = 7
    
    def get_progress(self, account_id):
        return self.stats_database_connector.get_time_in_sessions(account_id) / float(24 * 3600)
    
