import sys
import getopt
from cl4archiver import CL4Archiver
from utils import log
from validators import url as urlvalidate


def main():
    try:
        longopts = ["no-convert", "binpath=", 'output=']
        args = getopt.getopt(sys.argv[1:], 'nbo:', longopts)
    except getopt.GetoptError as e:
        log(e.msg, 4)
        sys.exit(-1)

    convert = True
    binpath = None
    output_path = 'archives'

    for opt in args[0]:
        if opt[0] in ['--no-convert', '-n']:
            convert = False
        elif opt[0] in ['--binpath', '-b']:
            binpath = opt[1]
        elif opt[0] in ['--output', '-o']:
            output_path = opt[1]

    if args[1]:
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
