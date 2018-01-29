import os
import sys
import json

from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, Sequence
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine

Base = declarative_base()


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    picture = Column(String(255))


class Club(Base):
    __tablename__ = 'club'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    is_big_club = Column(Boolean, unique=False, default=False)

    @property
    def serialize(self):

        return {
            'name': self.name,
            'id': self.id,
            'is_big_club': self.is_big_club,
        }


class Player(Base):
    __tablename__ = 'player'

    name = Column(String(80), nullable=False)
    id = Column(Integer, Sequence('player_id_seq'), primary_key=True)
    club_id = Column(Integer, ForeignKey('club.id'))
    club = relationship(Club)
    age = Column(Integer)
    position = Column(String(4))
    position_category = Column(Integer)
    market_value = Column(Integer)
    nationality = Column(String(60))


# We added this serialize function to be able to send JSON objects in a
# serializable format
    @property
    def serialize(self):

        return {
            'name': self.name,
            'id': self.id,
            'club': self.club.name,
            'age': self.age,
            'position': self.position,
            'position_category': self.position_category,
            'market_value': self.market_value,
            'nationality': self.nationality,
        }

engine = create_engine('sqlite:///epldata.db')


Base.metadata.create_all(engine)


# Adding all the players to the database
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

# Reading from the JSON file
try:
    teams = json.load(open('epldata_teams.json'))
    for team in teams:
        club_name = team['club'].replace("+", " ")
        club = Club(id=team['club_id'], name=club_name, is_big_club=bool(team['big_club']))
        session.add(club)
        session.commit() 
    print("All clubs added!")

    players = json.load(open('epldata_players.json'))
    for player in players:
        persona = Player(club_id=player['club_id'], name=unicode(player['name']), age=player['age'], position=player['position'], position_category=player['position_cat'], market_value=player['market_value'], nationality=player['nationality'])
        session.add(persona)
        session.commit()
    print("All players added!")
except:
    print("Error reading JSON file!")