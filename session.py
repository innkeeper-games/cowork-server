from datetime import datetime, timedelta
from span import Span

"""
A session is a period of time associated with a consumable and a duration. It's what's
created when user starts a timer.
"""

class Session:
    def __init__(self, id_, consumable, start_time, duration, timer_database_connector):
        self.id_ = id_
        self.start_time = start_time
        self.consumable = consumable

        # duration is a timedelta!
        self.duration = duration

        # sessions with no participants may end early
        self.expected_end_time = self.start_time + self.duration

        self.timer_database_connector = timer_database_connector

        self.spans = {}


    def get_id(self):
        return self.id_


    def get_participants(self):
        return self.spans.keys()
    

    def get_spans(self):
        return self.spans


    def get_consumable(self):
        return self.consumable 


    def get_expected_end_time(self):
        end_time = self.start_time + self.duration
        return end_time


    def get_time_since_start(self):
        return datetime.now() - self.start_time


    def add_participant(self, account_id, listing_id=None):
        if listing_id is not None:
            self.create_span(account_id, listing_id)
            return
        self.spans[account_id] = None


    def remove_participant(self, account_id):
        print("removing participant")
        if account_id in self.get_participants():
            print("account in participants. checking if there's a span")
            if self.spans[account_id] is not None:
                return self.end_span(account_id)
            # account for is_break case
            self.spans.pop(account_id)
            return len(self.spans.keys()) == 0
            

    def create_span(self, account_id, listing_id):
        # create a span at this point
        # every span expects to end at the expected end time
        if account_id in self.spans.keys():
            self.end_span(account_id)
        span_id = self.timer_database_connector.add_span(self.id_, account_id, datetime.now(), listing_id)
        self.spans[account_id] = Span(span_id, listing_id, self.id_, datetime.now(), self.expected_end_time, account_id, self.timer_database_connector)


    def end_span(self, account_id):
        print("there's a span. checking if in participants")
        if account_id in self.get_participants():
            # end the current span associated with the account
            print("trying to end the span")
            self.spans[account_id].end_now()
            self.spans.pop(account_id)
            return len(self.spans.keys()) == 0