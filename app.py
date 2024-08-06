from quart import Quart, request, render_template, redirect
from motor.motor_asyncio import AsyncIOMotorClient
import random, os, string

app = Quart(__name__)

# MongoDB connection
client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
db = client.link_shortener
links_collection = db.links

# List of whitespace characters to use for short codes
WHITESPACE_CHARS = [
    '\u0020',  # Space
    '\u00A0',  # No-Break Space
    '\u1680',  # Ogham Space Mark
    '\u2000',  # En Quad
    '\u2001',  # Em Quad
    '\u2002',  # En Space
    '\u2003',  # Em Space
    '\u2004',  # Three-Per-Em Space
    '\u2005',  # Four-Per-Em Space
    '\u2006',  # Six-Per-Em Space
    '\u2007',  # Figure Space
    '\u2008',  # Punctuation Space
    '\u2009',  # Thin Space
    '\u200A',  # Hair Space
    '\u202F',  # Narrow No-Break Space
    '\u205F',  # Medium Mathematical Space
    '\u3000',  # Ideographic Space
]

# Generate a random whitespace short code
def generate_short_code(length=8):
    return ''.join(random.choice(WHITESPACE_CHARS) for _ in range(length))

async def get_unique_short_code():
    while True:
        short_code = generate_short_code()
        existing_link = await links_collection.find_one({"short_code": short_code})
        if not existing_link:
            return short_code

@app.route("/", methods=["GET", "POST"])
async def index():
    if request.method == "POST":
        form = await request.form
        original_url = form.get("url")
        
        # Check if the original URL already exists in the database
        existing_link = await links_collection.find_one({"original_url": original_url})
        
        if existing_link:
            short_code = existing_link["short_code"]
        else:
            # Generate a unique whitespace short code
            short_code = await get_unique_short_code()
            
            # Store the link in the database
            await links_collection.insert_one({
                "original_url": original_url,
                "short_code": short_code
            })
        
        short_url = request.host_url + short_code
        return await render_template("index.html", short_url=short_url, short_code=short_code)
    
    return await render_template("index.html")

@app.route("/<path:short_code>")
async def redirect_to_url(short_code):
    link = await links_collection.find_one({"short_code": short_code})
    if link:
        return redirect(link["original_url"])
    return "Link not found", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=os.getenv("PORT", 8080))
