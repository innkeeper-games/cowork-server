from .achievement import Achievement

class OneReferralAchievement(Achievement):

    def __init__(self, stats_database_connector):
        super().__init__(stats_database_connector)
        self.reward = 300
        self.title = "Generous"
        self.description = "Refer one new user to Cowork"
        self.id_ = 5
    
    def get_progress(self, account_id):
        return min(self.stats_database_connector.get_number_of_completed_referrals(account_id), 1)
    
