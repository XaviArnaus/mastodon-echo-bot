import requests
import os
from urllib.parse import urlparse
import mimetypes

def download_media_from_url(url: str, destination_path: str) -> dict:
    parsed_url = urlparse(url)

    result = {
        "file": destination_path.strip("/") + "/" + os.path.basename(parsed_url.path),
        "mime_type": None
    }

    with open(result["file"], 'wb') as handle:
        # Download
        response = requests.get(
            url,
            stream=True,
            allow_redirects=True
        )

        # Check the response and raise if not OK
        if not response.ok:
            raise RuntimeError(response)

        # Write the binary
        for block in response.iter_content(1024):
            if not block:
                break

            handle.write(block)

    # Get the Mime type from the binary
    discovered_mime = mimetypes.guess_type(url)
    result["mime_type"]=discovered_mime[0] if discovered_mime else None

    return result