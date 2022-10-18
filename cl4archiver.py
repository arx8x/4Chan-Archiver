import shutil
import subprocess
from pprint import pp
import os
import json
import requests
from utils import log, download_file, get_remote_filesize, url_split, \
                  replace_extension
from parallel_tasks import ParallelRunner, Task, Function
# TODO: write file metadata and title


class CL4Archiver:
    def __init__(self, board: str, thread: str,
                 binary_path=None, output_path='archives'):
        self.__base_path = output_path
        self.__path = None

        self.thread = thread
        self.board = board
        # create API url
        self.url = f"https://a.4cdn.org/{board}/thread/{thread}.json"
        self.__headers_store = None
        self.__post_data_store = None

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

        self.post_file = f"{self.path}/thread.json"

    @property
    def __headers(self):
        if not self.__headers_store:
            r = requests.head(self.url)
            headers = r.headers
            headers = {key.lower(): value for key, value in headers.items()}
            self.__headers_store = headers
        return self.__headers_store

    @property
    def __post_data(self):
        if not self.__post_data_store:
            try:
                r = requests.get(self.url)
                data = r.content
                self.__post_data_store = json.loads(data)
            except Exception as e:
                log(e, 4)
            finally:
                if r:
                    r.close()
        return self.__post_data_store

    @property
    def path(self):
        if not self.__path:
            self.__path = f"{self.__base_path}/{self.board}/{self.thread}"
            os.makedirs(self.__path, exist_ok=True)
        return self.__path

    def __local_meta(self) -> dict:
        path = f"{self.path}/meta"
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
            log("Couldn't load remote headers", 3)
            return True

        def __write():
            nonlocal remote_headers, self
            if not only_peek and remote_headers:
                self.__write_meta()

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
            if local_val != remote_val:
                log(f"key: {key_to_check} didn't match")
                __write()
                return True
        return False

    def __write_meta(self):
        path = f"{self.path}/meta"
        with open(path, 'w') as file:
            json.dump(self.__headers, file)
            log("writing local metadata", 1)

    def archive(self, convert_media=True, remove_original=False):
        if not self.thread or not self.url:
            log("Instance is not properly initialized")
            return

        if not os.path.exists(self.post_file):
            log("local post doesn't exist", 3)
            should_write_posts = True
        else:
            should_write_posts = False

        has_updates = False
        if self.__is_local_outdated(only_peek=True):
            has_updates = True
            should_write_posts = True
        else:
            log("thread has no updates")

        api_data = None
        if has_updates or should_write_posts:
            api_data = self.__post_data
            post_file = f"{self.path}/thread.json"
            with open(post_file, 'w') as post_file:
                log('writing post data', 1)
                json.dump(api_data, post_file)

        if not has_updates:
            return

        log(f"Starting archive of thread: {self.thread} from /{self.board}/")
        if convert_media and not self.__ffmpeg_path:
            log("Cannot convert media because ffmpeg is not installed", 3)
            convert_media = False
        if not api_data:
            log('unable to get post data', 4)
            return
        posts = api_data['posts']

        def __callback(task):
            paths = task.return_data
            if isinstance(paths, tuple) and not all(paths):
                log(f"Could not get media for post {post['no']}", 4)

        tasks = []
        for post in posts:
            f = Function(self.__process_media, [post, convert_media, remove_original])
            task = Task(target=f, name=post['no'])
            tasks.append(task)

        runner = ParallelRunner(tasks, max_parallel=4)
        runner.run_all()
        # once done, write meta
        self.__write_meta()

    def __process_media(self, post, convert_media, remove_original):
        # TODO: make path and conv path here and pass those just as args
        if not (ext := post.get('ext')) or not post.get('tim'):
            # no media in this post
            return None
        path = self.__download_media(post)
        if not path:
            return (None, None)
        if convert_media and ext == '.webm':
            conv_path = self.__convert_media(path)
            if conv_path and remove_original:
                log("removing original file", 2)
                os.remove(path)
        else:
            conv_path = None
        return (path, conv_path)

    def __path_for_binary(self, binary):
        if self.__binary_path:
            path = self.__binary_path + binary
            if os.name == 'nt' and not path.endswith('.exe'):
                path += '.exe'
            return path if os.path.exists(path) else None
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
        if os.path.exists(path):
            print_message = "Local file exists"
            local_size = os.path.getsize(path)
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
        if os.path.exists(temporary_path):
            log(
                f'cleaning up temporary file from previous run: {temporary_path}', 2)
            os.remove(temporary_path)
        if os.path.exists(target_path):
            log("file already converted")
            return target_path
        log(f"converting {os.path.basename(media_path)}...", 1)
        command_args = [self.__ffmpeg_path, "-i", media_path, temporary_path]
        proc = subprocess.run(command_args, capture_output=True)
        if proc.returncode:
            log("conversion failed", 4)
            return None
        else:
            shutil.move(temporary_path, target_path)
            return target_path
