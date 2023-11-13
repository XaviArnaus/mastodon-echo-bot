from pyxavi.storage import Storage
from pyxavi.url import Url
import os

STORAGE_FILE = "storage/feeds.yaml"
PARAM = "urls_seen"
CLEANING_PARAMS = {
    "scheme": True
}
DEBUG = True


def log(text: str) -> None:
    if DEBUG is True:
        print(f"{text}")

def error(text: str) -> None:
    print(f"{text}")

def run():
    # Load the file in a Storage instance
    if os.path.exists(STORAGE_FILE):
        storage = Storage(STORAGE_FILE)
    else:
        error(f"Could not find {STORAGE_FILE}")
        exit(1)

    # getting the hashes
    keys = [key for key in storage._content.keys()]
    log(f"Got {len(keys)} hashes")

    # Now we loop the keys, to get the list of URLs in each.
    # Here we're emulating the get_hashed, as we don't know the unhashed value.
    for key in keys:
        storage_parameter = f"{key}.{PARAM}"
        urls = storage.get(storage_parameter)
        log(f"{len(urls)} urls in the hash {key}")

        # Now we walk through the URLs and clean them
        #   generating a new list of URLs
        new_urls = []
        for url in urls:
            new_url = Url.clean(url=url, remove_components=CLEANING_PARAMS)
            log(f"{url} => {new_url}")
            if new_url not in new_urls:
                new_urls.append(new_url)
        
        # Now we replace the parameter with the new URL list
        storage.set(storage_parameter, new_urls)
        log(f"Stored back {len(new_urls)} urls in the hash {key}")

    # Now we write the file to save the new values
    storage.write_file()
    log(f"Writting the file {storage._filename} and finishing.")

    # And that's it
    exit(0)