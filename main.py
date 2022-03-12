import sys
import getopt
import shutil
import subprocess
# from pprint import pprint
from os import makedirs as mkdirs, remove as del_file
from os.path import exists as file_exists, getsize, basename
import json
import requests
from validators import url as urlvalidate
from utils import log, download_file, get_remote_filesize, url_split, \
                  replace_extension

class CL4Archiver:
    def __init__(self, url, binary_path=None):
        if not urlvalidate(url):
            log("No thread url provided", 4)
            return
        self.__path = None

        # clean up and define binary path
        self.__binary_path = binary_path
        if self.__binary_path:
            binary_path = self.__binary_path.rstrip('/')
            binary_path += '/'
            self.__binary_path = binary_path
            log(f"binary path set to {self.__binary_path}")
        self.__ffmpeg_path = self.__path_for_binary('ffmpeg')
        if self.__ffmpeg_path:
            log(f"ffmpeg path set to {self.__ffmpeg_path}")
        else:
            log("ffmpeg not found", 3)

        # parse url and create API url
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

    @property
    def path(self):
        if not self.__path:
            self.__path = f"archives/{self.board}/{self.thread}"
            mkdirs(self.__path, exist_ok=True)
        return self.__path

    def archive(self, convert_media=True):
        log(f"Starting archive of thread: {self.thread} from /{self.board}/")
        if convert_media and not self.__ffmpeg_path:
            log("Cannot convert media because ffmpeg is not installed", 3)
            convert_media = False
        api_data = requests.get(self.url).content
        json_data = json.loads(api_data)
        posts = json_data['posts']
        for post in posts:
            self.__download_media(post, convert_media)

    def __path_for_binary(self, binary):
        if self.__binary_path:
            path = self.__binary_path + binary
            return path if file_exists(path) else None
        else:
            return shutil.which(binary)

    def __download_media(self, post, convert_media: bool) -> str:
        if not (ext := post.get('ext')) or not (name := post.get('tim')):
            return None
        should_download_file = True
        filename = f"{name}{ext}"
        url = f"https://i.4cdn.org/{self.board}/{filename}"
        log(f"Media {filename} for post {post.get('no')}")
        path = f"{self.path}/{filename}"
        if file_exists(path):
            print_message = "Local file exists"
            local_size = getsize(path)
            remote_size = get_remote_filesize(url)
            if local_size != remote_size:
                print_message += " but sizes are different (remote: %s vs local: %s)" \
                % (remote_size, local_size)
            else:
                should_download_file = False
                print_message += " and is complete"
            log(print_message)
        if should_download_file:
            log("Downloading...")
            if not download_file(url, path):
                log("Download failed")
                return None
        if convert_media:
            self.__convert_media(path)
        return path

    def __convert_media(self, media_path: str):
        target_path = replace_extension(media_path, 'mp4')
        temporary_path = target_path + "__ffmpeg_tmp.mp4"
        if file_exists(temporary_path):
            log(f'cleaning up temporary file from previous run: {temporary_path}')
            del_file(temporary_path)
        if file_exists(target_path):
            log("file already converted")
            return
        log(f"converting {basename(media_path)}...")
        command_args = [self.__ffmpeg_path, "-i", media_path, temporary_path]
        proc = subprocess.run(command_args, capture_output=True)
        if proc.returncode:
            log("conversion failed", 4)
        else:
            shutil.move(temporary_path, target_path)


try:
    args = getopt.getopt(sys.argv[1:], '', ["no-convert", "binpath="])
except getopt.GetoptError as e:
    log(e.msg, 4)
    sys.exit(-1)


onvert = True
binpath = None

for opt in args[0]:
    if opt[0] == '--no-convert':
        convert = False
    elif opt[0] == '--binpath':
        binpath = opt[1]

thread_url = args[1].pop()



c = CL4Archiver(thread_url, binpath)
c.archive(convert)
