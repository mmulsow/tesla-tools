#!/usr/bin/env python3

from math import sin, cos, sqrt, atan2, radians
import http.client
import json
import time
import yaml


API_HOST = 'owner-api.teslamotors.com'


class TeslaAPIError(Exception):
    pass


class TeslaAPI:
    USER_AGENT = 'Python 3'

    def __init__(self):
        self.access_token = None
        self._conn = None

    def _post_request(self, url, data):
        for i in range(3):
            try:
                body = json.dumps(data)

                headers = {
                    'User-Agent': self.USER_AGENT,
                    'Content-Type': 'application/json'
                }

                if self.access_token:
                    headers['Authorization'] = 'Bearer ' + self.access_token

                if self._conn is None:
                    self._conn = http.client.HTTPSConnection(API_HOST)
                self._conn.request('POST', url, body, headers)

                res = self._conn.getresponse()
                if res.status != 200:
                    raise TeslaAPIError('Error %s: %r' %
                                        (res.status, res.read()))

                ret = json.load(res)
                break
            except Exception as e:
                if i == 2:
                    raise

                print(time.ctime(), 'Error "%s". trying again...' % (e,))
                self._conn = None
                time.sleep(10)

        return ret

    def _get_request(self, url):
        for i in range(3):
            try:
                headers = {
                    'User-Agent': self.USER_AGENT,
                    'Authorization': 'Bearer %s' % self.access_token
                }

                if self._conn is None:
                    self._conn = http.client.HTTPSConnection(API_HOST)
                self._conn.request('GET', url, headers=headers)

                res = self._conn.getresponse()
                if res.status != 200:
                    raise TeslaAPIError('Error %s: %r' %
                                        (res.status, res.read()))

                ret = json.load(res)['response']
                break
            except Exception as e:
                if isinstance(e, TeslaAPIError) or i == 2:
                    raise

                print(time.ctime(), 'Error "%s". trying again...' % (e,))
                self._conn = None
                time.sleep(10)

        return ret

    def auth(self, email, password):
        data = {
          'grant_type': 'password',
          'client_id': CLIENT_ID,
          'client_secret': CLIENT_SCT,
          'email': email,
          'password': password
        }

        return self._post_request('/oauth/token?grant_type=password', data)

    def vehicles(self):
        return self._get_request('/api/1/vehicles')

    def charge_state(self, vehicle_id):
        url = '/api/1/vehicles/%s/data_request/charge_state' % (vehicle_id,)
        return self._get_request(url)

    def drive_state(self, vehicle_id):
        url = '/api/1/vehicles/%s/data_request/drive_state' % (vehicle_id,)
        return self._get_request(url)

    def set_charge_limit(self, vehicle_id, limit):
        url = '/api/1/vehicles/%s/command/set_charge_limit' % (vehicle_id,)
        data = {'percent': limit}
        return self._post_request(url, data)


def calc_dist(p1, p2):
    # approximate radius of earth in km
    R = 6373.0

    lat1 = radians(p1['latitude'])
    lon1 = radians(p1['longitude'])
    lat2 = radians(p2['latitude'])
    lon2 = radians(p2['longitude'])

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c


def main():
    with open('config.yml') as fp:
        config = yaml.load(fp)

    t = TeslaAPI()

    changed = {}
    for user in config['users']:
        changed[user] = False

    while True:
        for user in config['users']:
            print(time.ctime(), 'Checking for user', user)

            t.access_token = config['users'][user]['access_token']
            home = config['users'][user]['home']
            home_target = config['users'][user]['targets']['home']
            away_target = config['users'][user]['targets']['away']
            vehicle_id = config['users'][user]['vehicle_id']

            try:
                charge_state = t.charge_state(vehicle_id)
            except TeslaAPIError as e:
                if 'vehicle unavailable' in str(e):
                    print(time.ctime(), 'Vehichle unavailable')
                    continue

            if charge_state['charging_state'] in ['Charging', 'Complete']:
                if changed[user]:
                    continue
                changed[user] = True

                drive_state = t.drive_state(vehicle_id)
                distance = calc_dist(home, drive_state)
                if distance < 0.1:
                    print(time.ctime(), 'Charging at home to %s%%' %
                          (charge_state['charge_limit_soc'],))
                    if charge_state['charge_limit_soc'] != home_target:
                        print(time.ctime(),
                              'Changing charge target from %s to %s at home.' %
                              (charge_state['charge_limit_soc'], home_target))
                        t.set_charge_limit(vehicle_id, home_target)
                else:
                    print(time.ctime(), 'Charging %s km from home to %s%%' %
                          (distance, charge_state['charge_limit_soc']))
                    if charge_state['charge_limit_soc'] != away_target:
                        print(time.ctime(),
                              'Changing target from %s to %s for away.' %
                              (charge_state['charge_limit_soc'], away_target))
                        t.set_charge_limit(vehicle_id, away_target)
            else:
                print(time.ctime(), 'Not charging')
                changed[user] = False

        time.sleep(60)


if __name__ == '__main__':
    main()
