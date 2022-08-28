import json
import pandas as pd
import requests
import datetime as dt
import re

# y = json.loads(str(data))
# print(y)
def daily_games(date=None):
	if date == None:
		d = dt.date.today()
		x = d - dt.timedelta(days=1)
		year = x.year
		month = f"{x.month:02d}"
		day = f"{x.day:02d}"
		date = f'{year}{month}{day}'
	jsn = f"https://data.nba.net/10s/prod/v1/{date}/scoreboard.json"
	# jsn = f"https://data.nba.net/10s/prod/v1/20200122/scoreboard.json"
	page = requests.get(jsn)
	j = json.loads(page.content)
	daily_games = {}
	for game in range(len(j['games'])):
		game_id = j['games'][game]['gameId']
		team1 = str(j['games'][game]['vTeam']['triCode']).lower()
		team2 = str(j['games'][game]['hTeam']['triCode']).lower()
		daily_games[game_id] = [team1, team2]
	return daily_games


def get_pbp2(game_id):
	raw_game = f'https://cdn.nba.com/static/json/liveData/playbyplay/playbyplay_{game_id}.json'
	page = requests.get(raw_game)
	j = json.loads(page.content)
	df = pd.DataFrame(j['game']['actions'])
	df['clock'] = df['clock'].str.replace('PT','').replace('M',':').replace('S','')
	df['clock'] = df['clock'].str.replace('M',':')
	df['clock'] = df['clock'].str.replace('S','')
	# ndf = df[['clock', 'period', 'description', 'teamTricode', 'shotResult']]
	# ndf = ndf[ndf['shotResult'] == 'Made']
	# df.to_csv('/users/noame/downloads/pbp.csv')
	return df


def get_baskets(df):
	plays = dict()
	ndf = df[['clock', 'period', 'description', 'teamTricode', 'shotResult', 'actionType']]
	ndf = ndf[ndf['shotResult'] == 'Made']
	ndf = ndf[ndf['actionType'] != 'freethrow']
	for index, row in ndf.iterrows():
		plays.update({str(row['clock']).split(".")[0].strip("0"): [row['description'], row['period']]})
	return plays


def distribute(team1, team2, date=None):
	date = str(date).replace("-", "")
	team1 = team1.lower()
	team2 = team2.lower()
	d = daily_games(date)
	print(f"Games on: {date}")
	print(d)
	arr = [team1, team2]
	print(arr)
	try:
		game_id = (list(d.keys())[list(d.values()).index(sorted(arr))])
	except ValueError:
		game_id = (list(d.keys())[list(d.values()).index(sorted(arr, reverse=True))])
	df = get_pbp2(game_id)
	b = get_baskets(df)
	return b
