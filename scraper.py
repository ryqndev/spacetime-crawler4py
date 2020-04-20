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

def visible(item):
    return not ((item.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]']) or isinstance(item, Comment))

def cleanHTML(content):
    return u" ".join(x.strip() for x in filter(visible, BeautifulSoup(content, 'html.parser').findAll(text=True)))

def scraper(url, resp):
    if resp.status_code == 200:
        links = extract_next_links(url, resp)
        tokenMap = tokenize(cleanHTML(resp.content))
        return [link for link in links if is_valid(link)]
    else:
        print(f"Error: status_code = {resp.status_code} from url = {url}")

def extract_next_links(url, resp):
    return [link.get('href') for link in BeautifulSoup(resp.content).find_all('a', href=True) if "http" in link.get('href')]

def is_valid(url):
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