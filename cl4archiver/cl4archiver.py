import shutil
import subprocess
from pprint import pp
import os
import json
import requests
from typing import List, Dict, Tuple, Optional
from pyutils import Logger, download_file, get_remote_filesize, url_split, \
                  replace_extension
from parallel_tasks import ParallelRunner, Task, Function
from dataclasses import dataclass
from urllib.parse import urlparse
# TODO: write file metadata and title

logger = Logger()

@dataclass
class URLSpecs:
    base: str
    board: str
    thread: str 
    post: Optional[str] = None

class CL4Archiver:
    def __init__(self, board: str, thread: str, output_path: str,
                 binary_path: str = None):
        self.__thread = thread
        self.__board = board
        self.parallel = 1

        self.__base_path = None 
        self.__output_path = None
        if output_path:
            self.output_path = output_path

        # create API url
        self.__url = f"https://a.4cdn.org/{board}/thread/{thread}.json"
        self.__headers_store = None
        self.__post_data_store = None

        # clean up and define binary path
        self.__binary_path = binary_path
        if self.__binary_path:
            binary_path = self.__binary_path.rstrip('/')
            binary_path += '/'
            self.__binary_path = binary_path
            logger.log(f"binary path set to {self.__binary_path}")
        self.__ffmpeg_path = self.__path_for_binary('ffmpeg')
        if self.__ffmpeg_path:
            logger.log(f"ffmpeg path set to {self.__ffmpeg_path}")
        else:
            logger.log("ffmpeg not found", 3)

        self.post_file = f"{self.archive_path}/thread.json"

    @property
    def thread(self):
        return self.__thread

    @property
    def board(self):
        return self.__board

    @property
    def api_url(self):
        return self.__url

    @property
    def output_path(self):
        return self.__base_path

    @output_path.setter
    def output_path(self, path: str):
        if not os.path.exists(path):
            raise Exception(f"Path \"{path}\" doesn't exist")
        output_path = f"{path}/{self.board}/{self.thread}"
        os.makedirs(output_path, exist_ok=True)
        self.__base_path = path
        self.__output_path = output_path

    @property
    def archive_path(self):
        return self.__output_path

    @classmethod
    def parse_url(cls, url: str):
        parts = urlparse(url)
        if not parts.path:
            return None
        path_parts = parts.path.split('/')
        if len(path_parts) < 4:
            return None
        specs = URLSpecs(
            base=parts.netloc,
            board=path_parts[1],
            thread=path_parts[3]
        )
        if parts.fragment:
            specs.post = parts.fragment[1:]
        return specs

    @classmethod
    def from_url(cls, url: str, output_path: str) -> 'CL4Archiver':
        comps = cls.parse_url(url)
        return CL4Archiver(comps.board, comps.thread, output_path=output_path)

    @property
    def __headers(self):
        if not self.__headers_store:
            r = requests.head(self.api_url)
            if r.status_code != 200:
                return None
            headers = r.headers
            headers = {key.lower(): value for key, value in headers.items()}
            self.__headers_store = headers
        return self.__headers_store

    @property
    def __post_data(self):
        if not self.__post_data_store:
            try:
                r = requests.get(self.api_url)
                if r.status_code != 200:
                    return None
                data = r.content
                self.__post_data_store = json.loads(data)
            except Exception as e:
                logger.log(f"Unable to load post data: {e}", 4)
            finally:
                if r:
                    r.close()
        return self.__post_data_store

    @property
    def media_count(self):
        post_data = self.__post_data
        if not (posts := post_data.get('posts')):
            raise Exception("No posts data")
        media_count = 0
        for post in posts:
            if post.get('tim'):
                media_count += 1
        return media_count

    @property
    def total_media_size(self):
        post_data = self.__post_data
        if not (posts := post_data.get('posts')):
            raise Exception("No posts data")
        total_size = 0
        for post in posts:
            if post.get('tim'):
                total_size += post.get('fsize')
        return total_size


    def __local_meta(self) -> dict:
        path = f"{self.archive_path}/meta"
        if not os.path.exists(path):
            return None
        with open(path, 'r') as meta_file:
            try:
                meta = json.load(meta_file)
                return meta
            except Exception:
                return None

    def __is_local_outdated(self, only_peek=False) -> bool:
        keys_to_check = ['etag', 'last-modified', 'content-length']
        remote_headers = self.__headers
        if not remote_headers:
            logger.log("Couldn't load remote headers", 3)
            return True

        def __write():
            nonlocal remote_headers, self
            if not only_peek and remote_headers:
                self.__write_meta()

        # check for local meta
        meta = self.__local_meta()
        if not meta:
            logger.log("local metadata not found", 3)
            __write()
            return True

        # compare
        for key_to_check in keys_to_check:
            local_val = meta.get(key_to_check)
            remote_val = remote_headers.get(key_to_check)
            if not local_val or not remote_val:
                continue
            if local_val != remote_val:
                logger.log(f"key: {key_to_check} didn't match")
                __write()
                return True
        return False

    def __media_path_for_post(self, post) -> str:
        if (media_id := post.get('tim')) and (ext := post.get('ext')):
            return os.path.join(self.archive_path, f"{media_id}{ext}")

    def __conv_path_for_post(self, post) -> str:
        if (media_id := post.get('tim')) and (post_id := post.get('no')):
            return os.path.join(self.archive_path, f"{media_id}.mp4")

    def __write_meta(self):
        path = f"{self.archive_path}/meta"
        with open(path, 'w') as file:
            json.dump(self.__headers, file)
            logger.log("writing local metadata", 1)

    def archive(self, convert_media=True, remove_original=False):
        if not self.thread or not self.api_url:
            logger.log("Instance is not properly initialized")
            return

        if not os.path.exists(self.post_file):
            logger.log("local post doesn't exist", 3)
            should_write_posts = True
        else:
            should_write_posts = False

        has_updates = False
        if self.__is_local_outdated(only_peek=True):
            has_updates = True
            should_write_posts = True
        else:
            logger.log("thread has no updates")

        api_data = None
        if has_updates or should_write_posts:
            if not (api_data := self.__post_data):
                logger.log("Could not load post data", 4)
                return
            post_file = f"{self.archive_path}/thread.json"
            with open(post_file, 'w') as post_file:
                logger.log('writing post data', 1)
                json.dump(api_data, post_file)

        if not has_updates:
            return

        if convert_media and not self.__ffmpeg_path:
            logger.log("Cannot convert media because ffmpeg is not installed", 3)
            convert_media = False
        if not api_data:
            logger.log('unable to get post data', 4)
            return
        posts = api_data['posts']

        total_media_done = 0
        media_posts = [p for p in posts if p.get('ext') and p.get('tim')]
        total_media_posts = len(media_posts)

        logger.section_title("Archiving media")
        logger.log(f"Found {total_media_posts} media items in the thread")

        def __callback(task):
            nonlocal total_media_done, total_media_posts
            total_media_done += 1
            percent_done = round((total_media_done / total_media_posts) * 100)
            logger.log(f"Processed media {total_media_done}/{total_media_posts} ({percent_done}%)")

        tasks = []
        for post in media_posts:
            f = Function(self.__process_media, [post, convert_media, remove_original])
            task = Task(target=f, name=post['no'])
            tasks.append(task)

        runner = ParallelRunner(tasks, max_parallel=self.parallel, callback=__callback)
        runner.run_all()
        # once done, write meta
        self.__write_meta()

    def get_single_media(self, post_id: int, convert: bool = True, remove_original=False) -> Tuple[str, str]:
        if not self.thread or not self.api_url:
            logger.log("Instance is not properly initialized", 4)
            return
        if not (api_data := self.__post_data):
            logger.log("post data can't be retrieved from API", 4)
            return 
        if not (posts := api_data.get('posts')):
            logger.log(f"Could not get posts data from API data", 4)
            return
        for post in posts:
            if post['no'] == post_id:
                break
        else:
            logger.log(f"Post id {post_id} not found in thread")
            return
        return self.__process_media(post, convert, remove_original)
        
    def __process_media(self, post, convert_media, remove_original) -> Tuple[str, str]:
        # TODO: make path and conv path here and pass those just as args
        if not (ext := post.get('ext')) or not post.get('tim'):
            # no media in this post
            return None
        do_download = True
        download_path = self.__media_path_for_post(post)
        conv_path = self.__conv_path_for_post(post)
        # handle a special case where the converted media exists and
        # re-download isn't necessary. 
        # Otherwise it would download the file, skip the 
        # conversion (since it's already done) and remove the file
        # Essentially, the file is downloaded, not used in any way and then removed
        if convert_media and remove_original:
            if os.path.exists(convert_media):
                logger.log("Converted file exists. Skipping download")
                do_download = False
        if do_download and not (path := self.__download_media(post, download_path)):
            return (None, None)
        if convert_media and ext == '.webm':
            conv_path = self.__convert_media(download_path, conv_path)
            if conv_path and remove_original:
                if os.path.exists(download_path):
                    logger.log("removing original file", 2)
                    os.unlink(download_path)
                path = None
        else:
            conv_path = None
        if remove_original and not conv_path:
            logger.log("Original won't be removed because no conversion was done", 3)
        return (path, conv_path)

    def __path_for_binary(self, binary) -> str:
        if self.__binary_path:
            path = self.__binary_path + binary
            if os.name == 'nt' and not path.endswith('.exe'):
                path += '.exe'
            return path if os.path.exists(path) else None
        else:
            return shutil.which(binary)

    def __download_media(self, post: dict, path: str) -> bool:
        if not (ext := post.get('ext')) or not (name := post.get('tim')):
            return False
        should_download_file = True
        filename = f"{name}{ext}"
        url = f"https://i.4cdn.org/{self.board}/{filename}"
        logger.log(f"Media {filename} for post {post.get('no')}")
        if os.path.exists(path):
            print_message = "Local file exists"
            local_size = os.path.getsize(path)
            remote_size = get_remote_filesize(url)
            # if local file is complete, return success without re-download
            if local_size == remote_size:
                should_download_file = False
                logger.log(f"{print_message} and is complete")
                return True

            print_message += " but sizes are different (remote: %s vs local: %s)" \
                    % (remote_size, local_size)
            logger.log(print_message)
        if should_download_file:
            logger.log("Downloading...", 1)
            if download_file(url, path):
                return True
        logger.log("Download failed", 4)
        return False

    def __convert_media(self, media_path: str, target_path: str) -> bool:
        temporary_path = target_path + "__ffmpeg_tmp.mp4"
        if os.path.exists(temporary_path):
            logger.log(f'cleaning up temporary file from previous run: {temporary_path}', 2)
            os.remove(temporary_path)
        if os.path.exists(target_path):
            logger.log("file already converted")
            return target_path
        logger.log(f"converting {os.path.basename(media_path)}...", 1)
        command_args = [self.__ffmpeg_path, "-i", media_path, 
                        '-pix_fmt', 'yuv420p', temporary_path]
        proc = subprocess.run(command_args, capture_output=True)
        if not proc.returncode:
            shutil.move(temporary_path, target_path)
            return True
        logger.log("conversion failed", 4)
        return False
