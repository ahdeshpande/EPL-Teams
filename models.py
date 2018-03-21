from server import db


class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    picture = db.Column(db.String(255))

    def __init__(self, id, name, email, picture):
        self.id = id
        self.name = name
        self.email = email
        self.picture = picture

    def __repr__(self):
        return '<email {}>'.format(self.email)


class Club(db.Model):
    __tablename__ = 'club'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    is_big_club = db.Column(db.Boolean, unique=False, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship(User)
    player = db.relationship('Player', cascade='all, delete-orphan')

    def __init__(self, id, name, is_big_club, user_id, user, player):
        self.id = id
        self.name = name
        self.is_big_club = is_big_club
        self.user_id = user_id
        self.user = user
        self.player = player

    def __repr__(self):
        return '<name {}'.format(self.name)

    @property
    def serialize(self):
        return {
            'name': self.name,
            'id': self.id,
            'is_big_club': self.is_big_club,
        }


class Player(db.Model):
    __tablename__ = 'player'

    name = db.Column(db.String(80), nullable=False)
    id = db.Column(db.Integer, db.Sequence('player_id_seq'), primary_key=True)
    club_id = db.Column(db.Integer, db.ForeignKey('club.id'))
    club = db.relationship(Club)
    age = db.Column(db.Integer)
    position = db.Column(db.String(4))
    position_category = db.Column(db.Integer)
    market_value = db.Column(db.Integer)
    nationality = db.Column(db.String(60))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship(User)

    def __init__(self, name, id, club_id, club, age, position,
                 position_category, market_value, nationality, user_id, user):
        self.name = name
        self.id = id
        self.club_id = club_id
        self.club = club
        self.age = age
        self.position = position
        self.position_category = position_category
        self.market_value = market_value
        self.nationality = nationality
        self.user_id = user_id
        self.user = user

    def __repr__(self):
        return '<name {}'.format(self.name)

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
