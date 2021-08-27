import json
from datetime import datetime

from bson.objectid import ObjectId
from flask import Flask
from flask_cors import CORS
from flask_restful import Api, Resource, reqparse
from pymongo import DESCENDING, MongoClient, UpdateOne

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
    parser.add_argument('email', required=True, type=str)
    parser.add_argument('deviceId', required=True, type=str)
    args = parser.parse_args()

    if args['email']:
      user = db['user'].find_one({ 'device': args['deviceId'] }, projection={})
      if not user:
        now = datetime.now()
        result = db['user'].update_one(
          { 'email': args['email'] },
          {
            '$push': { 'device': args['deviceId'] },
            '$setOnInsert': {
              'createDate': now,
              'modifyDate': now
            }
          },
          upsert=True
        )
        if result.matched_count or result.upserted_id:
          return { 'result': f'device {args["deviceId"]} registered' }
        else:
          return { 'error': 'something went wrong' }
      else:
        return { 'result': f'device {args["deviceId"]} has been registered' }
    else:
      return { 'error': 'need email' }

class User(Resource):
  def __init__(self):
    self.parser = reqparse.RequestParser()
    self.parser.add_argument('email', required=True, type=str)

  def get(self):
    args = self.parser.parse_args()

    if args['email']:
      user = db['user'].find_one(args, projection={ 'device': False, 'history': False, 'recommend': False })
      if user:
        return json.loads(json.dumps({ 'user': user }, ensure_ascii=False, default=str))
      else:
        return { 'error': f'user {args["email"]} does not exist' }
    else:
      return { 'error': 'need email or deviceId' }

  def post(self):
    self.parser.add_argument('name', type=str)
    self.parser.add_argument('birthday', type=str)
    self.parser.add_argument('gender', type=str)
    args = self.parser.parse_args()

    if args['email']:
      now = datetime.now()
      args['modifyDate'] = now
      result = db['user'].update_one(
        { 'email': args['email'] },
        {
          '$set': args,
          '$setOnInsert': { 'createDate': now }
        },
        upsert=True
      )
      if result.matched_count or result.upserted_id:
        return { 'result': f'user {args["email"]} updated' }
      else:
        return { 'error': 'something went wrong' }
    else:
      return { 'error': 'need email' }

class History(Resource):
  def post(self):
    parser = reqparse.RequestParser()
    parser.add_argument('email', type=str)
    parser.add_argument('deviceId', type=str)
    parser.add_argument('title', required=True, type=str)
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
          {
            '$push': { f'history.{today}': data },
            '$setOnInsert': {
              'createDate': now,
              'modifyDate': now
            }
          },
          upsert=True
        )
      elif args['deviceId']:
        result = db['user'].update_one(
          { 'device': args['deviceId'] },
          { '$push': { f'history.{today}': data } }
        )
      else:
        return { 'error': 'need email or deviceId' }

      if result.matched_count or result.upserted_id:
        return { 'result': f'{result.matched_count} modified' }
      else:
        return { 'error': f'device {args["deviceId"]} does not exist' }
    else:
      return { 'error': 'need title in args' }

class Event(Resource):
  def __init__(self):
    self.parser = reqparse.RequestParser()
    self.parser.add_argument('info', required=True, type=dict)
    self.parser.add_argument('date', type=dict)
    self.info_parser = reqparse.RequestParser()
    self.info_parser.add_argument('establisher', required=True, type=str, location='info')
    self.info_parser.add_argument('title', required=True, type=str, location='info')

  def make_doc(self, args):
    doc = {}
    doc.update(args['info'])
    if 'date' in doc:
      doc.update((key, datetime.strptime(value, '%Y-%m-%dT%H:%M:00.000Z')) for key, value in args['date'].items())
    doc['modifyDate'] = self.now
    return doc

  def update_tags(self, tags):
    db['tag'].bulk_write([UpdateOne(
      { 'name': tag },
      {
        '$set': { 'lastUsedDate': self.now },
        '$setOnInsert': { 'createDate': self.now }
      },
      upsert=True
    ) for tag in tags])

  def get(self):
    events = list(db['event'].find().sort('modifyDate', DESCENDING))
    return json.loads(json.dumps({ 'events': events }, ensure_ascii=False, default=str))

  def post(self):
    args = self.parser.parse_args()
    info_args = self.info_parser.parse_args(req=args)

    if info_args['establisher'] and info_args['title']:
      self.now = datetime.now()
      doc = self.make_doc(args)
      doc['createDate'] = self.now

      if 'tags' in args['info'] and isinstance(args['info']['tags'], list):
        self.update_tags(args['info']['tags'])

      result = db['event'].insert_one(doc)
      if result.inserted_id:
        return { 'result': f'_id {result.inserted_id} inserted' }
      else:
        return { 'error': 'something went wrong' }
    else:
      return { 'error': 'need establisher and title in string args' }

  def patch(self):
    self.parser.add_argument('_id', required=True, type=ObjectId)
    args = self.parser.parse_args()
    info_args = self.info_parser.parse_args(req=args)

    if info_args['establisher'] and info_args['title']:
      self.now = datetime.now()
      doc = self.make_doc(args)

      if 'tags' in args['info'] and isinstance(args['info']['tags'], list):
        self.update_tags(args['info']['tags'])

      result = db['event'].update_one({ '_id': args['_id'] }, { '$set': doc })
      if result.matched_count:
        return { 'result': f'_id {args["_id"]} updated' }
      else:
        return { 'error': f'_id {args["_id"]} does not exist' }
    else:
      return { 'error': 'need establisher and title in string args' }

  def delete(self):
    parser = reqparse.RequestParser()
    parser.add_argument('_id', required=True, type=ObjectId)
    args = parser.parse_args()

    result = db['event'].delete_one(args)
    if result.deleted_count:
      return { 'result': f'_id {args["_id"]} deleted' }
    else:
      return { 'error': f'_id {args["_id"]} does not exist' }

class Recommend(Resource):
  def get(self):
    parser = reqparse.RequestParser()
    parser.add_argument('email', required=True, type=str)
    args = parser.parse_args()

    if args['email']:
      user = db['user'].find_one({ 'email': args['email'] }, projection={ 'recommend': True })
      if user:
        if 'recommend' in user:
          correspond = { recommend['_id']: recommend['score'] for recommend in user['recommend'] }
          events = db['event'].find({ '_id': { '$in': list(correspond.keys()) } })
          recommend = [{ 'event': event, 'score': correspond[event['_id']] } for event in events]
          recommend.sort(key=lambda e: e['score'], reverse=True)
          return json.loads(json.dumps(recommend, ensure_ascii=False, default=str))
        else:
          return { 'error': 'recommend did not update' }
      else:
        return { 'error': f'user {args["email"]} does not exist' }
    else:
      return { 'error': 'need email' }

api.add_resource(Device, '/api/device')
api.add_resource(User, '/api/user')
api.add_resource(History, '/api/history')
api.add_resource(Event, '/api/event')
api.add_resource(Recommend, '/api/recommend')

if __name__ == '__main__':
	app.run()
