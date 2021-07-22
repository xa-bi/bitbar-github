#!/usr/bin/env python
# -*- coding: utf-8 -*-

# <bitbar.title>Github review requests</bitbar.title>
# <bitbar.version>v1.0</bitbar.version>
# <bitbar.author>Xabi Vázquez</bitbar.author>
# <bitbar.author.github>xa-bi</bitbar.author.github>
# <bitbar.desc>This plugin will show you all the PRs waiting for your review.</bitbar.desc>
# <bitbar.image>https://github.com/xa-bi/bitbar-github/raw/master/images/sample-github-review-requests.png</bitbar.image>
# <bitbar.dependencies>python</bitbar.dependencies>
# <bitbar.abouturl>https://github.com/xa-bi/bitbar-github/</bitbar.abouturl>

GITHUB_API = 'https://api.github.com/graphql'
GITHUB_ACCESS_TOKEN = ''
GITHUB_LOGIN = ''

import datetime
import json
import os
import sys
from time import strptime
try:
  from urllib.request import Request, urlopen
except ImportError:
  from urllib2 import Request, urlopen

GITHUB_QUERY = '''{
  search(query: "type:pr state:open review-requested:%(login)s", type: ISSUE, first: 100) {
    edges {
      node {
        ... on PullRequest {
          repository {
            nameWithOwner
          }
          author {
            login
          }
          createdAt
          url
          number
          title
        }
      }
    }
  }
}'''

def execute_github_query(query):
  headers = {'Authorization': 'bearer ' + GITHUB_ACCESS_TOKEN, 'Content-Type': 'application/json'}
  data = json.dumps({'query': query}).encode('utf-8')
  req = Request(GITHUB_API, data, headers)

  try:
    response = urlopen(req)
  except:
    return

  buf = response.read()
  return json.loads(buf.decode('utf-8'))

def parse_date(text):
  date_obj = datetime.datetime.strptime(text, '%Y-%m-%dT%H:%M:%SZ')
  diff = datetime.datetime.now() - date_obj
  days = diff.days
  hours = diff.seconds / 3600
  minutes = diff.seconds % 3600 / 60
  seconds = diff.seconds % 3600 % 60

  res = ''
  if days > 0:
    res = '%s day%s' %(days, 's' if days > 1 else '')
  elif hours > 0:
    res = '%s hour%s' %(hours, 's' if hours > 1 else '')
  elif minutes > 0:
    res = '%s minute%s' %(minutes, 's' if minutes > 1 else '')
  elif seconds > 0:
    res = '%s second%s' %(seconds, 's' if seconds > 1 else '')

  return res

def get_reviews_requested(login):
  response = execute_github_query(GITHUB_QUERY % {'login': login})
  if response is None:
    return

  prs = response.get("data", {}).get("search", {}).get("edges", [])

  reviews_requested = []
  for pr in prs:
    node = pr['node']
    title = node['title']
    url = node['url']
    number = node['number']
    date = parse_date(node['createdAt'])
    repository = node['repository']['nameWithOwner']
    author = node['author']['login']
    reviews_requested.append({
      'title': title,
      'url': url,
      'number': number,
      'date': date,
      'repository': repository,
      'author': author
    })

  return reviews_requested

def fatal_error(error):
  print('Github reviews requested| color=red')
  print('---')
  print(error)
  sys.exit(0)

if __name__ == '__main__':
  try:
    with open(os.path.dirname(os.path.realpath(__file__)) + '/github-config.json') as json_data_file:
      data = json.load(json_data_file)
      GITHUB_ACCESS_TOKEN = data['GITHUB_ACCESS_TOKEN']
      GITHUB_LOGIN = data['GITHUB_LOGIN']
  except:
    fatal_error('Couldn\'t read [github-config.json] config file')

  if not all([GITHUB_ACCESS_TOKEN, GITHUB_LOGIN]):
    fatal_error('GITHUB_ACCESS_TOKEN and GITHUB_LOGIN cannot be empty')

  reviews_requested = get_reviews_requested(GITHUB_LOGIN)

  if reviews_requested is None:
    fatal_error('Unknown error. Is GITHUB_ACCESS_TOKEN valid?')

  warn_percentage = min(len(reviews_requested), 10) / 10.0
  color = '#00a357'

  if (warn_percentage > 0):
    start_color = { 'red': 255 , 'green': 196, 'blue': 0 }
    end_color = { 'red': 229 , 'green': 83, 'blue': 83 }

    red   = start_color['red'] + warn_percentage * (end_color['red'] - start_color['red'])
    green = start_color['green'] + warn_percentage * (end_color['green'] - start_color['green'])
    blue  = start_color['blue'] + warn_percentage * (end_color['blue'] - start_color['blue'])

    color = '#%02x%02x%02x' % (red, green, blue)

  print('#%s | color=%s' % (len(reviews_requested), color))
  print('---')
  if len(reviews_requested) == 0:
    print('No reviews requested :tada: ')

  for pr in reviews_requested:

    title = '%s - %s| color=#586069 href=%s size=16' % (pr['repository'], pr['title'], pr['url'])
    subtitle = '#%s opened %s ago by @%s | color=#586069 size=12' % (pr['number'], pr['date'], pr['author'])

    print(title.encode('utf-8').strip())
    print(subtitle.encode('utf-8').strip())
    print('---')
