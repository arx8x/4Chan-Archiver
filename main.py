import sys
import getopt
from cl4archiver import CL4Archiver
from utils import log


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
        c = CL4Archiver(thread_url, binpath, output_path=output_path)
        c.archive(convert)


if __name__ == '__main__':
    main()
