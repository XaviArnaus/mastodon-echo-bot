from pyxavi.storage import Storage
from urllib.parse import urlparse
from pyxavi.debugger import dd
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

def clean_url(url, remove_components: dict = {}) -> str:

    to_remove = {
        "scheme": False,
        "netloc": False,
        "path": False,
        "params": False,
        "query": False,
        "fragment": False
    }
    to_remove = {**to_remove, **remove_components}

    parsed = urlparse(url)
    
    if to_remove["scheme"] is True:
        parsed = parsed._replace(scheme="")
    if to_remove["netloc"] is True:
        parsed._replace(netloc="")
    if to_remove["path"] is True:
        parsed = parsed._replace(path="")
    if to_remove["params"] is True:
        parsed = parsed._replace(params="")
    if to_remove["query"] is True:
        parsed = parsed._replace(query="")
    if to_remove["fragment"] is True:
        parsed = parsed._replace(fragment="")
    
    return parsed.geturl()

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
        new_url = clean_url(url=url, remove_components=CLEANING_PARAMS)
        log(f"{url} => {new_url}")
        new_urls.append(new_url)
    
    # Now we replace the parameter with the new URL list
    storage.set(storage_parameter, new_urls)
    log(f"Stored back {len(new_urls)} urls in the hash {key}")

# Now we write the file to save the new values
storage.write_file()
log(f"Writting the file {storage._filename} and finishing.")

# And that's it
exit(0)