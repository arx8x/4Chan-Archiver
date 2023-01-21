import os
import urllib.request
from urllib.error import HTTPError
from urllib.parse import urlparse, parse_qs
from collections import namedtuple
import requests
import time

URLInfo = namedtuple(
    "URLInfo", ['url', 'domain', 'components', 'scheme', 'query', 'fragment'],
    defaults=(None,) * 5)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def log(entry, type=0):
    symbols = ['*', '+', '-', '!', '#', '>', '<']
    try:
        symbol = symbols[type]
    except Exception:
        symbol = '*'
    print(f"[{symbol}] {entry}")


def intervalcheck(key: str, duration: int, use_key_as_path: bool = False,
                  retouch: bool = True) -> bool:
    '''
    Checks if the given duration has passed for the given key.
    If the duration has passed, reset the duration
    '''
    expired = False
    if use_key_as_path:
        path = key
        dir = os.path.dirname(path)
    else:
        dir = 'intervalcheck'
        path = f"{dir}/{key}"
    os.makedirs(dir, exist_ok=True)
    if os.path.exists(path):
        last_modified = os.path.getmtime(path)
        current_time = time.time()
        delta = current_time - last_modified
        if delta > duration:
            expired = True
    else:
        expired = True

    # update the last_modified if needed
    if expired and retouch:
        with open(path, 'w+') as f:
            f.write('')
        return True
    return expired


def get_redirect_url(url):
    # urllib.request follows  rediects automatically
    # build a custom opener that neuters this behavior
    # so we'll get the redirect url from header without
    # going to the redirect url
    redirect_url = None
    try:
        opener = urllib.request.build_opener(NoRedirect)
        urllib.request.install_opener(opener)
        urllib.request.urlopen(url)
    except HTTPError as e:
        header_info = e.info()
        redirect_url = header_info.get('location')
    except Exception as e:
        print(e)

    # restore original behavior
    urllib.request.install_opener(
        urllib.request.build_opener(urllib.request.HTTPRedirectHandler))
    return redirect_url


def get_remote_filesize(url):
    if not url:
        return None
    try:
        r = requests.head(url)
        headers = r.headers
        if (size := headers.get('content-length')):
            return int(size)
    except Exception as e:
        print(e)
    return None


def url_filename(url):
    parsed = urlparse(url)
    return os.path.basename(parsed.path)


def download_file(url, local_path, headers=[]):
    opener = urllib.request.build_opener()
    opener.addheaders = headers
    urllib.request.install_opener(opener)
    urllib.request.urlretrieve(url, local_path)
    if os.path.exists(local_path):
        return True
    return False


def url_split(url):
    url_split = urlparse(url, allow_fragments=True)
    if not url_split.netloc:
        return ()
    components = [c for c in url_split.path.split('/') if c]
    query = parse_qs(url_split.query)
    pathinfo = URLInfo(url, url_split.netloc, components,
                       url_split.scheme, query, url_split.fragment)
    return pathinfo


def replace_extension(path, extension=None):
    if not path:
        return None
    path_split = os.path.splitext(path)
    # if no extension is given, remove extension
    if not extension:
        return path_split[0]
    if not path_split:
        return None
    new_path = f"{path_split[0]}.{extension}"
    return new_path