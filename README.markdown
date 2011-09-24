S4 Scraper
----------

A script to step through the leaderboards for SOCOM 4. Gather the results and dump to a CSV file.

###Files
- LICENSE: MIT license file
- README.markdown: Readme file
- scrape.py: Non-threaded version of the scraper (don't suggest running this one anymore unless you really have a reason to)
- scrapef.py: The threaded (multiprocessing, fast) version of the scraper
- smFunctions.sqlite: Functions file for sqlite manager in firefox. Helper to convert string data (ex. 23h36m to 1416 (minutes))

###Issues
There are issues with the implementation of the leaderboards that causes the time played for a player to often be synchronized to 60 minute changes.

Another issue is that the leaderboards are constantly changing across page views. So a player may move from one page to another and be re-parsed and the another player could move to an already parsed page and not be recorded. It would take constant runs of this script to gather all the players.

Expect this process to take 2 hours or more (single thread) or about 21 minutes (multithread, 24). It has to gather 100k players over 5k pages.
It uses multiprocessing instead of multithreading to avoid the CPython global interpreter lock (GIL). 

###Purpose
The reason for this was because people were debating over the number of people actually playing the game online due to the quality and direction of it's design. Scraping at two different time periods would give different play times for each players and with this you could tell if someone has played. Then you could query an approximate number of people who have played in the time span.

###What next
I had originally tried loading the data and manipulating it in LibreOffice but that has shown it's issues (5GB memory and crashing). I was able to load it in SQLite and manipulate/query the data very efficiently. A fun use of this data is to show play time vs players which shows the number of players who have played for a set of minute amounts.

###Sample data charts
win/loss vs kdr, min 1000 kills, min 10 reference points per kdr (to prevent spikes from rare cases):
http://i54.tinypic.com/2lj6gzo.png

Suppression, same specs:
http://i51.tinypic.com/vs2ddj.png

Suppression Classic, same:
http://i54.tinypic.com/2qmhfra.png

same, but 500 kills min(for a larger sample set):
http://i52.tinypic.com/692a3c.png


Suppression kdr vs player count:
http://i51.tinypic.com/vhf1w9.png

min 500 kills:
http://i52.tinypic.com/2uoqgld.png

min 1000:
http://i54.tinypic.com/30dl837.png

min 10000:
http://i53.tinypic.com/2qxq5va.png


Suppression Classic kdr vs player count:
http://i51.tinypic.com/2cwl93k.png

min 500 kills:
http://i56.tinypic.com/fzal1d.png

min 1000:
http://i53.tinypic.com/350t9gx.png

min 2500 (not enough players with >5000):
http://i54.tinypic.com/2ngeryr.png


Bomb Squad winp vs defusals:
http://i51.tinypic.com/e87c47.png

winp vs defusal rate(shorter is less time between defusals):
http://i52.tinypic.com/fwjg5.png


Bomb Squad Classic winp vs defusals:
http://i55.tinypic.com/mr3gj8.png

winp vs defusal rate(shorter is less time between defusals):
http://i52.tinypic.com/33a6ubl.png
