#
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
# simple test script for the youtube evaluator
#
# usage: yp-test.py [<video-id>=riyXuGoqJlY]
#

import sys
import logging
				
from optparse import OptionParser

from yp import YouTubeClient

log = logging.getLogger('ye')
log.setLevel(logging.DEBUG)
log.addHandler(logging.StreamHandler())

def main():

    try:
        params = process_options()
        client = YouTubeClient(params)

        log.info(client)
        success = client.run()
        print("Done: %s" % str(client))

    except KeyboardInterrupt:
        # give the right exit status, 128 + signal number
        # signal.SIGINT = 2
        sys.exit(128 + 2)
    except EnvironmentError as e:
        (errno, strerror) = e.args
        try:
            print(strerror, file=sys.stderr)
        except Exception:
            pass
        sys.exit(2)

    if success:
        sys.exit(0)
    else:
        sys.exit(1)

def process_options():
    usage = "%prog [<video-id>=riyXuGoqJlY]"
    description = "YouTube Download Test Client"
    parser = OptionParser(usage=usage, description=description)
    parser.add_option("-b", "--bwlimit", type="int", dest="bwlimit", help="limit download bandwidth to BW kBps")

    options, args = parser.parse_args(sys.argv)
    params = vars(options)

    video_id = "riyXuGoqJlY"
    if len(args) >= 2:
        params['video_id'] = args[1]

    # log.debug("params: %s args: %s" % (str(params), str(args)))
    return params

if __name__ == "__main__":
    main()
