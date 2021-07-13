from datetime import datetime

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_restful import Api, Resource, reqparse
from pymongo import MongoClient

# init app
app = Flask(__name__)
cors = CORS(app)
api = Api(app)

parser = reqparse.RequestParser()
parser.add_argument('id', required=True, help='id is required')
parser.add_argument('page_title', required=True, help='page_title is required')
parser.add_argument('timestamp', required=True, help='timestamp is required', type=float)

# init db
client = MongoClient('mongodb+srv://api:gPdCEpVRVWuOnGqp@cluster0.xgkp9.mongodb.net/?ssl=true&ssl_cert_reqs=CERT_NONE&retryWrites=true&w=majority')
db = client['recommended_system']
collection = db['user']

@app.route('/', methods=['GET'])
def index():
  data = collection.find_one(request.values['id'])
  if data:
    return jsonify(data)
  else:
    return jsonify({})

class Api(Resource):
  def post(self):
    args = parser.parse_args()
    date = datetime.fromtimestamp(args['timestamp'] / 1000)
    collection.update_one(
      { '_id': args['id'] },
      {
        '$push': {
          f'page_titles.{date.strftime("%Y-%m-%d")}': {
            'page_title': args['page_title'],
            'timestamp': date
          }
        }
      },
      upsert=True
    )
    return args

api.add_resource(Api, '/api')

if __name__ == '__main__':
	app.run()
