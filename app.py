from quart import Quart, request, render_template, redirect
from motor.motor_asyncio import AsyncIOMotorClient
import random

app = Quart(__name__)

# MongoDB connection
client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client.link_shortener
links_collection = db.links

# List of emojis to use for short codes
EMOJIS = [
    "😀", "😃", "😄", "😁", "😆", "😅", "😂", "🤣", "😊", "😇", "🙂", "🙃", "😉", "😌", "😍", "🥰", "😘", "😗", "😙",
    "😚", "😋", "😛", "😝", "😜", "🤪", "🤨", "🧐", "🤓", "😎", "🤩", "🥳", "😏", "😒", "😞", "😔", "😟", "😕", "🙁",
    "☹️", "😣", "😖", "😫", "😩", "🥺", "😢", "😭", "😤", "😠", "😡", "🤬", "🤯", "😳", "🥵", "🥶", "😱", "😨", "😰",
    "😥", "😓", "🤗", "🤔", "🤭", "🤫", "🤥", "😶", "😐", "😑", "😬", "🙄", "😯", "😦", "😧", "😮", "😲", "🥱", "😴",
    "🤤", "😪", "😵", "🤐", "🥴", "🤢", "🤮", "🤧", "😷", "🤒", "🤕", "🤑", "🤠", "😈", "👿", "👹", "👺", "🤡", "💩",
    "👻", "💀", "☠️", "👽", "👾", "🤖", "🎃", "😺", "😸", "😹", "😻", "😼", "😽", "🙀", "😿", "😾"
]

# Generate a random emoji short code
def generate_short_code(length=4):
    return ''.join(random.sample(EMOJIS, length))

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
            # Generate a unique emoji short code
            short_code = await get_unique_short_code()
            
            # Store the link in the database
            await links_collection.insert_one({
                "original_url": original_url,
                "short_code": short_code
            })
        
        short_url = request.host_url + short_code
        return await render_template("index.html", short_url=short_url)
    
    return await render_template("index.html")

@app.route("/<short_code>")
async def redirect_to_url(short_code):
    link = await links_collection.find_one({"short_code": short_code})
    if link:
        return redirect(link["original_url"])
    return "Link not found", 404

if __name__ == "__main__":
    app.run(debug=True)
