from .achievement import Achievement

class SixParticipantAchievement(Achievement):

    def __init__(self, stats_database_connector):
        super().__init__(stats_database_connector)
        self.reward = 800
        self.title = "Social Butterfly"
        self.description = "Focus with at least six other people at once"
        self.id_ = 4
    
    def get_progress(self, account_id):
        return (self.stats_database_connector.get_max_number_of_participants(account_id) - 1) / float(6)
    
