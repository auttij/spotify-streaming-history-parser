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

def most_common(lst):
    return max(set(lst), key=lst.count)

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

    if data:
      self.songs = data['songs']
      self.artists = data['artists']

    self.year = args.year
    self.count = args.count if args.count else 10
    self.extra = args.extra
    self.sortKey = args.sortKey
    self.keyword = args.keyword
    self.artists_only = args.artists

  def parse_files(self, filenames):
    for file in filenames:
      for song_data in self.songs_from_file(file):
        self.track_data(song_data)
  
  def process_data(self):
    self.filter_data()
    self.count_plays()

  def songs_from_file(self, filename):
    json_data = read_json(filename)
    for song_json in json_data:
      song_data = self.extract_data(song_json)
      if not song_data: 
        continue
      yield song_data

  def is_song(self, song_json):
    return song_json['master_metadata_track_name'] is not None

  def extract_data(self, song_json):
    if not self.is_song(song_json):
      return None
    
    key = song_json['spotify_track_uri']
    track = song_json['master_metadata_track_name']
    artist = song_json['master_metadata_album_artist_name']
    endTime = song_json['ts']
    timePlayed = song_json['ms_played']

    reason_start = song_json['reason_start']
    reason_end = song_json['reason_end']
    length = timePlayed \
      if reason_start == 'trackdone' and reason_end == 'trackdone' \
      else None

    return [key, track, artist, endTime, timePlayed, length]

  def track_data(self, song_data):
    key, track, artist, endTime, timePlayed, length = song_data

    if not key in self.songs:
      song_data = {
        'track': track,
        'artist': artist,
        'firstListen': endTime,
        'lastListen': endTime,
        'totalPlayed': timePlayed,
        'lengthMs': length,
        'plays': { endTime: timePlayed }
      }
      self.songs[key] = song_data
    else:
      self.songs[key]['totalPlayed'] += timePlayed
      self.songs[key]['lastListen'] = endTime
      self.songs[key]['plays'][endTime] = timePlayed
      if length and not self.songs[key]['lengthMs']:
        self.songs[key]['lengthMs'] = length

    if not artist in self.artists:
      self.artists[artist] = { 'totalPlayed': 0, 'artist': artist }
    self.artists[artist]['totalPlayed'] += timePlayed

  def filter_data(self):
    if not (self.year or self.keyword):
      return

    time_start = f"{self.year}-01-01 00:00"
    time_end = f"{self.year}-12-13 00:00"
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
      confirmed_length = song['lengthMs']
      length = confirmed_length if confirmed_length else most_common(list(song['plays'].values()))
      if length < 30000:
        length = 60000
      
      self.songs[key]["time"] = time_played
      self.songs[key]["length"] = convert_ms(length)
      self.songs[key]["count"] = total_listened // length

      plays = list(self.songs[key]['plays'].keys())
      first_play = plays[0]
      last_play = plays[-1]
      self.songs[key]['firstListen'] = first_play
      self.songs[key]['lastListen'] = last_play

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
  parser.add_argument("-c", "--count", help="The amount of results to show", default=10, type=int)
  parser.add_argument("-y", "--year", help="Filter results by year", default=None, type=int)
  parser.add_argument("-s", "--sortKey", help="Sort results based on Play count or total play time", choices=["time", "count"], required=False, default="time")
  parser.add_argument("-e", "--extra", help="Show some extra information about results", action="store_true")
  parser.add_argument('-k', "--keyword", help="keyword search filter", default=None)
  parser.add_argument("-a", "--artists", help="show artist statistics instead of tracks", action="store_true")
  return parser.parse_args()

if __name__ == '__main__':
  args = arg_parse()
  main(args)
