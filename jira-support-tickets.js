#!/opt/homebrew/bin/node

// Create a jira-config.json with your data.

// {
//   "JIRA_API_TOKEN": "ATATT3xFfGF",
//   "JIRA_USER_EMAIL": "xxxxxxxxxx@jobandtalent.com",
//   "JIRA_QUEUES": [18, 20],
//   "JIRA_DOMAIN": "https://jobandtalent.atlassian.net"
// }


const fs = require('fs');
const path = require('path');

const CONFIG_FILE = 'jira-config.json';
const PRIORITIES = {
  1: ':arrow_double_up:',
  2: ':arrow_up_small:',
  3: ':arrow_up_down:',
  4: ':arrow_down_small:',
  5: ':arrow_double_down:',
};
const COLORS = {
  "Solution in Development": "blue",
  "Investigation in Progress": "blue",
  "Waiting for Investigation": "gray",
  "Blocked": "blue",
  "Solution Development Done": "green",
  "Pending response": "green",
  "Scheduled to Development": "green"
};

function fatalError(error) {
  console.log(error);

  process.exit(1);
}

function timeSince(date) {
  const now = new Date();
  const diff = now - new Date(date);

  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  const rtf = new Intl.RelativeTimeFormat('en', { numeric: 'auto' });

  if (seconds < 60) return rtf.format(-seconds, 'second');
  if (minutes < 60) return rtf.format(-minutes, 'minute');
  if (hours < 24) return rtf.format(-hours, 'hour');
  return rtf.format(-days, 'day');
}

function pick_hex_colour(tickets_size) {
  if (tickets_size == 0) return '#02A61E';
  if (tickets_size <4) return '#FC8900';

  return '#FF0000';
}

function readJiraConfig() {
  try {
    const configPath = path.join(__dirname, CONFIG_FILE);

    if (!fs.existsSync(configPath)) {
      fatalError(`:x: Error: missing ${CONFIG_FILE}`);
    }

    const configData = fs.readFileSync(configPath, 'utf8');
    const config = JSON.parse(configData);

    if (["JIRA_API_TOKEN", "JIRA_USER_EMAIL", "JIRA_QUEUES", "JIRA_DOMAIN"].some( key => !config[key]) ) {
      fatalError(`:x: Error: invalid ${CONFIG_FILE} json file. Missing keys`);
    }

    return config;

  } catch (error) {
    if (error instanceof SyntaxError) {
      fatalError(`:x: Error: invalid ${CONFIG_FILE} json file`);
    } else {
      fatalError(`:x: Error: error reading ${CONFIG_FILE}`);
    }
  }
}

function getColor(color) {
  return COLORS[color] || "red";
}

async function getTickets(config, queueID, start = 0) {
  const auth = Buffer.from(`${config.JIRA_USER_EMAIL}:${config.JIRA_API_TOKEN}`).toString('base64');
  const url = `${config.JIRA_DOMAIN}/rest/servicedeskapi/servicedesk/1/queue/${queueID}/issue?start=${start}`;
  let data;

  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': `Basic ${auth}`,
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) {
      fatalError(`:x: Error: fetching data`);
    }

    const data = await response.json();

    return data;

  } catch (error) {
    fatalError(error);
  }
}

async function fetchAllOpenTickets(config, queueID) {
  let isLastPage = false;
  let totalIssues = [];
  const auth = Buffer.from(`${config.JIRA_USER_EMAIL}:${config.JIRA_API_TOKEN}`).toString('base64');

  let url = `${config.JIRA_DOMAIN}/rest/servicedeskapi/servicedesk/1/queue/${queueID}/issue`;

  while (!isLastPage) {
    const response = await fetch(url, {
      headers: {
        'Authorization': `Basic ${auth}`,
        'Accept': 'application/json'
      }
    });

    if (!response.ok) {
      fatalError(`:x: Error: fetching data`);
    }

    const data = await response.json();
    totalIssues = totalIssues.concat(data.values);

    isLastPage = data.isLastPage;
    url = data._links.next;
  }

  return totalIssues;
}

async function fetchAllTickets(config) {
  const tickets = [];

  for (queueID of config.JIRA_QUEUES) {
    const res = await fetchAllOpenTickets(config, queueID);

    res.forEach(ticket => {
      tickets.push({
        created: ticket.fields.created,
        assignee: ticket.fields.assignee?.displayName,
        reporter: ticket.fields.reporter?.displayName,
        priority: ticket.fields.priority.id,
        icon: PRIORITIES[+ticket.fields.priority.id],
        status: ticket.fields.status.name,
        summary: ticket.fields.summary,
        key: ticket.key,
        id: ticket.id,
        url: `${config.JIRA_DOMAIN}/browse/${ticket.key}`
      })
    });
  };

  return tickets;
}

async function main() {
  const config = readJiraConfig();
  tickets = await fetchAllTickets(config);

  console.log(`${tickets.length} :ticket: | size=12 color=${pick_hex_colour(tickets.length)}`);
  console.log('---');

  if (tickets.length === 0) {
    console.log('No :ticket: to solve :tada:');
  } else {
    tickets.sort((a, b) => a.priority - b.priority).forEach(ticket => {
      const assignedTo = ticket.assignee ? `Assignted to ${ticket.assignee}` : "Unassigned"
      console.log(`${ticket.icon} ${ticket.key} - ${ticket.summary} | href=${ticket.url} size=16`);
      console.log(`${ticket.status}. ${assignedTo}, reported by ${ticket.reporter} ${timeSince(ticket.created)} | color=${getColor(ticket.status)} size=12`);
      console.log('---');
    });
  }
}

main();
