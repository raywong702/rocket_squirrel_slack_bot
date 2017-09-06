# rocket_squirrel_slack_bot

This posts new RSS feed updates to Slack channels.

https://rocketsquirrel.org/@thewongguy/python/create-a-slack-bot-for-rss-feeds

## Requirements

* AWS S3 tokens
* Slack API token

* Python 3.6.1
* boto3
* feedparser
* requests
* slackclient

## Usage

Update the config.ini or export environment variables like so.

``` shell
export access_key_id = "youraccesskeyid"
export secret_access_key = "yoursecretaccesskey"
export region = "us-west-2"
export bucket_name = "rocketsquirrel"
export bucket_file = "feed.json"
export slack_token = "yourslacktoken"
export slack_channels = "#dotorg #_general"
export slack_blurb = "A Squirrel by the name of {author} has published a new blog entry. Check it out here! {url}"
export url = "https://rocketsquirrel.org/feed"
```

If config.ini is present, it will take values from there.

Run in a cron or host on AWS Lambda.

If using AWS Lambda, upload the zip and set the environment variables.
