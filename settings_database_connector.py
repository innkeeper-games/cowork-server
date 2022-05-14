import psycopg2
from database import config
from secrets import token_urlsafe
from database_connector import DatabaseConnector

class SettingsDatabaseConnector(DatabaseConnector):

    def __init__(self):
        super().__init__()
        self.connection = self.connect()


    def edit_display_name(self, account_id, display_name):
        cursor = self.connection.cursor()

        cursor.execute("""UPDATE account SET display_name = %s WHERE id = %s""", \
            (display_name, account_id,))

        self.connection.commit()
        cursor.close()
        return True


    def edit_room_title(self, room_id, room_title):
        cursor = self.connection.cursor()

        cursor.execute("""UPDATE room SET title = %s WHERE id = %s""", \
            (room_title, room_id,))

        self.connection.commit()
        cursor.close()
        return True


    def edit_room_description(self, room_id, room_description):
        cursor = self.connection.cursor()

        cursor.execute("""UPDATE room SET description = %s WHERE id = %s""", \
            (room_description, room_id,))

        self.connection.commit()
        cursor.close()
        return True


    def get_listed_rooms(self):
        rooms = {}
        cursor = self.connection.cursor()
        cursor.execute("""SELECT id, title, description FROM room WHERE listed = %s""", (True,))
        rooms_tuple = cursor.fetchall()
        for room in rooms_tuple:
            rooms[room[0]] = {
                "room_id": room[0],
                "room_title": room[1],
                "room_description": room[2]
            }
        cursor.close()
        if len(rooms) > 0:
            return rooms
        return []


    def get_rooms_for_username(self, username):
        userid = self.get_id_for_username(username)
        userid_exists = userid is not None
        if userid_exists:
            rooms = {}
            cursor = self.connection.cursor()
            cursor.execute("""SELECT room_id FROM membership WHERE account_id = %(id)s""", {'id': userid})
            rooms_tuple = cursor.fetchall()
            for room in rooms_tuple:
                cursor.execute("""SELECT id, title, description FROM room WHERE id = %(id)s""", {'id': room[0]})
                room = cursor.fetchone()
                rooms[room[0]] = {
                    "room_id": room[0],
                    "room_title": room[1],
                    "room_description": room[2]
                }
            cursor.close()
            if len(rooms) > 0:
                return rooms
            return []
        return None
    

    def get_room_title(self, room_id):
        cursor = self.connection.cursor()
        cursor.execute("""SELECT title FROM room WHERE id = %s""", (room_id,))
        title = cursor.fetchone()[0]
        cursor.close()
        return title


    def get_room_description(self, room_id):
        cursor = self.connection.cursor()
        cursor.execute("""SELECT description FROM room WHERE id = %s""", (room_id,))
        description = cursor.fetchone()[0]
        cursor.close()
        return description


    def get_room_owner_account_id(self, room_id):
        cursor = self.connection.cursor()
        cursor.execute("""SELECT owner_account_id FROM room WHERE id = %s""", (room_id,))
        owner_account_id = cursor.fetchone()[0]
        cursor.close()
        return owner_account_id


    def get_room_members(self, room_id):
        cursor = self.connection.cursor()
        cursor.execute("""SELECT account_id FROM membership WHERE room_id = %s""", (room_id,))
        members = cursor.fetchall()
        cursor.close()
        return members


    def create_room(self, title, owner_account_id, public=False):
        print("Creating room " + title + " with owner " + str(owner_account_id) + ".")
        cursor = self.connection.cursor()

        room_id = token_urlsafe(8)
        cursor.execute("""SELECT owner_account_id FROM room WHERE id = %s""", \
            (room_id,))
        while cursor.fetchone() is not None:
            room_id = token_urlsafe(8)
            cursor.execute("""SELECT owner_account_id FROM room WHERE id = %s""", \
                (room_id,))
    
        cursor.execute("""INSERT INTO room (id, public, title, owner_account_id) VALUES(%s, %s, %s, %s)""", \
            (room_id, public, title, owner_account_id,))
        self.connection.commit()
        cursor.close()
        self.create_membership(owner_account_id, room_id)
        return room_id


    def create_membership(self, account_id, room_id):
        # verify that the room is public OR the user has an invitation
        # also verify that the membership does not already exist
        cursor = self.connection.cursor()
        if not self.membership_exists(account_id, room_id):
            cursor.execute("""SELECT public FROM room WHERE id = %(room_id)s""", \
                {'room_id': room_id})
            public = cursor.fetchone()[0]
            invitation_exists = self.invitation_exists(account_id, room_id)

            account_id_is_owner = False
            cursor.execute("""SELECT owner_account_id FROM room WHERE id = %(room_id)s""", \
                {'room_id': room_id})
            owner_account_id = cursor.fetchone()[0]
            if owner_account_id == account_id:
                account_id_is_owner = True

            listed = False
            cursor.execute("""SELECT listed FROM room WHERE id = %(room_id)s""", \
                {'room_id': room_id})
            listed = cursor.fetchone()[0]
            if owner_account_id == account_id:
                account_id_is_owner = True

            if public == True or invitation_exists or account_id_is_owner or listed:
                membership_id = token_urlsafe(8)
                cursor.execute("""SELECT room_id FROM membership WHERE id = %s""", \
                    (membership_id,))
                while cursor.fetchone() is not None:
                    membership_id = token_urlsafe(8)
                    cursor.execute("""SELECT room_id FROM membership WHERE id = %s""", \
                        (membership_id,))

                cursor.execute("""INSERT INTO membership (id, account_id, room_id) VALUES(%s, %s, %s)""", \
                    (membership_id, account_id, room_id,))
                print("Created a membership for " + account_id + " in " + room_id + ".")
                self.connection.commit()
                cursor.close()
                if invitation_exists:
                    self.delete_invitations(account_id, room_id)
                return True
        cursor.close()
        return False


    def membership_exists(self, account_id, room_id):
        cursor = self.connection.cursor()
        cursor.execute("""SELECT id FROM membership WHERE account_id = %(account_id)s AND room_id = %(room_id)s""", \
            {'account_id': account_id, 'room_id': room_id})

        result = cursor.fetchone()
        membership_exists = result is not None
        cursor.close()
        return membership_exists
    

    def delete_membership(self, account_id, room_id):
        if self.membership_exists(account_id, room_id):
            cursor = self.connection.cursor()
            cursor.execute("""DELETE FROM membership WHERE account_id = %(account_id)s AND room_id = %(room_id)s""", \
                {'account_id': account_id, 'room_id': room_id})

            # delete empty rooms
            cursor.execute("""SELECT id FROM membership WHERE room_id = %(room_id)s""", \
                {'room_id': room_id})
            if cursor.fetchone() is None:
                cursor.execute("""DELETE FROM room WHERE id = %(room_id)s""", \
                {'room_id': room_id})

            self.connection.commit()
            cursor.close()
            return True
        return False


    def create_invitation(self, inviter_account_id, room_id, invitee_account_id):
        cursor = self.connection.cursor()
        if not self.invitation_exists(invitee_account_id, room_id):
            cursor.execute("""SELECT id FROM membership WHERE account_id = %(inviter_account_id)s AND room_id = %(room_id)s""", \
                {'inviter_account_id': inviter_account_id, 'room_id': room_id})
            if cursor.fetchone() is not None:
                
                invitation_id = token_urlsafe(8)
                cursor.execute("""SELECT invitee_account_id FROM invitation WHERE id = %s""", \
                    (invitation_id,))
                while cursor.fetchone() is not None:
                    invitation_id = token_urlsafe(8)
                    cursor.execute("""SELECT invitee_account_id FROM invitation WHERE id = %s""", \
                        (invitation_id,))

                cursor.execute("""INSERT INTO invitation (id, inviter_account_id, invitee_account_id, room_id) VALUES(%s, %s, %s, %s)""", \
                    (invitation_id, inviter_account_id, invitee_account_id, room_id))
                self.connection.commit()
                cursor.close()
                return True
        cursor.close()
        return False


    def create_referral(self, referrer_account_id, referee_username, room_id):
        cursor = self.connection.cursor()
        referral_id = token_urlsafe(8)

        cursor.execute("""SELECT referrer_account_id FROM referral WHERE id = %s""", \
            (referral_id,))
        while cursor.fetchone() is not None:
            referral_id = token_urlsafe(8)
            cursor.execute("""SELECT referrer_account_id FROM referral WHERE id = %s""", \
                (referral_id,))
    
        cursor.execute("""INSERT INTO referral (id, referrer_account_id, referee_username, room_id) VALUES(%s, %s, %s, %s)""", (referral_id, referrer_account_id, referee_username, room_id))
        self.connection.commit()
        cursor.close()
        return referral_id


    def referral_exists(self, referrer_account_id, referee_username):
        cursor = self.connection.cursor()
        referral_id = None

        cursor.execute("""SELECT referrer_account_id FROM referral WHERE referrer_account_id = %s AND referee_username = %s""", \
            (referrer_account_id, referee_username,))

        exists = cursor.fetchone() is not None
        cursor.close()
        return exists

    
    def delete_invitation(self, invitee_account_id, room_id, inviter_account_id):
        cursor = self.connection.cursor()
        cursor.execute("""DELETE FROM invitation WHERE invitee_account_id = %(invitee_account_id)s AND room_id = %(room_id)s AND inviter_account_id = %(inviter_account_id)s""", \
            {'invitee_account_id': invitee_account_id, 'room_id': room_id, 'inviter_account_id': inviter_account_id})
        self.connection.commit()
        cursor.close()


    def delete_invitation_by_id(self, invitation_id):
        cursor = self.connection.cursor()
        cursor.execute("""DELETE FROM invitation WHERE id = %(id)s""", {'id': invitation_id})
        self.connection.commit()
        cursor.close()


    def delete_invitations(self, invitee_account_id, room_id):
        cursor = self.connection.cursor()
        cursor.execute("""DELETE FROM invitation WHERE invitee_account_id = %(invitee_account_id)s AND room_id = %(room_id)s""", \
            {'invitee_account_id': invitee_account_id, 'room_id': room_id})
        self.connection.commit()
        cursor.close()


    def invitation_exists(self, invitee_account_id, room_id):
        cursor = self.connection.cursor()
        cursor.execute("""SELECT id FROM invitation WHERE invitee_account_id = %(invitee_account_id)s AND room_id = %(room_id)s""", \
            {'invitee_account_id': invitee_account_id, 'room_id': room_id})
        fetch = cursor.fetchone()
        cursor.close()
        if fetch is not None:
            return fetch[0]
        return False


    def get_incoming_invitations(self, account_id):
        cursor = self.connection.cursor()
        cursor.execute("""SELECT id, inviter_account_id, room_id FROM invitation WHERE invitee_account_id = %s ORDER BY creation_date DESC""", (account_id,))
        invitations = cursor.fetchall()
        cursor.close()
        return invitations

    
    def get_outgoing_invitations(self, account_id):
        cursor = self.connection.cursor()
        cursor.execute("""SELECT id, invitee_account_id, room_id FROM invitation WHERE inviter_account_id = %s ORDER BY creation_date DESC""", (account_id,))
        invitations = cursor.fetchall()
        cursor.close()
        return invitations


    def room_exists(self, room_id):
        cursor = self.connection.cursor()
        cursor.execute("""SELECT public FROM room WHERE id = %(id)s""", {'id': room_id})
        exists = cursor.fetchone() is not None
        cursor.close()
        return exists


    def set_room_privacy(self, account_id, room_id, private):
        # ANY MEMBER CAN CURRENTLY SET ROOM PRIVACY,
        # NOT JUST THE OWNER.
        cursor = self.connection.cursor()
        if self.membership_exists(account_id, room_id):
            cursor.execute("""UPDATE room SET public = %(public)s WHERE id = %(id)s""", \
                {'public': not private, 'id': room_id})
            self.connection.commit()
            cursor.close()
            return True
        cursor.close()
        return False
    

    def get_room_privacy(self, room_id):
        cursor = self.connection.cursor()
        cursor.execute("""SELECT public FROM room WHERE id = %(id)s""", {'id': room_id})
        public = cursor.fetchone()[0]
        cursor.close()
        return not public