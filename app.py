from quart import Quart, request, jsonify, redirect, render_template
from motor.motor_asyncio import AsyncIOMotorClient
import string
import random
import os
import datetime

MONGO_URI = os.getenv('MONGO_URI')
DATABASE_NAME = os.getenv('DATABASE_NAME', 'urlshortenerdb')
PORT = int(os.getenv('PORT', 8080))
LANDING_PAGE_ENABLED = os.getenv('LANDING_PAGE', 'OFF') == 'ON'
TIMER_ENABLED = os.getenv('TIMER_ENABLED', 'OFF') == 'ON'
TIMER_SECONDS = int(os.getenv('TIMER_SECONDS', 5))

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
    
    # Dynamically determine the domain
    protocol = 'https' if request.scheme == 'https' else 'http'
    domain = f"{protocol}://{request.headers.get('host', 'localhost')}"
    
    if create is not None and original_url:
        document = await collection.find_one({"original_url": original_url})
        
        if document:
            formatted_short_url = f"{domain}/{document['short_url']}"
            return jsonify(original_url=document['original_url'], short_url=formatted_short_url), 200

        short_url_code = generate_short_url()
        await collection.insert_one({
            "original_url": original_url,
            "short_url": short_url_code,
            "creation_time": datetime.datetime.utcnow(),
            "views": 0
        })

        formatted_short_url = f"{domain}/{short_url_code}"
        return jsonify(original_url=original_url, short_url=formatted_short_url), 201

    return jsonify(message="Provide a URL to shorten."), 400


@app.route('/<shortened_code>', methods=['GET'])
async def redirect_to_original(shortened_code):
    document = await collection.find_one({"short_url": shortened_code})
    if document:
        await collection.update_one({"short_url": shortened_code}, {"$inc": {"views": 1}})
        original_url = document['original_url']
        if LANDING_PAGE_ENABLED:
            return await render_template(
                'landing_page.html',
                url=original_url,
                views=document["views"] + 1,  # Increment views for immediate display
                creation_time=document["creation_time"],
                timer_enabled=TIMER_ENABLED,
                timer_seconds=TIMER_SECONDS
            )
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
    app.run(host="0.0.0.0", port=PORT, debug=True)
