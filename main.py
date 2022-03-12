import json
import requests
from pprint import pprint as pprint
from os import makedirs as mkdirs
from os.path import exists as file_exists, getsize
from utils import log, download_file, get_remote_filesize, url_split
from validators import url as urlvalidate
import sys

class CL4Archiver:
    def __init__(self, url):
        if not urlvalidate(url):
            log("No thread url provided", 4)
            return
        urlsplit = url_split(url)
        if not url_split or len((urlcomponents := urlsplit.components)) < 3:
            log("Unable to parse the url", 4)
            return
        self.board = urlcomponents[0]
        self.thread = urlcomponents[2]
        api_domain = 'a.4cdn.org'
        components = ['https:/', api_domain] + urlcomponents[:3]
        api_url = '/'.join(components)
        self.url = api_url + '.json'

    def archive(self):
        log(f"Starting archive of thread: {self.thread} from /{self.board}/")
        api_data = requests.get(self.url).content
        json_data = json.loads(api_data)
        posts = json_data['posts']
        for post in posts:
            media_url = self.__download_media(post)


    def __path_for_thread(self):
        path = f"archives/{self.board}/{self.thread}"
        mkdirs(path, exist_ok=True)
        return path

    def __download_media(self, post) -> str:
        if not (ext := post.get('ext')) or not (name := post.get('tim')):
            return None
        should_download_file = True
        filename = f"{name}{ext}"
        url = f"https://i.4cdn.org/{self.board}/{filename}"
        log(f"Media {filename} for post {post.get('no')}")
        path = self.__path_for_thread()
        path += f"/{filename}"
        if file_exists(path):
            print_message = "Local file exists and is complete"
            local_size = getsize(path)
            remote_size = get_remote_filesize(url)
            if local_size != remote_size:
                print_message += " but sizes are different (remote: %s vs local: %s)" % (remote_size, local_size)
            else:
                should_download_file = False
            log(print_message)
        if should_download_file:
            log(f"Downloading...")
            download_file(url, path)
        return

url = sys.argv.pop()

c = CL4Archiver(url)
c.archive()
