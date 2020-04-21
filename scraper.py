import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from bs4.element import Comment
from tokenizer import tokenize 

WHITELISTED_DOMAINS = ["ics.uci.edu", 
                       "cs.uci.edu", 
                       "informatics.uci.edu", 
                       "stat.uci.edu", 
                       "today.uci.edu/department/information_computer_sciences"
                       ]
#tokenMap = dict() #Keep track of how many times a token appears in the corpus
#mostTokens = 0    #The number of tokens of the longest page.
#urlOfLongest = ""    #Cooresponding url for mostTokens

def visible(item):
    return not ((item.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]']) or isinstance(item, Comment))

def cleanHTML(content):
    return u" ".join(x.strip() for x in filter(visible, BeautifulSoup(content, features='html.parser').findAll(text=True)))

def scraper(url, resp):
    if resp.status == 200:
        tokenCount = tokenize(cleanHTML(resp.raw_response.content),scraper.tokenMap)
        if tokenCount > scraper.mostTokens:
            scraper.mostTokens = tokenCount
            scraper.urlOfLongest = url
        print(f"mostTokens = {scraper.mostTokens}, len(tokemMap) = {len(scraper.tokenMap.keys())}")
        links = extract_next_links(url, resp.raw_response.content)
        return [link for link in links if is_valid(link)]
    else:
        print(f"Error: status_code = {resp.status} from url = {url}")

#Initialize statics for collecting statistics
scraper.tokenMap = dict()
scraper.mostTokens = 0
scraper.urlOfLongest = ""

def extract_next_links(url, content):
    return [link.get('href') for link in BeautifulSoup(content, features="html.parser").find_all('a', href=True) if "http" in link.get('href')]

def is_valid(url):
    global WHITELISTED_DOMAINS
    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False

        valid = False
        for dom in WHITELISTED_DOMAINS:
            if dom in url:
                valid = True
        if not valid:
            return False

        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())

    except TypeError:
        print ("TypeError for ", parsed)
        raise