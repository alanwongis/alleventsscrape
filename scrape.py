#!/bin/python3
""" scrapes the allevents.in website for car related events

    Version date: Aug 27, 2022
    Licence: MIT
    Copyright: Alan Wong

"""

import json
import logging
import pprint
import re
import time

import requests
from bs4 import BeautifulSoup

START_PAGE_NUM = 1
MAX_RESULTS = 10
MAX_SEARCH_PAGES = 60  # set this to the max pages to scan on Eventbrite
SEARCH_URLS = [
    "https://www.allevents.in"]

# filtering events uses keywords to decide to which events are car related events
# However some only contain keywords which are ambiguous (e.g. "Cruise in Chigago") which
# could be car related "Cruise down the Boulevard" vs "Cruise down the Mississippi"
# Until we implement better filter or have a way top curate the results, we'll
# exclude these items
INCLUDE_GREY_LIST = False

# threshold white term number in a description that switches an event to the white list
# (set to something useful)
WHITE_SCORE_THRESHOLD = 3

# if any of the following terms show up, definitely keep
WHITE_TERMS = [
    " car ", " car,", " car/", "porsche", "volkswagen", "vehicle", "motorcar", "motorshow",
    " cars ", "cars,", "car-", "tesla", "motorsport", "jeep", "chrysler", "ferrari", "volvo",
    "toyota", " audi ", " alfa ", " lotus", "automotive", "automobile", " vw ", "lexus",
    "nissan", "mercedes", "subaru", " auto ", "truck", "vette", "electric vehicle", "bmw",
    "track day", "speedway", "garage", "summit racing", "demolition", "demo derby", "cadillac",
    "low rider", " tires", "hot rod", "hotrod", "rods", "rally", "mustang", "driving",
    "wheels", "range rover", "fuel", "supercar", "driver"]

# .. but any of these, reject
BLACK_TERMS = [
    "boat", "yacht", "ships", " ship", "booze", "aviation", "aircraft",
    "airshow", "sail", "fishing", "fisherman", "air show", "aerospace",
    "party cruise", "dance cruise", "regatta", "dinner cruise", "brunch cruise",
    "breakfast cruise", "sunset cruise", "harbor cruise", "fireworks cruise",
    "siteseeing cruise", "drinks", "beer", "drone", "escooter",
    "helicopter", " sail ", "boobs", "party bus", "dancing", "kayak",
    "paddle", "music festival", "ballooning", "balloon", "drinks",
    "waterway", "pilot", "airplane", "whale watching", "party", "dj", "river cruise",
    "weekend cruise", "beer cruise", "wine", "ferry", " dock"]

# these terms actually aren't used, but are put here for reference.
# For example, you would expect "ride" to be a white term, but it triggers
# incorrectly on "boat ride".
GREY_TERMS = ["cruise", "ride", "ford", "concours", "drive", "parking"]

save_raw_dump = False  # flag to save the raw scrape

logging.basicConfig(filename='scrape.log', level=logging.WARNING)


def _get(endpoint):
    try:
        response = requests.get(endpoint, headers=my_headers, timeout=10)
        response.raise_for_status()
        # process response
        data = response.json()
        pprint.pprint(data)
        return data
    except requests.exceptions.HTTPError as errh:
        print(errh)


def get_page(url, n):
    # get the html for the page n of the search
    response = requests.get(url + str(n))
    raw_html = response.text
    soup = BeautifulSoup(raw_html, features='html.parser')
    return soup


def parse_event_from_html(soup):
    head = soup.find_all(_class="event-head")
    desc = soup.find_all(_class="event-description")
    tick = soup.find_all(_class="event-external-tickets")




def parse_event_from_json(js):
    # some processing..
    img_url = raw_ev["image"]
    img_vars = img_url.split("/")[-1].split("-")
    img_width = "0"
    img_height = "0"
    for v in img_vars:
        if v.startswith("w"):
            img_width = v[1:]
        if v.startswith("h"):
            img_height = v[1:]

    if "name" in raw_ev["location"]["address"].keys():
        address = raw_ev["location"]["address"]["name"]
    elif "streetAddress" in raw_ev["location"]["address"].keys():
        address = raw_ev["location"]["address"]["streetAddress"]
    else:
        raise

    event = {
        "name": raw_ev["name"],
        "description": raw_ev["description"],
        "bookingUrl": None,
        "eventType": None,
        "address": {
            "addressLineOne": address,
            "addressLineTwo": "",
            "addressLineThree": "",
            "city": raw_ev["location"]["address"]["addressLocality"],
            "state": raw_ev["location"]["address"]["addressRegion"],
            "country": raw_ev["location"]["address"]["addressCountry"],
            "geolocation": {
                "latitude": raw_ev["location"]["geo"]["latitude"],
                "longitude": raw_ev["location"]["geo"]["longitude"]
            }
        },
        "coverImage": {
            "url": img_url,
            "width": img_width,
            "height": img_height,
            "thumbnail": None,
            "caption": "",
            "mediaType": "img"
        },
        "price": {
            "currency": None,
            "value": None
        },
        "startDate": raw_ev["startDate"],
        "endDate": None,
        "maximumNumberOfAvailableSpots": None,
        "webex": None,
        "socialMedias": [
            {
                "url": None,
                "socialMediaType": None
            }
        ]
    }
    return event

def parse_event_details_page(url):
    soup = BeautifulSoup(requests.get(url).text, features='html.parser')
    json_scripts = soup.find_all(attrs={"type": "application/ld+json"})

    raw_jsn = None
    for sc in json_scripts:
        jsn = json.loads(sc.text)
        if jsn["@type"].lower().find("event") >=0:
            raw_jsn = jsn

    if raw_jsn is None:
        logging.warning("cannot find json event data on page: "+url)
        return parse_event_from_html(soup)
    else: # parse the json
        return parse_event_from_json(raw_jsn)


def parse_events(soup):
    event_divs = soup.find_all(class_="item event-item box-link")
    events = []

    for n, ev_div  in enumerate(event_divs[:min(len(event_divs), MAX_RESULTS)]):
        ev_url = ev_div['data-link'].split("?")[0]
        print(n + 1, ev_url)
        event = parse_event_details_page(ev_url)
        if event:
            thumb_url = ev_div.find_all(class_="thumb lazy")[0].img["src"]
            event["coverImage"]["thumbnail"] = thumb_url
            events.append(event)

    return events


def main():
    search_term = "car-shows-in-usa"
    req = requests.get(url="https://allevents.in/events/"+search_term)
    raw_html = req.text
    soup = BeautifulSoup(raw_html, features='html.parser')
    results_root = soup.find("div", class_="resgrid-row")
    events = parse_events(results_root)
    events_file = open("allevents_events.json", "w", encoding="utf-8")
    json.dump(events, events_file)



def test():
    soup = BeautifulSoup(requests.get("https://allevents.in/florham%20park/car-show/10000407546772367").text)
    print(parse_event_from_html(soup))

if __name__ == "__main__":
    #main()
    test()




