#!/usr/bin/env python
import boto3
import ConfigParser
import feedparser
import json
import requests
from slackclient import SlackClient


def get_s3_client(access_key_id, secret_access_key):
    return boto3.client('s3',
                        aws_access_key_id=access_key_id,
                        aws_secret_access_key=secret_access_key)


def create_s3_bucket(client, bucket_name, region):
    bucket_names = []
    for bucket in client.list_buckets()['Buckets']:
        bucket_names.append(bucket['Name'])
    if bucket_name not in bucket_names:
        region_constraint = {'LocationConstraint': region}
        try:
            client.create_bucket(ACL='private',
                                 Bucket=bucket,
                                 CreateBucketConfiguration=region_constraint)
        except Exception as e:
            if hasattr(e, 'message'):
                print(e.message)
            else:
                print(e)


def write_to_s3(client, bucket_name, bucket_file, date, title):
    body = {'date': date, 'title': title}
    json_body = json.dumps(body)
    return client.put_object(ACL='private',
                             Bucket=bucket_name,
                             Key=bucket_file,
                             Body=json_body)


def get_s3_obj(client, bucket_name, bucket_file, region):
    try:
        body = client.get_object(Bucket=bucket_name, Key=bucket_file)['Body']
    except:
        create_s3_bucket(client, bucket_name, region)
        write_to_s3(client, bucket_name, bucket_file, '', '')
        body = client.get_object(Bucket=bucket_name, Key=bucket_file)['Body']
    return json.loads(body.read())


def get_last_modified(url):
    return requests.head(url).headers['Last-Modified']


def has_new_posts(url, date):
    last_modified = get_last_modified(url)

    if last_modified == date:
        return False
    return True


def get_new_posts(client, bucket_name, bucket_file, url, date, title):
    if has_new_posts(url, date):
        urls = []
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
    return None


def post_to_slack(slack_client, posts, slack_channel):
    for post in posts:
        slack_client.api_call('chat.postMessage',
                              channel=slack_channel,
                              text=post,
                              as_user='true')


def main():
    config_file = 'config.ini'
    config_section = 'bot0'
    config = ConfigParser.ConfigParser()
    config.read(config_file)

    access_key_id = config.get(config_section, 'access_key_id')
    secret_access_key = config.get(config_section, 'secret_access_key')
    region = config.get(config_section, 'region')
    bucket_name = config.get(config_section, 'bucket_name')
    bucket_file = config.get(config_section, 'bucket_file')
    slack_token = config.get(config_section, 'token')
    url = config.get(config_section, 'url')

    slack_channel = '#general'

    client = get_s3_client(access_key_id, secret_access_key)

    date = 'tmp'
    title = u'Project Euler with ES6 \u2013 Problem 1'
    write_to_s3(client, bucket_name, bucket_file, date, title)

    json_body = get_s3_obj(client, bucket_name, bucket_file, region)
    date = json_body['date']
    title = json_body['title']

    posts = get_new_posts(client, bucket_name, bucket_file, url, date, title)
    print(posts)
    slack_client = SlackClient(slack_token)
    post_to_slack(slack_client, posts, slack_channel)


if __name__ == '__main__':
    main()
