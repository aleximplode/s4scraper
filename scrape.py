#!/usr/bin/python
'''
    Author: Alexander Godlewski
    Year: 2011
    
    A script to step through the leaderboards for SOCOM 4
    Gather the results and dump to a CSV file
    
    There are issues with the implementation of the leaderboards
        that causes the time played for a player to often be
        synchronized to 60 minute changes
    
    Another issue is that the leaderboards are constantly changing
        across page views. So it a player may move from one page to
        another and be re-parsed and the another player could move to
        an already parsed page and not be recorded. It would take constant
        runs of this script to gather all the players.
        
    Expect this process to take 2 hours or more. It has to gather 100k
        players over 5k pages
        
    There exists a multiprocessing version of this script that finishes
        the process in approx. 21 minutes
'''

import urllib2, urllib, re, os
from time import time

requestcount = 0
requestname = ''
records = 0
pages = 0
playerdata = dict()

# Regexs
re_viewstate = re.compile(r'__VIEWSTATE" value="(?P<viewstate>.*?)"')
re_records = re.compile(r'Displaying .*? of (?P<records>[0-9,]*) records')
re_pages = re.compile(r'<a id="ctl00_phContent_leaderboards_pager_btnLast".*?>\.\.\. (?P<pages>\d*)</a>')
re_player = re.compile(r'<span id="ctl00_phContent_leaderboards_rptStatsTable_ctl.*?<tr.*?></span>(?P<player>.*?)</tr>', re.DOTALL) # Get a player block
re_playeritems = re.compile(r'<td class=".*?">(?:\s*<a.*?>)?(?P<data>.+?)(?:</a>\s*)?</td>', re.DOTALL) # Individual player fields
re_prevpage = re.compile(r'__PREVIOUSPAGE" value="(?P<prev>.*?)"') # Previous page key

opener = urllib2.build_opener()
opener.add_handler(urllib2.HTTPHandler())
opener.add_handler(urllib2.HTTPCookieProcessor())
opener.add_handler(urllib2.HTTPRedirectHandler())
opener.add_handler(urllib2.UnknownHandler())

headers = {
   'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:6.0) Gecko/20100101 Firefox/6.0 Iceweasel/6.0',
   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
   'Accept-Language': 'en-us,en;q=0.5',
   'Accept-Encoding': 'gzip, deflate',
   'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
   'Connection': 'keep-alive',
   'Cache-Control': 'no-cache, no-cache',
   }



def scrape():
    ''' The main scraping function '''
    t0 = time()
    
    try:
        data = readurl('http://www.socom.com/en-us/Leaderboards/SOCOM4', 'Initial page request')
        vs = parseviewstate(data)
        
        postdata = genpostdata(vs, '', 'lbsubmit', {'dlDate1': 7, 'dlDate2': 21, 'dlDate3': 1986, 'scriptManager': 'panelCulture|lbSubmit'})
        data = readurl('http://www.socom.com/?url=%2fen-us%2fLeaderboards%2fSOCOM4', 'Submit to agegate', postdata)
        
        data = readurl('http://www.socom.com/en-us/Leaderboards/SOCOM4', 'Load first leaderboard page')
        
        global records
        records = parserecordcount(data)
        print 'Expecting about %d players scraped' % records
        
        global pages
        pages = parsepagecount(data)
        print 'Expecting about %d pages scraped' % pages
        
        parseplayers(data)

        for pagenum in range(2, pages + 1):
            vs = parseviewstate(data)
            prev = parseprevpagekey(data)
            postdata = genpostdata(vs, '', 'ctl00$phContent$leaderboards$pager$btnNext', {'__PREVIOUSPAGE': prev, 'ctl00$scriptManager': 'ctl00$phContent$leaderboards$panelLeaderBoards|ctl00$phContent$leaderboards$pager$btnNext'})
            data = readurl('http://www.socom.com/en-us/Leaderboards/SOCOM4', 'LB page %d' % pagenum, postdata)
            parseplayers(data)
        
    except urllib2.HTTPError, error:
        print ''
        print 'There has been an error with the following request:'
        print '%4d: %d - (%s)%s' % (requestcount, error.getcode(), requestname, error.geturl())  
              
    t1 = time()
    print ''
    print '###########################################################################'
    print '%d second%s elapsed(%4d requests, %6d players)' % (t1 - t0, '' if t1 - t0 == 1 else 's', requestcount, len(playerdata))
    print '###########################################################################'
    
    
    filename = 'output-%s-%s.csv' % (int(time()), os.getpid())
    print ''
    print 'Outputting the playerdata to %s' % filename
    outputcsv(filename)
    
def readurl(url, name, data = []):
    ''' Read a url and print info ''' 
    global requestcount
    global requestname
    requestcount += 1
    requestname = name
    
    req = urllib2.Request(url, urllib.urlencode(data), headers)
    page = opener.open(req)
                
    print '%4d: %d - (%s)%s' % (requestcount, page.getcode(), name, page.geturl())
    return page.read()

def parseplayers(data):
    ''' Parse the player data for a response '''
    matches = re_player.findall(data)
    for match in matches:
        fields = re_playeritems.findall(match)
        name = fields[1].strip().replace(',', '')
        if name in playerdata:
            print 'WARNING: %s already parsed' % name
                
        playerdata[name] = tuple(fields[i].strip().replace(',', '') for i in (0, 2, 3, 4, 5, 6, 7, 8))
            
def parseviewstate(data):
    ''' Parse the viewstate for a response '''
    rval = None
    
    match = re_viewstate.search(data)
    if match:
        rval = match.group('viewstate')
        
    return rval
        
def parserecordcount(data):
    ''' Get the record count to show the expected number of players scraped '''
    rval = 0
    
    match = re_records.search(data)
    if match:
        rval = int(match.group('records').replace(',', ''))
        
    return rval    
    
def parsepagecount(data):
    ''' Get the page count to show the expected number of pages scraped '''
    rval = 0
    
    match = re_pages.search(data)
    if match:
        rval = int(match.group('pages'))
        
    return rval    

def parseprevpagekey(data):
    ''' Get the previous page key '''
    rval = None
    
    match = re_prevpage.search(data)
    if match:
        rval = match.group('prev')
        
    return rval
    
def genpostdata(vs, ea, et, other = None):
    ''' Generate a POST dict, just simplifies code
    vs = viewstate
    ea = event arguement
    et = event target
    other = other post data (dict)
    '''
    data = dict()
    data['__VIEWSTATE'] = vs
    data['__EVENTARGUMENT'] = ea
    data['__EVENTTARGET'] = et
    
    if other:
        data = dict(data.items() + other.items())
    
    return data
        
def outputcsv(filename):
    ''' Output the csv file '''
    try:
        f = open(filename, 'w')
        for name, data in playerdata.items():
            f.write('%s,%s\n' % (name, ','.join(data)))
        f.close()
    except IOError:
        print 'There was an issue writing to %s' % filename
    
if __name__ == '__main__':
    scrape()