import json

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from models import Base, Player, Club

# Adding all the players to the database
engine = create_engine('sqlite:///epldata.db')
Base.metadata.create_all(engine)
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

# Reading from the JSON file
teams = json.load(open('epldata_teams.json'))
for team in teams:
    club_name = team['club'].replace("+", " ")
    try:
        club = Club(id=team['club_id'], name=club_name,
                    is_big_club=bool(team['big_club']))
        session.add(club)
        session.commit()
    except:
        # Club already present
        session.rollback()
        existing_club = session.query(Club).filter_by(
            id=team['club_id']).first()
        existing_club.name = club_name
        existing_club.is_big_club = bool(team['big_club'])
        session.add(existing_club)
        session.commit()

print("All clubs updated!")

players = json.load(open('epldata_players.json'))
for player in players:
    try:
        persona = Player(club_id=player['club_id'],
                         name=unicode(player['name']),
                         age=player['age'],
                         position=player['position'],
                         position_category=player['position_cat'],
                         market_value=player['market_value'],
                         nationality=player['nationality'])
        session.add(persona)
        session.commit()
    except:
        # Player already present
        session.rollback()
        persona = session.query(Player).filter_by(
            name=unicode(player['name'])).first()
        persona.club_id = player['club_id']
        persona.age = player['age']
        persona.position = player['position']
        persona.position_category = player['position_cat']
        persona.market_value = player['market_value']
        persona.nationality = player['nationality']
        session.add(persona)
        session.commit()

print("All players updated!")
