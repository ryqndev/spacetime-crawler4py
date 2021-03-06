import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from bs4.element import Comment
from tokenizer import tokenize, getTokenizedList
from difflib import SequenceMatcher 
from hashlib import sha256

WHITELISTED_DOMAINS = [".ics.uci.edu/", 
                       ".cs.uci.edu/", 
                       ".informatics.uci.edu/", 
                       ".stat.uci.edu/", 
                       "today.uci.edu/department/information_computer_sciences/",
                       "//ics.uci.edu/", 
                       "//cs.uci.edu/", 
                       "//informatics.uci.edu/", 
                       "//stat.uci.edu/", 
                       "//today.uci.edu/department/information_computer_sciences/"]

BLACKLISTED_DOMAINS = ["wics.ics.uci.edu/events", 
                        "evoke.ics.uci.edu/qs-personal-data-landscapes-poster/?",
                        "https://evoke.ics.uci.edu/viewing-the-world-through-technologys-eyes/?",
                        "https://evoke.ics.uci.edu/hollowing-i-in-the-authorship-of-letters-a-note-on-flusser-and-surveillance/?",
                        "https://evoke.ics.uci.edu/bowker-co-organizing-white-house-ostp-conference-on-big-data-and-privacy/?"]
                        
CUTOFF_RATIO = 0.008022722285

def visible(item):
    return not ((item.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]']) or isinstance(item, Comment))

def cleanHTML(content):
    htmlContent = BeautifulSoup(content, features='html.parser')
    if htmlContent.contains_replacement_characters:
        return None
    return u" ".join(x.strip() for x in filter(visible, htmlContent.findAll(text=True)))
    
def scraper(url, resp):
    if resp.status == 200:
        url = defragmentURL(url)
        scraper.uniqueWebpages.add(url)
        
        #Get unique ics subdomains
        subdomain = getSubdomain(url,"ics.uci.edu")
        if subdomain:
            if subdomain not in scraper.icsSubdomains:
                scraper.icsSubdomains[subdomain] = 1
            else:
                scraper.icsSubdomains[subdomain] += 1  

        contentHash = sha256(resp.raw_response.content).hexdigest()
        if contentHash not in scraper.pageHashes:
            scraper.pageHashes.add(contentHash)

            #We will ignore this page and return None if any decode errors were thrown.
            cleanedPage = cleanHTML(resp.raw_response.content)
            if cleanedPage is None:
                return None            
            tokenCount, byteCount, tokens = getTokenizedList(cleanedPage)

            #Only count the tokens if we consider this page to have a high information ratio.
            #We define this to be the ratio: bytesof(tokens) / bytesof(response.content)
            #We will use this CUTOFF_RATIO = 0.008022722285 as the cutoff
            curRatio = float(byteCount)/float(len(resp.raw_response.content))
            if curRatio > CUTOFF_RATIO:
                insertTokens(scraper.tokenMap, tokens)
                if tokenCount > scraper.mostTokens: #Update url with the most tokens
                    scraper.mostTokens = tokenCount
                    scraper.urlOfLongest = url
                
            #Fetch and return valid links.
            links = extract_next_links(url, resp.raw_response.content)
            return [link for link in links if is_valid(link)]
    elif resp.status >= 600:
        with open("600-errors.rtf", "a+") as f:
            f.write(f"status <{resp.status}> -- {resp.error} -- {url}\n")
    return None

#Initialize statics for collecting statistics on the corpus
scraper.tokenMap = dict()
scraper.mostTokens = 0
scraper.urlOfLongest = ""
scraper.icsSubdomains = dict()
scraper.uniqueWebpages = set()
scraper.pageHashes = set()

def insertTokens(tokenMap, toAddList):
    for token in toAddList:
        tokenMap[token] = 1 if token not in tokenMap else tokenMap[token] + 1

def getSubdomain(url, dom, prefix = "http://"):
    parsed = urlparse(url)
    if dom in parsed.netloc:
        sub = parsed.netloc.split(".")
        if "www" in parsed.netloc:
            return prefix + sub[1] + "." + dom + "/"
        return prefix + sub[0] + "."+ dom + "/"
    return None
   
def printStats():
    with open("results.rtf", "a+") as f:
        f.write("Top tokens:\n")
        for i, (token, count) in enumerate(sorted(scraper.tokenMap.items(), key=lambda pair: pair[1], reverse=True)):
            if i > 1000:
                break
            f.write(f"<{token}> <{count}>\n")
        f.write("\n\nICS subdomains:\n")
        for token, count in sorted(scraper.icsSubdomains.items(), key=lambda pair: pair[1], reverse=True):
            f.write(f"<{token}> <{count}>\n")  
        f.write("\n\n")
        f.write(f"Number of unique tokens: {len(scraper.tokenMap)}\n")
        f.write(f"Url with most tokens: {scraper.urlOfLongest} with {scraper.mostTokens} unique tokens.\n")
        f.write(f"Number of unique URLs scraped: {len(scraper.uniqueWebpages)}\n")

def defragmentURL(url):
    #Remove fragment from a url
    fragIndex = url.find("#")
    if fragIndex > 0:
        url = url[:(fragIndex-1 if url[fragIndex-1] == "/" else fragIndex)]
    elif url[-1] == "/":
        url = url[:-1]
    return url

def defragmentURLExtended(url):
    #Remove fragment and args from a url
    fragIndex = url.find("#")
    argIndex = url.find("?")
    if fragIndex > 0 and argIndex > 0:
        splitIndex = min(argIndex, fragIndex)
        url = url[:(splitIndex-1 if url[splitIndex-1] == "/" else splitIndex)]
    elif fragIndex > 0 or argIndex > 0:
        splitIndex = max(argIndex, fragIndex)
        url = url[:(splitIndex-1 if url[splitIndex-1] == "/" else splitIndex)]
    elif url[-1] == "/":
        url = url[:-1]
    return url

def extract_next_links(url, content):
    return [defragmentURL(l.get('href')) for l in BeautifulSoup(content, features="html.parser").find_all('a', href=True) if "http" in l.get('href')]

def is_valid(url):
    global WHITELISTED_DOMAINS  
    global BLACKLISTED_DOMAINS
    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False
        valid = False
        urlPath = defragmentURLExtended(url)
        for dom in WHITELISTED_DOMAINS:
            if dom in urlPath:
                valid = True
                break
        if not valid:
            return False
        
        for dom in BLACKLISTED_DOMAINS:
            if dom in url:
                return False

        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|ppsx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", url.lower())

    except TypeError:
        print ("TypeError for ", parsed)
        return False



