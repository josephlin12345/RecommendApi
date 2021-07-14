from datetime import datetime

# import tensorflow_hub as hub
# import tensorflow_text
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_restful import Api, Resource, reqparse
from pymongo import MongoClient, UpdateOne

# load sentence encoder
# url = 'universal-sentence-encoder-multilingual-large_3'
# embed = hub.load(url)

# init app
app = Flask(__name__)
cors = CORS(app)
api = Api(app)

# init db
client = MongoClient('mongodb+srv://api:gPdCEpVRVWuOnGqp@cluster0.xgkp9.mongodb.net/?ssl=true&ssl_cert_reqs=CERT_NONE&retryWrites=true&w=majority')
db = client['recommended_system']
user_db = db['user']
tag_db = db['tag']
event_db = db['event']

@app.route('/', methods=['GET'])
def index():
  parser = reqparse.RequestParser()
  parser.add_argument('id', required=True, help='id is required', type=str)
  id = parser.parse_args()['id']
  data = user_db.find_one(id)
  if data:
    return jsonify(data)
  else:
    return jsonify({})

class User(Resource):
  def __init__(self):
    self.parser = reqparse.RequestParser()
    self.parser.add_argument('id', required=True, help='id is required', type=str, location='json')
    self.parser.add_argument('pageTitle', required=True, help='pageTitle is required', type=str, location='json')

  def post(self):
    args = self.parser.parse_args()
    now = datetime.now()
    user_db.update_one(
      { '_id': args['id'] },
      {
        '$push': {
          f'pageTitles.{now.strftime("%Y-%m-%d")}': {
            'pageTitle': args['pageTitle'],
            'timestamp': now
          }
        }
      },
      upsert=True
    )
    return args

def toDate(dateString):
  return datetime.fromisoformat(dateString)# need convert

class Event(Resource):
  def __init__(self):
    self.parser = reqparse.RequestParser()
    self.parser.add_argument('id', required=True, help='id is required', type=str, location='json')
    self.parser.add_argument('author', required=True, help='author is required', type=str, location='json')
    self.parser.add_argument('title', required=True, help='title is required', type=str, location='json')
    self.parser.add_argument('url', default=None, type=str, location='json')
    self.parser.add_argument('description', default=None, type=str, location='json')
    self.parser.add_argument('startDate', default=None, type=toDate, location='json')
    self.parser.add_argument('endDate', default=None, type=toDate, location='json')
    self.parser.add_argument('image', default=None, type=str, location='json')
    self.parser.add_argument('tags', default=None, action='append', type=str, location='json')

  def post(self):
    args = self.parser.parse_args()
    now = datetime.now()
    event_db.update_one(
      { '_id': f'{args["author"]}-{args["id"]}' },
      {
        '$set': {
          'author': args['author'],
          'title': args['title'],
          # 'encoded_title': embed([args['title']]).numpy().tolist()[0],
          'url': args['url'],
          'description': args['description'],
          'startDate': args['startDate'],
          'endDate': args['endDate'],
          'image': args['image'],
          'tags': args['tags'],
          'modifyDate': now
        },
        '$setOnInsert': {
          'createDate': now
        }
      },
      upsert=True
    )
    if args['tags']:
      bulk_requests = []
      # embeded = embed(args['tags']).numpy().tolist().reverse()
      for tag in args['tags']:
        bulk_requests.append(
          UpdateOne(
            { 'name': tag },
            {
              '$set': {
                'lastUsedDate': now
              },
              '$setOnInsert': {
                # 'encoded_name': embeded.pop(),
                'createDate': now
              }
            },
            upsert=True
          )
        )
      tag_db.bulk_write(bulk_requests)

api.add_resource(User, '/api/user')
api.add_resource(Event, '/api/event')

if __name__ == '__main__':
	app.run()
