#!/bin/env python3
from argparse import ArgumentParser
from configparser import ConfigParser
from os import path
from re import compile as compile_
from requests import post, get
from requests.auth import HTTPBasicAuth

configPath = path.join(path.dirname(path.realpath(__file__)), 'config.ini')

config = ConfigParser()
config.read(configPath)

headers = {'User-Agent': 'ASF license checker by /u/prTopii'}
tokenClient = HTTPBasicAuth(config['Token']['id'], config['Token']['secret'])
tokenPost = {'grant_type': 'password', 'username': config['Login']['user'],
             'password': config['Login']['pass']}

ipc = config['DEFAULT']['ipchost']
licensed = config['DEFAULT']['licensed'].split(',')
license = compile_(r'!addlicense\s.+?,?(((,?|,\s?)\d+)+)')


def getReplies(comments):
    output = []
    for commentInfo in comments['data']['children']:
        try:
            comment = license.search(commentInfo['data']['body'])
            if comment:
                output = [c.strip(',').strip(' ') for c in
                          comment[1].split(',')]
            if commentInfo['data']['replies']:
                replies = getReplies(commentInfo['data']['replies'])
                if replies:
                    output.extend(replies)
        except Exception:
            pass
    if output:
        return output


def checkComments(link):
    try:
        commentRes = get(f'https://oauth.reddit.com{link}.json',
                         headers=headers).json()
    except Exception:
        print('Couldn\'t load comments.')
        return
    return getReplies(commentRes[1])


def checkSub(subreddits='r/FreeGamesOnSteam'):
    ids = set()
    try:
        tokenRes = post('https://www.reddit.com/api/v1/access_token',
                        auth=tokenClient, data=tokenPost,
                        headers=headers).json()
    except Exception:
        print('Couldn\'t connect to reddit api.')
        return
    headers['Authorization'] = tokenRes['token_type'] + ' ' \
        + tokenRes['access_token']
    for sub in subreddits.split(','):
        try:
            subRes = get(f'https://oauth.reddit.com/{sub}/new.json',
                         headers=headers).json()
        except Exception:
            print(f'Couldn\'t connect to {sub}.')
            break
        posts = [p['data']['permalink'] for p in subRes['data']['children']
                 if p['kind'] == 't3']
        for child in posts:
            comments = checkComments(child)
            if comments:
                for comment in comments:
                    if comment not in ids:
                        ids.add(comment)
    if ids:
        newIds = set(id for id in ids if id not in licensed)
        if newIds:
            post(ipc + f'/Api/Command/addlicense%20ASF%20{"%2C".join(newIds)}')
    config['DEFAULT']['licensed'] = ','.join(ids)
    with open(configPath, 'w') as f:
        config.write(f)


if __name__ == '__main__':
    parser = ArgumentParser(
        description='Checks subreddit(s) for steam new licenses.')
    parser.add_argument('sub', nargs='?', default='r/FreeGamesOnSteam',
                        help='Subreddit(s) to open. Takes r/subreddit or '
                        'user/subreddit. Separate subs with a comma.'
                        ' Defaults to r/FreeGamesOnSteam')
    args = parser.parse_args()
    checkSub(args.sub)
