#!/usr/bin/env PYTHONIOENCODING=UTF-8 /usr/bin/python3
# -*- coding: utf-8 -*-

# <bitbar.title>Github pending PRs</bitbar.title>
# <bitbar.version>v1.1</bitbar.version>
# <bitbar.author>Xabi Vázquez</bitbar.author>
# <bitbar.author.github>xa-bi</bitbar.author.github>
# <bitbar.desc>This plugin will show you all your opened PRs and the state of the review.</bitbar.desc>
# <bitbar.image>https://github.com/xa-bi/bitbar-github/raw/master/images/sample-github-pending-prs.png</bitbar.image>
# <bitbar.dependencies>python</bitbar.dependencies>
# <bitbar.abouturl>https://github.com/xa-bi/bitbar-github/</bitbar.abouturl>

GITHUB_API = 'https://api.github.com/graphql'
GITHUB_ACCESS_TOKEN = ''
GITHUB_LOGIN = ''

import datetime
import json
import os
import sys
from urllib.request import Request, urlopen

GITHUB_QUERY = '''{
  search(query: "type:pr state:open author:%(login)s", type: ISSUE, first: 100) {
    edges {
      node {
        ... on PullRequest {
          repository {
            nameWithOwner
          }
          title
          url
          createdAt
          isDraft
          mergeStateStatus
          commits(last: 1) {
            nodes {
              commit {
                statusCheckRollup {
                  state
                }
              }
            }
          }
          reviews(last: 10) {
            nodes {
              author {
                login
              }
              state
            }
          }
          reviewRequests(last: 10) {
            nodes {
              requestedReviewer {
                ... on User {
                  login
                }
              }
            }
          }
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
  except Exception:
    return

  buf = response.read()
  return json.loads(buf.decode('utf-8'))

def parse_date(text):
  date_obj = datetime.datetime.strptime(text, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc)
  diff = datetime.datetime.now(datetime.timezone.utc) - date_obj
  days = diff.days
  hours = diff.seconds / 3600
  minutes = diff.seconds % 3600 / 60
  seconds = diff.seconds % 3600 % 60

  res = ''
  if days > 0:
    res = '%s day%s' %(days, 's' if days >= 2 else '')
  elif hours > 0:
    res = '%d hour%s' %(hours, 's' if hours >= 2 else '')
  elif minutes > 0:
    res = '%d minute%s' %(minutes, 's' if minutes >= 2 else '')
  elif seconds > 0:
    res = '%s second%s' %(seconds, 's' if seconds >= 2 else '')

  return res

def get_pending_requests(login):
  response = execute_github_query(GITHUB_QUERY % {'login': login})
  if response is None:
    return

  prs = response.get("data", {}).get("search", {}).get("edges", [])

  pending_requests = []
  for pr in prs:
    node = pr['node']
    title = node['title']
    url = node['url']
    date = parse_date(node['createdAt'])
    repository = node['repository']['nameWithOwner']
    is_draft = node['isDraft']
    is_blocked = node['mergeStateStatus'] == 'BLOCKED'
    commit_nodes = node['commits']['nodes']
    rollup = commit_nodes[-1]['commit']['statusCheckRollup'] if commit_nodes else None
    ci_state = rollup['state'] if rollup else None
    pending = []
    aproved = []
    comments = []
    changes_requested = []
    for reviewer in node['reviewRequests']['nodes']:
      if reviewer['requestedReviewer']:
        pending.append(reviewer['requestedReviewer']['login'])
    for reviewer in node['reviews']['nodes']:
      login = reviewer['author']['login']
      if (reviewer['state'] == 'APPROVED') and login not in pending and login not in aproved:
        aproved.append(login)
      if (reviewer['state'] == 'COMMENTED') and login not in comments:
        comments.append(login)
      if (reviewer['state'] == 'CHANGES_REQUESTED') and login not in changes_requested:
        changes_requested.append(login)
    pending_requests.append({
      'title': title,
      'url': url,
      'date': date,
      'repository': repository,
      'pending': pending,
      'aproved': aproved,
      'comments': comments,
      'changes_requested': changes_requested,
      'is_draft': is_draft,
      'is_blocked': is_blocked,
      'ci_state': ci_state
    })

  return pending_requests

def fatal_error(error):
  print('Github pending PRs| color=red')
  print('---')
  print(error)
  sys.exit(0)

if __name__ == '__main__':
  try:
    with open(os.path.dirname(os.path.realpath(__file__)) + '/github-config.json') as json_data_file:
      data = json.load(json_data_file)
      GITHUB_ACCESS_TOKEN = data['GITHUB_ACCESS_TOKEN']
      GITHUB_LOGIN = data['GITHUB_LOGIN']
  except Exception:
    fatal_error('Couldn\'t read [github-config.json] config file')

  if not all([GITHUB_ACCESS_TOKEN, GITHUB_LOGIN]):
    fatal_error('GITHUB_ACCESS_TOKEN and GITHUB_LOGIN cannot be empty')

  pending_requests = get_pending_requests(GITHUB_LOGIN)

  if pending_requests is None:
    fatal_error('Unknown error. Is GITHUB_ACCESS_TOKEN valid?')

  warn_percentage = min(len(pending_requests), 10) / 10.0
  color = '#00a357'

  if (warn_percentage > 0):
    start_color = { 'red': 255 , 'green': 196, 'blue': 0 }
    end_color = { 'red': 229 , 'green': 83, 'blue': 83 }

    red   = start_color['red'] + warn_percentage * (end_color['red'] - start_color['red'])
    green = start_color['green'] + warn_percentage * (end_color['green'] - start_color['green'])
    blue  = start_color['blue'] + warn_percentage * (end_color['blue'] - start_color['blue'])

    color = '#%02x%02x%02x' % (int(red), int(green), int(blue))

  needs_attention = any(
    pr['changes_requested'] or pr['ci_state'] == 'FAILURE'
    for pr in pending_requests
  )
  ci_running = any(pr['ci_state'] == 'PENDING' for pr in pending_requests)
  warning = ' ⚠️' if needs_attention else ''
  hourglass = ' ⏳' if ci_running else ''

  print('#%s%s%s | color=%s' % (len(pending_requests), warning, hourglass, color))
  print('---')
  if len(pending_requests) == 0:
    print('No pending PRs :tada: ')

  for pr in pending_requests:
    aproved = (", ").join(pr['aproved'])
    pending = (", ").join(pr['pending'])
    comments = (", ").join(pr['comments'])
    changes_requested = (", ").join(pr['changes_requested'])

    draft_prefix = ':construction: ' if pr['is_draft'] else ''
    blocked_suffix = ' :lock:' if pr['is_blocked'] else ''
    ci_icons = {'SUCCESS': ':white_check_mark:', 'FAILURE': ':x:', 'PENDING': ':hourglass:'}
    ci_icon = ci_icons.get(pr['ci_state'], '') + ' ' if pr['ci_state'] else ''

    title = '%s%s%s - %s (%s ago)%s| color=#586069 href=%s size=16' % (draft_prefix, ci_icon, pr['repository'], pr['title'], pr['date'], blocked_suffix, pr['url'])
    print(title.strip())

    subtitle = ''
    if (aproved != ""):
       subtitle += ":white_check_mark: " + aproved + " "
    if (changes_requested != ""):
       subtitle += ":warning: " + changes_requested + " "
    if (pending != ""):
       subtitle += ":red_circle: " + pending + " "
    if (comments != ""):
       subtitle += ":pencil: " + comments + " "
    if (subtitle != ""):
      subtitle += ' | color=#586069 size=12'
      print(subtitle.strip())

    print('---')
