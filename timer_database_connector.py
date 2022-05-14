import psycopg2
from database import config
from secrets import token_urlsafe

from database_connector import DatabaseConnector

class TimerDatabaseConnector(DatabaseConnector):

    def __init__(self):
        super().__init__()
        self.connection = self.connect()


    def add_session(self, consumable, room_id, is_break):
        self.connection = self.connect()
        cursor = self.connection.cursor()
        session_id = token_urlsafe(8)

        cursor.execute("""SELECT consumable FROM session WHERE id = %s""", \
            (session_id,))
        while cursor.fetchone() is not None:
            session_id = token_urlsafe(8)
            cursor.execute("""SELECT consumable FROM session WHERE id = %s""", \
                (session_id,))
    
        cursor.execute("""INSERT INTO session (id, consumable, room_id, is_break) VALUES(%s, %s, %s, %s)""", \
            (session_id, consumable, room_id, is_break))
        self.connection.commit()
        cursor.close()
        return session_id


    def add_span(self, session_id, account_id, start_time, listing_id=None):
        self.connection = self.connect()
        cursor = self.connection.cursor()
        span_id = token_urlsafe(8)

        cursor.execute("""SELECT listing_id FROM span WHERE id = %s""", \
            (span_id,))
        while cursor.fetchone() is not None:
            span_id = token_urlsafe(8)
            cursor.execute("""SELECT listing_id FROM span WHERE id = %s""", \
                (span_id,))
    
        if listing_id == None:
            cursor.execute("""INSERT INTO span (id, account_id, session_id, start_time) VALUES(%s, %s, %s, %s)""", (span_id, account_id, session_id, start_time,))
        else:
            cursor.execute("""INSERT INTO span (id, listing_id, account_id, session_id, start_time) VALUES(%s, %s, %s, %s, %s)""", (span_id, listing_id, account_id, session_id, start_time,))
        self.connection.commit()
        cursor.close()
        return span_id


    def add_end_time_to_span(self, span_id, end_time):
        self.connection = self.connect()
        cursor = self.connection.cursor()

        cursor.execute("""UPDATE span SET end_time = %s WHERE id = %s""", \
            (end_time, span_id,))

        self.connection.commit()
        cursor.close()
        return True
    

    def add_wealth(self, account_id, wealth):
        self.connection = self.connect()
        cursor = self.connection.cursor()

        cursor.execute("""UPDATE account SET wealth = wealth + %s WHERE id = %s""", \
            (wealth, account_id,))
        
        self.connection.commit()
        cursor.close()
        return True