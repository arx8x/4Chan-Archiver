import sys
import getopt
from cl4archiver import CL4Archiver

try:
    args = getopt.getopt(sys.argv[1:], '', ["no-convert", "binpath="])
except getopt.GetoptError as e:
    log(e.msg, 4)
    sys.exit(-1)


convert = True
binpath = None

for opt in args[0]:
    if opt[0] == '--no-convert':
        convert = False
    elif opt[0] == '--binpath':
        binpath = opt[1]

if args[1]:
    thread_url = args[1].pop()
else:
    thread_url = ''


c = CL4Archiver(thread_url, binpath)
c.archive(convert)
