import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from bs4.element import Comment
from tokenizer import tokenize 
from difflib import SequenceMatcher 

WHITELISTED_DOMAINS = ["ics.uci.edu", 
                       "cs.uci.edu", 
                       "informatics.uci.edu", 
                       "stat.uci.edu", 
                       "today.uci.edu/department/information_computer_sciences"
                       ]
def visible(item):
    return not ((item.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]']) or isinstance(item, Comment))

def cleanHTML(content):
    return u" ".join(x.strip() for x in filter(visible, BeautifulSoup(content, features='html.parser').findAll(text=True)))

def scraper(url, resp):
    if resp.status == 200:
        url = defragmentURL(url)

        #Compute url similarity
        similarity = 0
        if scraper.previous is not None:
            similarity = SequenceMatcher(None, url, scraper.previous).ratio()
        tempURL = scraper.previous
        scraper.previous = url

        #Check that the previous url is sufficiently different from the current one
        if similarity < .95 and url not in scraper.uniqueWebpages:     
            tokenCount = tokenize(cleanHTML(resp.raw_response.content),scraper.tokenMap)
            #Update url with the most tokens
            if tokenCount > scraper.mostTokens:
                scraper.mostTokens = tokenCount
                scraper.urlOfLongest = url
                
            #Get unique ics subdomains
            links = extract_next_links(url, resp.raw_response.content)
            try:
                subdomain = getSubdomain(url,"ics.uci.edu")
                if subdomain:
                    scraper.icsSubdomains[subdomain] = len(set([link for link in links if is_valid(link)]))
#                 temp = url.split(".")
#                 if len(temp) > 1 and temp[1] == "ics" and "www" not in temp[0]: #https://xyz.ics.edu case
#                     scraper.icsSubdomains.add(temp[0][temp[0].find("//")+2:])
#                 elif len(temp) > 2 and temp[2] == "ics": #https://www.xyz.ics.edu case
#                     scraper.icsSubdomains.add(temp[1])
            except:
                print(f"Error obtaining subdomain for: {url}")

            
            scraper.uniqueWebpages.add(url)
            return [link for link in links if is_valid(link)]
    else:
        print(f"Error: status_code = {resp.status} from url = {url}")

#Initialize statics for collecting statistics on the corpus
scraper.tokenMap = dict()
scraper.mostTokens = 0
scraper.urlOfLongest = ""
scraper.icsSubdomains = dict()
scraper.uniqueWebpages = set()
scraper.previous = None

def getSubdomain(url, dom, prefix = "http://"):
    parsed = urlparse(url)
    if dom in parsed.netloc:
        sub = parsed.netloc.split(".")
        if "www" in parsed.netloc:
            return prefix + sub[1] + "." + dom + "/"
        return prefix + sub[0] + "."+ dom + "/"
    return None
   
def printStats():
    if(len(scraper.tokenMap) > 0):
        print("Top 50 tokens:")
        for i, (token, count) in enumerate(sorted(scraper.tokenMap.items(), key=lambda pair: pair[1], reverse=True)):
            if i > 50:
                break
            print(f"<{token}> <{count}>") 

    if(len(scraper.tokenMap) > 0):
        print("ICS subdomains:")
        for token, count in sorted(scraper.icsSubdomains.items(), key=lambda pair: pair[1], reverse=True):
            print(f"<{token}> <{count}>")  

    print(f"Number of unique tokens: {len(scraper.tokenMap)}")
    print(f"Url with most tokens: {scraper.urlOfLongest} with {scraper.mostTokens} unique tokens.")
    print(f"Number of unique URLs scraped: {len(scraper.uniqueWebpages)}")

# def defragmentURL(url):
#     #Remove fragment and args from a url
#     argIndex = url.find("?")
#     fragIndex = url.find("#")

#     #Split url at the first occurance of either "#" or "?" if either is present.
#     if fragIndex > 0 and argIndex > 0:
#         last = min(fragIndex, argIndex)
#         url = url[:(last-1 if url[last-1] == "/" else last)]
#     elif fragIndex > 0 or argIndex > 0:
#         last = max(fragIndex, argIndex)
#         url = url[:(last-1 if url[last-1] == "/" else last)]
#     return url

def defragmentURL(url):
    #Remove fragment and args from a url
    fragIndex = url.find("#")
    if fragIndex > 0:
        url = url[:(fragIndex-1 if url[fragIndex-1] == "/" else fragIndex)]
    elif url[-1] == "/":
        url = url[:-1]
    return url

# def extract_next_links(url, content):
#     diffLinks = list()
#     for link in [defragmentURL(l.get('href')) for l in BeautifulSoup(content, features="html.parser").find_all('a', href=True) if "http" in l.get('href')]:
#         similar = False
#         for other in diffLinks:
#             if SequenceMatcher(None, link, other).ratio() > .95:
#                 similar = True
#                 break
#         if similar == False:
#             diffLinks.append(link)
#     return diffLinks

def extract_next_links(url, content):
    return [defragmentURL(l.get('href')) for l in BeautifulSoup(content, features="html.parser").find_all('a', href=True) if "http" in l.get('href')]

def is_valid(url):
    global WHITELISTED_DOMAINS  
    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False
        try:
            domain = url.split("/")[2]
            valid = False
            for dom in WHITELISTED_DOMAINS:
                if dom in domain:
                    valid = True
            if not valid:
                return False
        except IndexError:
            print(f"Error: malformed url: {url}")
        
        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|ppsx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())

    except TypeError:
        print ("TypeError for ", parsed)
        raise