import json
from msilib import init_database
import random
from time import sleep
import requests
import os
import base64
import sqlite3 as sl


path = os.path.dirname(os.path.realpath(__file__))
keys = {}
spotify_keys = {}


def init_lastfm():
    global keys
    # access last.fm api keys from file
    if(os.path.exists(path + '/keys.json')):
        with open(path + '/keys.json') as f:
            keys = json.load(f)
    else:
        keys = {'lastfm_api_key': ''}
        with open(path + '/keys.json', 'w') as f:
            # ask user for api key
            keys['lastfm_api_key'] = input('Enter your last.fm api key: ')
            json.dump(keys, f)


def get_user():
    # get last.fm user from config
    if(os.path.exists(path + '/config.json')):
        with open(path + '/config.json') as f:
            config = json.load(f)

    else:
        config = {'lastfm_user': ''}
        # ask user for last.fm user
        config['lastfm_user'] = input('Enter your last.fm username: ')
        with open(path + '/config.json', 'w') as f:
            json.dump(config, f)

    return config['lastfm_user']


def get_top_tracks(user):
    # get last.fm user's top tracks
    url = 'http://ws.audioscrobbler.com/2.0/?method=user.gettoptracks&user=' + \
        user + '&api_key=' + keys['lastfm_api_key'] + '&format=json'
    response = requests.get(url)
    data = response.json()

    # get the tracks in "track - artist" format with scrobbles count
    top_tracks = []
    for track in data['toptracks']['track']:
        top_tracks.append({'track': track['name'], 'artist': track['artist']['name'],
                          'playcount': track['playcount'], 'duration': track['duration']})

    with open(path + '/top_tracks.json', 'w') as f:
        json.dump(top_tracks, f)

    return top_tracks


def scale(top_tracks):

    total = 0
    top_50_songs_scaled = []
    for song in top_tracks:
        print(song)
        if(int(song['duration']) == 0):
            song['duration'] = 120

        total += int(song['playcount']) * int(song['duration'])
        top_50_songs_scaled.append({'track': song['track'], 'artist': song['artist'], 'playcount': song['playcount'],
                                   'duration': song['duration'], 'uri': song['uri'], 'scaled': int(song['playcount']) * int(song['duration'])})

        total += int(song['playcount']) * int(song['duration'])

    new_total = 0

    # divide each song's scaled value by the total scaled value
    for song in top_50_songs_scaled:
        song['scaled'] = int(song['scaled']/total * 1000)
        new_total += song['scaled']

    # print each song into a json file
    for song in top_50_songs_scaled:
        print(song['track'] + ": " + str(song['scaled']/new_total * 100) + "%")

    print('Total: ' + str(new_total))

    return top_50_songs_scaled


def refresh(refresh_token):
    global spotify_tokens

    refresh_token = spotify_tokens['refresh_token']

    # encode in base64 the client id and client secret
    encoded = spotify_keys['client_id'] + ':' + spotify_keys['client_secret']
    encoded = encoded.encode('ascii')
    encoded = base64.b64encode(encoded)
    encoded = encoded.decode('ascii')

    # get new access token
    url = 'https://accounts.spotify.com/api/token'
    headers = {'Authorization': 'Basic ' + encoded}
    body = {'grant_type': 'refresh_token', 'refresh_token': refresh_token}
    response = requests.post(url, headers=headers, data=body)
    access_token = response.json()['access_token']
    try:
        refresh_token = response.json()['refresh_token']
    except:
        refresh_token = spotify_tokens['refresh_token']
    spotify_tokens = {'access_token': access_token,
                      'refresh_token': refresh_token}

    # save tokens to file
    with open(path + '/spotify_tokens.json', 'w') as f:
        json.dump(spotify_tokens, f)

    return spotify_tokens


def init_spotify():
    global spotify_keys, spotify_tokens

    # get client id and client secret from file
    if(os.path.exists(path + '/spotify_keys.json')):
        with open(path + '/spotify_keys.json') as f:
            spotify_keys = json.load(f)
    else:
        spotify_keys = {'client_id': '', 'client_secret': ''}
        with open(path + '/spotify_keys.json', 'w') as f:
            # ask user for api key
            spotify_keys['client_id'] = input('Enter your client id: ')
            spotify_keys['client_secret'] = input('Enter your client secret: ')
            json.dump(spotify_keys, f)

    # get tokens token from file
    if(os.path.exists(path + '/spotify_tokens.json')):
        with open(path + '/spotify_tokens.json') as f:
            spotify_tokens = json.load(f)

        refresh_token = spotify_tokens['refresh_token']

        # get new access token
        access_token = refresh(refresh_token)
        # get user id and save it to config
        user_id = get_user_id()
        with open(path + '/config.json', 'r+') as f:
            config = json.load(f)
            config['user_id'] = user_id
            f.seek(0)
            print(config)
            json.dump(config, f)

    else:
        # get auth token from spotify api with scopes of playlist-modify-private
        url = 'https://accounts.spotify.com/authorize' + "?client_id=" + \
            spotify_keys['client_id'] + "&response_type=code&grant_type=client_credentials" + \
            "&redirect_uri=http://localhost:8888/callback" + "&scope=playlist-modify-private"
        print(url)
        auth_token = input()

        # get access and refresh tokens from spotify api using auth token
        url = 'https://accounts.spotify.com/api/token'

        # encode in base64 the client id and client secret
        encoded = spotify_keys['client_id'] + \
            ':' + spotify_keys['client_secret']
        encoded = encoded.encode('ascii')
        encoded = base64.b64encode(encoded)
        encoded = encoded.decode('ascii')

        headers = {'Authorization': 'Basic ' + encoded}
        body = {'grant_type': 'authorization_code', 'code': auth_token,
                'redirect_uri': 'http://localhost:8888/callback'}

        response = requests.post(url, headers=headers, data=body)
        access_token = response.json()['access_token']
        refresh_token = response.json()['refresh_token']

        spotify_tokens = {'access_token': access_token,
                          'refresh_token': refresh_token}

        # save tokens to file
        with open(path + '/spotify_tokens.json', 'w') as f:
            json.dump(spotify_tokens, f)

        # get user id and save it to config
        user_id = get_user_id()
        with open(path + '/config.json', 'r+') as f:
            config = json.load(f)
            f.seek(0)
            config['user_id'] = user_id
            json.dump(config, f)

    return spotify_tokens


def search(artist, track):
    global spotify_tokens

    # get access token
    access_token = spotify_tokens['access_token']

    # get search results from spotify api
    url = 'https://api.spotify.com/v1/search?'
    headers = {'Authorization': 'Bearer ' + access_token}
    body = {'q': 'artist:' + artist + ' ' + 'track:'+track, 'type': 'track'}
    print("Searching for " + body['q'])
    response = requests.get(url, headers=headers, params=body)
    data = response.json()
    try:
        uri = data['tracks']['items'][0]['uri']
    except:
        uri = None

    return uri


def get_top_50_songs_uri():

    # open top 50 songs json file
    with open(path + '/top_tracks.json', encoding='utf-8') as f:
        top_tracks = json.load(f)

    # query sql database for artist and track
    con = sl.connect(path + '/track.db')
    cur = con.cursor()

    new_top_tracks = []

    for song in top_tracks:

        artist = song['artist']
        track = song['track']
        duration = song['duration']

        cur.execute(
            'SELECT * FROM tracks WHERE artist = ? AND track = ?', (artist, track))
        data = cur.fetchone()

        # get uri from the sql database
        if(data):
            uri = data[3]
            print(uri)
        else:
            uri = search(artist, track)
            if(uri != None):
                # add uri to sql database
                cur.execute('INSERT INTO tracks VALUES (?, ?, ?, ?)',
                            (artist, track, duration, uri))
                con.commit()
            else:
                # remove song from top 50 songs json file
                print('here')
                print(song)
                print("there")
                continue

        # add uri to list
        song['uri'] = uri
        new_top_tracks.append(song)

    con.close()

    return new_top_tracks


def create_playlist():

    # check for a playlist id in the config
    if(os.path.exists(path + '/config.json')):
        with open(path + '/config.json') as f:
            config = json.load(f)
        if('playlist_id' in config):
            playlist_id = config['playlist_id']

            # empty playlist
            unfollow_playlist(playlist_id)

    # create a new playlist
    global spotify_tokens

    # get access token
    access_token = spotify_tokens['access_token']

    # get user id
    user_id = get_user_id()

    # create new playlist
    url = 'https://api.spotify.com/v1/users/' + user_id + '/playlists'
    headers = {'Authorization': 'Bearer ' + access_token}
    body = {'name': 'Top 50 Songs hehe', "description": "Top 50 songs from the lastfm weighted by duration and scrobble count",
            "public": "false"}
    response = requests.post(url, headers=headers, json=body)

    print(response.json())

    # get playlist id
    playlist_id = response.json()['id']

    # save playlist id to config
    with open(path + '/config.json', 'r+') as f:
        config = json.load(f)
        config['playlist_id'] = playlist_id
        f.seek(0)
        json.dump(config, f)

    with open(path + '/config.json', 'w') as f:
        json.dump(config, f)

    # return playlist id
    return playlist_id


def unfollow_playlist(playlist_id):

    # get access token
    access_token = spotify_tokens['access_token']

    # unfollow playlist
    url = 'https://api.spotify.com/v1/playlists/' + playlist_id + '/followers'
    headers = {'Authorization': 'Bearer ' + access_token}
    body = {'public': False}

    response = requests.delete(url, headers=headers, params=body)


def add_songs_to_playlist(playlist_id, songs):

    # get access token
    access_token = spotify_tokens['access_token']

    # get playlist_id from config
    with open(path + '/config.json') as f:
        config = json.load(f)
    playlist_id = config['playlist_id']

    #shuffle songs so it looks cleaner
    random.shuffle(songs)

    # add songs to playlist in batches of 100
    for i in range(0, len(songs)+100, 100):
        uris = []
        for j in range(i, i + 100):
            if(j < len(songs)):
                uris.append(songs[j])
        url = 'https://api.spotify.com/v1/playlists/' + playlist_id + '/tracks'
        headers = {'Authorization': 'Bearer ' + access_token}
        body = {'uris': uris}
        response = requests.post(url, headers=headers, json=body)

        sleep(0.2)

    return response.json()


def get_user_id():

    # get access token
    access_token = spotify_tokens['access_token']

    # get user id from spotify api if it doesn't exist in config
    if(os.path.exists(path + '/config.json')):
        with open(path + '/config.json') as f:
            config = json.load(f)
        if('user_id' in config):
            user_id = config['user_id']
        else:
            url = 'https://api.spotify.com/v1/me'
            headers = {'Authorization': 'Bearer ' + access_token}
            response = requests.get(url, headers=headers)
            user_id = response.json()['id']
            config['user_id'] = user_id
            with open(path + '/config.json', 'w') as f:
                json.dump(config, f)

    return user_id


def init_database():
    global con

    # create database if it doesn't exist
    if(not os.path.exists(path + '/track.db')):
        con = sl.connect(path + '/track.db')
        cur = con.cursor()
        cur.execute(
            'CREATE TABLE tracks (artist TEXT, track TEXT, duration TEXT, uri TEXT)')
        con.commit()
        con.close()


def main():
    global keys

    # initialize last.fm information/keys
    init_lastfm()

    # get last.fm user
    user = get_user()

    # get last.fm user's recent tracks
    top_tracks = get_top_tracks(user)

    # save top tracks to file
    # save_to_file_filtered(top_tracks)

    # initialize spotify information/keys
    init_spotify()

    # init_database()
    init_database()

    # get the uri of the top 50 songs stored in a sql database
    top_50_songs = get_top_50_songs_uri()

    # scaled count of the top 50 songs
    top_50_songs_scaled = scale(top_50_songs)

    # create a new playlist
    playlist_id = create_playlist()

    songs = []
    for song in top_50_songs_scaled:
        print(song['scaled'])
        for i in range(song['scaled']):
            songs.append(song['uri'])

    # add songs to playlist
    add_songs_to_playlist(playlist_id, songs)


main()
