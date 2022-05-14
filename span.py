from datetime import datetime

"""
A span is the period of time, within a session, that a user is working on a single task.
"""

class Span:
    def __init__(self, id_, listing_id, session_id, start_time, expected_end_time, account_id, timer_database_connector):
        self.timer_database_connector = timer_database_connector

        self.listing_id = listing_id
        self.session_id = session_id
        self.account_id = account_id

        self.start_time = start_time
        self.expected_end_time = expected_end_time

        self.id_ = id_

        self.end_at(expected_end_time)

    def generate(self):
        pass


    def get_id(self):
        return self.id_


    def end_at(self, time):
        print("planning to end a span")
        self.timer_database_connector.add_end_time_to_span(self.id_, time)


    def end_now(self):
        print("ending a span")
        self.timer_database_connector.add_end_time_to_span(self.id_, datetime.now())