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
user_collection = db['user']
event_collection = db['event']
tag_collection = db['tag']

def toDate(dateString):
  return datetime.strptime(dateString, '%Y-%m-%dT%H:%M:00.000Z')

class User(Resource):
  def __init__(self):
    self.parser = reqparse.RequestParser()
    self.parser.add_argument('_id', required=True, help='_id(str) is required', type=str)

  # temp
  def get(self):
    args = self.parser.parse_args()

    data = user_collection.find_one(args['_id'])
    if data:
      return jsonify({ 'data': data })
    else:
      return jsonify({ 'error': f'_id {args["_id"]} not exist' })

  def post(self):
    self.parser.add_argument('pageTitle', required=True, help='pageTitle(str) is required', type=str)
    args = self.parser.parse_args()

    now = datetime.now()
    result = user_collection.update_one(
      { '_id': args['_id'] },
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
    if result.modified_count or result.upserted_id:
      return jsonify({ 'result': f'_id {args["_id"]} updated' })
    else:
      return jsonify({ 'error': 'something went wrong' })

class Event(Resource):
  def __init__(self):
    self.parser = reqparse.RequestParser()
    self.parser.add_argument('establisher', required=True, help='establisher(str) is required', type=str)
    self.parser.add_argument('title', required=True, help='title(str) is required', type=str)
    self.parser.add_argument('url', help='url(str)', type=str)
    self.parser.add_argument('description', help='description(str)', type=str)
    self.parser.add_argument('startDate', help='%Y-%m-%dT%H:%M:00.000Z', type=toDate)
    self.parser.add_argument('endDate', help='%Y-%m-%dT%H:%M:00.000Z', type=toDate)
    self.parser.add_argument('image', help='image(str)', type=str)
    self.parser.add_argument('tags', help='tags(list of str)', action='append', type=str)

  # temp
  def get(self):
    data = list(event_collection.find().sort('_id', ASCENDING))
    return jsonify({ 'data': data })

  def post(self):
    args = self.parser.parse_args()

    # find lastEventId
    try:
      lastEvent = list(event_collection.find().sort('_id', DESCENDING).limit(1))[0]
      lastEventId = lastEvent['_id']
    except:
      lastEventId = 0

    now = datetime.now()
    doc = args
    doc['_id'] = lastEventId + 1
    doc['modifyDate'] = now
    doc['createDate'] = now
    result = event_collection.insert_one(doc)
    if result.inserted_id:
      return jsonify({ 'result': f'_id {result.inserted_id} inserted' })
    else:
      return jsonify({ 'error': 'something went wrong' })

  def patch(self):
    self.parser.add_argument('_id', required=True, help='_id(int) is required', type=int)
    args = self.parser.parse_args()

    now = datetime.now()
    doc = { arg: value for arg, value in args.items() if value != None}
    doc['modifyDate'] = now
    result = event_collection.find_one_and_update({ '_id': args['_id'] }, { '$set': doc })
    if result:
      return jsonify({ 'result': f'_id {args["_id"]} updated' })
    else:
      return jsonify({ 'error': f'_id {args["_id"]} not exist' })

  def delete(self):
    parser = reqparse.RequestParser()
    parser.add_argument('_id', required=True, help='_id(int) is required', type=int)
    args = parser.parse_args()

    result = event_collection.delete_one({ '_id': args['_id'] })
    if result.deleted_count:
      return jsonify({ 'result': f'_id {args["_id"]} deleted' })
    else:
      return jsonify({ 'error': f'_id {args["_id"]} not exist' })

class Tag(Resource):
  def post(self):
    parser = reqparse.RequestParser()
    parser.add_argument('tags', required=True, help='tags(list of str) is required', action='append', type=str)
    args = parser.parse_args()

    now = datetime.now()
    result = tag_collection.bulk_write([UpdateOne(
      { 'name': tag },
      {
        '$set': { 'lastUsedDate': now },
        '$setOnInsert': { 'createDate': now }
      },
      upsert=True
    ) for tag in args['tags']])
    if result.modified_count or result.upserted_count:
      return jsonify({ 'result': f'{result.modified_count} tags updated & {result.upserted_count} tags inserted' })
    else:
      return jsonify({ 'error': 'something went wrong' })

api.add_resource(User, '/api/user')
api.add_resource(Event, '/api/event')
api.add_resource(Tag, '/api/tag')

if __name__ == '__main__':
	app.run(debug=True)
