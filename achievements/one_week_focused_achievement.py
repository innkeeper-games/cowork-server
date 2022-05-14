from .achievement import Achievement

class OneWeekFocusedAchievement(Achievement):

    def __init__(self, stats_database_connector):
        super().__init__(stats_database_connector)
        self.reward = 5000
        self.title = "Slow and Steady"
        self.description = "Focus for one week total"
        self.id_ = 8
    
    def get_progress(self, account_id):
        return self.stats_database_connector.get_time_in_sessions(account_id) / float(7 * 24 * 3600)
    
