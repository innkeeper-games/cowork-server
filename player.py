class Player:

    def __init__(self, account_id, uuid, active_listing_id=None):
        self.account_id = account_id
        self.uuid = uuid
        self.active_listing_id = active_listing_id
        self.active_session_id = None


    def get_id(self):
        return self.uuid


    def get_account_id(self):
        return self.account_id


    def get_active_listing_id(self):
        return self.active_listing_id


    def set_active_listing_id(self, active_listing_id):
        self.active_listing_id = active_listing_id


    def is_in_session(self):
        return self.active_session_id is not None


    def get_active_session_id(self):
        return self.active_session_id


    def set_active_session_id(self, active_session_id):
        self.active_session_id = active_session_id