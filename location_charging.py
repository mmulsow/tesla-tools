#!/usr/bin/env python3

from math import sin, cos, sqrt, atan2, radians
import http.client
import getpass
import json
import time

CLIENT_ID = '81527cff06843c8634fdc09e8ac0abefb46ac849f38fe1e431c2ef2106796384'
CLIENT_SCT = 'c7257eb71a564034f9419ee651c7d0e5f7aa6bfbd18bafb5c5c033b093bb2fa3'

HOME = {
    "latitude": 30.3978822,
    "longitude": -97.7145154,
}

HOME_TARGET = 80
AWAY_TARGET = 90


class TeslaAPIError(Exception):
    pass


class TeslaAPI:
    USER_AGENT = 'Python 3'

    def __init__(self, email, password):
        self._email = email
        self._conn = http.client.HTTPSConnection('owner-api.teslamotors.com')
        self._auth_data = self.auth(email, password)

    def _post_request(self, url, data):
        body = json.dumps(data)

        headers = {
            'User-Agent': self.USER_AGENT,
            'Content-Type': 'application/json'
        }

        if hasattr(self, '_auth_data'):
            headers['Authorization'] = \
                'Bearer ' + self._auth_data['access_token']

        self._conn.request('POST', url, body, headers)

        res = self._conn.getresponse()
        if res.status != 200:
            raise TeslaAPIError('Error %s: %r' % (res.status, res.read()))

        return json.load(res)

    def _get_request(self, url):
        headers = {
            'User-Agent': self.USER_AGENT,
            'Authorization': 'Bearer %s' % self._auth_data['access_token']
        }

        self._conn.request('GET', url, headers=headers)
        res = self._conn.getresponse()
        if res.status != 200:
            raise TeslaAPIError('Error %s: %r' % (res.status, res.read()))

        return json.load(res)['response']

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
    email = input('E-mail: ')
    password = getpass.getpass()

    t = TeslaAPI(email, password)
    vehicle_id = t.vehicles()[0]['id']

    changed = False
    while True:
        charge_state = t.charge_state(vehicle_id)
        if charge_state['charging_state'] == 'Charging':
            if changed:
                continue

            drive_state = t.drive_state(vehicle_id)
            distance = calc_dist(HOME, drive_state)
            if distance < 0.1:
                print('Charging at home to %s%%' %
                      (charge_state['charge_limit_soc'],))
                if charge_state['charge_limit_soc'] != HOME_TARGET:
                    print('Changing charge target from %s to %s at home.' %
                          (charge_state['charge_limit_soc'], HOME_TARGET))
                    t.set_charge_limit(vehicle_id, HOME_TARGET)
                    changed = True
            else:
                print('Charging %s km from home to %s%%' %
                      (distance, charge_state['charge_limit_soc']))
                if charge_state['charge_limit_soc'] != AWAY_TARGET:
                    print('Changing charge target from %s to %s at home.' %
                          (charge_state['charge_limit_soc'], AWAY_TARGET))
                    t.set_charge_limit(vehicle_id, AWAY_TARGET)
                    changed = True
        else:
            print('Not charging')
            changed = False

        time.sleep(60)


if __name__ == '__main__':
    main()
