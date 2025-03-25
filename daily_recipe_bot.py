from openai import OpenAI
import requests
from PIL import Image, ImageDraw, ImageFont
import io
import os
import re
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Set up OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# WordPress credentials
WP_USERNAME = os.getenv("WP_USERNAME")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")
WP_SITE = os.getenv("WP_SITE")
POST_URL = f"{WP_SITE}/wp-json/wp/v2/posts"
MEDIA_URL = f"{WP_SITE}/wp-json/wp/v2/media"

def generate_recipe():
    prompt = (
        "Generate a detailed recipe blog post for a unique but delicious dish. "
        "Include the following sections:\n\n"
        "1. <h1>Title</h1>\n"
        "2. Introduction\n"
        "3. Ingredients\n"
        "4. Instructions\n"
        "5. Tips & Variations\n"
        "6. Storage Instructions\n"
        "7. FAQs\n\n"
        "Format it as clean HTML for WordPress."
    )
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def extract_title(html):
    match = re.search(r"<h1>(.*?)</h1>", html, re.IGNORECASE)
    return match.group(1).strip() if match else "Delicious Recipe"

def generate_image(prompt_text):
    # Create a safe and focused image prompt
    safe_prompt = f"Professional food photography of {prompt_text}, plated, high quality, soft lighting"
    response = client.images.generate(
        model="dall-e-3",
        prompt=safe_prompt,
        n=1,
        size="1024x1024"
    )
    image_url = response.data[0].url
    image_data = requests.get(image_url).content
    return image_data

def create_title_image(image_data, title):
    image = Image.open(io.BytesIO(image_data)).convert("RGB")
    draw = ImageDraw.Draw(image)

    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 40)
    except:
        font = ImageFont.load_default()

    draw.rectangle([(0, 900), (1024, 1024)], fill=(0, 0, 0, 180))
    draw.text((30, 920), title, fill="white", font=font)

    # Save image (replace with your username)
    output_path = "/home/jamoesser/title_image.jpg"
    image.save(output_path)
    return output_path

def upload_media(image_path):
    with open(image_path, 'rb') as img:
        filename = os.path.basename(image_path)
        headers = {
            'Content-Disposition': f'attachment; filename={filename}',
        }
        response = requests.post(
            MEDIA_URL,
            headers=headers,
            data=img,
            auth=(WP_USERNAME, WP_APP_PASSWORD)
        )
    if response.status_code == 201:
        return response.json()['id']
    else:
        print("❌ Media upload failed:", response.text)
        return None

def create_wordpress_post(title, content, media_id):
    post_data = {
        "title": title,
        "content": content,
        "status": "publish",
        "featured_media": media_id
    }
    response = requests.post(
        POST_URL,
        json=post_data,
        auth=(WP_USERNAME, WP_APP_PASSWORD)
    )
    if response.status_code == 201:
        print("✅ Post published:", response.json()['link'])
    else:
        print("❌ Post failed:", response.text)

# ----- MAIN WORKFLOW -----
html_post = generate_recipe()
title = extract_title(html_post)

print("🧠 Generated Title:", title)
print("🎨 Generating image...")
image_data = generate_image(title)

print("🖼️ Creating Pinterest-style image...")
image_path = create_title_image(image_data, title)

print("⬆️ Uploading image to WordPress...")
media_id = upload_media(image_path)

print("📝 Publishing post...")
create_wordpress_post(title, html_post, media_id)
