import base64

import requests


def download_and_encode_image(image_url: str) -> str:
    response = requests.get(image_url)
    if response.status_code == 200:
        return base64.b64encode(response.content).decode('utf-8')
    else:
        raise Exception(f"Failed to download image from {image_url}")