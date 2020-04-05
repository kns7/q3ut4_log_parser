#!/usr/bin/env python
# -*- coding: utf-8 -*-

import cgi
import os
import re
import sqlite3
import sys


# Patterns
frag_prog = re.compile(r"^ *[0-9]+:[0-9]{2} Kill: [0-9]+ [0-9]+ [0-9]+: (?!<world>)(.*) killed (.*) by (?!MOD_CHANGE_TEAM$|MOD_FALLING$|MOD_WATER$|MOD_LAVA$|UT_MOD_BLED$|UT_MOD_FLAG$)(.*)$")
playerjoins_prog = re.compile(r'^ *([0-9]+):([0-9]+) ClientUserinfo: ([0-9]+) (.*)$')
playerchange_prog = re.compile(r"^ *[0-9]+:[0-9]+ ClientUserinfoChanged: ([0-9]+) (.*)$")
playerquits_prog = re.compile(r"^ *([0-9]+):([0-9]+) ClientDisconnect: ([0-9]+)$")
endgame_prog = re.compile(r"^ *([0-9]+):([0-9]+) ShutdownGame:$")
initround_prog = re.compile(r"^ *([0-9]+):([0-9]+) InitRound: (.*)$")
item_prog = re.compile(r"^ *[0-9]+:[0-9]{2} Item: ([0-9]+) (?!<world>)(.*)$")
flag_prog = re.compile(r"^ *[0-9]+:[0-9]{2} Flag: ([0-9]+) ([0-9]+): (.*)$")
teamscore_prog = re.compile(r"^ *([0-9]+):([0-9]+) red:([0-9]+)[ ]*blue:([0-9]+)$")
chat_prog = re.compile(r"^ *[0-9]+:[0-9]{2} (say|sayteam): [0:9]+ (?!<world>)(.*): (.*)$")

# Database connection
db_conn = None


# Create db
def create_db():
	global db_conn
	db_conn = sqlite3.connect(':memory:')
	#db_conn = sqlite3.connect('q3ut4.sqlite')
	db_conn.execute('create table frags (fragger text, fragged text, weapon text)')
	db_conn.execute('create table games (player text, start integer, stop integer)')
	db_conn.execute('create table flags (player text, event text)')
	db_conn.execute('create table score (player text, score int)')
	db_conn.execute('create table chats (player text, phrase text)')
	db_conn.execute('create table rounds (id int, winner text, red_score int, blue_score int)')
	db_conn.execute('create table teams (round_id int, player text, color text)')
	db_conn.commit()


# Read the log and populate db
def parse_log(logpath):
	global db_conn

	idd = {}
	logf = open(logpath, 'r')
	team = {}
	round_id = 0;
    
	while 1:
		logline = logf.readline()
		if (not logline):
			break

		m = frag_prog.match(logline)
		if (m):
			# Update the frags table
			db_conn.execute(
					'''insert into frags values (?, ?, ?)''', 
					(m.group(1), m.group(2), m.group(3)))
			continue

		m = playerjoins_prog.match(logline)
		if (m):
			if (m.group(3) not in idd):
				playerinfos = re.split(r"\\", m.group(4))
				playername = playerinfos[playerinfos.index('name')+1]
				time = int(m.group(1))*60 + int(m.group(2))
				# Update the players id dictionary
				idd[m.group(3)] = playername
				# And the player games table
				db_conn.execute(
					'''insert into games values (?, ?, -1)''',
					(playername, time))
			continue

		m = playerchange_prog.match(logline)
		if (m):
			playerinfos = re.split(r"\\", m.group(2))
			teamNb = int(playerinfos[playerinfos.index('t')+1])
			name = playerinfos[playerinfos.index('n')+1]
			team[m.group(1)] = teamNb
			continue
		
		m = playerquits_prog.match(logline)
		if (m):
			time = int(m.group(1))*60 + int(m.group(2))
			try:
				# Update the games table
				db_conn.execute(
					'''update games set stop=? where player = ? and stop = -1''',
					(time, idd[m.group(3)]))
				# And the players id dictionary
				del idd[m.group(3)]
				del team[m.group(3)]
			except KeyError:
				pass # Somehow, somebody disconnected without begin there in the
				     # first place, ignore it
			continue

		m = initround_prog.match(logline)
		if (m):
			round_id = round_id + 1
			db_conn.execute('''insert into rounds values(?, ?, ?, ?)''', (round_id,'', 0, 0))
			continue

		m = endgame_prog.match(logline)
		if (m):
			time = int(m.group(1))*60 + int(m.group(2))
			# New game, make everybody quits
			for k,v in idd.iteritems():
				db_conn.execute(
					'''update games set stop=? where player = ? and stop = -1''',
					(time, v))
				pass
			idd = {}
			team = {}
			continue

		m = item_prog.match(logline)
		if (m):
			if( m.group(2) == "team_CTF_redflag" or m.group(2) == "team_CTF_blueflag" ):
				db_conn.execute(
					'''insert into flags values (?, ?)''', 
					(idd[m.group(1)], "CATCH"))
				pass
			continue
		
		m = flag_prog.match(logline)
		if (m):
			if int(m.group(2)) == 0 :
				db_conn.execute(
					'''insert into flags values (?, ?)''', 
					(idd[m.group(1)], "DROP"))
				pass
			elif int(m.group(2)) == 1 :
				db_conn.execute(
					'''insert into flags values (?, ?)''', 
					(idd[m.group(1)], "RETURN"))
				pass
			elif int(m.group(2)) == 2 :
				db_conn.execute(
					'''insert into flags values (?, ?)''', 
					(idd[m.group(1)], "CAPTURE"))
				pass				
			continue
		m = teamscore_prog.match(logline)
		if(m):
			red_score = int(m.group(3))
			blue_score = int(m.group(4))
			#sys.stderr.write( 'red: ' + str(red_score) + ' blue: '+ str(blue_score) + '\n' )

			winner = ''
			if red_score > blue_score:
				winner = 'RED'
			if blue_score > red_score:
				winner = 'BLUE'
			db_conn.execute('''update rounds set winner=?, red_score=?, blue_score=? where id = ?''', (winner, red_score, blue_score, round_id))
			
			for k,v, in team.iteritems():
				player = idd[k]
				color = ''
				if v==1:
					color = 'RED'
				if v==2:
					color = 'BLUE'
				db_conn.execute('''insert into teams values(?,?,?)''', (round_id, player, color))
				
				#sys.stderr.write( player + ' ' + str(round_id) + ' ' + color + '\n' )
				if( (v == 1 and red_score > blue_score)
					or ( v == 2 and red_score < blue_score ) ):
					# player win
					db_conn.execute(
						'''insert into score values(?,?)''',
						(idd[k], 1))
				elif( (v == 1 and red_score < blue_score)
					  or ( v == 2 and red_score > blue_score ) ):
					# player lose
					db_conn.execute(
						'''insert into score values(?,?)''',
						(idd[k], -1))
			continue
		m = chat_prog.match(logline)
		if(m):
			#print(m.group(2), m.group(3))
			db_conn.execute(
					'''insert into chats values (?, ?)''',
					(m.group(2), m.group(3)))
			continue
	db_conn.commit()
	logf.close()

def filter_db( ratio ):
	global db_conn

	curs = db_conn.cursor()
	curs.execute('''
select player, sum(stop-start) as presence 
from games
group by lower(player)
order by sum(stop-start) desc
''')
	playtime = []
	
	for pt in curs:
		playtime.append(pt)
		
	max_time = playtime[0][1]
	
	for pt in playtime:
		if pt[1] < ratio * max_time:
			sys.stderr.write(pt[0]+' removed from database\n')
			db_conn.execute('''delete from frags where fragger = (?)''', (pt[0],))
			db_conn.execute('''delete from games where player = (?)''', (pt[0],))
			db_conn.execute('''delete from flags where player = (?)''', (pt[0],))
			db_conn.execute('''delete from score where player = (?)''', (pt[0],))
			db_conn.execute('''delete from chats where player = (?)''', (pt[0],))

	db_conn.execute('''delete from frags where fragger not in (select player from games)
	                                           or fragged not in (select player from games)''')
	db_conn.execute('''delete from flags where player not in (select player from games)''')
	db_conn.execute('''delete from score where player not in (select player from games)''')
	db_conn.execute('''delete from chats where player not in (select player from games)''')
	db_conn.execute('''delete from teams where player not in (select player from games)''')
	
	db_conn.commit()
	
	#player, max_time = playtime[0]	
	#sys.stderr.write(player + ' ' + str(max_time)+'\n')
	
			

# 
def frags_repartition():
	global db_conn
	print "<a name='frags-player'><h2 class='mt-5'>Frags repartition per player</h2></a>"

	curs = db_conn.cursor()
	curs.execute('''
select fragger, fragged, count(*) as frags 
from frags
group by lower(fragger), lower(fragged) 
order by lower(fragger) asc, count(*) desc
''')
	player = None
	for row in curs:
		if (player != row[0].lower()):
			if (player):
				print "} ; makeChart('%s',datas,'fragged')</script>" % player
			print "<h3>%s fragged:</h3><canvas id='%s_fragged' width='480' height='480'></canvas>" % (cgi.escape(row[0]),cgi.escape(row[0].lower()))
			print "<script>datas = {"
			player = row[0].lower()

		print "'%s':" % cgi.escape(row[1])
		print "%s," % str(row[2])
	print "} ; makeChart('%s',datas,'fragged')</script>" % player


# 
def death_repartition():
	global db_conn
	print "<a name='deaths-player'><h2 class='mt-5'>Deaths repartition per player</h2></a>"

	curs = db_conn.cursor()
	curs.execute('''
select fragged, fragger, count(*) 
from frags 
group by lower(fragged), lower(fragger)
order by lower(fragged) asc, count(*) desc
''')
	player = None
	for row in curs:
		if (player != row[0].lower()):
			if (player):
				print "} ; makeChart('%s',datas,'fraggedby')</script>" % player
			print "<h3>%s has been fragged by:</h3><canvas id='%s_fraggedby' width='480' height='480'></canvas>" % (cgi.escape(row[0]),cgi.escape(row[0].lower()))
			print "<script>datas = {"
			player = row[0].lower()

		print "'%s':" % cgi.escape(row[1])
		print "%s," % str(row[2])
	print "} ; makeChart('%s',datas,'fraggedby')</script>" % player


# 
def favorite_weapons():
	global db_conn
	print "<a name='weapons-player'><h2 class='mt-5'>Favorite weapons per player</h2></a>"
	curs = db_conn.cursor()
	curs.execute('''
select fragger, weapon, count(*) as frags 
from frags 
group by lower(fragger), lower(weapon) 
order by lower(fragger) asc, count(*) desc
''')
	player = None
	for row in curs:
		if (player != row[0].lower()):
			if (player):
				print "} ; makeChart('%s',datas,'weapons')</script>" % player
			print "<h3 class='mt-4'>%s weapons:</h3><canvas id='%s_weapons' width='480' height='480'></canvas>" % (cgi.escape(row[0]),cgi.escape(row[0].lower()))
			print "<script>datas = {"
			player = row[0].lower()

		print "'%s':" % cgi.escape(row[1].replace('UT_MOD_', ''))
		print "%s," % str(row[2])
	print "} ; makeChart('%s',datas,'weapons')</script>" % player


#
def fdratio_ranking():
	global db_conn
	print """\
    <a name="frags-deaths"><h2 class='mt-5'>Frag/death ratio-based ranking <small class='text-muted'>Ratio between Kills and deaths</small></h2></a>
    <table class='table table-hover table-sm'>
	<thead class='thead-dark'><tr><th>Rank</th><th>Player</th><th>Ratio</th></tr></thead>
	<tbody>\
"""
	players_curs = db_conn.cursor()
	players_curs.execute('''
select fragger
from frags
group by lower(fragger)
''')

	ratios = []
	for players_row in players_curs:
		tuple = (players_row[0],)

		frags_curs = db_conn.cursor()
		frags_curs.execute('''
select count(*)
from frags
where lower(fragger) = lower(?)
	and fragger != fragged
''', tuple)
		frags_row = frags_curs.fetchone()

		deaths_curs = db_conn.cursor()
		deaths_curs.execute('''
select count(*)
from frags
where lower(fragged) = lower(?)
''', tuple)
		deaths_row = deaths_curs.fetchone()

		try:
			ratios.append((players_row[0], float(frags_row[0]) / float(deaths_row[0])))
		except ZeroDivisionError:
			ratios.append((players_row[0], 666.0))

	ratios.sort(key=lambda ratio: ratio[1], reverse=True)
	i = 1
	for r in ratios:
		print "<tr><th>%s</th><td>%s</td><td>%f</td></tr>" % (i, cgi.escape(r[0]), r[1])
		i += 1
	print "</tbody></table>"

#
def frag_ranking():
	global db_conn
	print """\
    <a name="frags"><h2 class='mt-5'>Frag-based ranking <small class='text-muted'>Number of Kills</small></h2></a>
    <table class='table table-hover table-sm'>
	<thead class='thead-dark'><tr><th>Rank</th><th>Player</th><th>Kills</th></tr></thead>
	<tbody>\
"""
	curs = db_conn.cursor()
	curs.execute('''
select fragger, count(*) as frags 
from frags 
where fragger != fragged
group by lower(fragger)
order by count(*) desc, lower(fragger) asc
''')
	i = 1
	for row in curs:
		print "<tr><th>%s</th><td>%s</td><td>%s</td</tr>" % (i, row[0], row[1])
		i += 1
	print "</tbody></table>"

#
def presence_ranking():
	global db_conn
	print """\
    <a name="presence"><h2 class='mt-5'>Presence-based ranking <small class='text-muted'>Total time spent on the Server</small></h2></a>
    <table class='table table-hover table-sm'>
	<thead class='thead-dark'><tr><th>Rank</th><th>Player</th><th>Time</th></tr></thead>
	<tbody>\
"""
	curs = db_conn.cursor()
	curs.execute('''
select player, sum(stop-start) as frags 
from games
group by lower(player)
order by sum(stop-start) desc
''')
	i = 1
	for row in curs:
		hours = int(row[1]) / 3600
		minutes = (int(row[1]) - hours*3600) / 60
		seconds = (int(row[1]) - minutes*60) % 60
		print "<tr><th>%s</th><td>%s</td><td>%i:%.2i:%.2i</td></tr>" % (i, row[0], hours, minutes, seconds)
		i += 1
	print "</tbody></table>"

#
def he_ranking():
	global db_conn
	print """\
    <a name="bomber"><h2 class='mt-5'>Bomber ranking <small class='text-muted'>Kills with HE grenades</small></h2></a>
    <table class='table table-hover table-sm'>
	<thead class='thead-dark'><tr><th>Rank</th><th>Player</th><th>Kills</th></tr></thead>
	<tbody>\
"""
	curs = db_conn.cursor()
	curs.execute('''
select fragger, count(*) as frags 
from frags 
where weapon = "UT_MOD_HEGRENADE"
group by lower(fragger)
order by count(*) desc, lower(fragger) asc
''')
	i = 1
	for row in curs:
		print "<tr><th>%s</th><td>%s</td><td>%s</td</tr>" % (i, row[0], row[1])
		i += 1
	print "</tbody></table>"

#
def sniper_ranking():
	global db_conn
	print """\
    <a name="sniper"><h2 class='mt-5'>Sniper ranking <small class='text-muted'>Kills with Sniper rifles</small></h2></a>
    <table class='table table-hover table-sm'>
	<thead class='thead-dark'><tr><th>Rank</th><th>Player</th><th>Kills</th></tr></thead>
	<tbody>\
"""
	curs = db_conn.cursor()
	curs.execute('''
select fragger, count(*) as frags 
from frags 
where weapon = "UT_MOD_SR8" or weapon = "UT_MOD_PSG1"
group by lower(fragger)
order by count(*) desc, lower(fragger) asc
''')
	i = 1
	for row in curs:
		print "<tr><th>%s</th><td>%s</td><td>%s</td</tr>" % (i, row[0], row[1])
		i += 1
	print "</tbody></table>"

def capture_ranking():
	global db_conn
	print """\
    <a name="capture"><h2 class='mt-5'>Capture ranking <small class='text-muted'>Number of flags captured</small></h2></a>
    <table class='table table-hover table-sm'>
	<thead class='thead-dark'><tr><th>Rank</th><th>Player</th><th>Captures</th></tr></thead>
	<tbody>\
"""
	curs = db_conn.cursor()
	curs.execute('''
select player, count(*) as flags
from flags
where event = "CAPTURE"
group by lower(player)
order by count(*) desc, lower(player) asc
''')
	i = 1
	for row in curs:
		print "<tr><th>%s</th><td>%s</td><td>%s</td</tr>" % (i, row[0], row[1])
		i += 1
	print "</tbody></table>"

def attack_ranking():
	global db_conn
	print """\
    <a name="attack"><h2 class='mt-5'>Attack ranking <small class='text-muted'>Number of flags catched</small></h2></a>
    <table class='table table-hover table-sm'>
	<thead class='thead-dark'><tr><th>Rank</th><th>Player</th><th>Catches</th></tr></thead>
	<tbody>\
"""
	curs = db_conn.cursor()
	curs.execute('''
select player, count(*) as flags
from flags
where event = "CATCH"
group by lower(player)
order by count(*) desc, lower(player) asc
''')
	i = 1
	for row in curs:
		print "<tr><th>%s</th><td>%s</td><td>%s</td</tr>" % (i, row[0], row[1])
		i += 1
	print "</tbody></table>"

def defense_ranking():
	global db_conn
	print """\
	<a name='defense'><h2 class='mt-5'>Defense ranking <small class='text-muted'>Number of flags returned</small></h2></a>	
    <table class='table table-hover table-sm'>
	<thead class='thead-dark'><tr><th>Rank</th><th>Player</th><th>Returns</th></tr></thead>
	<tbody>\
"""
	curs = db_conn.cursor()
	curs.execute('''
select player, count(*) as flags
from flags
where event = "RETURN"
group by lower(player)
order by count(*) desc, lower(player) asc
''')
	i = 1
	for row in curs:
		print "<tr><th>%s</th><td>%s</td><td>%s</td</tr>" % (i, row[0], row[1])
		i += 1
	print "</tbody></table>"

def score_ranking():
	global db_conn
	print """\
	<a name='score'><h2 class='mt-5'>Score ranking <small class='text-muted'>based on victories vs. defeats</small></h2></a>
	<table class='table table-hover table-sm'>
	<thead class="thead-dark">
        <tr><th>Rank</th><th>Player</th><th>Victories</th><th>Defeats</th><th>Points</th></tr>
	</thead>
	<tbody>\
"""
	curs = db_conn.cursor()
	curs.execute('''
select player, COALESCE(win,0), COALESCE(lost,0), COALESCE(win,0) - COALESCE(lost,0)  as score
from
score
left outer join
(
  select player as player1, count(*) as win
  from score
  where score > 0
  group by lower(player)
) t1
on score.player=t1.player1
left outer join
(
  select player as player2, count(*) as lost
  from score
  where score < 0
  group by lower(player)
) t2
on score.player = t2.player2
group by lower(player1)
order by score desc, lower(player1) asc
''')
	i = 1
	for row in curs:

		print "<tr><th>%s.</th><td>%s</td><td>%s</td><td>%s</td><th>%s</th></tr>" % (i, row[0], row[1], row[2], row[3])
		i += 1
	print "</tbody></table>"

def chat_ranking():
	global db_conn
	print """\
    <a name="chat"><h2 class='mt-5'>Chat ranking <small class='text-muted'>Number of chats</small></h2></a>
    <table class='table table-hover table-sm'>
	<thead class="thead-dark">
        <tr><th>Rank</th><th>Player</th><th>Chats</th></tr>
	</thead>
	<tbody>\
"""
	curs = db_conn.cursor()
	curs.execute('''
select player, count(*) as chats
from chats
group by lower(player)
order by count(*) desc, lower(player) asc
''')
	i = 1
	for row in curs:
		print "<tr><th>%s.</th><td>%s</td><td>%s</td></tr>" % (i, row[0], row[1])
		i += 1
	print "</tbody></table>"
	
def best_teammates():
	global db_conn
	print """\
    <a name='teammates'><h2 class='mt-5'>Best teammates per player</h2></a>
	<ol>\
"""
	curs = db_conn.cursor()
	curs.execute('''\
SELECT DISTINCT player as player
FROM teams
ORDER BY player ASC
''')
	players = []
	for row in curs:
		players.append(row[0])

	for player in players:
		print "<h3>%s :</h3>" % player
		print "<table>"
		curs.execute('''
SELECT name1, teamate, oponent
FROM
(
  SELECT player2 as name1, count(*) as teamate
  FROM
  (
    SELECT player as name11, color, round_id
    FROM teams
    WHERE player=\"%s\" AND color!=\"\"
  ) t1
  LEFT OUTER JOIN
  (
    SELECT player as player2, color, round_id
    FROM teams
    WHERE player!=\"%s\" AND color!=\"\"
  ) t2
  ON t1.color=t2.color AND t1.round_id = t2.round_id
  GROUP BY LOWER(player2)
  ORDER BY count(*) DESC, LOWER(player2) ASC
) tt1
LEFT OUTER JOIN
(
  SELECT player2 as name2, count(*) as oponent
  FROM
  (
    SELECT player as player1, color, round_id
    FROM teams
    WHERE player=\"%s\" AND color!=\"\"
  ) t1
  LEFT OUTER JOIN
  (
    SELECT player as player2, color, round_id
    FROM teams
    WHERE player!=\"%s\" AND color!=\"\"
  ) t2
  ON t1.color!=t2.color AND t1.round_id = t2.round_id
  GROUP BY LOWER(player2)
  ORDER BY count(*) DESC, LOWER(name2) ASC
) tt2
ON tt1.name1=tt2.name2
''' % (player, player, player, player))
		for row in curs:
			print """\
<tr>
<td style="width: 180px;">%s : </td>
<td> %s </td>
<td> %s </td>
</tr>""" % (row[0], row[1], row[2])
	

# Main function
def main():
	global db_conn

	if (len(sys.argv) < 2):
		sys.exit(1)

	create_db()

	if os.path.isdir(sys.argv[1]):
		for logrpath in os.listdir(sys.argv[1]):
			logfpath = ''.join([sys.argv[1], '/', logrpath])
			parse_log(logfpath)
	else:
		parse_log(sys.argv[1])
	
	filter_db(0.05)
	
	print """\
<!DOCTYPE html>
<!--[if lt IE 7]>      <html class="no-js lt-ie9 lt-ie8 lt-ie7"> <![endif]-->
<!--[if IE 7]>         <html class="no-js lt-ie9 lt-ie8"> <![endif]-->
<!--[if IE 8]>         <html class="no-js lt-ie9"> <![endif]-->
<!--[if gt IE 8]><!-->
<html class="no-js">
<!--<![endif]-->

<head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>12 Salopards - UrbanTerror Stats</title>
    <meta name="description" content="Statistics from the UrT Server '12 Salopards'">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="style.css">
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.4.1/css/bootstrap.min.css"
        integrity="sha384-Vkoo8x4CGsO3+Hhxv8T/Q5PaXtkKtu6ug5TOeNV6gBiFeWPGFN9MuhOf23Q9Ifjh" crossorigin="anonymous">
	<script src="https://code.jquery.com/jquery-3.4.1.slim.min.js"
        integrity="sha384-J6qa4849blE2+poT4WnyKhv5vZF5SrPo0iEjwBvKU7imGFAV0wwj1yYfoRSJoZ+n"
        crossorigin="anonymous"></script>
    <script src="https://cdn.jsdelivr.net/npm/popper.js@1.16.0/dist/umd/popper.min.js"
        integrity="sha384-Q6E9RHvbIyZFJoft+2mJbHaEWldlvI9IOYy5n3zV9zzTtmI3UksdQRVvoxMfooAo"
        crossorigin="anonymous"></script>
    <script src="https://stackpath.bootstrapcdn.com/bootstrap/4.4.1/js/bootstrap.min.js"
        integrity="sha384-wfSDF2E50Y2D1uUdj0O3uMBJnjuUD4Ih7YwaYd1iqfktj0Uod8GCExl3Og8ifwB6"
        crossorigin="anonymous"></script>
	<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/2.9.3/Chart.min.js"></script>    
	<script src="chartjs-plugin-colorschemes.min.js"></script>
    <script src="script.js"></script>		
</head>

<body>
    <!--[if lt IE 7]>
            <p class="browsehappy">You are using an <strong>outdated</strong> browser. Please <a href="#">upgrade your browser</a> to improve your experience.</p>
        <![endif]-->
    <nav class="navbar navbar-dark fixed-top bg-dark flex-md-nowrap p-0 shadow">
        <a class="navbar-brand col-sm col-md mr-0" href="#">12 Salopards - Urban Terror Stats</a>
    </nav>
    <div class="container-fluid">
        <div class="row">
            <nav class="col-md-2 d-none d-md-block bg-light sidebar">
                <div class="sidebar-sticky">
                    <h6
                        class="sidebar-heading d-flex justify-content-between align-items-center px-3 mt-4 mb-1 text-muted">
                        <span>Available Reports</span>
                    </h6>
                    <ul class="nav flex-column">
                        <li class="nav-item"><a class="nav-link active" href="#score">Score ranking</a></li>
						<li class="nav-item"><a class="nav-link" href="#frags-deaths">Frags/Deaths ratio-based ranking</a></li>
                        <li class="nav-item"><a class="nav-link" href="#frags">Frag-based ranking</a></li>
                        <li class="nav-item"><a class="nav-link" href="#capture">Capture ranking</a></li>
                        <li class="nav-item"><a class="nav-link" href="#attack">Attack ranking</a></li>
                        <li class="nav-item"><a class="nav-link" href="#defense">Defense ranking</a></li>
                        <li class="nav-item"><a class="nav-link" href="#bomber">Bomber ranking</a></li>
                        <li class="nav-item"><a class="nav-link" href="#sniper">Sniper ranking</a></li>
                        <li class="nav-item"><a class="nav-link" href="#presence">Presence-based ranking</a></li>
                        <li class="nav-item"><a class="nav-link" href="#chat">Chat ranking</a></li>
                        <li class="nav-item"><a class="nav-link" href="#frags-player">Frags repartition per player</a></li>
                        <li class="nav-item"><a class="nav-link" href="#deaths-player">Deaths repartition per player</a></li>
                        <li class="nav-item"><a class="nav-link" href="#weapons-player">Favorite weapons per player</a></li>
                    </ul>
                </div>
            </nav>
            <main role="main" class="col-md-9 ml-sm-auto col-lg-10 px-4">\
"""
	score_ranking()
	fdratio_ranking()
	frag_ranking()
	capture_ranking()
	attack_ranking()
	defense_ranking()
	he_ranking()
	sniper_ranking()
	presence_ranking()
	chat_ranking()
	frags_repartition()
	death_repartition()
	favorite_weapons()
	best_teammates()
	db_conn.close()

	print """\
    </main>
    </div>
    </div>
  </body>
</html>\
"""


if __name__ == '__main__':
	main()
