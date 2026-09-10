import requests
import urllib.request


def fetch(url):
    requests.get(url)
    return urllib.request.urlopen(url)
