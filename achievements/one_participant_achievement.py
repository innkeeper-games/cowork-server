from .achievement import Achievement

class OneParticipantAchievement(Achievement):

    def __init__(self, stats_database_connector):
        super().__init__(stats_database_connector)
        self.reward = 100
        self.title = "Coworker"
        self.description = "Focus with at least one other person"
        self.id_ = 2
    
    def get_progress(self, account_id):
        return min(self.stats_database_connector.get_max_number_of_participants(account_id) - 1, 1)
    
