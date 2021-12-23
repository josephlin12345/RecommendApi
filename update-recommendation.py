import math
import time
from datetime import datetime, timedelta

import numpy as np
import tensorflow_hub as hub
import tensorflow_text
from pymongo import MongoClient

url = 'https://tfhub.dev/google/universal-sentence-encoder-multilingual-large/3'
embed = hub.load(url)
client = MongoClient('mongodb+srv://server:4IRLAFt0jrZB5giN@cluster0.xgkp9.mongodb.net/?ssl=true&ssl_cert_reqs=CERT_NONE&retryWrites=true&w=majority')
db = client['RecommendationSystem']

def update_recommend():
  events = list(db['event'].find(projection={ 'content.title': True }))
  events_embeddings = embed([event['content']['title'] for event in events])
  batch_size = 100
  events_embeddings_batches = [events_embeddings[i * batch_size: (i + 1) * batch_size] for i in range(math.ceil(len(events_embeddings) / batch_size))]

  now = datetime.now()
  users = list(db['user'].find(projection={ f'history.{(now - timedelta(day)).strftime("%Y-%m-%d")}': True for day in range(7) }))

  for user in users:
    history = [history['title'] for day in user['history'].values() for history in day][:100]
    if len(history):
      history_embeddings = embed(history)
      scores = []

      for events_embeddings in events_embeddings_batches:
        scores.extend([sum(similarity) for similarity in np.inner(events_embeddings, history_embeddings)])
      recommend = [{ '_id': event['_id'], 'score': score } for score, event in sorted(zip(scores, events), key=lambda x: x[0], reverse=True)[:10]]
      db['user'].update_one({ '_id': user['_id'] }, { '$set': { 'recommend': recommend } })
      print(f'user {user["_id"]} recommend updated')

while True:
  update_recommend()
  time.sleep(86400)
