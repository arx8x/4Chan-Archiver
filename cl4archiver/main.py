import sys
import getopt
from .cl4archiver import CL4Archiver
from .utils import log
from validators import url as urlvalidate
from os import listdir
from os.path import isdir, exists as path_exists

convert = True
binpath = None
output_path = 'archives'


def update_threads():
    log(" >>> running updater")
    global convert, binpath, output_path
    board_dirs = listdir(output_path)
    for board in board_dirs:
        board_dir = f"{output_path}/{board}"
        # skip hidden directories and . and ..
        if not isdir(board_dir) or board[0] == '.':
            continue
        thread_dirs = listdir(board_dir)
        for thread in thread_dirs:
            if not thread.isnumeric():
                log(f"\"{thread}\" isn't a valid thread id")
                continue
            thread_dir = f"{board_dir}/{thread}"
            if not isdir(thread_dir) or thread[0] == '.':
                # skip hidden directories and . and ..
                continue
            log(f" >>> checking {thread} from /{board}/")
            meta_file_path = f"{thread_dir}/meta"
            if not path_exists(meta_file_path):
                log(" >>> thread has no initial data to update")
                continue
            cl4 = CL4Archiver(board, thread, binpath, output_path)
            cl4.archive(convert)


def main():
    try:
        longopts = ["no-convert", "binpath=", 'output=', 'udpate']
        args = getopt.getopt(sys.argv[1:], 'unbo:', longopts)
    except getopt.GetoptError as e:
        log(e.msg, 4)
        sys.exit(-1)

    global convert, binpath, output_path
    update = False

    for opt in args[0]:
        if opt[0] in ['--no-convert', '-n']:
            convert = False
        elif opt[0] in ['--binpath', '-b']:
            binpath = opt[1]
        elif opt[0] in ['--output', '-o']:
            output_path = opt[1]
        elif opt[0] in ['--update', '-u']:
            update = True
    if update:
        update_threads()
        sys.exit()
    elif args[1]:
        thread_url = args[1].pop()
        if not thread_url or not urlvalidate(thread_url):
            log("No thread url provided", 4)
            sys.exit(-1)
        urlsplit = thread_url.split('/')
        if not urlsplit:
            log("Unable to parse the url", 4)
            sys.exit(-1)
        board = urlsplit[3]
        thread = urlsplit[5]
        c = CL4Archiver(board, thread, binpath, output_path=output_path)
        c.archive(convert)


if __name__ == '__main__':
    main()
