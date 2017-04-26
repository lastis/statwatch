import requests
import time
import imageio
import os
import numpy as np
import threading
from livestreamer import Livestreamer

class TwitchRecorder(threading.Thread):
    def __init__(self, username):
        threading.Thread.__init__(self)
        self.username = username

        self.buf_720 = int(2e6)
        self.buf_360 = int(250*1e6)
        self.buf_160 = int(1e6)
        
    def run(self):
        print('Starting ' + self.username) 
        session = Livestreamer()
        session.set_option('http-headers', 'Client-ID=jzkbprff40iqj646a697cyrvl0zt2m6')
        streams = session.streams("http://twitch.tv/"+self.username)
        assert len(streams) != 0, 'Stream not open.'

        directory = os.path.join('images', self.username)
        try:
            os.makedirs(directory)
        except:
            pass
        
        qualities = streams.keys()
        stream = None
        if '360p' in qualities:
            stream = streams['360p']
        # elif 'medium' in qualities:
        #     stream = streams['medium']
        assert stream is not None, self.username + ': No valid stream quality found.'

        period = 10
        timer = time.time() + period
        data = b''
        with stream.open() as fd:
            while True:
                data += fd.read(self.buf_160)
                if time.time() > timer:
                    timer = time.time() + period

                    ts = str(int(time.time()))
                    fname = self.username+'_'+ts
                    path = os.path.join('movies', fname + '.mp4')
                    print(path)
                    open(path, 'wb').write(data)
                    data = b''


            

class MovieAnalyser(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

        self.crop_360_defeat_victory = [140, 220, 210, 410];

        self.score_img_720 = imageio.imread('reference_images/image_01_720p.jpg').flatten()
        self.score_img_160 = imageio.imread('reference_images/image_01_160p.jpg').flatten()
        self.score_img_360 = imageio.imread('reference_images/image_01_360p.jpg').flatten()

        # self.score_160_thresh = 1.5e8/16
        # self.score_360_thresh = 1.5e8/8
        # self.score_360_thresh = 0.001
        self.score_thresh = 0.001

        self.tab_720 = imageio.imread('reference_images/tab_01_720p.jpg').flatten()
        self.tab_360 = imageio.imread('reference_images/tab_01_360p.jpg')[270:,:].flatten()
        self.tab_160 = imageio.imread('reference_images/tab_01_160p.jpg').flatten()

        self.tab_thresh = 0.0008
        # self.tab_160_thresh = 1.5e8/16
        # self.tab_360_thresh = 1.5e8/8
        # self.tab_360_thresh = 0

    def run(self):
        print('Starting analyser')
        while True:
            for root, dirs, files, in os.walk('movies'):
                for name in files:
                    path = os.path.join(root, name)
                    reader = imageio.get_reader(path,  'ffmpeg')
                    fps = reader.get_meta_data()['fps']
                    duration = reader.get_meta_data()['duration']
                    analysis_fps = 2
                    print('Analyzing: ' + path)

                    for i in range(int(duration*analysis_fps)):
                        i = int(i / analysis_fps * fps)
                        img = reader.get_data(i)

                        score = self.is_score(img)
                        tab = self.is_tab(img)
                        if score < self.score_thresh or tab < self.tab_thresh:
                            un = name.split('.')[0].rsplit('_', 1)[0]
                            ts = int(name.split('.')[0].rsplit('_', 1)[1]) + i / fps
                            ts = int(ts)
                            fname = un + '_' + str(ts) + '.png'
                            path_img = os.path.join('images', un, fname)
                            imageio.imwrite(path_img, img)
                            print(path_img, tab, score)
                    os.remove(path)
            time.sleep(1)

    def is_score(self, img):
        img = img.flatten()
        return np.sum((img - self.score_img_360)*(img - self.score_img_360))/(255*255*len(img))
        # return np.sum((img - self.score_img_160)*(img - self.score_img_160))
        # return np.sum((img - self.score_img_720)*(img - self.score_img_720))

    def is_tab(self, img):
        img = img[270:,:].flatten()
        return np.sum((img - self.tab_360)*(img - self.tab_360))/(255*255*len(img))
        # return np.sum((img - self.tab_160)*(img - self.tab_160))
        # return np.sum((img - self.tab_720)*(img - self.tab_720))



limit = 100;
streamers_dict = [1]*limit
streamers = []
offset = 0
while len(streamers_dict) == limit:
    url = 'https://api.twitch.tv/kraken/search/streams?query=overwatch&limit='+str(limit)+'&offset='+str(offset)
    r = requests.get(url, headers = {"Client-ID" : 'jzkbprff40iqj646a697cyrvl0zt2m6'}, timeout = 15)
    r.raise_for_status()
    info = r.json()
    streamers_dict = info['streams']
    for streamer in streamers_dict:
        streamers.append(streamer['channel']['name'])
    offset += limit
    time.sleep(1)

print(streamers)

N = 15
for i in range(N):
    rec = TwitchRecorder(streamers[i])
    rec.start()
    time.sleep(0.5)

analyser = MovieAnalyser()
analyser.start()
