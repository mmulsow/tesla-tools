#!/usr/bin/env python3

from math import sin, cos, sqrt, atan2, radians
import time

from tesla_api import TeslaAPI, TeslaAPIError


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


def update_charge_worker(User):

    changed = {}

    while True:
        t = TeslaAPI()
        for user in User.query.all():
            t.access_token = user.access_token

            for v in user.vehicles:
                try:
                    print(time.ctime(), user.email, v.vin)

                    home = {
                        'latitude': v.home_lat,
                        'longitude': v.home_lon
                    }

                    limit = t.charge_state(v.id)['charge_limit_soc']
                    distance = calc_dist(home, t.drive_state(v.id))

                    print(time.ctime(),
                          'dist: %0.3f, limit: %s, home: %s, away: %s' %
                          (distance, limit, v.home_target, v.away_target))

                    if distance < 0.5:
                        if limit != v.home_target:
                            if changed.get(v.id) != 'home':
                                print(time.ctime(), 'changing to home')
                                changed[v.id] = 'home'
                                t.set_charge_limit(v.id, v.home_target)
                    else:
                        if limit != v.away_target:
                            if changed.get(v.id) != 'away':
                                print(time.ctime(), 'changing to away')
                                changed[v.id] = 'away'
                                t.set_charge_limit(v.id, v.away_target)

                except TeslaAPIError as e:
                    print(time.ctime(), 'Error: %s' % (e,))
                except Exception as e:
                    print(time.ctime(), 'Error: %s' % (e,))

        t = None # garbage collector hint
        time.sleep(300)
