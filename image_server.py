#!/home/slzatz/frontpages/.venv/bin/python

from flask import Flask, send_file
import requests
import wand.image
from io import BytesIO
import random
from frontpageurls import urls

app = Flask(__name__)

user_agent = "Mozilla/5.0 (Wayland; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
headers = {'User-Agent': user_agent}

#urls = urls[0:21] + urls[50:]

def display_image(uri, w=None, h=None):
    #global can_transfer_with_files
    print(uri)
    try:
        response = requests.get(uri, timeout=5.0, headers=headers)
    except (requests.exceptions.ConnectionError,
            requests.exceptions.TooManyRedirects,
            requests.exceptions.ChunkedEncodingError,
            requests.exceptions.ReadTimeout) as e:
        print(f"requests.get({uri}) generated exception:\n{e}")
        return False

    if response.status_code != 200:
        print(f"status code = {response.status_code}")
        return False
        
    # it is possible to have encoding == None and ascii == True
    if response.encoding or response.content.isascii():
        print(f"{uri} returned ascii text and not an image")
        return False

    # this try/except is needed for occasional bad/unknown file format
    try:
        img = wand.image.Image(file=BytesIO(response.content))
    except Exception as e:
        print(f"wand.image.Image(file=BytesIO(response.content))"\
              f"generated exception from {uri} {e}")
        return False

    #img.transform(resize='825x1600>')
    if w and h:
        img.transform(resize=f"{w}x{h}>")


    if img.format == 'JPEG':
        #tf = NamedTemporaryFile(suffix='.rgba', delete=False)
        #img.save(filename = tf.name)
        #return tf
        img.save(filename = "fp.jpg")
        img.close()
    else:
        print("format is not JPEG")
        return False

@app.route("/image")
def image():
    return send_file("image.jpg", mimetype="image/jpg")

@app.route("/imagejpg")
def imagejpg():
    #f = display_image("https://upload.wikimedia.org/wikipedia/commons/d/d5/Bob_Dylan_-_Azkena_Rock_Festival_2010_1.jpg", 800, 1200)
    partial_url = random.choice(urls)
    f = display_image("https://www.frontpages.com" + partial_url, 400, 800)
    #f = display_image("https://www.frontpages.com" + partial_url)
    return send_file("fp.jpg", mimetype="image/jpg")

if __name__ == "__main__":
    app.run(debug=True,
            host='0.0.0.0',
            port=5000)
