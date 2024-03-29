from datetime import datetime
from threadpool import ThreadPool

import json
import pymongo
import requests
import time
import traceback

pool = ThreadPool(5)

db = pymongo.Connection().novena
username = 'lunixbochs'

def get_difficulty():
    try:
        response = requests.get('http://novena-puzzle.crowdsupply.com/difficulty')
        return response.json().get('difficulty')
    except Exception:
        traceback.print_exc()

@pool
def submit(h):
    try:
        response = requests.post('http://novena-puzzle.crowdsupply.com/submit', data=json.dumps({
            'username': username, 'contents': h['contents'],
        }))
        if response.status_code == 502:
            response = False
        else:
            response = response.json()
    except Exception:
        traceback.print_exc()
        response = None
    db.hashes.update({'_id': h['_id']}, {'$set': {'response': response, 'submitted': True}})

difficulty = get_difficulty()
try:
    highest = max(difficulty, db.hashes.difficulty.find().sort('difficulty', -1)[0]).get('difficulty')
except Exception:
    highest = difficulty
    traceback.print_exc()

print 'difficulty:', difficulty
print 'highest:', highest
while True:
    for i in xrange(30):
        hashes = list(db.hashes.find({'bits': {'$lte': highest, '$gte': difficulty}, 'submitted': {'$exists': False}}))
        for h in hashes:
            print 'submitting: "%s":' % h['contents'],
            try:
                response = submit(h)
                db.hashes.update({'_id': h['_id']}, {'$set': {'response': response, 'submitted': True}})
                print response
            except Exception:
                traceback.print_exc()
        time.sleep(1)
    new_diff = get_difficulty()
    if new_diff != difficulty:
        highest = max(new_diff, difficulty)
        difficulty = new_diff
        print 'difficulty changed:', new_diff
        print 'highest difficulty:', highest
        db.hashes.difficulty.insert({'time': datetime.now(), 'difficulty': difficulty})
