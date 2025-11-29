from flask_sqlalchemy import SQLAlchemy
from uuid import uuid4
from datetime import datetime
from enum import Enum
import random
db = SQLAlchemy()

#Фаза игры
class Phase(Enum):
    LOBBY = 'lobby'
    DAY = 'day'
    FIRST_NIGHT = 'first_night'
    NIGHT = 'night'
    VOITING = 'voting'
    FINAL_VOITING = 'final_voting'
    ENDED = 'ended'

class PlayerRole(Enum):
    MAFIA = 'mafia'
    CIVILIAN = 'civilian'
    SHERIFF = 'sheriff'
    DOCTOR = 'doctor'
    MISTRESS = 'mistress'
    MANIAC = 'maniac'

class PlayerStatus(Enum):
    ALIVE = 'alive'
    DEAD = 'dead'
    KILLED = 'killed'

class Player(db.Model):
    __tablename__ = 'players'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    nickname = db.Column(db.String(50), nullable=False, default='Player') #никнейм
    socket_id = db.Column(db.String(100), nullable=False, unique=True) 
    current_lobby_id = db.Column(db.String(36), db.ForeignKey('lobbies.id')) 
    avatar = db.Column(db.String(200), default=None) #аватарка

    role = db.Column(db.String(20)) #роль
    status = db.Column(db.String(20)) #статус

    votes_against = db.Column(db.Integer) #голоса за него
    has_voted = db.Column(db.Boolean) #голосовал ли он
    voted_against = db.Column(db.String(36)) #за кого голосовал
    night_voted_against = db.Column(db.String(36)) #за кого голосовал ночью(не для мирных)
    has_night_voted = db.Column(db.Boolean) #голосовал ли он ночью

    current_lobby = db.relationship('Lobby', back_populates='players')

class Lobby(db.Model):
    __tablename__ = 'lobbies'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(random.randint(100000, 999999)))
    host_socket_id = db.Column(db.String(100), nullable=False)
    players_count = db.Column(db.Integer, default=0)
    max_players = db.Column(db.Integer, nullable=False, default=8)
    location = db.Column(db.Integer)

    current_day = db.Column(db.Integer, default=0)
    current_night = db.Column(db.Integer, default=0)

    phase = db.Column(db.String(20), default=Phase.LOBBY.value)
    mafia_count = db.Column(db.Integer, default=1)
    is_maniac = db.Column(db.Boolean, default=False)
    is_mistress = db.Column(db.Boolean, default=False)
    is_sheriff_can_shot = db.Column(db.Boolean, default=False)

    players = db.relationship('Player', back_populates='current_lobby')