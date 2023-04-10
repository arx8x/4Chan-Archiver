import sys
import getopt
from .cl4archiver import CL4Archiver
from .utils import log
from validators import url as urlvalidate
import os

convert = os.environ.get('CL4ARCHIVER_CONVERT', '1') == '1'
binpath = os.environ.get('CL4ARCHIVER_BINPATH', None)
output_path = os.environ.get('CL4ARCHIVER_OUTPUT')
if (threads := os.environ.get('CL4ARCHIVER_PARALLEL')):
    threads = int(threads)
else:
    threads = 1

def update_threads():
    log(" >>> running updater")
    global convert, binpath, output_path
    board_dirs = os.listdir(output_path)
    for board in board_dirs:
        board_dir = f"{output_path}/{board}"
        # skip hidden directories and . and ..
        if not os.path.isdir(board_dir) or board.startswith('.'):
            continue
        thread_dirs = os.listdir(board_dir)
        for thread in thread_dirs:
            if not thread.isnumeric():
                log(f"\"{thread}\" isn't a valid thread id")
                continue
            thread_dir = f"{board_dir}/{thread}"
            if not os.path.isdir(thread_dir) or thread.startswith('.'):
                # skip hidden directories and . and ..
                continue
            log(f" >>> checking {thread} from /{board}/")
            meta_file_path = f"{thread_dir}/meta"
            if not os.path.exists(meta_file_path):
                log(" >>> thread has no initial data to update")
                continue
            cl4 = CL4Archiver(board, thread, binpath, output_path)
            cl4.archive(convert)


def main():

    if len(sys.argv) < 2:
        print_help()
        sys.exit()

    if '-h' in sys.argv or '--help' in sys.argv:
        print_help()
        sys.exit()

    try:
        longopts = ["no-convert", "binpath=", 'output=', 'udpate', 'parallel']
        args = getopt.getopt(sys.argv[1:], 'uhnbo:p:', longopts)
    except getopt.GetoptError as e:
        log(e.msg, 4)
        sys.exit(-1)

    global convert, binpath, output_path, threads
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
        elif opt[0] in ['--parallel', '-p']:
            threads = int(opt[1])
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
        # default output path
        if not output_path:
            output_path = '4chan_archives'
            if not os.path.exists(output_path):
                os.mkdir(output_path)
        c = CL4Archiver(board, thread, binpath, output_path=output_path)
        c.parallel = threads
        c.archive(convert)

def print_help():
    print("Usage: cl4archiver [options] <thread_url>")
    print("Options:")
    print("  -n, --no-convert\tDon't convert media files")
    print("  -b, --binpath\t\tPath to the youtube-dl binary")
    print("  -o, --output\t\tOutput path for the archives")
    print("  -u, --update\t\tUpdate existing archives")
    print("  -p, --parallel\tNumber of threads to use for media (default: 1)")
    print("  -h, --help\t\tShow this help message")

if __name__ == '__main__':
    main()
