import sys
import getopt
from .cl4archiver import CL4Archiver
from pyutils import Logger
from validators import url as urlvalidate
import os

logger = Logger()

convert = os.environ.get('CL4ARCHIVER_CONVERT', '1') == '1'
binpath = os.environ.get('CL4ARCHIVER_BINPATH', None)
remove_orig_file = os.environ.get('CL4ARCHIVER_PARALLEL', False)
output_path = os.environ.get('CL4ARCHIVER_OUTPUT')
if (threads := os.environ.get('CL4ARCHIVER_PARALLEL')):
    threads = int(threads)
else:
    threads = 1

def update_threads():
    logger.section_title("Updating Threads")
    global convert, binpath, output_path, remove_orig_file
    board_dirs = os.listdir(output_path)
    for board in board_dirs:
        board_dir = f"{output_path}/{board}"
        # skip hidden directories and . and ..
        if not os.path.isdir(board_dir) or board.startswith('.'):
            continue
        thread_dirs = os.listdir(board_dir)
        for thread in thread_dirs:
            if not thread.isnumeric():
                logger.log(f"\"{thread}\" isn't a valid thread id", 3)
                continue
            thread_dir = f"{board_dir}/{thread}"
            if not os.path.isdir(thread_dir) or thread.startswith('.'):
                # skip hidden directories and . and ..
                continue
            logger.log(f"Updating thread {thread} from /{board}/")
            meta_file_path = f"{thread_dir}/meta"
            if not os.path.exists(meta_file_path):
                logger.log("Thread was never archived and has no initial data", 3)
                continue
            cl4 = CL4Archiver(board, thread, output_path=output_path, binary_path=binpath)
            cl4.archive(convert_media=convert, remove_original=remove_orig_file)


def main():

    if len(sys.argv) < 2:
        print_help()
        sys.exit()

    if '-h' in sys.argv or '--help' in sys.argv:
        print_help()
        sys.exit()

    try:
        longopts = ["no-convert", 'remove-orig', "binpath=", 'output=', 'udpate', 'parallel']
        args = getopt.getopt(sys.argv[1:], 'uhnrbo:p:', longopts)
    except getopt.GetoptError as e:
        logger.log(e.msg, 4)
        sys.exit(-1)

    global convert, binpath, output_path, threads, remove_orig_file
    update = False
    for opt in args[0]:
        if opt[0] in ['--no-convert', '-n']:
            convert = False
        elif opt[0] in ['--remove-orig', '-r']:
            remove_orig_file = True
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
    elif args[1]:
        thread_url = args[1].pop()
        if not thread_url or not urlvalidate(thread_url):
            logger.log("No thread url provided", 4)
            sys.exit(-1)
        urlsplit = thread_url.split('/')
        if not urlsplit:
            logger.log("Unable to parse the url", 4)
            sys.exit(-1)
        board = urlsplit[3]
        thread = urlsplit[5]
        # default output path
        if not output_path:
            output_path = '4chan_archives'
            if not os.path.exists(output_path):
                os.mkdir(output_path)
        c = CL4Archiver(board, thread, output_path=output_path, binary_path=binpath)
        c.parallel = threads
        logger.section_title(f"Archiving thread {thread} from /{board}/")
        c.archive(convert_media=convert, remove_original=remove_orig_file)

def print_help():
    print("Usage: cl4archiver [options] <thread_url>")
    print("Options:")
    print("  -n, --no-convert\tDon't convert media files")
    print("  -r, --remove-orig\tRemove original file after conversion")
    print("  -b, --binpath\t\tPath to the youtube-dl binary")
    print("  -o, --output\t\tOutput path for the archives")
    print("  -u, --update\t\tUpdate existing archives")
    print("  -p, --parallel\tNumber of threads to use for media (default: 1)")
    print("  -h, --help\t\tShow this help message")

if __name__ == '__main__':
    main()
