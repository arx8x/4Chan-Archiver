import shutil
import subprocess
from pprint import pprint
from os import makedirs as mkdirs, remove as del_file
from os.path import exists as file_exists, getsize, basename
import json
import requests
from validators import url as urlvalidate
from utils import log, download_file, get_remote_filesize, url_split, \
                  replace_extension
# TODO: media conversion remove original
# TODO: Windows support
# TODO: archive post json
# TODO: check header to see if post has new content
# TODO: output dir
# TODO: write file metadata and title


class CL4Archiver:
    def __init__(self, url, binary_path=None):
        self.__path = None
        # parse url and create API url
        if not urlvalidate(url):
            log("No thread url provided", 4)
            raise Exception("No proper thread url supplied")
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

    @property
    def path(self):
        if not self.__path:
            self.__path = f"archives/{self.board}/{self.thread}"
            mkdirs(self.__path, exist_ok=True)
        return self.__path

    def __local_meta(self) -> dict:
        path = f"{self.path}/meta"
        if not file_exists(path):
            return None
        with open(path, 'r') as meta_file:
            try:
                meta = json.load(meta_file)
                return meta
            except Exception:
                return None

    def __is_local_outdated(self, only_peek=False) -> bool:
        keys_to_check = ['etag', 'last-modified', 'content-length']
        remote_headers = requests.get(self.url).headers
        # convert keys to lowercase for case-insensitive comparison
        remote_headers = {key.lower(): value for key, value in
                          remote_headers.items()}
        if not remote_headers:
            log("Couldn't load remote headers", 3)
            return True

        def __write():
            nonlocal remote_headers, self
            if not only_peek and remote_headers:
                self.__write_meta(remote_headers)

        # check for local meta
        meta = self.__local_meta()
        if not meta:
            log("local metadata not found", 3)
            __write()
            return True

        # compare
        for key_to_check in keys_to_check:
            local_val = meta.get(key_to_check)
            remote_val = remote_headers.get(key_to_check)
            if not local_val or not remote_val:
                continue
            log(f'comparing {key_to_check}')
            if local_val != remote_val:
                log(f"key: {key_to_check} didn't match")
                __write()
                return True
        log("remote headers have no change")
        return False

    def __write_meta(self, headers: dict):
        path = f"{self.path}/meta"
        with open(path, 'w') as file:
            json.dump(headers, file)
            log("writing local metadata", 1)

    def archive(self, convert_media=True, remove_original=False):
        if not self.thread or not self.url:
            log("Instance is not properly initialized")
            return

        if not self.__is_local_outdated():
            log("thread has no updates")
            return

        log(f"Starting archive of thread: {self.thread} from /{self.board}/")
        if convert_media and not self.__ffmpeg_path:
            log("Cannot convert media because ffmpeg is not installed", 3)
            convert_media = False
        api_data = requests.get(self.url).content
        post_file = f"{self.path}/post.json"
        with open(post_file, 'wb') as post_file:
            log('writing post data', 1)
            post_file.write(api_data)
        json_data = json.loads(api_data)
        posts = json_data['posts']
        for post in posts:
            if not (ext := post.get('ext')) or not post.get('tim'):
                # no media in this post
                continue
            path = self.__download_media(post)
            if not path:
                continue
            if convert_media and ext == '.webm':
                conv_path = self.__convert_media(path)
                if conv_path and remove_original:
                    log("removing original file", 2)
                    del_file(path)

    def __path_for_binary(self, binary):
        if self.__binary_path:
            path = self.__binary_path + binary
            return path if file_exists(path) else None
        else:
            return shutil.which(binary)

    def __download_media(self, post) -> str:
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
            log("Downloading...", 1)
            if not download_file(url, path):
                log("Download failed", 4)
                return None
        return path

    def __convert_media(self, media_path: str):
        target_path = replace_extension(media_path, 'mp4')
        temporary_path = target_path + "__ffmpeg_tmp.mp4"
        if file_exists(temporary_path):
            log(
                f'cleaning up temporary file from previous run: {temporary_path}', 2)
            del_file(temporary_path)
        if file_exists(target_path):
            log("file already converted")
            return
        log(f"converting {basename(media_path)}...", 1)
        command_args = [self.__ffmpeg_path, "-i", media_path, temporary_path]
        proc = subprocess.run(command_args, capture_output=True)
        if proc.returncode:
            log("conversion failed", 4)
            return None
        else:
            shutil.move(temporary_path, target_path)
            return target_path
