from quart import Quart, request, jsonify, redirect, render_template
from motor.motor_asyncio import AsyncIOMotorClient
import string
import random
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

MONGO_URI = os.getenv('MONGO_URI', '')
DATABASE_NAME = os.getenv('DATABASE_NAME', 'urlshortenerdb')
PORT = int(os.getenv('PORT', 8080))
LANDING_PAGE_ENABLED = os.getenv('LANDING_PAGE', 'OFF') == 'ON'

app = Quart(__name__)
client = AsyncIOMotorClient(MONGO_URI)
db = client[DATABASE_NAME]
collection = db.shortened_urls

def generate_short_url(length=6):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

@app.route('/', methods=['GET'])
async def create_url():
    create = request.args.get('create')
    original_url = request.args.get('url')
    
    if create is not None and original_url:
        document = await collection.find_one({"original_url": original_url})
        
        if document:
            return jsonify(original_url=document['original_url'], short_url=document['short_url']), 200

        short_url = generate_short_url()
        await collection.insert_one({"original_url": original_url, "short_url": short_url})

        return jsonify(original_url=original_url, short_url=short_url), 201

    return jsonify(message="Provide a URL to shorten."), 400

@app.route('/<shortened_code>', methods=['GET'])
async def redirect_to_original(shortened_code):
    document = await collection.find_one({"short_url": shortened_code})
    if document:
        original_url = document['original_url']
        if LANDING_PAGE_ENABLED:
            return await render_template('landing_page.html', url=original_url)
        return redirect(original_url)
    return jsonify(error="Shortened URL not found"), 404

@app.route('/revoke/', methods=['DELETE'])
async def revoke_url():
    data = await request.json

    # Fetch the original or short URL from the request
    original_url = data.get('original_url')
    short_url = data.get('short_url')

    if original_url:
        result = await collection.delete_one({"original_url": original_url})
    elif short_url:
        result = await collection.delete_one({"short_url": short_url})
    else:
        return jsonify(message="Provide either the original URL or the short URL to revoke."), 400

    if result.deleted_count > 0:
        return jsonify(message="URL successfully revoked."), 200
    else:
        return jsonify(message="URL not found."), 404


if __name__ == '__main__':
    app.run(port=PORT, debug=True)
