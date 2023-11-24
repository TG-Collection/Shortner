from quart import Quart, request, jsonify, redirect
from motor.motor_asyncio import AsyncIOMotorClient
import string
import random
import os


MONGO_URI = os.getenv('MONGO_URI')


app = Quart(__name__)

# Connect to MongoDB
client = AsyncIOMotorClient(MONGO_URI)
db = client['url_shortener']
collection = db['urls']

def generate_short_url():
    characters = string.ascii_letters + string.digits
    while True:
        short_url = ''.join(random.choice(characters) for _ in range(5))
        existing_link = await collection.find_one({'short_url': short_url})
        if not existing_link:
            return short_url

@app.route('/')
async def home():
    return "URL Shortener API"

@app.route('/shorten', methods=['POST'])
async def shorten_url():
    data = await request.get_json()

    if 'url' in data:
        original_url = data['url']
    elif 'url' in request.args:
        original_url = request.args['url']
    else:
        return {'error': 'Missing URL parameter'}, 400

    short_url = await generate_short_url()

    await collection.insert_one({'short_url': short_url, 'original_url': original_url})

    return {'short_url': short_url}

@app.route('/<short_url>')
async def redirect_to_original(short_url):
    link = await collection.find_one({'short_url': short_url})

    if link:
        original_url = link['original_url']
        return redirect(original_url)
    else:
        return {'error': 'Short URL not found'}, 404


if __name__ == '__main__':
    app.run(host="0.0.0.0", port="8080", debug=True)
