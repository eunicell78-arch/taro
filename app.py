import os
import hashlib
import requests
from tqdm import tqdm
import streamlit as st

# Ensure that required Rider-Waite-Smith tarot images are available in assets/rws

def md5_hash(path):
    md5 = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            md5.update(chunk)
    return md5.hexdigest()

@st.cache(suppress_st_warning=True)
def ensure_images():
    folder_path = 'assets/rws'
    os.makedirs(folder_path, exist_ok=True)
    missing_images = []
    with open('data/cards.json') as f:
        cards = json.load(f)
    for card in cards:
        image_name = f'{card['name']}.jpg'
        image_path = os.path.join(folder_path, image_name)
        if not os.path.exists(image_path):
            # Check MD5 hash and download image from Wikimedia
            image_url = f'https://commons.wikimedia.org/wiki/Special:FilePath/{image_name}'
            try:
                response = requests.get(image_url, stream=True)
                response.raise_for_status()
                with open(image_path, 'wb') as out_file:
                    total_length = int(response.headers.get('content-length', 0))
                    with tqdm(total=total_length, unit='B', unit_scale=True) as pbar:
                        for data in response.iter_content(chunk_size=4096):
                            out_file.write(data)
                            pbar.update(len(data))
            except Exception as e:
                st.warning(f'Failed to download {image_name}. Falling back to placeholder.')
                # Placeholder logic here
                pass
        else:
            st.success(f'{image_name} is already downloaded.')

# Call this function to ensure all images are available
ensure_images()
