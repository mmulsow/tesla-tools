#!/usr/bin/env python3

import http.client
import json
import time
import yaml


API_HOST = 'owner-api.teslamotors.com'
CLIENT_ID = '81527cff06843c8634fdc09e8ac0abefb46ac849f38fe1e431c2ef2106796384'
CLIENT_SCT = 'c7257eb71a564034f9419ee651c7d0e5f7aa6bfbd18bafb5c5c033b093bb2fa3'


class TeslaAPIError(Exception):
    pass


class TeslaAPI:
    USER_AGENT = 'Python 3'

    def __init__(self, access_token=None):
        self.access_token = access_token
        self._conn = None

    def _post_request(self, url, data):
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

        return json.load(res)

    def _get_request(self, url):
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
