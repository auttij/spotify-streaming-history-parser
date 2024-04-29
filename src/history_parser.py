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
  lengths = []
  for i, column in enumerate(headers):
    col = list(map(lambda x: len(str(x[i])), rows))
    lengths.append(max(col + [len(column)]) + 2)

  for i, header in enumerate(headers):
    print(f"{header.ljust(lengths[i])}", end="")
  print()

  for row in rows:
    for i, val in enumerate(row):
      print(f"{str(val).ljust(lengths[i])}", end="")
    print()

def pp(data, args):
  count = args.count
  year = args.year
  show_extra = args.extra

  sortKey = "count" if args.sortKey == "count" else "totalPlayed"

  l = sorted(data.values(), key=lambda v: v[sortKey], reverse=True)
  headers = ["Artist", "Track", "Play Count", "Time Listened"]  if not show_extra \
    else ["Artist", "Track", "Play Count", "Time Listened", "Track length", "First Listen", "Last listened"]
  keys = ["artistName", "trackName", "count", "time"] if not show_extra \
    else ["artistName", "trackName", "count", "time", "length", "endTime", "lastListen"]

  rows = [
    [line[key] for key in keys]
    for line in l[:count]
  ]

  tabulate(headers, rows)

  if year:
    print(f"\nyear filter {year}")

def aggregate_data(output_arr, file_data, filter_year=2024):
  for song in file_data:
    if filter_year:
      time_start = f"{filter_year}-01-01 00:00"
      time_end = f"{filter_year}-12-13 00:00"

      if not (time_start < song["endTime"] < time_end):
        continue

    key = f"{song['artistName']}-{song['trackName']}"
    if key not in output_arr:
      song_data = {
        'endTime': song['endTime'],
        'lastListen': song['endTime'],
        'artistName': song['artistName'],
        'trackName': song['trackName'],
        'maxListened': song['msPlayed'],
        'totalPlayed': song['msPlayed'],
        'played': [song['msPlayed']],
      }
      output_arr[key] = song_data
    else:
      output_arr[key]['totalPlayed'] += song['msPlayed']
      output_arr[key]['played'].append(song['msPlayed'])
      output_arr[key]['lastListen'] = song['endTime']
      old_max = output_arr[key]['maxListened']
      msPlayed = song['msPlayed']
      if msPlayed > old_max:
        output_arr[key]['maxListened'] = msPlayed

def convert_ms(ms):
  seconds=int(ms/1000)%60
  minutes=int(ms/(1000*60))%60
  hours=int(ms/(1000*60*60))%24
  if hours > 0:
    return f"{hours}h {minutes}min {seconds}s"
  else:
    return f"{minutes}min {seconds}s"

def most_common(lst):
    return max(set(lst), key=lst.count)

def count_plays(data):
  for key in data:
    song = data[key]
    total_listened = song['totalPlayed']
    time_played = convert_ms(total_listened)

    length = most_common(song['played'])
    length = length if length > 60000 else 60000

    try:
      data[key]["count"] = total_listened // length
      data[key]["time"] = time_played
      data[key]["length"] = convert_ms(length)
    except: 
      data[key]["count"] = 0
      data[key]["time"] = 0
      data[key]["length"] = 0
      

def main(args):
  base = "StreamingHistory_music_"

  parsed_data = {}

  for filename in get_filenames(base):
    file_data = read_json(filename)
    aggregate_data(parsed_data, file_data, args.year)
  count_plays(parsed_data)
  pp(parsed_data, args)

def arg_parse():
  parser = ArgumentParser()
  parser.add_argument("-c", "--count", help="The amount of results to show", default=10, type=int)
  parser.add_argument("-y", "--year", help="Filter results by year", default=None, type=int)
  parser.add_argument("-s", "--sortKey", help="Sort results based on Play count or total play time", choices=["time", "count"], required=False, default="count")
  parser.add_argument("-e", "--extra", help="Show some extra information about results", action="store_true")
  return parser.parse_args()

if __name__ == '__main__':
  args = arg_parse()
  main(args)