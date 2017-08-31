#!/usr/bin/env python
import boto3
import configparser
import feedparser
import json
import os
import requests
from slackclient import SlackClient


def get_s3_client(access_key_id, secret_access_key):
    ''' access_key_id: aws access key for user with s3 privileges
    secret_access_key: aws secret access key for user with s3 priviliges
    returns a s3 client
    '''
    return boto3.client('s3',
                        aws_access_key_id=access_key_id,
                        aws_secret_access_key=secret_access_key)


def create_s3_bucket(client, bucket_name, region):
    ''' client: s3 client
    bucket_name: s3 bucket
    region: aws region
    creates s3 bucket in region
    '''
    bucket_names = []
    for bucket in client.list_buckets()['Buckets']:
        bucket_names.append(bucket['Name'])
    if bucket_name not in bucket_names:
        region_constraint = {'LocationConstraint': region}
        client.create_bucket(ACL='private',
                             Bucket=bucket,
                             CreateBucketConfiguration=region_constraint)


def write_to_s3(client, bucket_name, bucket_file, date, title):
    ''' client: s3 client
    bucket_name: s3 bucket
    bucket_file: name of file to upload to s3 bucket
    date: date of last update of rss feed
    title: title of last rss feed
    put json object of date and title to s3 bucket
    returns result of put object
    '''
    body = {'date': date, 'title': title}
    json_body = json.dumps(body)
    return client.put_object(ACL='private',
                             Bucket=bucket_name,
                             Key=bucket_file,
                             Body=json_body)


def get_s3_obj(client, bucket_name, bucket_file, region):
    ''' client: s3 client
    bucket_name: s3 bucket
    bucket_file: s3 object to be retrieved
    region: aws region
    if no s3 object, create initial bucket and write empty date and title to s3
    returns json of s3 object
    '''
    try:
        body = client.get_object(Bucket=bucket_name, Key=bucket_file)['Body']
    except:
        create_s3_bucket(client, bucket_name, region)
        write_to_s3(client, bucket_name, bucket_file, '', '')
        body = client.get_object(Bucket=bucket_name, Key=bucket_file)['Body']
    return json.loads(body.read())


def get_last_modified(url):
    ''' url: rss feed url
    returns header of last-modified
    '''
    return requests.head(url).headers['Last-Modified']


def has_new_posts(url, date):
    ''' url: rss feed url
    date: string. last stored last-modified date header from s3
    returns true if there is new content in rss feed
    returns false if no new content in rss feed
    '''
    last_modified = get_last_modified(url)

    if last_modified == date:
        return False
    return True


def get_new_posts(client, bucket_name, bucket_file, url, date, title):
    ''' client: s3 client
    bucket_name: s3 bucket
    bucket_file: s3 object to be retrieved
    url: rss feed url
    date: last stored last-modified date header from s3
    title: last stored rss feed's post's title
    updates json in s3 object with latest date and title
    returns list of new rss feed's posts' urls in chronological order
    '''
    urls = []
    if has_new_posts(url, date):
        feed = feedparser.parse(url)
        new_date = get_last_modified(url)
        new_title = feed.entries[0].title
        write_to_s3(client, bucket_name, bucket_file, new_date, new_title)

        for item in feed.entries:
            if item.title == title:
                break
            urls.append(item.link)
        urls.reverse()
    return urls


def post_to_slack(slack_client, posts, slack_channel):
    '''
    slack_client: slack client object
    posts: list of new rss feed's posts' urls in chronological order
    slack_channel: name of slack channel to post to
    posts new posts to slack channel
    '''
    for post in posts:
        slack_client.api_call('chat.postMessage',
                              channel=slack_channel,
                              text=post,
                              as_user='true')


def load_config(config_file, config_section):
    ''' config_file: name of config file to load environment variables from
    config_section: section of config file to load
    loads environment variables from config file if it exists or attempts to
    load environment variables from exported variables
    returns a list for the environment variables: access_key_id,
    secret_access_key, region, bucket_name, bucket_file, slack_token,
    slack_channel, url
    '''
    dir_path = os.path.dirname(os.path.realpath(__file__))

    if os.path.isfile(dir_path + '/' + config_file):
        config = configparser.ConfigParser()
        config.read(config_file)

        access_key_id = config.get(config_section, 'access_key_id')
        secret_access_key = config.get(config_section, 'secret_access_key')
        region = config.get(config_section, 'region')
        bucket_name = config.get(config_section, 'bucket_name')
        bucket_file = config.get(config_section, 'bucket_file')
        slack_token = config.get(config_section, 'token')
        slack_channel = config.get(config_section, 'channel')
        url = config.get(config_section, 'url')
    else:
        access_key_id = os.environ['access_key_id']
        secret_access_key = os.environ['secret_access_key']
        region = os.environ['region']
        bucket_name = os.environ['bucket_name']
        bucket_file = os.environ['bucket_file']
        slack_token = os.environ['token']
        slack_channel = os.environ['channel']
        url = os.environ['url']

    return [access_key_id, secret_access_key, region, bucket_name, bucket_file,
            slack_token, slack_channel, url]


def main():
    ''' loads environment variables, creates s3 client, retrives stored date
    and title of last modified date string and last post's title. print the
    posts' urls and post the urls to slack
    '''
    config_file = 'config.ini'
    config_section = 'bot0'

    (access_key_id,
     secret_access_key,
     region,
     bucket_name,
     bucket_file,
     slack_token,
     slack_channel,
     url) = load_config(config_file, config_section)

    client = get_s3_client(access_key_id, secret_access_key)

    # Temp force update
    # date = 'tmp'
    # title = u'Project Euler with ES6 \u2013 Problem 1'
    # write_to_s3(client, bucket_name, bucket_file, date, title)

    json_body = get_s3_obj(client, bucket_name, bucket_file, region)
    date = json_body['date']
    title = json_body['title']

    posts = get_new_posts(client, bucket_name, bucket_file, url, date, title)
    print(posts)
    slack_client = SlackClient(slack_token)
    post_to_slack(slack_client, posts, slack_channel)


def lambda_handler(event, context):
    ''' call main if called from aws lambda
    '''
    main()


if __name__ == '__main__':
    ''' call main if executed from terminal
    '''
    main()
