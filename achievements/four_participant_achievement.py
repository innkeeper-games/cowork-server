from .achievement import Achievement

class FourParticipantAchievement(Achievement):

    def __init__(self, stats_database_connector):
        super().__init__(stats_database_connector)
        self.reward = 500
        self.title = "Team Player"
        self.description = "Focus with at least four other people at once"
        self.id_ = 3
    
    def get_progress(self, account_id):
        return (self.stats_database_connector.get_max_number_of_participants(account_id) - 1) / float(4)
    
