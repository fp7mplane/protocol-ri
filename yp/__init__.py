#
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
#
# YouTubeClient for evaluating downloads
#

import logging
import os
import subprocess
from threading import Timer
import time

import pycurl

from flvlib.tags import FLV, VideoTag, AudioTag
from flvlib.primitives import get_ui24,get_ui8
from yp.utils import SeekableByteQueue

log = logging.getLogger('ye')

class Player(SeekableByteQueue):
    """ Abstract class for a Player emulator  that is fed a byte stream by the downloader """

    def __init__(self):
        SeekableByteQueue.__init__(self)
        self._playout_started = 0
        self._underrunTimer = None

    def feed(self, data):
        """ new data is pushed in by the downloader """
        raise NotImplementedError()

    def mediaDuration(self):
        """ get the presentation TS of the last complete frame """
        raise NotImplementedError()

    def underrun(self):
        """ ran out of media buffer """
        self._metrics['rebuffer.events'] = self._metrics['rebuffer.events'] + 1
        log.info("%04.03f Underrun!" % time.time())

    def __str__(self):
        return ' MediaPlayer(unparsed bytes: %d, mediaDuration: %.4f)' % \
            (self.availBytes(), self.mediaDuration())
                

class FLVPlayer(Player):
    """ Reads a FLV stream and emulates playout by advancing the stream as time passes """
    FILE_HEADER_SIZE = 9
    TAG_HEADER_SIZE = 15

    def __init__(self):
        Player.__init__(self)
        self._lastAudioTS = 0
        self._lastVideoTS = 0
        self.flv = FLV(self)

    def feed(self, data):
        """ input downloaded media data here piece by piece """
        self.put(data)

        # nothing parsed yet
        if self.tell() == 0:
            if self.availBytes() >= self.FILE_HEADER_SIZE:
                self.flv.parse_header()
        else:
            tag = 0
            while tag != None:
                avail = self.availBytes()
                tag = None
                if avail >= self.TAG_HEADER_SIZE:
                    # peek for tag size
                    tag_type = get_ui8(self)
                    tag_size = get_ui24(self)
                    # log.debug("peek: %02X %u, available: %u" % (tag_type,tag_size,avail))
                    self.seek(-4, os.SEEK_CUR)
                    # size + next header size
                    if avail >= tag_size + self.TAG_HEADER_SIZE:
                        tag = self.flv.get_next_tag()
                        if type(tag) == VideoTag:
                            self._lastVideoTS = tag.timestamp
                            # log.debug("lastVideo: %u", self._lastVideoTS)
                        elif type(tag) == AudioTag:
                            self._lastAudioTS = tag.timestamp
                            # log.debug("lastAudio: %u", self._lastAudioTS)
            if not self._playout_started > 0 and self.mediaDuration() > 3:
                self._playout_started = time.time()
                log.info("%04.3f 3 seconds of media buffered, starting playout" % \
                    (self._playout_started - YouTubeClient.singleton._start_time))
            if self._playout_started > 0:
                if self._underrunTimer != None:
                    self._underrunTimer.cancel()
                t = time.time()
                self._underrunTimer = Timer(self.mediaDuration() - (t - self._playout_started), self.underrun)
                self._underrunTimer.start()
                # log.debug('%04.03f duration: %f, timer: %f' % (t, self.mediaDuration(), self.mediaDuration() - (t - self._playout_started)))

    def mediaDuration(self):
        """ get the presentation TS of the last complete frame """
        return min(self._lastVideoTS, self._lastAudioTS) / 1000.0

    def bufferedUntil(self):
        """ until when the buffer contains media """ 
        start_time = self._playout_started
        if start_time == 0:
            start_time = time.time()
        return self._playout_started + min(self._lastVideoTS, self._lastAudioTS) / 1000.0
        
    def __str__(self):
        return ' FLVPlayer(unparsed bytes: %d, last A/V TS: %u/%u)' % \
            (self.availBytes(), self._lastAudioTS, self._lastVideoTS)


class MediaNotFound(Exception):
    pass

def writeFunction(data):
    if YouTubeClient.singleton != None:
        YouTubeClient.singleton.receive(data)

def bwstats():
    """ BW Statistics, called on every sec """
    ytclient = YouTubeClient.singleton
    ytclient._bwstats = None
    now = time.time()

    downloaded = ytclient._metrics['octets.layer7']
    bps = (downloaded - bwstats._lastBytes) * 8.0  
    bwstats._lastBytes = downloaded

    _min = ytclient._metrics['bandwidth.min.bps']
    _max = ytclient._metrics['bandwidth.max.bps']
    # log.debug("tick: %s bps: %s" % (str(now), str(bps)))
    if bps > _max:
        ytclient._metrics['bandwidth.max.bps'] = bps
    if bps < _min or _min < 0:
        ytclient._metrics['bandwidth.min.bps'] = bps

    calc_delay = time.time() - now
    ytclient._bwstats = Timer(1.0 - calc_delay, bwstats)
    ytclient._bwstats.start()

class YouTubeClient(object):
    """Downloads a YouTube FLV video and evaluates download quality""" 

    singleton = None

    def __init__(self, params):
        YouTubeClient.singleton = self
     
        self._video_id = 'riyXuGoqJlY'  # default
        if 'video_id' in params:
            self._video_id = params['video_id']
        
        self.player = FLVPlayer()
        self._curl = pycurl.Curl()
        self._curl.setopt(pycurl.WRITEFUNCTION, writeFunction)
        self._curl.setopt(pycurl.CONNECTTIMEOUT, 5)
        if params['bwlimit']:
            self._curl.setopt(pycurl.MAX_RECV_SPEED_LARGE, params['bwlimit'])
            log.info('Limiting pycurl bandwidth to %d' %  params['bwlimit'])
        # self._curl.setopt(curl.TIMEOUT, 5)

        self._bwstats = None # 
        
        self._metrics = { 
            'octets.layer7': 0,
            'delay.download.ms': -1,
            'bandwidth.min.bps': -1, 'bandwidth.max.bps': -1, 'bandwidth.avg.bps': -1,
            'delay.urlresolve.ms': -1,
            'delay.srvresponse.ms': -1,
            'rebuffer.events': 0
        }

    def getURL(self):
        """ Figure out the URL for the video using youtube_dl """
        url = None
        try:
            url = subprocess.check_output(
                ["youtube-dl",'--default-search', 'auto', '-g','-f', '5', self._video_id], 
                stderr=None ).decode('UTF-8') 
        except subprocess.CalledProcessError as e:
            raise MediaNotFound(self._video_id)
        return url

    def receive(self, data):
        """ receive data from YouTube """
        if self._metrics['delay.srvresponse.ms'] == -1:
            self._metrics['delay.srvresponse.ms'] = (time.time() - self._http_start_time) * 1000.0
            # start the ticker now so compute BW stats only after the 1st server reply pkt
            bwstats._lastBytes = 0
            self._bwstats = Timer(1.0, bwstats)
            self._bwstats.start()

        self._metrics['octets.layer7'] += len(data)
        self.player.feed(data)

    def run(self):
        """ Execute """
        self._start_time = time.time()
        log.info('%04.03f Query for media URL' % (time.time() - self._start_time))
        try:
            self._url = self.getURL()
            # log.debug('%04.03f URL: %s' % (time.time(), self._url))
            self._curl.setopt(pycurl.URL, self._url)
            self._metrics['delay.urlresolve.ms'] = (time.time() - self._start_time) * 1000.0
            self._http_start_time = time.time()
            log.info('%04.03f URL extacted, starting download' % (self._http_start_time - self._start_time))
            self._curl.perform()
            self._metrics['delay.download.ms'] = (time.time() - self._http_start_time) * 1000.0
            self._metrics['bandwidth.avg.bps'] = 8.0 * self._metrics['octets.layer7'] \
                / (self._metrics['delay.download.ms'] / 1000.0)
            log.info("%04.03f Download finished" % (time.time() - self._start_time))
            self._curl.close()
        except Exception:
            self._metrics = {}
        finally:
            if self._bwstats:
                self._bwstats.cancel()
            if self.player._underrunTimer != None:
                self.player._underrunTimer.cancel()
        return self._metrics

    def __str__(self):
        return ("YouTubeClient of video_id %s, metrics: %s " % (self._video_id, str(self._metrics)))
	
