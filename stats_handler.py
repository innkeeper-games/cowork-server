from handler import Handler
from stats_database_connector import StatsDatabaseConnector

from datetime import datetime

import json
from uuid import uuid4
import logging
import asyncio

from emailer import Emailer

from settings_database_connector import SettingsDatabaseConnector

# achievements
from achievements.five_hours_focused_achievement import FiveHoursFocusedAchievement
from achievements.one_participant_achievement import OneParticipantAchievement
from achievements.four_participant_achievement import FourParticipantAchievement
from achievements.six_participant_achievement import SixParticipantAchievement
from achievements.one_referral_achievement import OneReferralAchievement
from achievements.three_referral_achievement import ThreeReferralAchievement
from achievements.twenty_four_hours_focused_achievement import TwentyFourHoursFocusedAchievement
from achievements.one_week_focused_achievement import OneWeekFocusedAchievement

# key is type, value is dictionary of requirements and types
message_templates = {
    "request_sessions": {"type": "request_sessions"},
    "request_achievements": {"type": "request_achievements"}
}

class StatsHandler(Handler):

    def __init__(self, authentication_handler):
        self.authentication_handler = authentication_handler
        self.stats_database_connector = StatsDatabaseConnector()
        self.settings_database_connector = SettingsDatabaseConnector()
        self.sessions = {}
        self.achievements = [
            FiveHoursFocusedAchievement(self.stats_database_connector),
            TwentyFourHoursFocusedAchievement(self.stats_database_connector),
            OneParticipantAchievement(self.stats_database_connector),
            FourParticipantAchievement(self.stats_database_connector),
            SixParticipantAchievement(self.stats_database_connector),
            OneReferralAchievement(self.stats_database_connector),
            ThreeReferralAchievement(self.stats_database_connector),
            OneWeekFocusedAchievement(self.stats_database_connector)
        ]

    def is_valid(self, message):
        global message_templates
            
        return Handler.is_valid(self, message_templates, message)


    async def consumer(self, websocket, message):
        message_valid = self.is_valid(message)
        session_valid = False
        if message_valid:
            if message["type"] == "request_sessions":
                await self.request_sessions(websocket, message)
            elif message["type"] == "request_achievements":
                await self.request_achievements(websocket, message)
        else:
            logging.error(
                "Message type is " + message["type"] + " " + str(message))
            logging.error(
                str(message_valid) + " " + str(session_valid))


    def send_achievement_email(self, account_id):
        username = self.stats_database_connector.get_username_for_id(account_id)
        max_progress = 0
        max_achievement = None
        for achievement in self.achievements:
            complete = self.stats_database_connector.is_achievement_complete(account_id, achievement)
            progress = achievement.get_progress(account_id)

            if not complete:
                # should it be completed?
                if progress >= max_progress:
                    max_progress = progress
                    max_achievement = achievement
    
        title = max_achievement.get_title()
        description = max_achievement.get_description()
        progress = str(progress * 100) + "%"
        reward = max_achievement.get_reward()
        self.emailer.send_achievement_email(username, title, description, progress, reward)


    async def request_sessions(self, websocket, message):
        username = self.authentication_handler.usernames[websocket]
        account_id = self.stats_database_connector.get_id_for_username(username)
        if self.authentication_handler.auth_database_connector.get_pro(account_id):
            sessions = self.stats_database_connector.get_sessions_for_account(account_id)
            response = {"channel": "stats", "type": "request_sessions", "sessions": sessions}
            response_json = json.dumps(response, default=str)
            await websocket.send(response_json)
    

    async def request_achievements(self, websocket, message):
        username = self.authentication_handler.usernames[websocket]
        account_id = self.stats_database_connector.get_id_for_username(username)
        achievements = []

        # this is also when we can check if complete

        for achievement in self.achievements:
            complete = self.stats_database_connector.is_achievement_complete(account_id, achievement)
            progress = achievement.get_progress(account_id)
            just_completed = False
            if not complete:
                # should it be completed?
                if progress >= 1:
                    self.stats_database_connector.set_achievement_complete(account_id, achievement)
                    response = {"channel": "stats", "type": "complete_ahievement", "achievement": {
                        "achievement_id": achievement.get_id(),
                        "title": achievement.get_title(),
                        "description": achievement.get_description(),
                        "progress": progress,
                        "reward": achievement.get_reward(),
                        "complete": True
                    }}
                    response_json = json.dumps(response, default=str)
                    await websocket.send(response_json)
                    complete = True
                    just_completed = True
    
            achievements.append({
                "achievement_id": achievement.get_id(), # is this necessary? might help with image/icon later
                "title": achievement.get_title(),
                "description": achievement.get_description(),
                "progress": progress,
                "reward": achievement.get_reward(),
                "just_completed": just_completed,
                "complete": complete
            })
        response = {"channel": "stats", "type": "request_achievements", "achievements": achievements}
        response_json = json.dumps(response, default=str)
        await websocket.send(response_json)

