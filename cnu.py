#!flask/bin/python
from flask import Flask, jsonify, make_response, abort, request, Response
from pymongo import MongoClient
import pymongo
from bson.json_util import dumps, loads
import json
import threading
import pygal
from pygal import Config
from pygal.style import LightSolarizedStyle, LightGreenStyle

client = MongoClient()
db = client.cnu
locations = db.locations
updates = db.updates
feedback = db.feedback
graphs = db.graphs
info = []

update_cursor = updates.find()
location_cursor = locations.find()

def requery_updates():
    threading.Timer(60, requery_updates).start()
    global update_cursor
    update_cursor = updates.find()

    global info
    info = []
    for record in update_cursor:
        location = record.get('location')
        found = False
        for i in info:
            if i.get('location') == location:
                found = True
                people = i.get('people')
                i.update({'people':people+1})
        if not found:
            info.append({'location':location,'people':1})
    for i in info:
        people = i.get('people')
        crowded = 1 if people > 10 else 2 if people > 20 else 0
        i.update({'crowded':crowded})

def requery_locations():
    threading.Timer(60 * 5, requery_locations).start()
    global location_cursor
    location_cursor = locations.find()

requery_updates()
requery_locations()

app = Flask(__name__)

@app.route('/')
def index():
    abort(400)

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify( { 'error': 'Not found' } ), 404)

@app.errorhandler(400)
def bad_request(error):
    return make_response(jsonify( { 'error': 'Bad request' } ), 400)

# Get

@app.route('/cnu/api/v1.0/locations', methods = ['GET'])
def get_locations():
    return dumps(location_cursor)

@app.route('/cnu/api/v1.0/info/', methods = ['GET'])
def get_info():
    return dumps(info)

@app.route('/cnu/api/v1.0/data/<location>/', methods=['GET'])
def get_data(location):
    graph = graphs.find({'location': location})
    if not graph:
        abort(404)
    return dumps(graph)

@app.route('/cnu/api/v1.0/data/<location>/<time>', methods=['GET'])
def get_data_by_time(location, time):
    graph = graphs.find_one({'location': location, 'time': time})
    if not graph:
        abort(404)
    return dumps(graph)

@app.route('/cnu/api/v1.0/graphs/<location>/', methods=['GET'])
def get_graph(location):
    response = app.send_static_file('graphs/' + location + '.svg')
    response.mimetype = 'text/html'
    return response

@app.route('/cnu/api/v1.0/menus/<location>/', methods=['GET'])
def get_menu(location):
    response = app.send_static_file('menus/' + location + '.txt')
    return response

# Post
@app.route('/cnu/api/v1.0/locations', methods = ['POST'])
def create_location():
    if not request.json:
        abort(400)
    locations.insert(request.json)
    return make_response("OK", 201)

@app.route('/cnu/api/v1.0/update', methods = ['POST'])
def update_user():
    if not request.json or not 'id' in request.json:
        abort(400)
    key = {'id':request.json['id']}
    updates.update(key, request.json, upsert=True)
    return make_response("OK", 201)

@app.route('/cnu/api/v1.0/feedback', methods = ['POST'])
def create_feedback():
    if not request.json or not 'id' in request.json:
        abort(400)
    feedback.insert(request.json)
    return make_response("OK", 201)

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0')