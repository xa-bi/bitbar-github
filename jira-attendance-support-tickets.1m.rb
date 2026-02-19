#!/usr/bin/env ruby
# frozen_string_literal: true

require_relative 'jira_client'

# link this file into xbar plugins folder
# ln -s PATH/jira_script.rb XBAR_PATH/xbar/plugins/jira-attendance-support-tickets.1m.rb

# Make it executable
# chmod a+x PATH/jira_script.rb

# This makes the colour pick between: green (#02A61E), orange (#FC8900) or red (#FF0000)
# green is for zero, orange is for between 1 and 3 and red for 4 and on
def pick_hex_colour(tickets_size)
  case tickets_size
  when 0
    '#02A61E'
  when 1..3
    '#FC8900'
  else
    '#FF0000'
  end
end

def queues(ids)
  queues_ids = ids.is_a?(Array) ? ids : [ids]
  ids.map { |id| JiraClient.new.get_queue(servicedesk_id: 1, queue_id: id) }
end

# Scheduler and Workforce respectively
all_queues = queues([18, 20])
size = all_queues.sum { |queue| queue['size'].to_i }

tickets = all_queues.reduce([]) { |values, queue| values + queue['values'] }

puts "#{size} :ticket: | size=12 color=#{pick_hex_colour(size)}"
puts '---'
puts 'No :ticket: to solve :tada:' if size.zero?

tickets.each do |ticket|
  url = "https://jobandtalent.atlassian.net/browse/#{ticket['key']}"
  if ticket.dig('fields', 'status', 'name').end_with?('support')
    puts "#{ticket['key']} - #{ticket.dig('fields', 'summary')} | href=#{url} size=12"
  else
    puts "#{ticket['key']} is #{ticket.dig('fields', 'status', 'name')} | href=#{url} size=12"
  end
  puts '---'
end
