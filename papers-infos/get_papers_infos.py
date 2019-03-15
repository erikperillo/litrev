#!/usr/bin/env python3

import user
import json
import os
import time
import random


WEBDRIVER_PATH = '/home/erik/papers-infos/chromedriver'
SRC_PATH = '/home/erik/papers-infos/titles.csv'
DST_DIR_PATH = '/home/erik/papers-infos/results_google_scholar'
MAX_N_RETRIES = 3


def get_paper_info(usr, query):
    data = {
        'query': query,
        'success': True,
        'message': '',
        'result': {},
    }
    try:
        result = usr.get_paper_info(query)
        data['result'] = result
    except Exception as e:
        print('ERROR on query "{}": "{}"'.format(query, e))
        data['success'] = False
        data['message'] = str(e)
    return data


def save_json(path, dct):
    with open(path, 'w') as f:
        json.dump(dct, f, indent=4, sort_keys=True)


def save_paper_info(i, data):
    path = os.path.join(DST_DIR_PATH, '{}.json'.format(i))
    save_json(path, data)
    return path


def main():
    if not os.path.isdir(DST_DIR_PATH):
        os.makedirs(DST_DIR_PATH)

    usr = user.User(WEBDRIVER_PATH)

    with open(SRC_PATH) as f:
        queries = [l.strip() for l in f if l.strip()]
    print('loaded {} queries'.format(len(queries)))

    for i, query in enumerate(queries):
        print('in query {}/{}: "{}"'.format(i+1, len(queries), query))
        for _ in range(MAX_N_RETRIES):
            data = get_paper_info(usr, query)
            if data['success']:
                path = save_paper_info(i, data)
                print('saved query to', path)
                break
            else:
                print('trying again')
        sleep_time = random.uniform(60, 180)
        print('sleeping for {} seconds'.format(sleep_time))
        time.sleep(sleep_time)


if __name__ == '__main__':
    main()
