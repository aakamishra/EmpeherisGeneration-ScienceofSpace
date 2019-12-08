import os
from cs50 import SQL
import math
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from flask import Response
from astropy.coordinates import SkyCoord
from astropy import units as u
from astropy.wcs import WCS
from astroquery.jplhorizons import conf, Horizons
import PIL
import matplotlib
import matplotlib.pyplot as plt
import mpld3
import matplotlib.colors as colors
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.text import TextPath
from matplotlib.transforms import Affine2D
from matplotlib.backend_bases import key_press_handler
from matplotlib.figure import Figure
from matplotlib import cm
import math
import random
import io
import numpy as np
from mpl_toolkits import mplot3d
from mpl_toolkits.mplot3d import axes3d, Axes3D
import mpl_toolkits.mplot3d.art3d as art3d
import csv
from datetime import date
import geocoder

conf.horizons_server = 'https://ssd.jpl.nasa.gov/horizons_batch.cgi'

# to store information about the images uploaded
db = SQL("sqlite:///images.db")
basedir = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = '/static/Images/uploads'

# Here we query the current date and time from datetime
today = date.today()
# We organize it in a format that is acceptable to the JSON query
d1 = today.strftime("%Y-%m-%d")
day = int(today.strftime("%d")) + 1
# We increment the day because we want the oribital data between 1 day
d2 = today.strftime(f"%Y-%m-{day}")

# These are the coordinates for Cambridge, MA (TODO fix geocoder)
lat, lon = 42.3736, -71.1097
geo = 42.3736, -71.1097

# Configure application
app = Flask(__name__)
obj = ''
# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# This code is similar to the flask finance application we made in pset8
# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
Session(app)

# This is an annual epoch query


def locate(name):
    location = {'lon': lon, 'lat': lat, 'elevation': 0.0158}
    eph = Horizons(id=name, location=location, epochs={'start': '2019-1-1', 'stop': '2019-12-20', 'step': '30d'}).ephemerides()
    return eph

# This is a daily epoch query


def locate1(name):
    location = {'lon': lon, 'lat': lat, 'elevation': 0.0158}
    eph = Horizons(id=name, location=location, epochs={'start': d1, 'stop': d2, 'step': '1h'}).ephemerides()

    return eph


def plot_png(astro_obj):

    data = locate(astro_obj)

    fig = Figure(figsize=(4, 4), dpi=400)
    # Here we set the bounds for the axes of out plot.
    fig.add_subplot(111, projection='3d').set_ylim([-10, 10])
    fig.add_subplot(111, projection='3d').set_zlim([-10, 10])
    # We also want to make the plot rotatable
    fig.add_subplot(111, projection='3d').set_xlim([-10, 10])
    fig.add_subplot(111, projection='3d').mouse_init()
    # We intialize our subplots as 3 dimensional
    ax = fig.gca(projection='3d')

    # Essentially this is to help get rid of tick labels on our graph
    ax.set_yticklabels([])
    ax.set_xticklabels([])

    # Here we try to convert from equatorial to cartesian coordinates using some
    # basic linear algebra and then try to superimpose that on the Earth' atmosphere
    z = np.sin(np.array((2*math.pi/180)*data['RA']))
    x = np.cos(np.array((2*math.pi/180)*data['RA']))*np.cos((2*math.pi/180)*np.array(data['DEC']))
    y = np.sin(np.array((2*math.pi/180)*data['RA']))*np.cos((2*math.pi/180)*np.array(data['DEC']))
    # Here we display the oribit in green on the 3d Earth projection
    ax.scatter(x, y, z, color='green')

    # Taken from https://stackoverflow.com/questions/30269099/creating-a-rotatable-3d-earth?lq=1

    # This code was created by Author sulkeh

    bm = PIL.Image.open('static/Images/blue_marble.jpg')
    bm = np.array(bm)/256
    lons = np.linspace(-180, 180, bm.shape[1]) * np.pi/180
    lats = np.linspace(-90, 90, bm.shape[0])[::-1] * np.pi/180
    x = np.outer(np.cos(lons), np.cos(lats)).T
    y = np.outer(np.sin(lons), np.cos(lats)).T
    z = np.outer(np.ones(np.size(lons)), np.sin(lats)).T
    ax.plot_surface(x, y, z, rstride=4, cstride=4, facecolors=bm)

    # End of borrowed code

    # I learned how to translate between equalitorial to cartesian in math 23

    z = np.sin(np.array((2*math.pi/180)*lon))

    # This takes our current longitude and latidude location

    x = np.cos(np.array((2*math.pi/180)*lon))*np.cos((2*math.pi/180)*np.array(lat))

    # Using a similar calculation as before but invereted we figure out
    # the location of Cambridge in a normalized 3-dimensional sphere

    y = np.sin(np.array((2*math.pi/180)*lon))*np.cos((2*math.pi/180)*np.array(lat))
    ax.scatter(x, y, z, color='black')
    ax.text(x, y, z, "Location")
    u, v = np.mgrid[0:2*np.pi:20j, 0:np.pi:10j]
    # Here we scale the earth's atmoshpere by drawing a basic wireframe arounf the globe
    x = 1.2*np.cos(u)*np.sin(v)
    y = 1.2*np.sin(u)*np.sin(v)
    # Here we are scaling the wireframe for the Earth's secondary projection
    z = 1.2*np.cos(v)
    # The frame will be in red, but also slightly transparent as well hence the alpha value
    ax.plot_wireframe(x, y, z, color="r", alpha=0.4)

    for angle in range(0, 4):
        # Here we alternate the rotation of the plot at different angles and save the
        # pictures that we generate
        ax.view_init(40, angle*90)
        # Seeting images with different views of the Earth
        # We cannot just upload the plot because we cannot make 3d interactive plots yet in
        # html for matplot lib because mpld3 does not support that

        # This probably takes the longest time in code
        file = f"static/Images/plot{angle}.png"
        fig.savefig(file)


def make_plot(obj):
    # First we send out the query to retreive the object we want to view
    eph = locate1(obj)
    # We set a basic canvas plot with a relative space of 4 plots
    # This (4,4) is meant for the tKinter interface
    fig = Figure(figsize=(4, 4), dpi=400)
    # We add a subplot to plot within the plot we have just created
    ax = fig.add_subplot(1, 1, 1)
    # The this is the variation of points as the object travels through the sky
    # within a single day
    ax.scatter(np.array(eph['AZ']), np.array(eph['EL']))
    # Here 'AZ' means azimuthal (degrees clockwise from the secondary axis of Earth)
    # Elevation means the the degrees above the horizont that the object will appear
    # The maximum for this will be about 90* and for 'AZ' its is 360 because the Earth
    # is not flat :)
    location = {'lon': lon, 'lat': lat, 'elevation': 0.0158}
    eph = Horizons(id=obj, location=location).ephemerides()
    # Now we make a specialized query to JPL Horions in order to make
    # a second scatter that display's the object's current location
    # on the parabola of its daily cycle in the sky
    ax.axvline(eph['RA'][0], color='red')
    ax.axhline(0, color='white')
    # This axis is just to show where the horizon is
    ax.set_facecolor('xkcd:navy blue')
    # The background is set to blue to make the plot look like its representing night
    file = f"static/Images/path.png"
    # We save this png to dsiplay later
    fig.savefig(file)


@app.route("/portal", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        obj = request.form.get("astro_obj")
        # Here we query the form to get the name of the object the user inputted
        if obj.isnumeric():
            JS_format = int(obj)
            # we check to see of its numeric because some queries have to have the
            # official NASA given identification number
        else:
            JS_format = '{0}'.format(obj)
            # Otherwise we format the string ocrrecty for the JSON query used for the
            # database query we want to execute via our server config
        plot_png(JS_format)
        # Now we use that object query and input it into the two functions to make
        # the correct oribtal plots
        make_plot(JS_format)
        eph = locate(JS_format)['RA'], locate(JS_format)['DEC']
        return render_template("home.html", geo=geo, eph=eph)
    else:
        return render_template('query.html', user=geo)

# I think this section speaks for itself, thhe tabs just have cool pictures that I took
@app.route("/", methods=["GET", "POST"])
def index():
    return render_template('index.html')


@app.route("/jupiter")
def jupiter():
    return render_template('jupiter.html')


@app.route("/saturn")
def saturn():
    return render_template('saturn.html')


@app.route("/moon")
def moon():
    return render_template('moon.html')

# The purpose of the data method is to get the raw portal query information
# this contains useful data about apprent magnitude and barycenters for
# any relvant calculations
@app.route("/data", methods=["GET", "POST"])
def data():
    if request.method == "POST":
        obj = request.form.get("astro")
        if obj.isnumeric():
            JS_format = int(obj)
            # We repeat the same process of making sure the query can be properly inputted
            # horizons is very finnicky
        else:
            JS_format = '{0}'.format(obj)  # Once again we format the query
            eph = locate1(JS_format)
            # Then we generate the ephemeris data we want

            with open('static/data.csv', mode='w') as data:
                csv_writer = csv.writer(data, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                for row in eph:
                    csv_writer.writerow(row)
                    # Now we write the data for every hour into a single row of CSV file
                    # Each data point is spearated by a comma for latter parsing
        return render_template("download.html")
    else:
        return render_template('csv.html')


# The purpose of uploads is to demonstrate
@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        image = request.files['file']
        # Here we get the file that we asked for input in our form
        imagename = image.filename
        # Then we save those file to be dispayed later
        image.save(f"static/Images/uploads/{imagename}")
        # We save the file name in the sql database to use later
        db.execute("INSERT INTO exchange (symbol, time) VALUES (:symbol,:time)",
                   symbol=imagename, time=d1)
        image_list = db.execute("SELECT * FROM exchange")
        return render_template("display.html", images=image_list)
    else:
        return render_template('upload.html')


@app.route("/display", methods=["GET", "POST"])
def display():
    # We then get back the names from the data base by pushing an sql query
    image_list = db.execute("SELECT * FROM exchange")
    # We then pass on this list to the html template
    return render_template("display.html", images=image_list)

# Thank you for reading through all of the those comments!
# Here is a smiley face :)