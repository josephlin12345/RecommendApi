import hashlib
import json
from datetime import datetime

from bson.objectid import ObjectId
from flask import Flask
from flask_cors import CORS
from flask_restful import Api, Resource, reqparse
from pymongo import MongoClient

app = Flask(__name__)
cors = CORS(app)
api = Api(app)

client = MongoClient('')
db = client['RecommendationSystem']

def validate(email, password, projection):
  user = db['user'].find_one({ 'email': email }, projection=projection)
  if user:
    if user['password'] == hashlib.sha512(password.encode()).hexdigest():
      return { 'user': user }
    else:
      return { 'error': 'wrong password' }
  else:
    return { 'error': f'email {email} does not exist' }

class SignUp(Resource):
  def post(self):
    parser = reqparse.RequestParser()
    parser.add_argument('email', required=True, type=str)
    parser.add_argument('password', required=True, type=str)
    args = parser.parse_args()
    if not args['email'] or not args['password']:
      return { 'error': 'email and password can not be null' }

    user = db['user'].find_one({ 'email': args['email'] }, projection={})
    if not user:
      now = datetime.now()
      db['user'].insert_one({
        'email': args['email'],
        'password': hashlib.sha512(args['password'].encode()).hexdigest(),
        'name': None,
        'gender': None,
        'birthday': None,
        'modifyDate': now,
        'createDate': now,
        'device': [],
        'history': {},
        'recommend': [list(db['event'].aggregate([{ '$sample': { 'size': 10 }}, { '$project': { '_id': True } }]))]
      })
      return { 'result': f'user {args["email"]} sign up successfully' }
    else:
      return { 'error': f'user {args["email"]} already exist' }

class SignIn(Resource):
  def post(self):
    parser = reqparse.RequestParser()
    parser.add_argument('email', required=True, type=str)
    parser.add_argument('password', required=True, type=str)
    args = parser.parse_args()
    if not args['email'] or not args['password']:
      return { 'error': 'email and password can not be null' }

    result = validate(args['email'], args['password'], { '_id': False, 'password': True })
    if 'user' in result:
      return { 'result': f'user {args["email"]} sign in successfully' }
    else:
      return result

class Profile(Resource):
  def __init__(self):
    self.parser = reqparse.RequestParser()
    self.parser.add_argument('email', required=True, type=str)
    self.parser.add_argument('password', required=True, type=str)

  def get(self):
    args = self.parser.parse_args()
    if not args['email'] or not args['password']:
      return { 'error': 'email and password can not be null' }

    result = validate(args['email'], args['password'], projection={ 'device': False, 'history': False, 'recommend': False })
    if 'user' in result:
      user = result['user']
      user.pop('password')
      return json.loads(json.dumps({ 'result': user }, ensure_ascii=False, default=str))
    else:
      return result

  def patch(self):
    args = self.parser.parse_args()
    if not args['email'] or not args['password']:
      return { 'error': 'email and password can not be null' }

    result = validate(args['email'], args['password'], projection={ '_id': False, 'password': True })
    if 'user' in result:
      self.parser.add_argument('name', type=str)
      self.parser.add_argument('birthday', type=str)
      self.parser.add_argument('gender', type=str)
      self.parser.add_argument('new_password', type=str, nullable=False)
      args = self.parser.parse_args()

      profile = {}
      if args.get('birthday', None):
        try:
          profile['birthday'] = datetime.strptime(args['birthday'], '%Y/%m/%d')
        except:
          profile['birthday'] = None
      if args.get('gender', None):
        valid_gender = ('F', 'M', 'S')
        profile['gender'] = args['gender'] if args['gender'] in valid_gender else None
      if args.get('name', None):
        profile['name'] = args['name']
      if args.get('new_password', None):
        profile['password'] = hashlib.sha512(args['new_password'].encode()).hexdigest()
      profile['modifyDate'] = datetime.now()

      db['user'].update_one({ 'email': args['email'] }, { '$set': profile })
      return { 'result': f'user {args["email"]} profile updated' }
    else:
      return result

class Password(Resource):
  def patch(self):
    parser = reqparse.RequestParser()
    parser.add_argument('email', required=True, type=str)
    parser.add_argument('password', required=True, type=str)
    parser.add_argument('new_password', required=True, type=str)
    args = parser.parse_args()
    if not args['email'] or not args['password'] or not args['new_password']:
      return { 'error': 'email, password and new_password can not be null' }

    result = validate(args['email'], args['password'], projection={ '_id': False, 'password': True })
    if 'user' in result:
      password = hashlib.sha512(args['new_password'].encode()).hexdigest()
      db['user'].update_one({ 'email': args['email'] }, { '$set': { 'password': password } })
      return { 'result': f'user {args["email"]} password changed' }
    else:
      return result

class Device(Resource):
  def __init__(self):
    self.parser = reqparse.RequestParser()
    self.parser.add_argument('email', required=True, type=str)
    self.parser.add_argument('password', required=True, type=str)

  def get(self):
    args = self.parser.parse_args()
    if not args['email'] or not args['password']:
      return { 'error': 'email and password can not be null' }

    result = validate(args['email'], args['password'], projection={ '_id': False, 'password': True })
    if 'user' in result:
      user = db['user'].find_one({ 'email': args['email'] }, projection={ '_id': False, 'device': True })
      return { 'result': user }
    else:
      return result

  def post(self):
    self.parser.add_argument('deviceId', required=True, type=str)
    args = self.parser.parse_args()
    if not args['email'] or not args['password'] or not args['deviceId']:
      return { 'error': 'email, password and deviceId can not be null' }

    result = validate(args['email'], args['password'], projection={ '_id': False, 'password': True })
    if 'user' in result:
      user = db['user'].find_one({ 'device': args['deviceId'] }, projection={})
      if not user:
        db['user'].update_one({ 'email': args['email'] }, { '$push': { 'device': args['deviceId'] } })
        return { 'result': f'device {args["deviceId"]} combined with user {args["email"]}' }
      else:
        return { 'error': f'device {args["deviceId"]} has been registered' }
    else:
      return result

  def patch(self):
    self.parser.add_argument('deviceId', type=str, action='append', default=[])
    args = self.parser.parse_args()
    if not args['email'] or not args['password']:
      return { 'error': 'email and password can not be null' }

    result = validate(args['email'], args['password'], projection={ '_id': False, 'password': True, 'device': True })
    if 'user' in result:
      for _id in args['deviceId']:
        if _id not in result['user']['device']:
          return { 'error': 'You can only remove your own device' }
      db['user'].update_one({ 'email': args['email'] }, { '$set': { 'device': args['deviceId'] } })
      return { 'result': f'user {args["email"]} device updated' }
    else:
      return result

  def delete(self):
    args = self.parser.parse_args()
    if not args['email'] or not args['password']:
      return { 'error': 'email and password can not be null' }

    result = validate(args['email'], args['password'], projection={ '_id': False, 'password': True })
    if 'user' in result:
      db['user'].update_one({ 'email': args['email'] }, { '$set': { 'device': [] } })
      return { 'result': f'user {args["email"]} device reset' }
    else:
      return result

class Recommend(Resource):
  def get(self):
    parser = reqparse.RequestParser()
    parser.add_argument('email', required=True, type=str)
    parser.add_argument('password', required=True, type=str)
    parser.add_argument('offset', required=True, type=int)
    parser.add_argument('limit', required=True, type=int)
    args = parser.parse_args()
    if not args['email'] or not args['password']:
      return { 'error': 'email and password can not be null' }
    if args['offset'] < 0:
      args['offset'] = 0
    if args['limit'] > 100:
      args['limit'] = 100
    elif args['limit'] < 1:
      args['limit'] = 1

    result = validate(args['email'], args['password'], projection={ '_id': False, 'password': True, 'recommend': True })
    if 'user' in result:
      user = result['user']
      correspond = { recommend['_id']: recommend['score'] for recommend in user['recommend'][args['offset']: args['offset'] + args['limit']] }
      events = db['event'].find({ '_id': { '$in': list(correspond.keys()) } })
      result = [{ 'event': event, 'score': correspond[event['_id']] } for event in events]
      result.sort(key=lambda e: e['score'], reverse=True)
      return json.loads(json.dumps({ 'result': result }, ensure_ascii=False, default=str))
    else:
      return result

class History(Resource):
  def post(self):
    parser = reqparse.RequestParser()
    parser.add_argument('email', type=str)
    parser.add_argument('password', type=str)
    parser.add_argument('deviceId', type=str)
    parser.add_argument('title', required=True, type=str)
    args = parser.parse_args()
    if ((not args['email'] or not args['password']) and not args['deviceId']) or not args['title']:
      return { 'error': '(email + password)/deviceId and title can not be null' }

    result = validate(args['email'], args['password'], projection={ '_id': False, 'password': True })
    if 'user' in result:
      now = datetime.now()
      today = now.strftime('%Y-%m-%d')
      data = {
        'title': args['title'],
        'timestamp': now
      }
      if args['email']:
        query = { 'email': args['email'] }
      elif args['deviceId']:
        query = { 'device': args['deviceId'] }

      result = db['user'].update_one(query, { '$push': { f'history.{today}': data } })
      if result.matched_count:
        return { 'result': f'device/email {args["deviceId"]}/{args["email"]} updated' }
      else:
        return { 'error': f'device/email {args["deviceId"]}/{args["email"]} does not exist' }
    else:
      return result

class Event(Resource):
  def __init__(self):
    self.parser = reqparse.RequestParser()
    self.parser.add_argument('email', required=True, type=str)
    self.parser.add_argument('password', required=True, type=str)
    self.parser.add_argument('content', required=True, type=dict)
    self.content_parser = reqparse.RequestParser()
    self.content_parser.add_argument('title', required=True, type=str, location='content')
    self.content_parser.add_argument('image', required=True, type=str, location='content')
    self.content_parser.add_argument('detail', required=True, type=str, location='content')
    self.content_parser.add_argument('organizer', required=True, type=str, location='content')
    self.content_parser.add_argument('url', required=True, type=str, location='content')
    self.content_parser.add_argument('date', type=dict, location='content')

  def get(self):
    parser = reqparse.RequestParser()
    parser.add_argument('type', type=str)
    args = parser.parse_args()

    if args.get('type', None) == 'single':
      parser.add_argument('_id', required=True, type=ObjectId)
      args = parser.parse_args()

      result = db['event'].find_one(args['_id'])
    else:
      parser.add_argument('offset', required=True, type=int)
      parser.add_argument('limit', required=True, type=int)
      parser.add_argument('sort', type=str)
      parser.add_argument('order', type=int)
      parser.add_argument('q', type=str)
      if args.get('type', None) == 'user':
        parser.add_argument('email', required=True, type=str)
      args = parser.parse_args()

      if args['offset'] < 0:
        args['offset'] = 0
      if args['limit'] > 100:
        args['limit'] = 100
      elif args['limit'] < 1:
        args['limit'] = 1
      if not args.get('sort', None):
        args['sort'] = '_id'
      if not args.get('order', None) or (args['order'] != 1 and args['order'] != -1):
        args['order'] = 1

      query = {}
      if args.get('q', None):
        query['$text'] = { '$search': args['q'], '$language': 'none' }
      if args.get('type', None) == 'user':
        query['establisher'] = args['email']

      result = list(db['event'].find(query).sort(args['sort'], args['order']).skip(args['offset']).limit(args['limit']))
    return json.loads(json.dumps({ 'result': result }, ensure_ascii=False, default=str))

  def post(self):
    args = self.parser.parse_args()
    content_args = self.content_parser.parse_args(req=args)
    args['content'].update(content_args)
    if not args['email'] or not args['password'] or not args['content']['title']:
      return { 'error': 'email, password and content.title can not be null' }
    if not args['content']['url'].startswith('http://') and not args['content']['url'].startswith('https://'):
      return { 'error': 'content.url must start with http:// or https://' }
    if not args['content']['image'].startswith('http://') and not args['content']['image'].startswith('https://'):
      return { 'error': 'content.image must start with http:// or https://' }

    result = validate(args['email'], args['password'], projection={ '_id': False, 'password': True })
    if 'user' in result:
      args['establisher'] = args.pop('email')
      args.pop('password')
      args.pop('unparsed_arguments')
      now = datetime.now()
      args['modifyDate'] = now
      args['createDate'] = now
      if args['content'].get('date', None):
        for k, v in args['content'].pop('date').items():
          try:
            args['content'][k] = datetime.strptime(v, '%Y-%m-%dT%H:%M:00.000Z')
          except:
            pass

      db['event'].insert_one(args)
      return { 'result': f'event {args["content"]["title"]} inserted' }
    else:
      return result

  def patch(self):
    self.parser.add_argument('_id', required=True, type=ObjectId)
    args = self.parser.parse_args()
    content_args = self.content_parser.parse_args(req=args)
    args['content'].update(content_args)
    if not args['email'] or not args['password'] or not args['content']['title']:
      return { 'error': 'email, password and content.title can not be null' }
    if not args['content']['url'].startswith('http://') and not args['content']['url'].startswith('https://'):
      return { 'error': 'content.url must start with http:// or https://' }
    if not args['content']['image'].startswith('http://') and not args['content']['image'].startswith('https://'):
      return { 'error': 'content.image must start with http:// or https://' }

    result = validate(args['email'], args['password'], projection={ '_id': False, 'password': True })
    if 'user' in result:
      event = db['event'].find_one(args['_id'])
      if event:
        if event['establisher'] == args['email']:
          if args['content'].get('date', None):
            for k, v in args['content'].pop('date').items():
              try:
                args['content'][k] = datetime.strptime(v, '%Y-%m-%dT%H:%M:00.000Z')
              except:
                pass

          db['event'].update_one({ '_id': args['_id'] }, { '$set': { 'content': args['content'], 'modifyDate': datetime.now() } })
          return { 'result': f'event {args["content"]["title"]} updated' }
        else:
          return { 'error': 'You do not have permission to modify this event.' }
      else:
        return { 'error': f'event {args["_id"]} does not exist' }
    else:
      return result

  def delete(self):
    parser = reqparse.RequestParser()
    parser.add_argument('email', required=True, type=str)
    parser.add_argument('password', required=True, type=str)
    parser.add_argument('_id', required=True, type=ObjectId)
    args = parser.parse_args()
    if not args['email'] or not args['password']:
      return { 'error': 'email and password can not be null' }

    result = validate(args['email'], args['password'], projection={ '_id': False, 'password': True })
    if 'user' in result:
      event = db['event'].find_one(args['_id'])
      if event:
        if event['establisher'] == args['email']:
          db['event'].delete_one({ '_id': args['_id'] })
          return { 'result': f'event id {args["_id"]} deleted' }
        else:
          return { 'error': 'You do not have permission to delete this event.' }
      else:
        return { 'error': f'event id {args["_id"]} does not exist' }
    else:
      return result

api.add_resource(SignUp, '/api/sign_up')
api.add_resource(SignIn, '/api/sign_in')
api.add_resource(Profile, '/api/profile')
api.add_resource(Password, '/api/password')
api.add_resource(Device, '/api/device')
api.add_resource(Recommend, '/api/recommend')
api.add_resource(History, '/api/history')
api.add_resource(Event, '/api/event')

if __name__ == '__main__':
  app.run()
