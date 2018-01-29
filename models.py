from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, Sequence
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
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
