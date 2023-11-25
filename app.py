from quart import Quart, request, jsonify, redirect
from motor.motor_asyncio import AsyncIOMotorClient
import string
import random
import os

MONGO_URI = os.getenv('MONGO_URI')
DOMAIN = os.getenv('DOMAIN')

app = Quart(__name__)

# Connect to MongoDB
client = AsyncIOMotorClient(MONGO_URI)
db = client['url_shortener']
collection = db['urls']

async def generate_short_url():
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(5))

async def get_short_code_for_url(original_url):
    link = await collection.find_one({'original_url': original_url})
    return link['short_code'] if link else None

async def get_or_generate_short_url(original_url):
    short_code = await get_short_code_for_url(original_url)
    if short_code:
        return f'{DOMAIN}/{short_code}'
    else:
        new_short_code = await generate_short_url()
        await collection.insert_one({'short_code': new_short_code, 'original_url': original_url})
        return f'{DOMAIN}/{new_short_code}'

@app.route('/')
async def home():
    return "URL Shortener API"

@app.route('/shorten', methods=['POST', 'GET'])
async def shorten_url():
    if request.method == 'POST':
        data = await request.get_json()
        if 'url' in data:
            original_url = data['url']
        else:
            return {'error': 'Missing URL parameter'}, 400
    elif request.method == 'GET':
        original_url = request.args.get('url')
        if not original_url:
            return {'error': 'Missing URL parameter'}, 400
    else:
        return {'error': 'Method not allowed'}, 405

    short_url = await get_or_generate_short_url(original_url)

    return {'short_url': short_url}

@app.route('/<short_code>')
async def redirect_to_original(short_code):
    link = await collection.find_one({'short_code': short_code})

    if link:
        original_url = link['original_url']
        return redirect(original_url)
    else:
        return {'error': 'Short URL not found'}, 404

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080, debug=True)
