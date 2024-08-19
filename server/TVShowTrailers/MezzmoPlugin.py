# -*- coding: utf-8 -*-
# #!/usr/bin/python

# Important: Plugins cannot be developed standalone outside of Mezzmo enviroment.  You will need to
# create plugins and load them into Mezzmo to get them to compile and run correctly, since
# Mezzmo injects paths & objects into python interpreter at runtime.  Use logging to debug your
# python script.

# See 'Plugins\MezzmoBaseClasses' folder for definition of Mezzmo classes that are to used
# for creating MezzmoPlugin, MezzmoDirectory, MezzmoItem and MezzmoSetting objects
from mezzmo import *

import logging
import time
import json
from functools import partial
from datetime import datetime, timedelta

import urllib
import urllib2

import pickle
from time import gmtime, strftime

# movie trailer feed URLs
#MOVIETRAILERS_URL_CONFIG    = 'http://api.themoviedb.org/3/configuration?api_key=dee64c83bd0310bc227948c9d4bc5aab'
#MOVIETRAILERS_URL_LIST      = 'http://api.themoviedb.org/3/movie/{}?api_key=dee64c83bd0310bc227948c9d4bc5aab'
#MOVIETRAILERS_URL_DETAILS   = 'http://api.themoviedb.org/3/movie/{}?#api_key=dee64c83bd0310bc227948c9d4bc5aab&append_to_response=videos,releases,casts'
#MOVIETRAILERS_URL_YOUTUBE   = 'https://www.youtube.com/watch?v={}'
#MOVIETRAILERS_URL_BASE      = ''
#MOVIETRAILERS_POSTER_SIZE   = 'w500'
#MOVIETRAILERS_BACKDROP_SIZE = 'original'


# global dictionary of user preferences for this plugin (see def get_prefs() & def mezzmo_set_settings()
TVShowTrailerSettings = {}

########################################################################################################################
def getTrailerDetails(db, tmdb_id):


    trcurr = db.execute('select tmdb_id, mezzmoTrURL, trType, trTitle, trOverview, trTagline, trRelease_date, trImdb_id, trWebsite, \
    trPoster_path, trBackdrop_path, trUser_rating, trGenres, trProd_company, trContent_rating, trArtist_actor, trComposer, var1    \
    from tvTrailers where tmdb_id = ?', (tmdb_id,))
    trtuple = trcurr.fetchone()
    
    if trtuple:
        # has a trailer video, so create new MezzmoItem object & fill in details
        if 'n' not in TVShowTrailerSettings['detloggingtv'].lower():
            genLog(str(trtuple))
        item = MezzmoItem()
        item.title = trtuple[3]
        if item.title[:4] == 'The ':
            item.sort_title = item.title[4:]
        elif item.title[:3] == 'An ':
            item.sort_title = item.title[3:]
        elif item.title[:2] == 'A ':
            item.sort_title = item.title[2:]
        else:
            item.sort_title = item.title
        item.type = "video"
        if TVShowTrailerSettings['trcategorytv'].lower() in ['video', 'movie', 'tvtrailer']:
            item.category = TVShowTrailerSettings['trcategorytv']
        else:
            item.category = 'video'
        item.themoviedb_id = trtuple[0]
        item.uri = trtuple[1]
        item.description = trtuple[4]
        item.tagline = trtuple[5]
        item.release_date = trtuple[6]
        if len(trtuple[6]) == 10:
            item.year = trtuple[6][:4]
        if len(TVShowTrailerSettings['trkeywordtv']) > 2:
            item.keywords = TVShowTrailerSettings['trkeywordtv']
        item.imdb_id = trtuple[7]
        item.website = trtuple[8]
        item.poster_uri = trtuple[9]
        item.backdrop_uri = trtuple[10]
        item.user_rating = trtuple[11]
        #item.album_series = trtuple[17]
        item.album_series = trtuple[3]
        if trtuple[12]:
            genre_text = ''
            genre_text = trtuple[12].split('##')
            genres = []
            for g in genre_text:
                genres.append(g) 
            item.genre = genres
        if trtuple[13]:
            production_company_text = ''
            production_company_text = trtuple[13].split('##')
            production_companies = []
            for p in production_company_text:
                production_companies.append(p) 
            item.production_company = production_companies
        item.content_rating = trtuple[14]
        if trtuple[15]:
            artist_actor_text = ''
            artist_actor_text = trtuple[15].split('##')
            artist_actors = []
            for g in artist_actor_text:
                artist_actors.append(g) 
            item.artist_actor = artist_actors
        if trtuple[16]:
            composer_director_creator_text = ''
            composer_director_creator_text = trtuple[16].split('##')
            composer_director_creators = []
            for c in composer_director_creator_text:
                composer_director_creators.append(c) 
            item.composer_director_creator = composer_director_creators
        return item
    return None


########################################################################################################################
def trailerDirectoryCallback(type):

    # function to get list of trailers for a given type
    content = []
    
    # themoviedb.org has server-side rate limiting (max. 40 requests in a 10 second span), so wait a little to try to keep within this limit
    #time.sleep(0.15)

    db = openTrailerDB()     

    dbcurr = db.execute('select count (tmdb_id) from tvTrailers where trType = ?', (type,))
    dbtuple = dbcurr.fetchone()

    if dbtuple:
        if 'n' not in TVShowTrailerSettings['detloggingtv'].lower():
            genLog('Number of TV Shows found for ' + type + ': ' + str(dbtuple[0]))
        dbcurr = db.execute('select tmdb_id from tvTrailers where trType = ? ORDER BY trRelease_date DESC', (type,))
        dbtuple = dbcurr.fetchall()
        for trailer in range(len(dbtuple)):
             item = getTrailerDetails(db, dbtuple[trailer][0])
             if item != None:
                 content.append(item)
    else:
        content = None

    db.close()
        
    return content


########################################################################################################################

def openTrailerDB():

    global TVShowTrailerSettings

    trailerdb = TVShowTrailerSettings['mezchannelpathtv'].rstrip('\\') + '\\tvshows\\trailers\\mezzmo_tvtrailers.db'   

    if 'n' not in TVShowTrailerSettings['detloggingtv'].lower():
        genLog(trailerdb)
    
    try:
        from sqlite3 import dbapi2 as sqlite
    except:
        from pysqlite2 import dbapi2 as sqlite

    try:                     
        db = sqlite.connect(trailerdb)
        if 'n' not in TVShowTrailerSettings['detloggingtv'].lower():
            genLog('SQLite Connection successful')
    except:
        if 'n' not in TVShowTrailerSettings['detloggingtv'].lower():
            genLog('SQLite Connection unsuccessful')
    return db


########################################################################################################################
def get_prefs(language):

    # partial callback that define the preferences that user can set to change the behaviour of movie trailers plugin
    prefs = []
    
    pref_1 = MezzmoSetting()
    pref_1.id = "mezchannelpathtv"
    pref_1.type = "text"
    pref_1.label = "Local path to Mezzmo channels folder. (i.e. e:\mezzmo_channels ) "
    pref_1.description = "Enter local path to Mezzmo Channels folder "
    pref_1.text_hide_value = 0
    pref_1.default_value = ""
    prefs.append(pref_1)

    pref_3 = MezzmoSetting()
    pref_3.id = "trcategorytv"
    pref_3.type = "text"
    pref_3.label = "Trailer media category type Video, Movie, or TvTrailer.  Default is Video ?  "
    pref_3.description = "Enable trailer media category type "
    pref_3.text_hide_value = 0
    pref_3.default_value = "Video"
    prefs.append(pref_3)

    pref_4 = MezzmoSetting()
    pref_4.id = "trkeywordtv"
    pref_4.type = "text"
    pref_4.label = "Enable default keyword(s) for all trailers.  Default is blank.  "
    pref_4.description = "Enter a default keyword "
    pref_4.text_hide_value = 0
    pref_4.default_value = ""
    prefs.append(pref_4)


    pref_2 = MezzmoSetting()
    pref_2.id = "detloggingtv"
    pref_2.type = "text"
    pref_2.label = "Enable detailed logging (Y/N) ?  "
    pref_2.description = "Enable detailed logging "
    pref_2.text_hide_value = 0
    pref_2.default_value = "N"
    prefs.append(pref_2)

    return prefs


########################################################################################################################
def mezzmo_set_settings(settings_path):

    # callback function that is called by Mezzmo on plugin startup and after user changes preference settings;
    # 'settings_path' contains the full path to the pickled settings file

    # reload preference settings
    global TVShowTrailerSettings
    with open(settings_path, "rb") as f:
        TVShowTrailerSettings = pickle.load(f)


########################################################################################################################
def mezzmo_get_plugins(language):

    # entry point callback function that is called by Mezzmo to get the list of plugins that this module defines;
    # this module defines 1 plugin - a Movie Trailers plugin
    # 'language' contains the Mezzmo user-set language (e.g. 'en', 'fr', 'de', etc.)

    # define Movie Trailers plugin details
    plugins = []
    plugin = MezzmoPluginContentProvider()
    plugin.id = "mezzmo.plugin.TVShowTrailers"
    plugin.title = "TV Show Trailers"
    plugin.version = "1.0.4"
    plugin.author = "Conceiva Pty. Ltd., jbinkley60"
    plugin.web_link = "https://www.themoviedb.org/"
    plugin.description = 'View TV Show trailers for current and upcoming TV Show series releases.\n\nTrailer information provided by www.themoviedb.org.'
    plugin.media_type = ["video"]
    plugin.category = ["Video"]
    plugin.poster_uri = "TVShowTrailers.jpg"
    plugin.backdrop_uri = "TVShowTrailersBackdrop.jpg"
    plugin.settings = partial(get_prefs, language=language)

    # add the top-level directories for the Trailer plugin

    # view trailers for airing today TV Shows
    nowplayingDirectory = MezzmoDirectory()
    nowplayingDirectory.title = "Airing Today"
    nowplayingDirectory.description = "View TV Show trailers for TV series that are airing today."
    nowplayingDirectory.children = partial(trailerDirectoryCallback, "airing_today")
    nowplayingDirectory.ttl = 0
    nowplayingDirectory.backdrop_uri = "TVShowTrailersBackdrop.jpg"
    nowplayingDirectory.sort_by = "Release date (Ascending)"
    plugin.children.append(nowplayingDirectory)
    
    # view trailers for TV Shows that are on now
    upcomingDirectory = MezzmoDirectory()
    upcomingDirectory.title = "Currently Airing TV Shows"
    upcomingDirectory.description = "View TV Show trailers for TV series that are currently airing."
    upcomingDirectory.children = partial(trailerDirectoryCallback, "on_the_air")
    upcomingDirectory.ttl = 0
    upcomingDirectory.backdrop_uri = "TVShowTrailersBackdrop.jpg"
    upcomingDirectory.sort_by = "Sort Title (Ascending)"
    plugin.children.append(upcomingDirectory)
    
    # view trailers for popular movies
    popularDirectory = MezzmoDirectory()
    popularDirectory.title = "Popular TV Shows"
    popularDirectory.description = "View TV Show trailers for popular series."
    popularDirectory.children = partial(trailerDirectoryCallback, "popular")
    popularDirectory.ttl = 0
    popularDirectory.backdrop_uri = "TVShowTrailersBackdrop.jpg"
    popularDirectory.sort_by = "Sort Title (Ascending)"
    plugin.children.append(popularDirectory)
    
    # view trailers for top-rated movies
    topratedDirectory = MezzmoDirectory()
    topratedDirectory.title = "Top Rated TV Shows"
    topratedDirectory.description = "View TV Show trailers for top rated series."
    topratedDirectory.children = partial(trailerDirectoryCallback, "top_rated")
    topratedDirectory.ttl = 0
    topratedDirectory.backdrop_uri = "TVShowTrailersBackdrop.jpg"
    topratedDirectory.sort_by = "Sort Title (Ascending)"
    plugin.children.append(topratedDirectory)
    
    # add Trailer plugin to list of plugin that this module defines
    plugins.append(plugin)

    # return list of plugins
    return plugins


########################################################################################################################
def mezzmo_set_logging(status, logging_path):

    # callback function that is called by Mezzmo on plugin startup and when user Mezzmo user turns on/off logging;
    # 'logging_path' contains the path where logs can be stored
    if status == 1:
        # turn logging on
        file_name = logging_path + time.strftime("%Y-%m-%d-%H-%M-%S.txt")
        fmt_line = "%(asctime)s: %(filename)s: %(funcName)s (%(lineno)d): %(message)s"
        fmt_date = "%Y-%m-%d %H:%M:%S"
        logging.basicConfig(filename = file_name, filemode = "w", level = logging.DEBUG, format=fmt_line, datefmt=fmt_date)
        logging.disable(logging.NOTSET)
        logging.info("Logging turned on")
    else:
        #turn logging off
        logging.info("Logging turned off")
        logging.disable(logging.CRITICAL)


########################################################################################################################
def genLog(mgenlog):                                        #  Write to logfile

        logoutfile = TVShowTrailerSettings['mezchannelpathtv'].rstrip('\\') + '\\tvshows\\trailers\\logfile.txt'

        fileh = open(logoutfile, "a")                       #  open logf file
        currTime = datetime.now().strftime('%Y-%m-%d %H:%M:%S') 
        data = fileh.write(currTime + ' - ' + mgenlog + '\n')
        fileh.close()