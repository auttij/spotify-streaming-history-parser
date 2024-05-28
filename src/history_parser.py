import os
from argparse import ArgumentParser
import json

### printing utils 

def tabulate(headers, rows):
  index_len = len(str(len(rows)))
  lengths = []
  for i, column in enumerate(headers):
    col = list(map(lambda x: len(str(x[i])), rows))
    lengths.append(max(col + [len(column)]) + 2)

  header_row = [" " * index_len] + [f"{header.ljust(lengths[i])}" for i, header in enumerate(headers)]
  print(" ".join(header_row))

  for i, row in enumerate(rows):
    line = [str(i + 1).rjust(index_len)] + [f"{str(val).ljust(lengths[j])}" for j, val in enumerate(row)]
    print(" ".join(line))

### utils functions

def convert_ms(ms):
  seconds=int(ms/1000)%60
  minutes=int(ms/(1000*60))%60
  hours=int(ms/(1000*60*60))%24
  days = int(ms/(1000*60*60*24))
  if days > 0:
    return f"{days}d {hours}h {minutes}min {seconds}s"
  if hours > 0:
    return f"{hours}h {minutes}min {seconds}s"
  else:
    return f"{minutes}min {seconds}s"

def estimate_time(plays):
  # Round to 1 sec
  rounded_values = list(round_1000(x) for x in plays)

  # Filter out times lasting under 10s, to get rid of skips
  non_zero = [val for val in rounded_values if not val < 10000]

  # if no listens remain keep longest listen
  if len(non_zero) == 0:
    non_zero = [max(rounded_values)]

  # Get most common occurency
  # If same track is listened through multiple times,
  # this value is most likely the track length
  common = most_common(non_zero)

  # if the most common occurency has only been listened once
  # get the longest listen instead. More accurate results for
  # songs with few listening times
  if non_zero.count(common) == 1:
    common = max(non_zero)
  return common

def most_common(lst):
    return max(set(lst), key=lst.count)

def round_1000(x):
  return int(round(x / 1000.0)) * 1000

### File utils

def json_files(data_folder):
  folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), data_folder)
  return [os.path.join(data_folder, filename) for filename in os.listdir(folder) if filename.endswith('.json')]

def read_json(filepath):
  print(f'reading file {filepath}')
  with open(filepath, 'r', encoding='utf-8') as jf:
    return json.load(jf)
  
def write_json(filepath, data):
  with open(filepath, 'w', encoding='utf-8') as jf:
    json.dump(data, jf)

class Statistics():
  def __init__(self, args, data=None):
    self.songs = {}
    self.artists = {}
    self.total = 0
    self.flavor = None

    if data:
      self.songs = data['songs']
      self.artists = data['artists']

    self.year_start = None
    self.year_end = None
    self.year = None
    if (args.year):
      self.year_start = args.year[0]
      self.year_end = args.year[-1]
      self.year = f"{self.year_start}..{self.year_end}" if len(args.year) > 1 else f"{self.year_start}"
    self.count = args.count
    self.extra = args.extra
    self.sortKey = args.sortKey
    self.keyword = args.keyword
    self.artists_only = args.artists

    self.track_key = None

  def recognize_data_flavor(self, song_data):
    if 'master_metadata_track_name' in song_data:
      self.flavor = 'full'
      self.track_key = 'master_metadata_track_name'
      self.artist_key = 'master_metadata_album_artist_name'
      self.endtime_key = 'ts'
      self.ms_key = 'ms_played'
    else:
      self.flavor = 'partial'
      self.track_key = 'trackName'
      self.artist_key = 'artistName'
      self.endtime_key = 'endTime'
      self.ms_key = 'msPlayed'

  def parse_files(self, filenames):
    for file in filenames:
      for song_data in self.songs_from_file(file):
        self.track_data(song_data)
  
  def process_data(self):
    self.filter_data()
    self.count_plays()
    self.count_artist_data()

  def songs_from_file(self, filename):
    json_data = read_json(filename)
    if self.flavor is None:
      self.recognize_data_flavor(json_data[0])
    for song_json in json_data:
      song_data = self.extract_data(song_json)
      if not song_data: 
        continue
      yield song_data

  def is_song(self, song_json):
    return song_json[self.track_key] is not None

  def extract_data(self, song_json):
    if not self.is_song(song_json):
      return None
    
    track = song_json[self.track_key]
    artist = song_json[self.artist_key]
    key = f"{artist}-{track}"
    endTime = song_json[self.endtime_key]
    timePlayed = song_json[self.ms_key]

    return [key, track, artist, endTime, timePlayed]

  def track_data(self, song_data):
    key, track, artist, endTime, timePlayed = song_data

    if not key in self.songs:
      song_data = {
        'track': track,
        'artist': artist,
        'firstListen': endTime,
        'lastListen': endTime,
        'totalPlayed': timePlayed,
        'plays': { endTime: timePlayed }
      }
      self.songs[key] = song_data
    else:
      self.songs[key]['totalPlayed'] += timePlayed
      self.songs[key]['lastListen'] = endTime
      self.songs[key]['plays'][endTime] = timePlayed

  def filter_data(self):
    if not (self.year_start or self.keyword):
      return

    time_start = f"{self.year_start}-01-01 00:00"
    time_end = f"{self.year_end}-12-13 00:00"
    def year_filter(time):
      if self.year:
        return time_start < time < time_end
          
    for key, song in list(self.songs.items()):
      if self.keyword:
        kw = self.keyword.lower()
        track = song['track']
        artist = song['artist']
        if not (kw in track.lower() or kw in artist.lower()):
          del self.songs[key]
          continue

      if self.year:
        plays = song['plays']
        filtered = { k: w for k, w in plays.items() if year_filter(k) }
        song['plays'] = filtered
        song['totalPlayed'] = sum(song['plays'].values())
        if not filtered:
          del self.songs[key]

  def count_plays(self):
    for key in self.songs:
      song = self.songs[key]
      total_listened = song['totalPlayed']
      self.total += total_listened
      time_played = convert_ms(total_listened)
      length = estimate_time(song['plays'].values())

      if length < 30000:
        length = 60000
      
      self.songs[key]["time"] = time_played
      self.songs[key]["length"] = convert_ms(length)
      self.songs[key]["count"] = total_listened // length

      plays = list(self.songs[key]['plays'].keys())
      first_play = min(plays)
      last_play = max(plays)
      self.songs[key]['firstListen'] = first_play
      self.songs[key]['lastListen'] = last_play

  def count_artist_data(self):
    for song in list(self.songs.values()):
      artist = song['artist']
      totalPlayed = song['totalPlayed']
      if not artist in self.artists:
        self.artists[artist] = { 'totalPlayed': 0, 'artist': artist }
      self.artists[artist]['totalPlayed'] += totalPlayed
    
    for key in self.artists:
      artist = self.artists[key]
      artist['time'] = convert_ms(artist['totalPlayed'])

  def pretty_print(self):
    if self.artists_only:
      self.pretty_print_artists()
    else:
      self.pretty_print_songs()

    print(f"\ntotal time {convert_ms(self.total)}")

    if self.year:
      print(f"\nyear filter {self.year}")

  def pretty_print_songs(self):
    count = self.count
    show_extra = self.extra

    sortKey = "count" if self.sortKey == "count" else "totalPlayed"

    l = sorted(self.songs.values(), key=lambda v: v[sortKey], reverse=True)
    headers = ["Artist", "Track", "Play Count", "Time Listened"]  if not show_extra \
      else ["Artist", "Track", "Play Count", "Time Listened", "Track length", "First Listen", "Last listened"]
    keys = ["artist", "track", "count", "time"] if not show_extra \
      else ["artist", "track", "count", "time", "length", "firstListen", "lastListen"]

    rows = [
      [line[key] for key in keys]
      for line in l[:count]
    ]
    tabulate(headers, rows)

  def pretty_print_artists(self):
    count = args.count
    headers = ["Artist", "Time Listened"]
    keys = ["artist", "time"]
    sortKey = 'totalPlayed'

    l = sorted(self.artists.values(), key=lambda v: v[sortKey], reverse=True)

    rows = [
      [line[key] for key in keys]
      for line in l[:count]
    ]

    tabulate(headers, rows)

  def write_to_file(self, filename):
    write_json(filename, {'songs': self.songs, 'artists': self.artists, 'total': self.total })

def main(args):
  data = None
  if os.path.exists('parsed.json'):
    data = read_json('parsed.json')
  s = Statistics(args, data)
  if not data:
    s.parse_files(json_files('data'))
    s.write_to_file('parsed.json')
  s.process_data()
  s.pretty_print()

def arg_parse():
  parser = ArgumentParser()
  parser.add_argument("-a", "--artists", help="Show artist statistics instead of tracks", action="store_true")
  parser.add_argument("-c", "--count", help="The amount of results to show", default=10, type=int)
  parser.add_argument("-e", "--extra", help="Show some extra information about results", action="store_true")
  parser.add_argument('-k', "--keyword", help="Keyword search filter", default=None)
  parser.add_argument("-s", "--sortKey", help="Sort results based on Play count or total play time", choices=["time", "count"], required=False, default="count")
  parser.add_argument("-y", "--year", help="Filter results by year or range of years", action="extend", nargs="+", default=None)
  return parser.parse_args()

if __name__ == '__main__':
  args = arg_parse()
  main(args)
