from datetime import datetime

# import tensorflow_hub as hub
# import tensorflow_text
from flask import Flask, jsonify
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
establisher_db = db['establisher']

def toDate(dateString):
  return datetime.strptime(dateString, '%Y-%m-%dT%H:%M:00.000Z')

class User(Resource):
  def get(self):
    parser = reqparse.RequestParser()
    parser.add_argument('id', required=True, help='id is required', type=str)
    args = parser.parse_args()

    data = user_db.find_one(args['id'])
    if data:
      return jsonify(data)
    else:
      return jsonify({})

  def post(self):
    parser = reqparse.RequestParser()
    parser.add_argument('id', required=True, help='id is required', type=str, location='json')
    parser.add_argument('pageTitle', required=True, help='pageTitle is required', type=str, location='json')
    args = parser.parse_args()

    now = datetime.now()
    user_db.update_one(
      { '_id': args['id'] },
      {
        '$push': {
          f'pageTitles.{now.strftime("%Y-%m-%d")}': {
            'pageTitle': args['pageTitle'],
            # 'encodedPageTitle': embed([args['pageTitle']]).numpy().tolist()[0],
            'timestamp': now
          }
        }
      },
      upsert=True
    )
    return args

class Event(Resource):
  def post(self):
    parser = reqparse.RequestParser()
    parser.add_argument('establisher', required=True, help='establisher is required', type=str, location='json')
    parser.add_argument('title', required=True, help='title is required', type=str, location='json')
    parser.add_argument('url', default=None, type=str, location='json')
    parser.add_argument('description', default=None, type=str, location='json')
    parser.add_argument('startDate', default=None, type=toDate, location='json')
    parser.add_argument('endDate', default=None, type=toDate, location='json')
    parser.add_argument('image', default=None, type=str, location='json')
    parser.add_argument('tags', default=None, action='append', type=str, location='json')
    args = parser.parse_args()

    # find establisher lastEventId
    establisher = establisher_db.find_one({ 'name': args['establisher'] })
    if establisher == None:
      establisher_db.insert_one({
        'name': args['establisher'],
        'lastEventId': 0
      })
      establisher = establisher_db.find_one({ 'name': args['establisher'] })
    lastEventId = establisher['lastEventId'] + 1

    now = datetime.now()
    event_db.update_one(
      { '_id': f'{args["establisher"]}-{lastEventId}' },
      {
        '$set': {
          'establisher': args['establisher'],
          'title': args['title'],
          # 'encodedTitle': embed([args['title']]).numpy().tolist()[0],
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
    establisher_db.update_one({ 'name': args['establisher'] }, { '$set': { 'lastEventId': lastEventId } })
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
                # 'encodedName': embeded.pop(),
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
