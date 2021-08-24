from datetime import datetime

from flask import Flask, jsonify
from flask_cors import CORS
from flask_restful import Api, Resource, reqparse
from pymongo import ASCENDING, DESCENDING, MongoClient, UpdateOne

# init app
app = Flask(__name__)
cors = CORS(app)
api = Api(app)

# init db
client = MongoClient('mongodb+srv://api:gPdCEpVRVWuOnGqp@cluster0.xgkp9.mongodb.net/?ssl=true&ssl_cert_reqs=CERT_NONE&retryWrites=true&w=majority')
db = client['recommended_system']

class Device(Resource):
  def post(self):
    parser = reqparse.RequestParser()
    parser.add_argument('email', required=True, help='email(str) is required', type=str)
    parser.add_argument('deviceId', required=True, help='deviceId(str) is required', type=str)
    args = parser.parse_args()

    user = db['user'].find_one({ f'device.{args["deviceId"]}': { '$exists': True } })
    if not user:
      result = db['user'].update_one(
        { 'email': args['email'] },
        { '$set': { f'device.{args["deviceId"]}': {} } },
        upsert=True
      )
      if result.modified_count or result.upserted_id:
        return jsonify({ 'result': f'device {args["deviceId"]} registered' })
      else:
        return jsonify({ 'error': 'something went wrong' })
    else:
      return jsonify({ 'result': f'device {args["deviceId"]} has been registered' })

class User(Resource):
  def __init__(self):
    self.parser = reqparse.RequestParser()
    self.parser.add_argument('email', required=True, help='email(str) is required', type=str)

  def get(self):
    args = self.parser.parse_args()

    if args['email']:
      data = db['user'].find_one(args, projection={ '_id': False, 'device': False })
      if data:
        return jsonify({ 'data': data })
      else:
        return jsonify({ 'error': f'user {args["email"]} does not exist' })
    else:
      return jsonify({ 'error': 'must have email or deviceId' })

  def post(self):
    self.parser.add_argument('name', type=str)
    self.parser.add_argument('birthday', type=str)
    self.parser.add_argument('gender', type=str)
    args = self.parser.parse_args()

    if args['email']:
      result = db['user'].update_one(
        { 'email': args['email'] },
        { '$set': args},
        upsert=True
      )
      if result.matched_count:
        return jsonify({ 'result': f'user {args["email"]} updated' })
      else:
        return jsonify({ 'error': 'something went wrong' })
    else:
      return jsonify({ 'error': 'must have email' })

class History(Resource):
  def post(self):
    parser = reqparse.RequestParser()
    parser.add_argument('email', type=str)
    parser.add_argument('deviceId', type=str)
    parser.add_argument('title', required=True, help='title(str) is required', type=str)
    args = parser.parse_args()

    if args['title']:
      now = datetime.now()
      today = now.strftime('%Y-%m-%d')
      data = {
        'title': args['title'],
        'timestamp': now
      }

      if args['email']:
        result = db['user'].update_one(
          { 'email': args['email'] },
          { '$push': { f'device.default.{today}': data } },
          upsert=True
        )
      elif args['deviceId']:
        result = db['user'].update_one(
          { f'device.{args["deviceId"]}': { '$exists': True } },
          { '$push': { f'device.{args["deviceId"]}.{today}': data } }
        )
      else:
        return jsonify({ 'error': 'must have email or deviceId' })

      if result.matched_count:
        return jsonify({ 'result': f'{result.matched_count} modified' })
      else:
        return jsonify({ 'error': f'device {args["deviceId"]} did not exist' })
    else:
      return jsonify({ 'error': 'must have title in args' })

class Event(Resource):
  def __init__(self):
    self.parser = reqparse.RequestParser()
    self.parser.add_argument('string', required=True, help='string(dict) is required', type=dict)
    self.parser.add_argument('number', required=True, help='number(dict) is required', type=dict)
    self.parser.add_argument('date', required=True, help='date(dict) is required', type=dict)
    self.parser.add_argument('list', required=True, help='list(dict) is required', type=dict)
    self.string_parser = reqparse.RequestParser()
    self.string_parser.add_argument('establisher', required=True, help='establisher(str) is required', type=str, location='string')
    self.string_parser.add_argument('title', required=True, help='title(str) is required', type=str, location='string')

  def make_doc(self, args, now):
    doc = {}
    doc.update(args['string'])
    doc.update(args['number'])
    doc.update(args['list'])
    doc.update((key, datetime.strptime(value, '%Y-%m-%dT%H:%M:00.000Z')) for key, value in args['date'].items())
    doc['modifyDate'] = now
    return doc

  def update_tags(self, tags, now):
    db['tag'].bulk_write([UpdateOne(
      { 'name': tag },
      {
        '$set': { 'lastUsedDate': now },
        '$setOnInsert': { 'createDate': now }
      },
      upsert=True
    ) for tag in tags])

  #temp
  def get(self):
    data = list(db['event'].find().sort('_id', ASCENDING))
    return jsonify({ 'data': data })

  def post(self):
    args = self.parser.parse_args()
    string_args = self.string_parser.parse_args(req=args)

    if string_args['establisher'] and string_args['title']:
      now = datetime.now()
      doc = self.make_doc(args, now)
      try:
        lastEvent = list(db['event'].find().sort('_id', DESCENDING).limit(1))[0]
        doc['_id'] = lastEvent['_id'] + 1
      except:
        doc['_id'] = 1
      doc['createDate'] = now

      if 'tags' in args['list']:
        self.update_tags(args['list']['tags'], now)

      result = db['event'].insert_one(doc)
      if result.inserted_id:
        return jsonify({ 'result': f'_id {result.inserted_id} inserted' })
      else:
        return jsonify({ 'error': 'something went wrong' })
    else:
      return jsonify({ 'error': 'must have establisher and title in string args' })

  def patch(self):
    self.parser.add_argument('_id', required=True, help='_id(int) is required', type=int)
    args = self.parser.parse_args()
    string_args = self.string_parser.parse_args(req=args)

    if string_args['establisher'] and string_args['title']:
      now = datetime.now()
      doc = self.make_doc(args, now)

      if 'tags' in args['list']:
        self.update_tags(args['list']['tags'], now)

      result = db['event'].update_one({ '_id': args['_id'] }, { '$set': doc })
      if result.modified_count:
        return jsonify({ 'result': f'_id {args["_id"]} updated' })
      else:
        return jsonify({ 'error': 'something went wrong' })
    else:
      return jsonify({ 'error': 'must have establisher and title in string args' })

  def delete(self):
    parser = reqparse.RequestParser()
    parser.add_argument('_id', required=True, help='_id(int) is required', type=int)
    args = parser.parse_args()

    result = db['event'].delete_one(args)
    if result.deleted_count:
      return jsonify({ 'result': f'_id {args["_id"]} deleted' })
    else:
      return jsonify({ 'error': f'_id {args["_id"]} not exist' })

api.add_resource(Device, '/api/device')
api.add_resource(User, '/api/user')
api.add_resource(History, '/api/history')
api.add_resource(Event, '/api/event')

if __name__ == '__main__':
	app.run()
