"""Translate SES SNS notifications into privacy-limited PostHog events."""

from functools import lru_cache
import hashlib
import hmac
import json
import os
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from uuid import NAMESPACE_URL, uuid5

import boto3


EVENTS = {
    'Send': 'email_sent',
    'Delivery': 'email_delivered',
    'Open': 'email_opened',
    'Click': 'email_link_clicked',
    'Bounce': 'email_bounced',
    'Complaint': 'email_complaint_received',
    'Subscription': 'email_unsubscribed',
}


@lru_cache(maxsize=1)
def configuration():
    response = boto3.client('ssm').get_parameter(
        Name=os.environ['CONFIG_PARAMETER'], WithDecryption=True,
    )
    return json.loads(response['Parameter']['Value'])


def opted_out(preferences):
    return preferences.get('unsubscribeAll', False) or any(
        topic.get('topicName') == 'weekly-predictions'
        and topic.get('subscriptionStatus', '').lower() == 'optout'
        for topic in preferences.get('topicSubscriptionStatus', [])
    )


def link_type(link):
    parsed = urlsplit(link)
    if parsed.hostname in {'nba-mvp.com', 'www.nba-mvp.com'}:
        if parsed.path.rstrip('/') == '/confirm':
            return 'confirm_subscription'
        if parsed.path in {'', '/'}:
            return 'view_prediction'
    if parsed.hostname and parsed.hostname.endswith('.amazonaws.com') and 'unsubscribe' in parsed.path.lower():
        return 'unsubscribe'
    return 'other'


def translate(notification, sns_message_id, config):
    event_type = notification.get('eventType')
    if event_type not in EVENTS:
        return []
    mail = notification['mail']
    detail = notification.get(event_type.lower(), {})
    if event_type == 'Subscription':
        if not opted_out(detail.get('newTopicPreferences', {})) or opted_out(detail.get('oldTopicPreferences', {})):
            return []

    properties = {
        '$process_person_profile': False,
        'ses_message_id': mail['messageId'],
        'source': 'ses',
    }
    for name in ('message_type', 'audience', 'season', 'week'):
        values = mail.get('tags', {}).get(name, [])
        if values:
            value = values[0]
            properties[name] = int(value) if name in {'season', 'week'} and value.isdigit() else value
    if event_type == 'Click':
        properties['link_type'] = link_type(detail.get('link', ''))
    if event_type == 'Bounce':
        properties['bounce_type'] = detail.get('bounceType', 'Unknown')
        properties['bounce_subtype'] = detail.get('bounceSubType', 'Unknown')
    if event_type in {'Open', 'Click'} and 'isBotEvent' in detail:
        properties['bot_likelihood'] = detail['isBotEvent']

    recipients = mail.get('destination', [])
    if event_type == 'Bounce':
        recipients = [item['emailAddress'] for item in detail.get('bouncedRecipients', [])]
    elif event_type == 'Complaint':
        recipients = [item['emailAddress'] for item in detail.get('complainedRecipients', [])]
    elif event_type == 'Delivery':
        recipients = detail.get('recipients', recipients)
    batch = []
    for recipient in recipients:
        recipient_id = 'email:' + hmac.new(
            config['recipient_secret'].encode(), recipient.strip().lower().encode(), hashlib.sha256,
        ).hexdigest()
        batch.append({
            'event': EVENTS[event_type],
            'distinct_id': recipient_id,
            'properties': properties,
            'timestamp': detail.get('timestamp', mail['timestamp']),
            'uuid': str(uuid5(NAMESPACE_URL, f'{sns_message_id}:{recipient_id}')),
        })
    return batch


def handler(event, context):
    config = configuration()
    count = 0
    for record in event['Records']:
        sns = record['Sns']
        batch = translate(json.loads(sns['Message']), sns['MessageId'], config)
        if not batch:
            continue
        request = Request(
            config['host'].rstrip('/') + '/batch/',
            data=json.dumps({'api_key': config['api_key'], 'batch': batch}).encode(),
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        with urlopen(request, timeout=10) as response:
            if response.status != 200:
                raise RuntimeError('PostHog did not accept the events')
        count += len(batch)
    return {'captured': count}
