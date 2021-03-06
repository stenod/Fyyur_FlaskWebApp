# ----------------------------------------------------------------------------#
# Imports
# ----------------------------------------------------------------------------#

import datetime
import sys

import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for, jsonify
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import CSRFProtect
from sqlalchemy import inspect

from forms import *
from flask_migrate import Migrate

# ----------------------------------------------------------------------------#
# App Config.
# ----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)
csrf = CSRFProtect(app)


# ----------------------------------------------------------------------------#
# Models.
# ----------------------------------------------------------------------------#

class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    genres = db.Column(db.String(120))
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    seeking_talent = db.Column(db.BOOLEAN, nullable=False, default=False)
    seeking_description = db.Column(db.String(300))
    website = db.Column(db.String(120))
    facebook_link = db.Column(db.String(120))
    shows = db.relationship('Show', backref='venue', lazy=True)


class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.String(120))
    seeking_venue = db.Column(db.BOOLEAN, nullable=False, default=False)
    seeking_description = db.Column(db.String(300))
    image_link = db.Column(db.String(500))
    website_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    shows = db.relationship('Show', backref='artist', lazy=True)


class Show(db.Model):
    __tablename__ = 'Show'
    id = db.Column(db.Integer, primary_key=True)
    artist_id = db.Column(db.Integer, db.ForeignKey('Artist.id'), nullable=False)
    venue_id = db.Column(db.Integer, db.ForeignKey('Venue.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


# ----------------------------------------------------------------------------#
# Filters.
# ----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(value)
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format)


app.jinja_env.filters['datetime'] = format_datetime


# ----------------------------------------------------------------------------#
# Controllers.
# ----------------------------------------------------------------------------#

@app.route('/')
def index():
    return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
    data = []
    cities = db.session.query(Venue.city,
                              Venue.state).group_by(Venue.city, Venue.state).all()
    for idx, c in enumerate(cities):
        city = {}
        num_upcoming_shows = db.session.query(db.func.count(Show.artist_id)).filter_by(artist_id=Venue.id)
        print(idx, c)
        city['city'] = c.city
        city['state'] = c.state
        city['venues'] = db.session.query(Venue.id, Venue.name, num_upcoming_shows.label('num_upcoming_shows')) \
            .filter_by(city=c.city).group_by(Venue.id, Venue.name).all()
        data.append(city)

    return render_template('pages/venues.html', areas=data)


@app.route('/venues/search', methods=['POST'])
def search_venues():
    response = {}
    search_term = request.form.get('search_term', '')
    num_upcoming_shows = db.session.query(db.func.count(Show.artist_id)).filter_by(artist_id=Venue.id)

    response['count'] = Venue.query.filter(db.func.lower(Venue.name).contains(db.func.lower(search_term))).count()
    response['data'] = db.session.query(Venue.id, Venue.name, num_upcoming_shows.label('num_upcoming_shows')) \
        .filter(db.func.lower(Venue.name).contains(db.func.lower(search_term))).all()

    return render_template('pages/search_venues.html', results=response,
                           search_term=request.form.get('search_term', ''))


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    # shows the venue page with the given venue_id
    current_time = datetime.utcnow()
    upcoming_shows = db.session.query(Artist.id.label('artist_id'), Artist.name.label('artist_name'),
                                      Artist.image_link.label('artist_image_link'),
                                      Show.start_time).join(Show) \
        .filter(Show.start_time > current_time, Show.venue_id == venue_id).all()
    past_shows = db.session.query(Artist.id, Artist.name, Artist.image_link,
                                  Show.start_time).join(Show) \
        .filter(Show.start_time < current_time, Show.venue_id == venue_id).all()

    data = object_as_dict(Venue.query.filter(Venue.id == venue_id).first())
    data['genres'] = data['genres'].split(',')
    data['upcoming_shows'] = upcoming_shows
    data['past_shows'] = past_shows
    data['num_upcoming_shows'] = len(data['upcoming_shows'])
    data['num_past_shows'] = len(data['past_shows'])

    return render_template('pages/show_venue.html', venue=data)


#  Create Venue
#  ----------------------------------------------------------------


@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    form = VenueForm(request.form)
    if request.method == 'POST' and form.validate():
        try:
            venue = Venue(name=form.name.data, city=form.city.data, state=form.state.data, address=form.address.data,
                          phone=form.phone.data,
                          genres=','.join(form.genres.data),
                          facebook_link=form.facebook_link.data, website=form.website_link.data,
                          seeking_talent=form.seeking_talent.data,
                          seeking_description=form.seeking_description.data)
            db.session.add(venue)
            db.session.commit()
            flash('Venue ' + request.form['name'] + ' was successfully listed!')
        except:
            db.session.rollback()
            print(sys.exc_info())
            flash('Venue ' + request.form['name'] + ' could have not been added')
        finally:
            db.session.close()
    return render_template('pages/home.html')


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    # SQLAlchemy ORM to delete a record. Handle cases where the session commit could fail.
    venue = Venue.query.filter_by(id=venue_id)
    try:
        venue.delete()
        db.session.commit()
        flash('Venue successfully deleted!')
        return jsonify({'success': True})
    except:
        db.session.rollback()
        flash('Error: Venue could not be deleted deleted!')
        return jsonify({'success': False}), 400
    finally:
        db.session.close()


#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
    data = db.session.query(Artist.id, Artist.name).all()
    return render_template('pages/artists.html', artists=data)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    # seach for "A" should return "Guns N Petals", "Matt Quevado", and "The Wild Sax Band".
    # search for "band" should return "The Wild Sax Band".
    response = {}
    search_term = request.form.get('search_term', '')
    num_upcoming_shows = db.session.query(db.func.count(Show.artist_id)).filter_by(artist_id=Venue.id)

    response['count'] = Artist.query.filter(db.func.lower(Artist.name).contains(db.func.lower(search_term))).count()
    response['data'] = db.session.query(Artist.id, Artist.name, num_upcoming_shows.label('num_upcoming_shows')) \
        .filter(db.func.lower(Artist.name).contains(db.func.lower(search_term))).all()
    return render_template('pages/search_artists.html', results=response,
                           search_term=request.form.get('search_term', ''))


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    # shows the venue page with the given venue_id
    current_time = datetime.utcnow()
    upcoming_shows = db.session.query(Venue.id.label('venue_id'), Venue.name.label('venue_name'),
                                      Venue.image_link.label('venue_image_link'),
                                      Show.start_time).join(Show) \
        .filter(Show.start_time > current_time, Show.artist_id == artist_id).all()
    past_shows = db.session.query(Venue.id, Venue.name, Venue.image_link,
                                  Show.start_time).join(Show) \
        .filter(Show.start_time < current_time, Show.artist_id == artist_id).all()

    data = object_as_dict(Artist.query.filter(Artist.id == artist_id).first())
    data['genres'] = data['genres'].split(',')
    data['upcoming_shows'] = upcoming_shows
    data['past_shows'] = past_shows
    data['num_upcoming_shows'] = len(upcoming_shows)
    data['num_past_shows'] = len(past_shows)

    return render_template('pages/show_artist.html', artist=data)


#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    artist = Artist.query.get(artist_id)
    form = ArtistForm(obj=artist)
    form.genres.data = artist.genres.split(',')
    return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    try:
        artist = Artist.query.get(artist_id)
        form = ArtistForm(request.form)
        artist.name = form.name.data
        artist.state = form.state.data
        artist.city = form.city.data
        artist.phone = form.phone.data
        artist.genres = ','.join(form.genres.data)
        artist.facebook_link = form.facebook_link.data
        db.session.commit()
    except:
        db.session.rollback()
    finally:
        db.session.close()
        return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    venue = Venue.query.get(venue_id)
    form = VenueForm(obj=venue)
    form.genres.data = venue.genres.split(',')
    return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    try:
        venue = Venue.query.get(venue_id)
        form = VenueForm(request.form)
        venue.name = form.name.data
        venue.state = form.state.data
        venue.city = form.city.data
        venue.address = form.address.data
        venue.phone = form.phone.data
        venue.genres = ','.join(form.genres.data)
        venue.facebook_link = form.facebook_link.data
        db.session.commit()
    except:
        db.session.rollback()
    finally:
        db.session.close()
        return redirect(url_for('show_venue', venue_id=venue_id))


#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    form = ArtistForm(request.form)
    if request.method == 'POST' and form.validate():
        try:
            artist = Artist(name=form.name.data, city=form.city.data, state=form.state.data,
                            phone=form.phone.data,
                            genres=','.join(form.genres.data),
                            facebook_link=form.facebook_link.data, website_link=form.website_link.data,
                            seeking_venue=form.seeking_venue.data,
                            seeking_description=form.seeking_description.data)
            db.session.add(artist)
            db.session.commit()
            flash('Artist ' + request.form['name'] + ' was successfully listed!')
        except:
            db.session.rollback()
            print(sys.exc_info())
            flash('Artist ' + request.form['name'] + ' could not have been added')
        finally:
            db.session.close()
    return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
    # displays list of shows at /shows
    # TODO: replace with real venues data.
    #       num_shows should be aggregated based on number of upcoming shows per venue.

    data = db.session.query(Venue.id.label('venue_id'),
                            Venue.name.label('venue_name'),
                            Artist.id.label('artist_id'),
                            Artist.name.label('artist_name'),
                            Artist.image_link.label('artist_image_link'),
                            Show.start_time).join(Venue, Artist).all()
    return render_template('pages/shows.html', shows=data)


@app.route('/shows/create')
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    form = ShowForm(request.form)
    if request.method == 'POST' and form.validate():
        try:
            show = Show(artist_id=form.artist_id.data, venue_id=form.venue_id.data, start_time=form.start_time.data)
            db.session.add(show)
            db.session.commit()
            flash('Show was successfully listed!')
        except:
            db.session.rollback()
            print(sys.exc_info())
            flash('Error: Show was not listed!')
        finally:
            db.session.close()
    return render_template('pages/home.html')


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')


def object_as_dict(obj):
    return {c.key: getattr(obj, c.key)
            for c in inspect(obj).mapper.column_attrs}


# ----------------------------------------------------------------------------#
# Launch.
# ----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
