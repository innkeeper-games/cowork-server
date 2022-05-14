import psycopg2
from database import config
from secrets import token_urlsafe

from database_connector import DatabaseConnector

class ChatDatabaseConnector(DatabaseConnector):

    def __init__(self):
        super().__init__()
        self.connection = self.connect()


    def get_chats_for_room(self, room_id, number, before_chat_id=None):
        cursor = self.connection.cursor()
        if before_chat_id != None:
            cursor.execute("""SELECT sent_date FROM chat WHERE id = %s""", (before_chat_id,))
            fetched_data = cursor.fetchone()
            if len(fetched_data) > 0:
                sent_date = fetched_data[0]
                cursor.execute("""SELECT id, account_id, sent_date, contents, edited FROM chat WHERE room_id = %s AND sent_date < %s ORDER BY sent_date DESC LIMIT %s""", (room_id, sent_date, number))
                chats = cursor.fetchall()
                return chats
        else:
            cursor.execute("""SELECT id, account_id, sent_date, contents, edited FROM chat WHERE room_id = %s ORDER BY sent_date DESC LIMIT %s""", (room_id, number,))
            chats = cursor.fetchall()
            return chats
        cursor.close()
        return []


    def add_chat_message(self, account_id, room_id, contents):
        cursor = self.connection.cursor()
        chat_id = token_urlsafe(8)

        cursor.execute("""SELECT account_id FROM chat WHERE id = %s""", \
            (chat_id,))
        while cursor.fetchone() is not None:
            chat_id = token_urlsafe(8)
            cursor.execute("""SELECT account_id FROM chat WHERE id = %s""", \
                (chat_id,))
    
        cursor.execute("""INSERT INTO chat (id, account_id, room_id, contents) VALUES(%s, %s, %s, %s)""", (chat_id, account_id, room_id, contents))
        self.connection.commit()
        cursor.close()
        return chat_id
    

    def get_time_for_chat(self, chat_id):
        cursor = self.connection.cursor()

        cursor.execute("""SELECT sent_date FROM chat WHERE id = %s""", \
            (chat_id,))
        fetched_data = cursor.fetchone()
        if fetched_data is not None:
            if len(fetched_data) > 0:
                sent_date = fetched_data[0]
                cursor.close()
                return sent_date

        cursor.close()
        return None
    

    def chat_exists(self, chat_id):
        cursor = self.connection.cursor()

        cursor.execute("""SELECT sent_date FROM chat WHERE id = %s""", \
            (chat_id,))
        fetched_data = cursor.fetchone()
        return fetched_data is not None


    def get_room_id_for_chat(self, chat_id):
        cursor = self.connection.cursor()

        cursor.execute("""SELECT room_id FROM chat WHERE id = %s""", \
            (chat_id,))
        fetched_data = cursor.fetchone()
        return fetched_data[0]


    def get_account_id_for_chat(self, chat_id):
        cursor = self.connection.cursor()

        cursor.execute("""SELECT account_id FROM chat WHERE id = %s""", \
            (chat_id,))
        fetched_data = cursor.fetchone()
        return fetched_data[0]


    def edit_chat(self, chat_id, new_contents):
        cursor = self.connection.cursor()

        cursor.execute("""UPDATE chat SET contents = %s, edited = %s WHERE id = %s""", \
                (new_contents, True, chat_id))
        
        self.connection.commit()
        cursor.close()
        return True


    def delete_chat(self, chat_id):
        cursor = self.connection.cursor()

        cursor.execute("""DELETE FROM chat WHERE id = %s""", (chat_id,))

        self.connection.commit()
        cursor.close()
        return True
