import json

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from models import Base, Player, Club, User

# Adding all the players to the database
engine = create_engine('sqlite:///epldata.db')
Base.metadata.create_all(engine)
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

# Reading from the JSON file
users = json.load(open('epldata_users.json'))
for user in users:
    try:
        user_profile = User(id=user['id'],
                            name=user['name'],
                            email=user['email'],
                            picture=user['picture'])
        session.add(user_profile)
        session.commit()
    except:
        # User already present
        session.rollback()
        exisiting_user = session.query(User).filter_by(
            id=user['id']).first()
        exisiting_user.name = user['name']
        exisiting_user.email = user['email']
        exisiting_user.picture = user['picture']
        session.add(exisiting_user)
        session.commit()

print("All users updated!")

teams = json.load(open('epldata_teams.json'))
for team in teams:
    club_name = team['club'].replace("+", " ")
    try:
        club = Club(id=team['club_id'], name=club_name,
                    is_big_club=bool(team['big_club']),
                    user_id=team['user_id'])
        session.add(club)
        session.commit()
    except:
        # Club already present
        session.rollback()
        existing_club = session.query(Club).filter_by(
            id=team['club_id']).first()
        existing_club.name = club_name
        existing_club.is_big_club = bool(team['big_club'])
        existing_club.user_id = team['user_id']
        session.add(existing_club)
        session.commit()

print("All clubs updated!")

players = json.load(open('epldata_players.json'))
for player in players:
    try:
        persona = Player(id=player['id'],
                         club_id=player['club_id'],
                         name=unicode(player['name']),
                         age=player['age'],
                         position=player['position'],
                         position_category=player['position_cat'],
                         market_value=player['market_value'],
                         nationality=player['nationality'],
                         user_id=player['user_id'])
        session.add(persona)
        session.commit()
    except:
        # Player already present
        session.rollback()
        persona = session.query(Player).filter_by(
            id=player['id']).first()
        persona.club_id = player['club_id']
        persona.age = player['age']
        persona.position = player['position']
        persona.position_category = player['position_cat']
        persona.market_value = player['market_value']
        persona.nationality = player['nationality']
        persona.user_id = player['user_id']
        session.add(persona)
        session.commit()

print("All players updated!")
