# -*- coding: utf-8 -*-
from bs4 import BeautifulSoup
import json
import requests
import time

from rdc.etl.harness.threaded import ThreadedHarness
from rdc.etl.hash import Hash
from rdc.etl.io import STDIN
from rdc.etl.transform import Transform
from rdc.etl.transform.extract import Extract
from rdc.etl.transform.flow.sort import Sort
from rdc.etl.transform.join import Join
from rdc.etl.transform.util import Log

URL_CAPITALS = u'http://en.wikipedia.org/wiki/List_of_national_capitals_in_alphabetical_order'
URL_MASK_GEOCODE = u'http://maps.googleapis.com/maps/api/geocode/json?sensor=false&address={address}'

@Extract
def extract_capitals():
    r = requests.get(URL_CAPITALS)
    capitals = BeautifulSoup(r.content)

    for tr in capitals.select('table.wikitable tr'):
        td = tr.find_all('td')
        if len(td) >= 2:
            city = td[0].select('a:first-child')[0].string
            country = td[1].select('a:first-child')[0].string
            if city and len(city) and country and len(country):
                yield Hash((('city', city), ('country', country), ))

@Transform
def add_address(hash, channel=STDIN):
    # TODO - logic for forming address could be much more complex (ex. street addresses, regions, free-form, etc.)
    address = None
    if 'city' in hash and len(hash['city']) and 'country' in hash and len(hash['country']):
        address = hash['city'] + ',' + hash['country']

    yield hash.update({'address': address})

@Join
def geocode(hash, channel=STDIN):
    latitude = None
    longitude = None
    
    if 'address' in hash:
        time.sleep(0.1)
        r = requests.get(URL_MASK_GEOCODE.format(**hash))
        r_json = json.loads(r.content)
        try:
            latitude = r_json['results'][0]['geometry']['location']['lat']
            longitude = r_json['results'][0]['geometry']['location']['lng']
        except (IndexError, KeyError,):
            pass

    yield hash.update({'latitude': latitude, 'longitude': longitude})

if __name__ == '__main__':
    harness = ThreadedHarness()
    harness.add_chain(extract_capitals, add_address, geocode, Log(), Sort(key=('country', )), Log())
    harness()

    print '\n'.join(map(repr, harness.get_threads()))