# q3ut4_log_parser

**Q3UT4 Log Parser** is a parser for generating some statistics from Urban Terror log files. 

## Presentation

From the log file, it generates an HTML file with following statistics:

- **Score ranking** Rank players based on their victories and defeats. 
- **Kills/Deaths Ratio ranking** Rank players based on their ratio Kills/Deaths
- **Capture ranking** Rank players based on their flags captures
- **Attack ranking** Rank players based on their flags catched
- **Defense ranking** Rank players based on their flags returned to base
- **Bomber ranking** Rank players based on their Kills with HE Grenades
- **Sniper ranking** Rank players based on their Kills with Sniper rifles (SR8, PSG-1)
- **Presence ranking** Rank players based on their time spent on the server
- **Chat ranking** Rank players based on their amount of chat lines
- **Kill repartition** Count for each player the number of Kill for each player against other players
- **Death repartition** Count for each player the number of Death provocated by other players
- **Favorite weapons** Count the use (kills) of weapons for each players 

## Installation

### Over Git
You can directly clone this repository to your Web-Server. 

    git clone https://github.com/kns7/q3ut4_log_parser.git q3ut4_log_parser



### Manual (ZIP Download)

You can download the latest version of q3ut4_log_parser from the [GitHub releases](https://github.com/kns7/q3ut4_log_parser/archive/master.zip). 

Decompress the archive onto your Web-Server.

    unzip master.zip /var/www/q3ut4_log_parser

## Configuration

### Setup Apache2 

Setup a VirtualHost in Apache 2.4 for the website. 
Make sure, you are pointing the DocumentRoot to the subfolder *www* contained in the archive.

    <VirtualHost *:80>
	    ServerName urtstats.example.org
	    DocumentRoot /var/www/q3ut4_log_parser/www

	    <Directory /var/www/q3ut4_log_parser/www>
    		Options Indexes
		    DirectoryIndex index.html
		    AllowOverride None
		    Require all granted
	    </Directory>
    </VirtualHost>


### Setup a Cron job

In order to get the latest statistics, plan to run a cron job

    vi /etc/crontab

Add following line to your crontab

    * */1   * * *   www-data /var/www/q3ut4_log_parser/q3ut4_log_parser.py /path/to/logfile.log > /var/www/q3ut4_log_parser/www/index.html

Change the user if needed as the paths (to the games Logfile and the Webserver root). Make sure you pick a user who has read access to the game logfile (usually *q3ut4/games.log*)


## Sources

This project is a fork of https://github.com/negre/q3ut4_log_parser