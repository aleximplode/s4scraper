#!/usr/bin/python
'''
    Author: Alexander Godlewski
    Year: 2011
    
    A script to browse through the leaderboards for SOCOM 4
        using multiprocessing to overcome network blocking
        
    Gather the results and dump to a CSV file
    
    There are issues with the implementation of the leaderboards
        that causes the time played for a player to often be
        synchronized to 60 minute changes
    
    Another issue is that the leaderboards are constantly changing
        across page views. So it a player may move from one page to
        another and be re-parsed and the another player could move to
        an already parsed page and not be recorded. It would take constant
        runs of this script to gather all the players.
        
    Expect this process to take approx. 21 minutes or more, depending on how 
        many processes you choose(variable numproc). It has to gather 100k
        players over 5k pages
'''

import urllib2, urllib, re, os, multiprocessing
from time import time

manager = multiprocessing.Manager()

requestcount = manager.Value('d', 0)
pages = manager.Value('d', 0)
playerdata = manager.dict()
numproc = 24
processes = []

waitevent = manager.Event()
procwait = manager.Value('d', numproc)
procwaitlock = manager.Lock()

pagelist = manager.list()
pagelistlock = manager.Lock()

pagecountlock = manager.Lock()
requestcountlock = manager.Lock()
playerdatalock = manager.Lock()

# Regexs
re_viewstate = re.compile(r'__VIEWSTATE" value="(?P<viewstate>.*?)"')
re_records = re.compile(r'Displaying .*? of (?P<records>[0-9,]*) records')
re_pages = re.compile(r'<a id="ctl00_phContent_leaderboards_pager_btnLast".*?>\.\.\. (?P<pages>\d*)</a>')
re_player = re.compile(r'<span id="ctl00_phContent_leaderboards_rptStatsTable_ctl.*?<tr.*?>(?:</span>)?(?P<player>.*?)</tr>', re.DOTALL) # Get a player block
re_playeritems = re.compile(r'<td class=".*?">(?:\s*<a.*?>)?(?P<data>.+?)(?:</a>\s*)?</td>', re.DOTALL) # Individual player fields
re_prevpage = re.compile(r'__PREVIOUSPAGE" value="(?P<prev>.*?)"') # Previous page key

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
        for i in range(1, numproc + 1):            
            process = multiprocessing.Process(
                                              target = scrapeproc, 
                                              args = (
                                                      waitevent,
                                                      pagelist, 
                                                      pagelistlock, 
                                                      procwait, 
                                                      procwaitlock, 
                                                      playerdatalock, 
                                                      requestcountlock, 
                                                      pagecountlock, 
                                                      pages, 
                                                      i - 1, 
                                                      playerdata, 
                                                      requestcount
                                                      )
                                              )
            processes.append(process)
            process.start()
            
        for p in processes:
            p.join()
                    
    except urllib2.HTTPError, error:
        print ''
        print 'There has been an error with the following request:'
        print '%4d: %d - %s' % (requestcount, error.getcode(), error.geturl())
        
        for p in processes:
            p.terminate()
              
    t1 = time()
    
    print ''
    print '###########################################################################'
    print '%d second%s elapsed(%4d requests, %6d players)' % (t1 - t0, '' if t1 - t0 == 1 else 's', requestcount.value, len(playerdata))
    print '###########################################################################'
    
    
    filename = 'output-%s-%s.csv' % (int(time()), os.getpid())
    print ''
    print 'Outputting the playerdata to %s' % filename
    outputcsv(filename)
    
    
def scrapeproc(we, pl, pllock, pw, pwlock, pdlock, rclock, plock, p, offset, pd, rc):
    ''' A process to scrape pages '''
    opener = urllib2.build_opener()
    opener.add_handler(urllib2.HTTPHandler())
    opener.add_handler(urllib2.HTTPCookieProcessor())
    opener.add_handler(urllib2.HTTPRedirectHandler())
    opener.add_handler(urllib2.UnknownHandler())
    
    data = readurl(rclock, requestcount, opener, 'http://www.socom.com/en-us/Leaderboards/SOCOM4', 'Initial page request')
    vs = parseviewstate(data)
    
    postdata = genpostdata(vs, '', 'lbsubmit', {'dlDate1': 7, 'dlDate2': 21, 'dlDate3': 1986, 'scriptManager': 'panelCulture|lbSubmit'})
    data = readurl(rclock, requestcount, opener, 'http://www.socom.com/?url=%2fen-us%2fLeaderboards%2fSOCOM4', 'Submit to agegate', postdata)
    
    data = readurl(rclock, requestcount, opener, 'http://www.socom.com/en-us/Leaderboards/SOCOM4', 'Load first leaderboard page')
        
    pagecount = parsepagecount(data)
    
    plock.acquire()
    if pagecount > p.value:
        p.value = pagecount
    plock.release() 
    
    # Decrement procwait count, at 0 continue
    pwlock.acquire()
    
    if pw.value == 1:
        print 'Expecting %d pages' % p.value
        pl.extend(range(1, p.value + 1))
        we.set()
        
    pw.value = pw.value - 1
    pwlock.release()
    
    # Wait until all processes have reached the same point so
    #    the page count is at the max value found. All 
    #    openerdirectors are prepared to visit the pages
    we.wait()
    
    # Loop until there are no more pages left to be parsed
    while True:
        pllock.acquire()
        
        # No pages left
        if not pl:
            pllock.release()
            break
        
        pagenum = pl.pop(0)
        pllock.release()
        
        vs = parseviewstate(data)
        prev = parseprevpagekey(data)
        
        postdata = genpostdata(vs, '', '', 
                               {
                                '__PREVIOUSPAGE': prev, 
                                'ctl00$phContent$leaderboards$txtName': '', 
                                'ctl00$phContent$leaderboards$btnGoToRank': 'GO', 
                                'ctl00$phContent$leaderboards$txtRank': ((pagenum - 1) * 20) + 1,
                                'ctl00$scriptManager': 'ctl00$phContent$leaderboards$panelLeaderBoards|ctl00$phContent$leaderboards$btnGoToRank'
                                }
                               )
        
        data = readurl(rclock, rc, opener, 'http://www.socom.com/en-us/Leaderboards/SOCOM4', 'LB page %d of %d' % (pagenum, p.value), postdata)
        parseplayers(pdlock, pd, data)

def readurl(rclock, rc, od, url, name, data = []):
    ''' Read a url and print info ''' 
    rclock.acquire()
    currequestnum = rc.value + 1
    rc.value += 1
    rclock.release()
    
    req = urllib2.Request(url, urllib.urlencode(data), headers)
    page = od.open(req)
                
    print '%4d: %d - (%s)%s' % (currequestnum, page.getcode(), name, page.geturl())
    return page.read()

def parseplayers(pdlock, pd, data):
    ''' Parse the player data for a response '''
    matches = re_player.findall(data)
    for match in matches:
        fields = re_playeritems.findall(match)
        
        name = fields[1].strip().replace(',', '')
        
        pdlock.acquire()
        if name in pd:
            print 'WARNING: %s already parsed' % name

        pd[name] = tuple(fields[i].strip().replace(',', '') for i in (0, 2, 3, 4, 5, 6, 7, 8))
        pdlock.release()
            
def parseviewstate(data):
    ''' Parse the viewstate for a response '''
    rval = None
    
    match = re_viewstate.search(data)
    if match:
        rval = match.group('viewstate')
        
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