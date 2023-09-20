import requests
import threading
import re # regex, it's a crap library name
import mimetypes
import extraui
import os
from urllib.parse import urlparse
from urllib.parse import quote
from urllib.parse import unquote
from urllib.parse import urljoin
from urllib.parse import urlsplit
from itertools import chain

schemeColonMap = {"http":"://","https":"://","tel":":","mailto":":","ftp":"://",}

def verifyFullURLFUNC(url): # a function that checks if a url is absolute (USE WEBASSET.VERIFYFULLURL() FOR WEBASSETS)
    if urlparse(url).netloc == '' and urlparse(url).scheme == '':
        return False
    return True

def escapeFromHTML(url): # converts links that may be inside of a href tag into a valid URL for requests
    # the function name is realistically not great but i thought it sounded cool and poetic
    try:
        # everything after .replace("&amp;","&") is just to account for some bizarre oddities some websites have.
        return unquote(url).replace("&amp;","&").replace("+&+","+%26amp%3B+")
    except: # it might not work always :3
        return url

def reformatURL(url): # attempts to generate a url from a url, gets rid of things like #
    parse = urlparse(url)
    scheme = parse.scheme
    if not(scheme):
        extraui.warn("URL doesn't have scheme assuming HTTPS. (Encountered in reformatURL())")
        scheme = "https"
    return scheme + schemeColonMap[scheme] + parse.netloc + '/' + parse.path[0:] if parse.path[0] == "/" else parse.path + "?" if parse.query else "" + parse.query 

def reformatPartialURL(url): # may not return valid URL, it just does it's job
    ret = ""
    parse = urlparse(url)
    if parse.scheme:
        ret += parse.scheme + schemeColonMap[parse.scheme]
    if parse.netloc:
        ret += parse.netloc
    if parse.path:
        ret += parse.path
    if parse.query:
        ret += '?' + parse.query
    return ret

class WebAsset(): # parent class for all things online
    allWebAssets = []
    def __init__(self, url, caller):
        self.url = url
        self.failedAccess = False
        self.broken = False
        self.absoluteUrl = None
        self.caller = caller
        self.downloaded = False
        self.downloadLocation = ""
        self.extension = ""
        self.rootObj = None
        self.depth = None
        WebAsset.allWebAssets.append(self)
        self.getAbsoluteURL()
        try:
            response = requests.get(self.getAbsoluteURL(), cookies=self.getRootObj().cookies)
        except: # trust me, i know that this is stupid, but keeping exceptions inside of tuples and such just plain didnt work, i have no idea why 
            #extraui.warn(f"Failed to get {self.getAbsoluteURL() if self.getAbsoluteURL() else self.getStartingURL()} {self.getAbsoluteURL()}")
            self.failedAccess = True
        if not(self.failedAccess):
            self.absoluteUrl = response.url # uses redirects in case there are any
            if response.headers.get('content-type'):
                self.extension = mimetypes.guess_extension(response.headers.get('content-type'))[1:] if mimetypes.guess_extension(response.headers.get('content-type')) else ""
        try:
            if type(self.url).__name__ != "list" and not(self.extension):
                self.extension = self.url.split(".")[-1].split("?")[0]
        except Exception as e:
            extraui.warn(f"Cannot use {self.getAbsoluteURL() if self.getAbsoluteURL() else self.getStartingURL()} {self.getAbsoluteURL()} could not find type (this issue is usually caused by other problems)")
            self.broken = True
            self.failedAccess = True

    def getStartingURL(self): # returns the initial url given to the constructor
        return self.url

    def verifyFullURL(self): # like verifyFullURLFUNC, checks if the object started off as an absolute internet URL
        if urlparse(self.getStartingURL()).netloc == '' or urlparse(self.getStartingURL()).scheme == '':
            return False
        return True

    def getDownloadLocation(self): # converts the absoluteUrl to a local path where the file is downloaded
        if self.downloadLocation:
            return self.downloadLocation
        if not(self.absoluteUrl):
            self.getAbsoluteURL()
        self.downloadLocation = reformatPartialURL(self.getAbsoluteURL()).replace("/","!slash!").replace(".","!dot!").replace(":","!colon!").replace("?","!qmark!")+"."+self.extension
        return self.downloadLocation

    def getRootObj(self): # returns the archiver object
        if self.rootObj: # reduce time spent climbing up the tree
            return self.rootObj
        tempClass = self.caller
        while type(tempClass).__name__ != 'Archive':
            tempClass = tempClass.caller
        self.rootObj = tempClass
        return tempClass

    def getDepth(self): # gets the depth of the current site
        if self.depth != None:
            return self.depth
        i = 1
        tempClass = self.caller
        while type(tempClass).__name__ != 'Archive':
            tempClass = tempClass.caller
            i += 1
        self.depth = i
        return i

    def download(self): # downloads and saves the content
        self.getDownloadLocation()
        if self.failedAccess == True:
            return
        if os.path.exists(self.getDownloadLocation()):
            return
        response = requests.get(self.getAbsoluteURL(), cookies=self.getRootObj().cookies)
        with open(self.getRootObj().downloadDir + self.getDownloadLocation(), "wb") as File:
            File.write(response.content)
        self.downloaded = True

    def getAbsoluteURL(self):
        # probably the most important method
        # returns the absolute net url
        # accounts for: the url being empty (returing the parent url), the url already being absolute, the url being absolute but only to the parent site (begins with /), the url being completely relative to the previous site.
        # required so that two sites of completely different urls but that resolve to the same site are recognized as equal
        if self.absoluteUrl:
            return self.absoluteUrl
        if self.getStartingURL().split("#")[0] == "":
            self.absoluteUrl = escapeFromHTML(self.caller.getAbsoluteURL())
            return self.absoluteUrl
        if self.verifyFullURL():
            self.absoluteUrl = escapeFromHTML(self.getStartingURL())
            return self.absoluteUrl
        if self.getStartingURL()[0] == '/':
            tempClass = self.caller
            while not(tempClass.verifyFullURL()):
                if tempClass.absoluteUrl:
                    parse = urlparse(tempClass.getAbsoluteURL())
                    self.absoluteUrl = escapeFromHTML(urljoin(parse.scheme+"://"+parse.netloc, self.getStartingURL()))
                    return self.absoluteUrl
                tempClass = tempClass.caller
            parse = urlparse(tempClass.getStartingURL())
            self.absoluteUrl = escapeFromHTML(urljoin(parse.scheme+"://"+parse.netloc, self.getStartingURL()))
            return self.absoluteUrl
        self.absoluteUrl = escapeFromHTML(urljoin(self.caller.getAbsoluteURL(), self.getStartingURL()))
        return self.absoluteUrl

class Src(WebAsset): # the source class, used for things like images and videos and gifs
    # not super necessary but used to ensure that the program doesnt try to squeeze sites out
    # of binary image data
    allSrcs = []
    processedSrcs = []
    def __init__(self, url, caller):
        super().__init__(url, caller)
        self.getRootObj().allSrcs.append(self)
        Src.allSrcs.append(self)

    def getDownloadLocation(self): # converts the absoluteUrl to a local path where the file is downloaded
        if self.downloadLocation:
            return self.downloadLocation
        if not(self.absoluteUrl):
            self.getAbsoluteURL()
        self.downloadLocation = 'src/' + reformatPartialURL(self.getAbsoluteURL()).replace("/","!slash!").replace(".","!dot!").replace(":","!colon!").replace("?","!qmark!")+"."+self.extension
        return self.downloadLocation
    def __repr__(self):
        return f"<SRC: {self.getDownloadLocation()},{self.getStartingURL()},{self.getAbsoluteURL()}>\n"

class Site(WebAsset): # The site class, stores a site and all of it's attributes, like child sites
    allSites = []
    processedSites = []
    def __init__(self, url, caller):
        super().__init__([url], caller)
        self.completed = False
        self.processed = False
        if not(self.failedAccess or self.broken):
            self.extension = 'html' if not(self.getAbsoluteURL().split("/")[-1].split(".")[-1].split("?")[0] in self.getRootObj().types) else self.getAbsoluteURL().split("/")[-1].split(".")[-1].split("?")[0]
            self.getRootObj().allSites.append(self)
        self.sites = []
        Site.allSites.append(self)

    def getStartingURL(self):
        return self.url[0]

    def addURL(self, url):
        self.url.append(url)

    def process(self): # Runs through the downloaded file, finding hrefs and other links, creating the required objects
        if self.processed or self.failedAccess or self.broken:
            return
        if self.getDepth() > self.getRootObj().maxDepth and self.extension != "css":
            return
        print("Starting " + self.getAbsoluteURL() + "\t( @ Depth", self.getDepth(), ")")
        print("Downloading " + self.getAbsoluteURL())
        self.download()
        print("Processing " + self.getAbsoluteURL())
        with open(self.getRootObj().downloadDir + self.getDownloadLocation(), "r") as File:
            try:
                content = File.read()
            except:
                extraui.warn("Could not read file " + self.getDownloadLocation())
                self.broken = True
                return
            # regex stuff (this WILL be made better, i SUCK at regex)
            # (im so sorry to anyone who has ever googled regex tutorial)
            hrefs = [x[1] for x in re.findall("href=([\"'])(.*?)\\1", content)]
            hrefs.extend([x[1] for x in re.findall("href=([\''])(.*?)\\1", content)])
            srcs = [x[1] for x in re.findall("src=([\"'])(.*?)\\1", content)]
            srcs.extend([x[1] for x in re.findall("src=([\''])(.*?)\\1", content)])
            correct = lambda a : a[1 if a[0] in ["'",'"'] else 0 : -1 if a[-1] in ["'",'"'] else len(a)] # WHO USES CSS url() AND DOESNT USE QUOTATION MARKS... WHYYYY
            srcs.extend([correct(x[4:-1]) for x in re.findall(r"url\([^)]*\)", content)])
            #srcs.extend(x[5:-3] for x in re.findall('url\\(\"[^\"]*\"\\);', content))
            #srcs.extend(x[5:-3] for x in re.findall('url\\(\'[^\']*\'\\);', content))
            urlsAbove = [self.getAbsoluteURL()]
            tempClass = self.caller
            while type(tempClass).__name__ != "Archive":
                urlsAbove.append(tempClass.getAbsoluteURL())
                tempClass = tempClass.caller
            urlsAbove.append(tempClass.getAbsoluteURL())
            for href in hrefs:
                if (urlparse(href).netloc == urlparse(self.getAbsoluteURL()).netloc or urlparse(href).netloc == ""):
                    class tempSite(Site): # a less cpu intensive class that still allows us to get the absoluteURL (used to see if a site already exists)
                        def __init__(self, url, caller):
                            self.url = [url]
                            self.absoluteUrl = None
                            self.caller = caller

                    allLocalSiteUrls = [x.getAbsoluteURL() for x in self.sites] + urlsAbove # all sites that are stored within the current site
                    allGlobalSiteUrls = [x.getAbsoluteURL() for x in self.getRootObj().allSites] # all sites ever for this archive
                    tempFullAddress = tempSite(href,self)
                    if tempFullAddress.getAbsoluteURL() in allGlobalSiteUrls and not(tempFullAddress.getAbsoluteURL() in allLocalSiteUrls): # pretty poor attempt to prevent a site being made twice
                        for site in self.getRootObj().allSites:
                            if tempFullAddress.getAbsoluteURL() == site.getAbsoluteURL():
                                self.sites.append(site) # if the site already exists, a reference is appended to the current Site's list
                    elif tempFullAddress.getAbsoluteURL() in allLocalSiteUrls:
                        for site in self.sites:
                            if tempFullAddress.getAbsoluteURL() == site.getAbsoluteURL():
                                site.addURL(href) # if a site is already in the global list and the current site's list, it adds the URL to the local site's url list (used for find and replace hrefs)
                    else:
                        self.sites.append(Site(href,self)) # if this is a newly discovered site, create a new object
                    del tempFullAddress
            for src in srcs:
                class tempSrc(Src):
                    def __init__(self, url, caller): # same as before but for sources
                        self.url = url
                        self.absoluteUrl = None
                        self.caller = caller
                tempFullAddress = tempSrc(src,self)
                allSrcUrls = [x.getAbsoluteURL() for x in self.getRootObj().allSrcs]
                if not(tempFullAddress.getAbsoluteURL() in allSrcUrls):
                    Src(src,self)
                del tempFullAddress
        self.processed = True
        print("Finished processing " + self.getAbsoluteURL())

    def start(self):
        if self.failedAccess or self.getDepth()>=self.getRootObj().maxDepth or self.completed or not(self.processed):
            return
        print("Completed " + self.getAbsoluteURL())
        self.completed = True
        def start4Threads(site):
            site.process()
            site.start()
        for site in self.sites:
            newThread = threading.Thread(target=start4Threads, args=(site,))
            self.getRootObj().queue.append(newThread)
    
    def __repr__(self):
        return f"<SITE:{self.getAbsoluteURL()},{self.url}>"

class Archive():
    def __init__(self, url: str, downloadDir: str, cookies: list={}, stayOnSameDomain: bool=True, maxDepth: int=2, limitToHT: bool=True, threadCount: int=5):
        assert verifyFullURLFUNC(url), "Initial URL must be valid"
        self.url = url
        self.allSites = []
        self.allSrcs = []
        self.downloadDir = downloadDir if downloadDir[-1] == '/' else downloadDir + '/'
        self.cookies = cookies
        mimetypes.init()
        self.types = [x.replace(".","") for x in list(mimetypes.types_map.keys())] # a list of all file extensions, used in the Site().__init__()
        self.initialSite = Site(url,self)
        self.maxDepth = maxDepth
        self.threads = [None,]*threadCount
        self.queue = []

    def getAbsoluteURL(self):
        return self.url
    
    def startDownload(self):
        def handleQueue(archive): # function running on seperate thread that 
            cycleCount = 0 # really crap solution to race conditions (accounts for the time between initialsite being processed and the queue/threads being filled)
            # we cannot go off of Site().completed because it isnt triggered if we have reached the maxDepth, as it is designed to
            while not(archive.initialSite.processed):
                pass
            while (next((item for item in archive.threads if item is not None), False) or archive.queue) or cycleCount < 10000:
                for i, thread in enumerate(archive.threads):
                    if thread:
                        if not(thread.is_alive()):
                            thread.join()
                            del thread
                            self.threads[i] = None
                for i in range(len(archive.threads)-1):
                    if not(archive.threads[i]) and archive.queue:
                        archive.threads[i] = archive.queue[0]
                        archive.queue.pop(0)
                        archive.threads[i].start()
                if not(next((item for item in archive.threads if item is not None), False) or archive.queue):
                    cycleCount+=1
                else:
                    cycleCount=0
        queueHandler = threading.Thread(target=handleQueue,args=(self,))
        queueHandler.start()
        self.initialSite.process()
        self.initialSite.start()
        queueHandler.join()
        print("Finished site tree generation and site downloads")
        if not(os.path.isdir(self.downloadDir+'src')):
            os.mkdir(self.downloadDir+'src')
        print("Downloading sources")
        for src in self.allSrcs:
            if src.broken or src.failedAccess:
                continue
            print(f"Downloading {src.absoluteUrl}")
            print(src.extension)
            with open(self.downloadDir + src.getDownloadLocation(), "wb") as File:
                response = requests.get(src.getAbsoluteURL(), cookies=self.cookies)
                File.write(response.content)
            print(f"Downloaded {src.absoluteUrl}")
        print(f"Finished downloading sources")


    def applyLocalisation(self):
        print("Converting online links to local offline links")
        for currentSite in self.allSites:
            if currentSite.extension in ['css','html'] and not(currentSite.broken or currentSite.failedAccess) and currentSite.processed:
                try:
                    content = ""
                    with open(self.downloadDir + currentSite.getDownloadLocation(), "r") as File:
                        content = File.read()
                    for x in self.allSites:
                        if not(x.downloaded):
                            continue
                        for j in x.url:
                            content = content.replace(f"href=\"{j}\"",f"href=\"{quote(x.getDownloadLocation())}\"")
                            content = content.replace(f"href=\'{j}\'",f"href=\"{quote(x.getDownloadLocation())}\"")
                    for x in self.allSrcs:
                        content = content.replace(f"url(\"{x.url}\")",f"url(\"{quote(x.getDownloadLocation())}\")")
                        content = content.replace(f"url(\'{x.url}\')",f"url(\"{quote(x.getDownloadLocation())}\")")
                        content = content.replace(f"src=\"{x.url}\"",f"src=\"{quote(x.getDownloadLocation())}\"")
                        content = content.replace(f"src=\'{x.url}\'",f"src=\"{quote(x.getDownloadLocation())}\"")
                        content = content.replace(f"url({x.url})",f"url(\'{quote(x.getDownloadLocation())}\')")
                    with open(self.downloadDir + currentSite.getDownloadLocation(), "w") as File:
                        File.write(content)
                except:
                    pass
                    extraui.warn(f"Failed to modify {currentSite.getAbsoluteURL()}")
        print("Finished editing files")
