import os
import random
import string
import httplib2
import json
import requests
import pycountry

from flask import (Flask,
                   render_template,
                   url_for,
                   request,
                   redirect,
                   flash,
                   jsonify)
from flask_sqlalchemy import SQLAlchemy

from sqlalchemy.orm import load_only

from flask import session as login_session

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
from flask import make_response

app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
session = db.session

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "EPL Teams"

from models import Player, Club, User


@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in range(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
        if login_session['provider'] == 'facebook':
            fbdisconnect()

        del login_session['provider']
        del login_session['state']
        flash("You have successfully been logged out.")
        return redirect(url_for('showClubs'))
    else:
        # login_session.clear()
        flash("You were not logged in")
        return redirect(url_for('showClubs'))


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print("Token's client ID does not match app's.")
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(
            json.dumps('Current user is already connected.'),
            200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['provider'] = 'google'
    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    # see if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;' \
              'border-radius: 150px;-webkit-border-radius: 150px;' \
              '-moz-border-radius: 150px;"> '
    flash("Now logged in as %s" % login_session['username'])
    print("done!")
    return output


@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session.get('access_token')
    if access_token is None:
        print('Access Token is None')
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    print('In gdisconnect access token is %s', access_token)
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print('result is ')
    print(result)

    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    print("access token received %s " % access_token)

    app_id = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_id']
    app_secret = json.loads(
        open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=f' \
          'b_exchange_token&client_id=%s&client_secret=%s&' \
          'fb_exchange_token=%s' % (
              app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.8/me"

    '''Due to the formatting for the result from the server token exchange we
    have to split the token first on commas and select the first index which
    gives us the key : value for the server access token then we split it on
    colons to pull out the actual token value and replace the remaining
    quotes with nothing so that it can be used directly in the graph api
    calls '''

    token = result.split(',')[0].split(':')[1].replace('"', '')

    url = 'https://graph.facebook.com/v2.8/me?access_token=%s&' \
          'fields=name,id,email' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    # print "url sent for API access:%s"% url
    # print "API JSON result: %s" % result
    data = json.loads(result)

    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # The token must be stored in the login_session in order to properly logout
    login_session['access_token'] = token

    # Get user picture
    url = 'https://graph.facebook.com/v2.8/me/picture?access_token=' \
          '%s&redirect=0&height=200&width=200' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;' \
              'border-radius: 150px;-webkit-border-radius: 150px;' \
              '-moz-border-radius: 150px;"> '

    flash("Now logged in as %s" % login_session['username'])
    return output


@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    access_token = login_session.get('access_token')
    if access_token is None:
        print('Access Token is None')
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    print('In fbdisconnect access token is %s', access_token)
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (
        facebook_id, access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    print('result is ')
    print(result)

    data = json.loads(result)

    if data.keys()[0] == 'success':
        del login_session['access_token']
        del login_session['facebook_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        response = make_response(json.dumps('Successfully disconnected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
        'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


# ==================
# Club Operations
# ==================
# View All Clubs
# View Club <id>
# Add new Club
# Update Club <id>
# Delete Club <id>
@app.route('/')
@app.route('/clubs')
def showClubs():
    clubs = session.query(Club).all()
    if 'username' not in login_session:
        return render_template("publicClubs.html", clubs=clubs)
    else:
        user_info = getUserInfo(login_session['user_id'])
        return render_template("clubs.html", clubs=clubs,
                               photo=user_info.picture)


@app.route('/clubs/<int:club_id>/')
def showClub(club_id):
    club = session.query(Club).filter_by(id=club_id).first()
    players = session.query(Player).filter_by(club_id=club.id).order_by(
        Player.position)

    if 'username' not in login_session:
        return render_template('publicClubPlayers.html', club=club,
                               players=players)
    else:
        user_info = getUserInfo(login_session['user_id'])
        return render_template('clubPlayers.html', club=club, players=players,
                               photo=user_info.picture)


@app.route('/clubs/new', methods=['GET', 'POST'])
def newClub():
    if 'username' not in login_session:
        return redirect('/login')

    if request.method == 'POST':
        newClub = Club(name=request.form['name'],
                       user_id=login_session['user_id'])
        session.add(newClub)
        session.commit()
        flash("New Club Created!")
        return redirect(url_for('showClubs'))
    else:
        return render_template("newClub.html")


@app.route('/clubs/<int:club_id>/edit', methods=['GET', 'POST'])
def editClub(club_id):
    if 'username' not in login_session:
        return redirect('/login')

    editedClub = session.query(Club).filter_by(id=club_id).one()
    if request.method == 'POST':
        if request.form['name']:
            editedClub.name = request.form['name']
            session.add(editedClub)
            session.commit()
            flash("Club Successfully Edited!")
            return redirect(url_for('showClubs'))
        else:
            flash("Enter name of Club!")
            return render_template('editClub.html', club_id=club_id,
                                   Club=editedClub)
    else:
        return render_template('editClub.html', club_id=club_id,
                               Club=editedClub)


@app.route('/club/<int:club_id>/delete', methods=['GET', 'POST'])
def deleteClub(club_id):
    if 'username' not in login_session:
        return redirect('/login')

    deletedClub = session.query(Club).filter_by(id=club_id).one()

    if deletedClub.user_id != login_session['user_id']:
        flash("You are not authorized to delete this club.")
        return redirect(url_for('showClubs'))

    if request.method == 'POST':
        session.delete(deletedClub)
        session.commit()
        flash("Club Successfully Deleted!")
        return redirect(url_for('showClubs'))
    else:
        return render_template('deleteClub.html', club_id=club_id,
                               Club=deletedClub)


# ==================
# Player Operations
# ==================
# Add new Player
# Update Player <id>
# Delete Player <id>

@app.route('/clubs/<int:club_id>/players/new/', methods=['GET', 'POST'])
def newPlayer(club_id):
    if 'username' not in login_session:
        return redirect('/login')

    clubs = session.query(Club).options(load_only("name")).all()
    positions = session.query(Player.position).distinct().all()
    position_categories = ['Attackers', 'Midfielders', 'Defenders',
                           'Goalkeepers']
    countries = [country.name for country in pycountry.countries]

    if request.method == 'POST':
        player_name = request.form['name']
        player_club_name = request.form['club_name']
        player_club = session.query(Club).filter_by(
            name=player_club_name).first()
        player_age = request.form['age']
        player_position = request.form['position']
        player_position_category = position_categories.index(
            request.form['position_category'])
        player_market_value = request.form['market_value']
        player_nationality = request.form['nationality']
        newPlayer = Player(name=player_name, club=player_club,
                           age=player_age,
                           position=player_position,
                           position_category=player_position_category,
                           market_value=player_market_value,
                           nationality=player_nationality,
                           user_id=login_session['user_id'])
        session.add(newPlayer)
        session.commit()
        flash("New Player Created")
        return redirect(url_for('showClub', club_id=club_id))
    else:
        return render_template('newPlayer.html', club_id=club_id,
                               clubs=clubs,
                               positions=positions,
                               position_categories=position_categories,
                               countries=countries)


@app.route('/clubs/<int:club_id>/players/<int:player_id>/edit',
           methods=['GET', 'POST'])
def editPlayer(club_id, player_id):
    if 'username' not in login_session:
        return redirect('/login')

    editedPlayer = session.query(Player).filter_by(id=player_id).one()
    clubs = session.query(Club).options(load_only("name")).all()
    positions = session.query(Player.position).distinct().all()
    position_categories = ['Attackers', 'Midfielders', 'Defenders',
                           'Goalkeepers']
    countries = [country.name for country in pycountry.countries]

    if request.method == 'POST':
        if request.form['name'] and request.form['description'] and \
                request.form['price'] and request.form['course']:
            editedPlayer.name = request.form['name']
            club_name = request.form['club_name']
            editedPlayer.club = session.query(Club).filter_by(
                name=club_name).first()
            editedPlayer.age = request.form['age']
            editedPlayer.positon = request.form['position']
            editedPlayer.position_category = position_categories.index(
                request.form['position_category'])
            editedPlayer.market_value = request.form['market_value']
            editedPlayer.nationality = request.form['nationality']
            session.add(editedPlayer)
            session.commit()
            flash("Player Successfully Edited")
            return redirect(url_for('showMenu', club_id=club_id))
        else:
            flash("Enter details about the Player")
            return render_template('editPlayer.html', club_id=club_id,
                                   player_id=player_id, Player=editedPlayer,
                                   clubs=clubs, positions=positions,
                                   position_categories=position_categories,
                                   countries=countries)

    else:
        return render_template('editPlayer.html', club_id=club_id,
                               player_id=player_id, Player=editedPlayer,
                               clubs=clubs, positions=positions,
                               position_categories=position_categories,
                               countries=countries)


@app.route('/club/<int:club_id>/players/<int:player_id>/delete/',
           methods=['GET', 'POST'])
def deletePlayer(club_id, player_id):
    if 'username' not in login_session:
        return redirect('/login')

    deletedPlayer = session.query(Player).filter_by(id=player_id).one()

    if deletedPlayer.user_id != login_session['user_id']:
        flash("You are not authorized to delete this player.")
        return redirect(url_for('showClub', club_id=club_id))

    if request.method == 'POST':
        session.delete(deletedPlayer)
        session.commit()
        flash("Player Successfully Deleted")
        return redirect(url_for('showClub', club_id=club_id))
    else:
        return render_template('deletePlayer.html', club_id=club_id,
                               player_id=player_id, Player=deletedPlayer)


# JSON endpoints
@app.route('/api/players/JSON')
def playersJSON():
    players = session.query(Player).all()
    return jsonify(Players=[i.serialize for i in players])


@app.route('/api/clubs/JSON')
def clubsJSON():
    clubs = session.query(Club).all()
    return jsonify(Clubs=[i.serialize for i in clubs])


if __name__ == '__main__':
    app.run()
