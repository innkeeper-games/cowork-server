import psycopg2
from database import config
from secrets import token_urlsafe

from datetime import datetime

from database_connector import DatabaseConnector

class StatsDatabaseConnector(DatabaseConnector):

    def __init__(self):
        super().__init__()
        self.connection = self.connect()


    def get_sessions_for_account(self, account_id):
        cursor = self.connection.cursor()
        # start by getting all spans for this account, then get the sessions and corresponding data later
        sessions = {}
        cursor.execute("""SELECT id, listing_id, session_id, start_time, end_time FROM span WHERE account_id = %s""", (account_id,))
        spans = cursor.fetchall()
        for span in spans:
            session_id = span[2]
            if not session_id in sessions:
                sessions[session_id] = {}
                session = self._get_session(session_id)
                sessions[session_id]["consumable"] = session[0]
                sessions[session_id]["room_id"] = session[1]
                sessions[session_id]["is_break"] = session[2]
                # gather other data, like participants
                sessions[session_id]["participants"] = self._get_participants_for_session(session_id)
                sessions[session_id]["spans"] = []

            listing_id = span[1]
            cursor.execute("""SELECT id, tag_id FROM tagging WHERE listing_id = %s""", (listing_id,))
            taggings = cursor.fetchall()
            tags = []
            for tagging in taggings:
                tag_id = tagging[1]
                cursor.execute("""SELECT id, color, title, account_id FROM tag WHERE id = %s""", (tag_id,))
                tag = cursor.fetchone()
                tag_a = {
                    "tagging_id": tagging[0],
                    "tag_id": tag[0],
                    "color": tag[1],
                    "title": tag[2]
                }
                tags.append(tag_a)
            
            span_d = {}
            if span[4] == None:
                span_d = {"id": span[0], "listing_id": span[1], "tags": tags, "session_id": span[2], "start_time": span[3].isoformat(), "end_time": None}
            else:
                span_d = {"id": span[0], "listing_id": span[1], "tags": tags, "session_id": span[2], "start_time": span[3].isoformat(), "end_time": span[4].isoformat()}
            sessions[session_id]["spans"].append(span_d)
        cursor.close()
        return sessions
    

    def _get_session(self, session_id):
        cursor = self.connection.cursor()
        cursor.execute("""SELECT consumable, room_id, is_break FROM session WHERE id = %s""", (session_id,))
        session = cursor.fetchone()
        return session


    def _get_participants_for_session(self, session_id):
        cursor = self.connection.cursor()
        # start by getting all spans for this account, then get the sessions and corresponding data later
        cursor.execute("""SELECT id, account_id FROM span WHERE session_id = %s""", (session_id,))
        spans = cursor.fetchall()
        participants = set()
        for span in spans:
            participants.add(span[1])
        cursor.close()
        return participants


    # get total time in seconds
    def get_time_in_sessions(self, account_id):
        cursor = self.connection.cursor()
        cursor.execute("""SELECT start_time, end_time FROM span WHERE account_id = %s""", (account_id,))
        spans = cursor.fetchall()
        seconds = 0
        for span in spans:
            if span[0] is not None and span[1] is not None:
                difference = (span[1] - span[0])
                seconds += difference.total_seconds()
        cursor.close()
        return seconds


    def get_max_number_of_participants(self, account_id):
        cursor = self.connection.cursor()
        sessions = {}
        cursor.execute("""SELECT id, session_id FROM span WHERE account_id = %s""", (account_id,))
        spans = cursor.fetchall()
        max_participants = 0
        for span in spans:
            session_id = span[1]
            if not session_id in sessions:
                sessions[session_id] = {}
                sessions[session_id]["participants"] = self._get_participants_for_session(session_id)
                max_participants = max(len(sessions[session_id]["participants"]), max_participants)
        cursor.close()
        return max_participants


    def get_number_of_completed_referrals(self, account_id):
        cursor = self.connection.cursor()
        cursor.execute("""SELECT id FROM referral WHERE referrer_account_id = %s AND completed = %s""", \
            (account_id, True))
        result = len(cursor.fetchall())
        return result


    def is_achievement_complete(self, account_id, achievement):
        cursor = self.connection.cursor()
        cursor.execute("""SELECT id FROM achievement_get WHERE achievement_id = %s AND account_id = %s""", \
            (achievement.get_id(), account_id))
        result = cursor.fetchone()
        return result is not None


    def set_achievement_complete(self, account_id, achievement):
        cursor = self.connection.cursor()

        cursor.execute("""UPDATE account SET wealth = wealth + %s WHERE id = %s""", \
            (achievement.get_reward(), account_id,))

        achievement_get_id = token_urlsafe(8)

        cursor.execute("""SELECT id FROM achievement_get WHERE id = %s""", \
            (achievement_get_id,))
        while cursor.fetchone() is not None:
            achievement_get_id = token_urlsafe(8)
            cursor.execute("""SELECT account_id FROM chat WHERE id = %s""", \
                (achievement_get_id,))
    
        cursor.execute("""INSERT INTO achievement_get (id, account_id, achievement_id) VALUES(%s, %s, %s)""", (achievement_get_id, account_id, achievement.get_id()))
        self.connection.commit()
        cursor.close()
        return achievement_get_id