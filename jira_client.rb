# frozen_string_literal: true

require 'json'
require 'Base64'
require 'net/http'

# JIRA Client to access JIRA API.
class JiraClient
  # In order to make it work you gotta set both global ENV vars in as follows:
  # launchctl setenv "JIRA_USER_EMAIL" "marcelo.ribeiro@jobandtalent.com"
  # launchctl setenv "JIRA_API_TOKEN" JIRA_API_TOKEN_HERE
  # You can create your JIRA_API_TOKEN at https://id.atlassian.com/manage-profile/security/api-tokens
  def initialize(domain = 'https://jobandtalent.atlassian.net')
    @domain = domain.end_with?('/') ? domain[0..-2] : domain
    @credentials = Base64.strict_encode64("#{ENV['JIRA_USER_EMAIL']}:#{ENV['JIRA_API_TOKEN']}")
  end

  def get(uri)
    Net::HTTP.start(uri.host, uri.port, use_ssl: true) do |https|
      request = Net::HTTP::Get.new(uri)
      request['Content-Type'] = 'application/json'
      request['Authorization'] = "Basic #{@credentials}"

      response = https.request(request)
      response.code.start_with?('20') ? JSON.parse(response.body) : response.body
    end
  end

  def get_queue(servicedesk_id:, queue_id:)
    get(URI("#{@domain}/rest/servicedeskapi/servicedesk/#{servicedesk_id}/queue/#{queue_id}/issue"))
  end
end
