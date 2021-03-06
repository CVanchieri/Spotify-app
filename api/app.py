"""  Main application for Spotify Flask App """

from decouple import config
#from dotenv import load_dotenv
from flask import Flask, render_template, jsonify, request
#from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import numpy as np
import pandas as pd
import psycopg2

from .recommend import Recommendations
from .spotify_functions import get_base_song_vector, query_spotify, get_album_art
from .prediction import make_genre_vector, get_genre, augment_song_vector

import json
import urllib
from os import getenv


#DB = SQLAlchemy()
# Make app factory
def create_app():
    app = Flask(__name__)
   #app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///spotify_tracks.sqlite3'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['ENV'] = config('ENV')
    rec_engine = Recommendations()
    
    CORS(app)

    # DB.init_app(app)

    # conn = sqlite3.connect('spotify_tracks.sqlite3')

    @app.route("/")
    def root():
        return render_template('base.html', title='Home')

    @app.route('/testpath/<track_id>')
    def testpath(track_id):
        """Using this to test prediction functions."""
        vec = augment_song_vector(get_base_song_vector(track_id))

        labels = list(vec.index)
        values = list(vec.values)

        output = dict(zip(labels,values))
        return output

    # three routes
    # /by_track_id : takes a set of track ids (including a set of one!), returns ten recommendations

    # I'm thinking this can be used for favorites as well, if "favorites" just ends up being a set of
    # track ids?

    @app.route('/by_track_id/<track_id>')
    def by_track_id(track_id):
        """takes a set of track ids (including a set of one!), returns ten recommendations."""

        #content = request.get_json(force=True)

        ten_track_df = get_ten_tracks()

        tuples = [item for item in ten_track_df.itertuples(index=False)]

        labels = ['artist_name', 'track_name', 'track_id', 'genre', 'danceability_diff', 'energy_diff',
       'loudness_diff', 'mode', 'speechiness_diff', 'acousticness_diff', 'instrumentalness_diff',
       'liveness_diff', 'valence_diff', 'tempo_diff']

        tupledicts = [dict(zip(labels,tuple)) for tuple in tuples]

        return json.dumps(tupledicts)

        # /search query
    @app.route('/query', methods=['POST'])
    @app.route('/query/<query_string>', methods=['GET'])

    def query(query_string=None, message=''):
        query_string = request.values['query_string']
        res = query_spotify(urllib.parse.unquote(query_string))
        return jsonify(res)

    @app.route('/recommend', methods=['POST'])
    @app.route('/recommend/<track_id>', methods=['GET'])
    def recommend(track_id=None, message=''):
        track_id = request.values['track_id']
        """Using this to test prediction functions."""
        # connect to the database
        rec_engine.connect(psycopg2.connect("postgres://hbxxvjdj:WKiU7AFZ_NQlwT1D0EQWStM1EwUqOg4K@rajje.db.elephantsql.com:5432/hbxxvjdj"))
        # get the base song vector for the track to be recommended
        vector = get_base_song_vector(track_id)
        # make dict out of base vector
        labels = list(vector.index)
        values = list(vector.values)
        original_dict = dict(zip(labels,values))
        # features to find difference for
        feature_list = ['acousticness', 'danceability', 'duration_ms', 'energy',
                        'instrumentalness', 'key', 'liveness', 'loudness', 'mode',
                        'speechiness', 'tempo', 'time_signature', 'valence']
        augmented = augment_song_vector(vector)
        # get recommendations
        recommendations = rec_engine.recommend(augmented)
        for rec in recommendations:
            # add the difference values
            for feature in feature_list:
                rec[feature+'_diff'] = rec[feature] - original_dict[feature]
            # add album art
            rec['album_art'] = get_album_art(rec['track_id'])
        return jsonify(recommendations)

    return app