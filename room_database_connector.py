import psycopg2
from database import config
from secrets import token_urlsafe

from database_connector import DatabaseConnector

class RoomDatabaseConnector(DatabaseConnector):

    def __init__(self):
        super().__init__()
        self.connection = self.connect()


    def process_transaction(self, account_id, item):
        cursor = self.connection.cursor()

        cost = item.get_cost()
        cursor.execute("""UPDATE account SET wealth = wealth - %s WHERE id = %s""", \
            (item.get_cost(), account_id,))
        
        self.connection.commit()
        cursor.close()


    def get_inventory(self, account_id):
        cursor = self.connection.cursor()

        cursor.execute("""SELECT inventory FROM account WHERE id = %s""", \
            (account_id,))
        fetched_data = cursor.fetchone()
        if fetched_data is not None:
            if len(fetched_data) > 0:
                inventory = fetched_data[0]
                cursor.close()
                return inventory

        cursor.close()
        return None


    def save_inventory(self, account_id, save_json):
        cursor = self.connection.cursor()

        cursor.execute("""UPDATE account SET inventory = %s WHERE id = %s""", \
            (save_json, account_id,))
        
        self.connection.commit()
        cursor.close()


    def save_persist_objects(self, room_id, save_json):
        cursor = self.connection.cursor()

        cursor.execute("""UPDATE room SET persist_objects = %s WHERE id = %s""", \
            (save_json, room_id,))
    
        self.connection.commit()
        cursor.close()
    

    def get_persist_objects(self, room_id):
        cursor = self.connection.cursor()

        cursor.execute("""SELECT persist_objects FROM room WHERE id = %s""", \
            (room_id,))
        fetched_data = cursor.fetchone()
        if fetched_data is not None:
            if len(fetched_data) > 0:
                persist_objects = fetched_data[0]
                cursor.close()
                return persist_objects

        cursor.close()
        return None