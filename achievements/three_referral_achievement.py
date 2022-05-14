from .achievement import Achievement

class ThreeReferralAchievement(Achievement):

    def __init__(self, stats_database_connector):
        super().__init__(stats_database_connector)
        self.reward = 800
        self.title = "Bearheart"
        self.description = "Refer three new users to Cowork"
        self.id_ = 6
    
    def get_progress(self, account_id):
        return min(self.stats_database_connector.get_number_of_completed_referrals(account_id) / float(3), 1)
    
