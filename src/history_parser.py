from os import path
from argparse import ArgumentParser
import sys
import json

def get_filenames(base):
  i = 0
  filepath = f"{base}{i}.json"
  names = []
  while path.exists(filepath):
    names.append(filepath)
    i += 1
    filepath = f"{base}{i}.json"
  return names

def read_json(filepath):
  with open(filepath, 'r', encoding='utf-8') as jf:
      return json.load(jf)
  
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

def print_tracks(data, args):
  count = args.count
  show_extra = args.extra

  sortKey = "count" if args.sortKey == "count" else "totalPlayed"
  song_data = data['songs']

  l = sorted(song_data.values(), key=lambda v: v[sortKey], reverse=True)
  headers = ["Artist", "Track", "Play Count", "Time Listened"]  if not show_extra \
    else ["Artist", "Track", "Play Count", "Time Listened", "Track length", "First Listen", "Last listened"]
  keys = ["artistName", "trackName", "count", "time"] if not show_extra \
    else ["artistName", "trackName", "count", "time", "length", "endTime", "lastListen"]

  rows = [
    [line[key] for key in keys]
    for line in l[:count]
  ]

  tabulate(headers, rows)

def print_artists(data, args):
  count = args.count
  headers = ["Artist", "Time Listened"]
  keys = ["artistName", "time"]
  artist_data = data['artists']
  sortKey = 'totalPlayed'

  l = sorted(artist_data.values(), key=lambda v: v[sortKey], reverse=True)

  rows = [
    [line[key] for key in keys]
    for line in l[:count]
  ]

  tabulate(headers, rows)

def pp(data, args):
  if args.artists:
    print_artists(data, args)
  else:
    print_tracks(data, args)

  print(f"\ntotal time {convert_ms(data['total'])}")

  year = args.year
  if year:
    print(f"\nyear filter {year}")

def aggregate_data(output_arr, file_data, args):

  filter_year = args.year
  filter_keyword = args.keyword
  song_arr = output_arr['songs']
  artist_arr = output_arr['artists']

  for song in file_data:
    if filter_year:
      time_start = f"{filter_year}-01-01 00:00"
      time_end = f"{filter_year}-12-13 00:00"

      if not (time_start < song["endTime"] < time_end):
        continue

    key = f"{song['artistName']}-{song['trackName']}"
    if filter_keyword:
      if not filter_keyword.lower() in key.lower():
        continue

    output_arr['total'] += song['msPlayed']

    if key not in song_arr:
      song_data = {
        'endTime': song['endTime'],
        'lastListen': song['endTime'],
        'artistName': song['artistName'],
        'trackName': song['trackName'],
        'maxListened': song['msPlayed'],
        'totalPlayed': song['msPlayed'],
        'played': [song['msPlayed']],
      }
      song_arr[key] = song_data
    else:
      song_arr[key]['totalPlayed'] += song['msPlayed']
      song_arr[key]['played'].append(song['msPlayed'])
      song_arr[key]['lastListen'] = song['endTime']
      old_max = song_arr[key]['maxListened']
      msPlayed = song['msPlayed']
      if msPlayed > old_max:
        song_arr[key]['maxListened'] = msPlayed

    artist_key = song['artistName']
    if not artist_key in artist_arr:
      artist_arr[artist_key] = { 'artistName': artist_key, 'totalPlayed': 0 }
    artist_arr[artist_key]['totalPlayed'] += song['msPlayed']

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

def count_plays(full_data):
  data = full_data['songs']

  for key in data:
    song = data[key]
    total_listened = song['totalPlayed']
    time_played = convert_ms(total_listened)

    length = most_common(song['played'])
    length = length if length > 60000 else 60000

    data[key]["time"] = time_played
    data[key]["length"] = convert_ms(length)

    try:
      data[key]["count"] = total_listened // length
    except: 
      data[key]["count"] = 0

  artist_data = full_data["artists"]
  for key in artist_data:
    artist = artist_data[key]
    total_listened = artist['totalPlayed']
    time_played = convert_ms(total_listened)
    artist["time"] = time_played

def main(args):
  base = "StreamingHistory_music_"

  parsed_data = { 'songs': {}, 'artists': {}, 'total': 0 }

  for filename in get_filenames(base):
    file_data = read_json(filename)
    aggregate_data(parsed_data, file_data, args)
  count_plays(parsed_data)
  pp(parsed_data, args)

def arg_parse():
  parser = ArgumentParser()
  parser.add_argument("-c", "--count", help="The amount of results to show", default=10, type=int)
  parser.add_argument("-y", "--year", help="Filter results by year", default=None, type=int)
  parser.add_argument("-s", "--sortKey", help="Sort results based on Play count or total play time", choices=["time", "count"], required=False, default="count")
  parser.add_argument("-e", "--extra", help="Show some extra information about results", action="store_true")
  parser.add_argument("-k", "--keyword", help="keyword search filter", default=None)
  parser.add_argument("-a", "--artists", help="show artist statistics instead of tracks", action="store_true")
  return parser.parse_args()

if __name__ == '__main__':
  args = arg_parse()
  main(args)
