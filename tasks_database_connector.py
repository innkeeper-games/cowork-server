import psycopg2
from database import config
from secrets import token_urlsafe

from database_connector import DatabaseConnector

class TasksDatabaseConnector(DatabaseConnector):

    def __init__(self):
        super().__init__()
        self.connection = self.connect()


    def get_lists_for_account(self, account_id):
        cursor = self.connection.cursor()
        cursor.execute("""SELECT id, title, index, archive, room_id FROM list WHERE account_id = %s""", (account_id,))
        lists = cursor.fetchall()
        cursor.close()
        return lists


    def get_tags_for_account(self, account_id):
        cursor = self.connection.cursor()
        cursor.execute("""SELECT id, color, title FROM tag WHERE account_id = %s""", (account_id,))
        tags = cursor.fetchall()
        cursor.close()
        return tags


    def get_listings_for_account_and_list(self, account_id, list_id, index=0, count=0):
        cursor = self.connection.cursor()
        if index == 0 and count == 0:
                cursor.execute("""SELECT id, task_id, list_id, index, active FROM listing WHERE account_id = %s AND list_id = %s""", (account_id, list_id))
        else:
            cursor.execute("""SELECT id, task_id, list_id, index, active FROM listing WHERE account_id = %s AND list_id = %s AND index < %s AND index >= %s""", (account_id, list_id, index + count, index))
        listings = cursor.fetchall()
        cursor.close()
        return listings


    def get_listing_for_account_and_task(self, account_id, task_id):
        cursor = self.connection.cursor()
        cursor.execute("""SELECT id, list_id, index, active id FROM listing WHERE task_id = %s AND account_id = %s""", (task_id, account_id))
        listing = cursor.fetchone()
        cursor.close()
        return listing


    def get_tasks_for_listings(self, listings):
        cursor = self.connection.cursor()
        tasks = []
        for listing in listings:
            task_id = listing[1]
            cursor.execute("""SELECT id, public, active, title, contents, room_id, complete FROM task WHERE id = %s""", (task_id,))
            task = cursor.fetchone()
            tasks.append(task)
        cursor.close()
        return tasks


    def get_task_for_listing(self, listing_id):
        cursor = self.connection.cursor()
        cursor.execute("""SELECT task_id FROM listing WHERE id = %s""", (listing_id,))
        listing = cursor.fetchone()
        task_id = listing[0]
        cursor.execute("""SELECT id, public, active, title, contents, room_id, complete FROM task WHERE id = %s""", (task_id,))
        task = cursor.fetchone()
        cursor.close()
        return task


    def get_tags_for_listing(self, listing_id):
        cursor = self.connection.cursor()
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
        cursor.close()
        return tags


    def get_assignments_for_task(self, task_id):
        cursor = self.connection.cursor()
        cursor.execute("""SELECT id, account_id FROM assignment WHERE task_id = %s""", (task_id,))
        assignments = cursor.fetchall()
        cursor.close()
        return assignments


    def get_taggings_for_task(self, task_id):
        cursor = self.connection.cursor()
        cursor.execute("""SELECT id, tag_id FROM tagging WHERE task_id = %s""", (task_id,))
        taggings = cursor.fetchall()
        cursor.close()
        return taggings


    def account_has_task(self, account_id, task_id):
        cursor = self.connection.cursor()
        cursor.execute("""SELECT id FROM listing WHERE account_id = %s AND task_id = %s""", (account_id, task_id,))
        id_ = cursor.fetchone()
        cursor.close()
        return id_ is not None


    def account_can_edit_task(self, account_id, task_id):
        cursor = self.connection.cursor()
        # for now, just return whether they have any permissions at all
        cursor.execute("""SELECT id, can_edit_contents, can_edit_title FROM task_permission WHERE account_id = %s AND task_id = %s""", (account_id, task_id,))
        id_ = cursor.fetchone()
        cursor.close()
        return id_ is not None


    def account_has_listing(self, account_id, listing_id):
        cursor = self.connection.cursor()
        cursor.execute("""SELECT index FROM listing WHERE account_id = %s AND id = %s""", (account_id, listing_id,))
        index = cursor.fetchone()
        cursor.close()
        return index is not None


    def account_has_list(self, account_id, list_id):
        cursor = self.connection.cursor()
        cursor.execute("""SELECT title FROM list WHERE account_id = %s AND id = %s""", (account_id, list_id,))
        title = cursor.fetchone()
        cursor.close()
        return title is not None


    def get_task(self, task_id):
        cursor = self.connection.cursor()
        cursor.execute("""SELECT id, public, active, title, contents, room_id, complete FROM task WHERE id = %s""", (task_id,))
        task = cursor.fetchone()
        cursor.close()
        return task
    

    def account_can_use_tag(self, account_id, tag_id):
        cursor = self.connection.cursor()
        cursor.execute("""SELECT account_id FROM tag WHERE id = %s""", (tag_id,))
        tag = cursor.fetchone()
        cursor.close()
        return tag[0] == account_id
    

    def account_has_tagging(self, account_id, tagging_id):
        cursor = self.connection.cursor()
        cursor.execute("""SELECT listing_id FROM tagging WHERE id = %s""", (tagging_id,))
        listing_id = cursor.fetchone()
        print(listing_id)
        cursor.execute("""SELECT index FROM listing WHERE id = %s AND account_id = %s""", (listing_id, account_id))
        index = cursor.fetchone()
        print(index)
        cursor.close()
        return index is not None


    def get_tag(self, tag_id):
        cursor = self.connection.cursor()
        cursor.execute("""SELECT id, title, color FROM tag WHERE id = %s""", (tag_id,))
        tag = cursor.fetchone()
        cursor.close()
        return tag
    

    def delete_listings_for_list_and_account(self, list_id, account_id):
        cursor = self.connection.cursor()

        cursor.execute("""SELECT id, task_id FROM listing WHERE list_id = %s AND account_id = %s""", \
            (list_id, account_id,))
        results = cursor.fetchall()

        cursor.execute("""DELETE FROM listing WHERE list_id = %s AND account_id = %s""", \
            (list_id, account_id,))

        for listing in results:
            cursor.execute("""SELECT id FROM listing WHERE task_id = %s""", \
                (listing[1],))
            if cursor.fetchone() is None:
                print("Deleting a task that has no more listings.")
                cursor.execute("""DELETE FROM task WHERE id = %s""", \
                    (listing[1],))
        
        self.connection.commit()
        cursor.close()
        return results


    def delete_listing_for_task_and_account(self, task_id, account_id):
        cursor = self.connection.cursor()

        cursor.execute("""SELECT id, list_id, index FROM listing WHERE task_id = %s AND account_id = %s""", \
            (task_id, account_id,))
        result = cursor.fetchone()

        cursor.execute("""DELETE FROM listing WHERE task_id = %s AND account_id = %s""", \
            (task_id, account_id,))

        cursor.execute("""SELECT id FROM listing WHERE task_id = %s""", \
            (task_id,))
        if cursor.fetchone() is None:
            print("Deleting a task that has no more listings.")
            cursor.execute("""DELETE FROM task WHERE id = %s""", \
                (task_id,))
        
        cursor.execute("""SELECT id, index FROM listing WHERE list_id = %s AND index > %s""", \
            (result[1], result[2],))
        greaters = cursor.fetchall()
        for i in range(len(greaters)):
            cursor.execute("""UPDATE listing SET index = %s WHERE id = %s""", \
                (greaters[i][1] - 1, greaters[i][0]))
        
        self.connection.commit()
        cursor.close()
        return result


    def delete_list(self, list_id):
        cursor = self.connection.cursor()

        cursor.execute("""SELECT account_id, index FROM list WHERE id = %s""", \
            (list_id,))
        result = cursor.fetchone()
        account_id = result[0]
        index = result[1]

        cursor.execute("""SELECT id, index FROM list WHERE account_id = %s AND index > %s""", \
            (account_id, index,))
        greaters = cursor.fetchall()
        for i in range(len(greaters)):
            cursor.execute("""UPDATE list SET index = %s WHERE id = %s""", \
                (greaters[i][1] - 1, greaters[i][0]))

        cursor.execute("""DELETE FROM list WHERE id = %s""", \
            (list_id,))
 
        self.connection.commit()
        cursor.close()
        return True


    def delete_assignment(self, account_id, task_id):
        cursor = self.connection.cursor()

        cursor.execute("""DELETE FROM assignment WHERE account_id = %s AND task_id = %s""", \
            (account_id, task_id,))
        
        self.connection.commit()
        cursor.close()
        return True



    def add_task(self, public, active, title, contents, room_id=None):
        cursor = self.connection.cursor()
        task_id = token_urlsafe(8)

        cursor.execute("""SELECT public FROM task WHERE id = %s""", \
            (task_id,))
        while cursor.fetchone() is not None:
            task_id = token_urlsafe(8)
            cursor.execute("""SELECT public FROM task WHERE id = %s""", \
                (task_id,))
    
        if room_id is None:
            cursor.execute("""INSERT INTO task (id, public, active, title, contents) VALUES(%s, %s, %s, %s, %s)""", (task_id, public, active, title, contents,))
        else:
            cursor.execute("""INSERT INTO task (id, public, active, title, contents, room_id) VALUES(%s, %s, %s, %s, %s, %s)""", (task_id, public, active, title, contents, room_id,))

        self.connection.commit()
        cursor.close()
        return task_id


    def add_task_permission(self, account_id, task_id, can_edit_contents, can_edit_title, can_edit_settings):
        cursor = self.connection.cursor()

        task_permission_id = token_urlsafe(8)
        cursor.execute("""SELECT id FROM task_permission WHERE id = %s""", \
            (task_permission_id,))
        while cursor.fetchone() is not None:
            task_permission_id = token_urlsafe(8)
            cursor.execute("""SELECT id FROM task_permission WHERE id = %s""", \
                (task_permission_id,)) 

        cursor.execute("""INSERT INTO task_permission (id, account_id, task_id, can_edit_contents, can_edit_title, can_edit_settings) VALUES(%s, %s, %s, %s, %s, %s)""", \
            (task_permission_id, account_id, task_id, can_edit_contents, can_edit_title, can_edit_settings))
        
        self.connection.commit()
        cursor.close()
        return task_permission_id


    def edit_task_title(self, task_id, title):
        cursor = self.connection.cursor()

        cursor.execute("""UPDATE task SET title = %s WHERE id = %s""", \
            (title, task_id,))

        self.connection.commit()
        cursor.close()
        return True


    def edit_task_contents(self, task_id, contents):
        cursor = self.connection.cursor()

        cursor.execute("""UPDATE task SET contents = %s WHERE id = %s""", \
            (contents, task_id,))

        self.connection.commit()
        cursor.close()
        return True


    def set_listing_active(self, listing_id, active):
        cursor = self.connection.cursor()

        cursor.execute("""SELECT account_id FROM listing WHERE id = %s""", \
            (listing_id,))
        account_id = cursor.fetchone()[0]

        cursor.execute("""UPDATE listing SET active = %s WHERE account_id = %s AND active = %s""", \
            (False, account_id, True))

        cursor.execute("""UPDATE listing SET active = %s WHERE id = %s""", \
            (active, listing_id,))

        self.connection.commit()
        cursor.close()
        return True


    def set_task_public(self, task_id, public):
        cursor = self.connection.cursor()

        cursor.execute("""UPDATE task SET public = %s WHERE id = %s""", \
            (public, task_id,))

        self.connection.commit()
        cursor.close()
        return True
    

    def set_listing_archived(self, listing_id, archived):
        cursor = self.connection.cursor()

        cursor.execute("""SELECT id, title FROM list WHERE account_id = %s""", (account_id,))
        lists = cursor.fetchall()
        
        archive
        tasks
        for l in lists:
            if l[1] == "Archive":
                archive = l
            if l[1] == "Tasks":
                tasks = l

        if archived:
            cursor.execute("""SELECT id, index FROM listing WHERE list_id = %s""", \
                (archive[0],))
            new_greaters = cursor.fetchall()
            for i in range(len(new_greaters)):
                cursor.execute("""UPDATE listing SET index = %s WHERE id = %s""", \
                    (new_greaters[i][1] + 1, new_greaters[i][0]))
        
            cursor.execute("""UPDATE listing SET index = %s, list_id = %s WHERE id = %s""", \
                (0, archive[0], listing_id))
        else:
            cursor.execute("""SELECT id, index FROM listing WHERE list_id = %s""", \
                (tasks[0],))
            index = len(cursor.fetchall()) - 1      
            cursor.execute("""UPDATE listing SET index = %s, list_id = %s WHERE id = %s""", \
                (index, tasks[0], listing_id))

        self.connection.commit()
        cursor.close()
        return True
    

    def set_task_complete(self, task_id, complete):
        cursor = self.connection.cursor()

        cursor.execute("""UPDATE task SET complete = %s WHERE id = %s""", \
            (complete, task_id,))

        self.connection.commit()
        cursor.close()
        return True


    def get_active_listing_id(self, account_id):
        cursor = self.connection.cursor()
        cursor.execute("""SELECT id FROM listing WHERE active = %s AND account_id = %s""", (True, account_id,))
        listing_id = cursor.fetchone()
        cursor.close()
        return listing_id
    

    def add_listing(self, account_id, task_id, list_id, index):
        # add listing
        # increment all listings in this list with indices >= this one
        cursor = self.connection.cursor()
        listing_id = token_urlsafe(8)

        cursor.execute("""SELECT account_id FROM listing WHERE id = %s""", \
            (listing_id,))
        while cursor.fetchone() is not None:
            listing_id = token_urlsafe(8)
            cursor.execute("""SELECT account_id FROM listing WHERE id = %s""", \
                (listing_id,))
    
        cursor.execute("""SELECT id, index FROM listing WHERE list_id = %s AND index >= %s""", \
            (list_id, index,))
        greaters = cursor.fetchall()
        for i in range(len(greaters)):
            cursor.execute("""UPDATE listing SET index = %s WHERE id = %s""", \
                (greaters[i][1] + 1, greaters[i][0]))

        cursor.execute("""INSERT INTO listing (id, account_id, task_id, list_id, index) VALUES(%s, %s, %s, %s, %s)""", (listing_id, account_id, task_id, list_id, index,))

        self.connection.commit()
        cursor.close()
        return listing_id


    def edit_listing(self, listing_id, list_id, index):
        cursor = self.connection.cursor()

        cursor.execute("""SELECT list_id, index FROM listing WHERE id = %s""", \
            (listing_id,))
        result = cursor.fetchone()
        old_list_id = result[0]
        old_index = result[1]

        if list_id == old_list_id:
            if index > old_index:
                cursor.execute("""SELECT id, index FROM listing WHERE list_id = %s AND index <= %s AND index > %s""", \
                    (list_id, index, old_index,))
                lessers = cursor.fetchall()
                for i in range(len(lessers)):
                    cursor.execute("""UPDATE listing SET index = %s WHERE id = %s""", \
                        (lessers[i][1] - 1, lessers[i][0]))
            elif index < old_index:
                cursor.execute("""SELECT id, index FROM listing WHERE list_id = %s AND index >= %s AND index < %s""", \
                    (list_id, index, old_index,))
                greaters = cursor.fetchall()
                for i in range(len(greaters)):
                    cursor.execute("""UPDATE listing SET index = %s WHERE id = %s""", \
                        (greaters[i][1] + 1, greaters[i][0]))
            else:
                self.connection.commit()
                cursor.close()
                return False
        else:
            cursor.execute("""SELECT id, index FROM listing WHERE list_id = %s AND index > %s""", \
                (old_list_id, old_index,))
            old_greaters = cursor.fetchall()
            for i in range(len(old_greaters)):
                cursor.execute("""UPDATE listing SET index = %s WHERE id = %s""", \
                    (old_greaters[i][1] - 1, old_greaters[i][0]))
            cursor.execute("""SELECT id, index FROM listing WHERE list_id = %s AND index >= %s""", \
                (list_id, index,))
            new_greaters = cursor.fetchall()
            for i in range(len(new_greaters)):
                cursor.execute("""UPDATE listing SET index = %s WHERE id = %s""", \
                    (new_greaters[i][1] + 1, new_greaters[i][0]))
        
        cursor.execute("""UPDATE listing SET index = %s, list_id = %s WHERE id = %s""", \
            (index, list_id, listing_id))

        self.connection.commit()
        cursor.close()
        return True


    def add_assignment(self, account_id, task_id):
        cursor = self.connection.cursor()
        assignment_id = token_urlsafe(8)

        cursor.execute("""SELECT account_id FROM assignment WHERE id = %s""", \
            (assignment_id,))
        while cursor.fetchone() is not None:
            assignment_id = token_urlsafe(8)
            cursor.execute("""SELECT account_id FROM assignment WHERE id = %s""", \
                (assignment_id,))
    
        cursor.execute("""INSERT INTO assignment (id, account_id, task_id) VALUES(%s, %s, %s)""", (assignment_id, account_id, task_id,))
        self.connection.commit()
        cursor.close()
        return assignment_id


    def add_tag(self, account_id, color, title):
        cursor = self.connection.cursor()
        tag_id = token_urlsafe(8)

        cursor.execute("""SELECT title FROM tag WHERE id = %s""", \
            (tag_id,))
        while cursor.fetchone() is not None:
            tag_id = token_urlsafe(8)
            cursor.execute("""SELECT title FROM tag WHERE id = %s""", \
                (tag_id,))
    
        cursor.execute("""INSERT INTO tag (id, account_id, color, title) VALUES(%s, %s, %s, %s)""", (tag_id, account_id, color, title,))
        self.connection.commit()
        cursor.close()
        return tag_id

    
    def delete_tag(self, tag_id):
        cursor = self.connection.cursor()
        cursor.execute("""DELETE FROM tag WHERE id = %s""", (tag_id,))
        self.connection.commit()
        cursor.close()
        return True


    def add_tagging(self, tag_id, listing_id):
        cursor = self.connection.cursor()
        tagging_id = token_urlsafe(8)

        cursor.execute("""SELECT id FROM tagging WHERE id = %s""", \
            (tagging_id,))
        while cursor.fetchone() is not None:
            tagging_id = token_urlsafe(8)
            cursor.execute("""SELECT id FROM tagging WHERE id = %s""", \
                (tagging_id,))
    
        cursor.execute("""INSERT INTO tagging (id, tag_id, listing_id) VALUES(%s, %s, %s)""", (tagging_id, tag_id, listing_id,))
        self.connection.commit()
        cursor.close()
        return tagging_id

    
    def delete_tagging(self, tagging_id):
        cursor = self.connection.cursor()
        cursor.execute("""DELETE FROM tagging WHERE id = %s""", (tagging_id,))
        self.connection.commit()
        cursor.close()
        return True


    def add_list(self, account_id, title, index, inbox=False, room_id=None, archive=False):
        cursor = self.connection.cursor()
        list_id = token_urlsafe(8)

        cursor.execute("""SELECT account_id FROM list WHERE id = %s""", \
            (list_id,))
        while cursor.fetchone() is not None:
            list_id = token_urlsafe(8)
            cursor.execute("""SELECT account_id FROM list WHERE id = %s""", \
                (list_id,))

        cursor.execute("""SELECT id, index FROM list WHERE account_id = %s AND index >= %s""", \
            (account_id, index,))
        greaters = cursor.fetchall()
        for i in range(len(greaters)):
            cursor.execute("""UPDATE list SET index = %s WHERE id = %s""", \
                (greaters[i][1] + 1, greaters[i][0]))
    
        if room_id is None:
            cursor.execute("""INSERT INTO list (id, account_id, title, index, inbox, archive) VALUES(%s, %s, %s, %s, %s, %s)""", (list_id, account_id, title, index, inbox, archive,))
        else:
            cursor.execute("""INSERT INTO list (id, account_id, title, index, inbox, archive, room_id) VALUES(%s, %s, %s, %s, %s, %s, %s)""", (list_id, account_id, title, index, inbox, archive, room_id,))
        
        self.connection.commit()
        cursor.close()
        return list_id


    def account_has_inbox_list(self, account_id):
        cursor = self.connection.cursor()
        cursor.execute("""SELECT id FROM list WHERE account_id = %s AND inbox""", (account_id,))
        id_ = cursor.fetchone()
        cursor.close()
        return id_


    def edit_list_title(self, list_id, title):
        cursor = self.connection.cursor()

        cursor.execute("""UPDATE list SET title = %s WHERE id = %s""", \
            (title, list_id,))

        self.connection.commit()
        cursor.close()
        return True


    def move_list(self, list_id, index):
        cursor = self.connection.cursor()

        cursor.execute("""SELECT id, account_id, index FROM list WHERE id = %s""", \
            (list_id,))
        result = cursor.fetchone()
        old_index = result[2]
        account_id = result[1]

        print("Old index: " + str(old_index))
        print("New index: " + str(index))
    
        if index > old_index:
            cursor.execute("""SELECT id, index FROM list WHERE account_id = %s AND index <= %s AND index > %s""", \
                (account_id, index, old_index,))
            lessers = cursor.fetchall()
            print(lessers)
            for i in range(len(lessers)):
                print("Moving " + str(lessers[i][1]) + " to " + str(lessers[i][1] - 1))
                cursor.execute("""UPDATE list SET index = %s WHERE id = %s""", \
                    (lessers[i][1] - 1, lessers[i][0]))
        elif index < old_index:
            cursor.execute("""SELECT id, index FROM list WHERE account_id = %s AND index >= %s AND index < %s""", \
                (account_id, index, old_index,))
            greaters = cursor.fetchall()
            print(greaters)
            for i in range(len(greaters)):
                print("Moving " + str(greaters[i][1]) + " to " + str(greaters[i][1] + 1))
                cursor.execute("""UPDATE list SET index = %s WHERE id = %s""", \
                    (greaters[i][1] + 1, greaters[i][0]))
        else:
            self.connection.commit()
            cursor.close()
            self.connection.close()
            return False

        cursor.execute("""UPDATE list SET index = %s WHERE id = %s""", \
            (index, list_id,))

        self.connection.commit()
        cursor.close()
        return True