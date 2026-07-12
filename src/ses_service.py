"""Shared Amazon SES v2 delivery and contact-list helpers."""

from datetime import datetime, timezone
from functools import lru_cache
import json
import os

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from email_validator import EmailNotValidError, validate_email


AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
CONTACT_LIST_NAME = os.getenv('SES_CONTACT_LIST_NAME', 'nba-mvp-prod')
TOPIC_NAME = os.getenv('SES_TOPIC_NAME', 'weekly-predictions')
FROM_EMAIL = os.getenv('SES_FROM_EMAIL', 'NBA MVP Predictions <predictions@nba-mvp.com>')
REPLY_TO_EMAIL = os.getenv('SES_REPLY_TO_EMAIL', '')
CONFIGURATION_SET = os.getenv('SES_CONFIGURATION_SET', '')
ADMIN_EMAIL_PARAMETER = os.getenv('ADMIN_EMAIL_PARAMETER', '/nbamvp/admin-email')
SUBSCRIPTION_SECRET_PARAMETER = os.getenv(
  'SUBSCRIPTION_SECRET_PARAMETER',
  '/nbamvp/subscription-token-secret',
)


@lru_cache(maxsize=1)
def ses_client():
  return boto3.client(
    'sesv2',
    region_name=AWS_REGION,
    config=Config(retries={'max_attempts': 5, 'mode': 'standard'}),
  )


@lru_cache(maxsize=1)
def ssm_client():
  return boto3.client('ssm', region_name=AWS_REGION)


def normalize_email(email):
  try:
    return validate_email(email, check_deliverability=False).normalized.lower()
  except EmailNotValidError as exc:
    raise ValueError(str(exc)) from exc


@lru_cache(maxsize=8)
def get_parameter(name, decrypt=False):
  response = ssm_client().get_parameter(Name=name, WithDecryption=decrypt)
  return response['Parameter']['Value']


def get_admin_email():
  return normalize_email(get_parameter(ADMIN_EMAIL_PARAMETER))


def get_subscription_secret():
  env_secret = os.getenv('SUBSCRIPTION_TOKEN_SECRET')
  if env_secret:
    return env_secret
  return get_parameter(SUBSCRIPTION_SECRET_PARAMETER, decrypt=True)


def send_email(to_address, subject, html, text, *, subscription_managed=False, tags=None):
  request = {
    'FromEmailAddress': FROM_EMAIL,
    'Destination': {'ToAddresses': [normalize_email(to_address)]},
    'Content': {
      'Simple': {
        'Subject': {'Data': subject, 'Charset': 'UTF-8'},
        'Body': {
          'Text': {'Data': text, 'Charset': 'UTF-8'},
          'Html': {'Data': html, 'Charset': 'UTF-8'},
        },
      },
    },
  }
  if REPLY_TO_EMAIL:
    request['ReplyToAddresses'] = [normalize_email(REPLY_TO_EMAIL)]
  if CONFIGURATION_SET:
    request['ConfigurationSetName'] = CONFIGURATION_SET
  if tags:
    request['EmailTags'] = [{'Name': key, 'Value': str(value)} for key, value in tags.items()]
  if subscription_managed:
    request['ListManagementOptions'] = {
      'ContactListName': CONTACT_LIST_NAME,
      'TopicName': TOPIC_NAME,
    }
  return ses_client().send_email(**request)


def send_admin_email(subject, html, text=None):
  return send_email(
    get_admin_email(),
    subject,
    html,
    text or 'NBA MVP Predictions administrative notification.',
    tags={'audience': 'admin'},
  )


def create_contact_list():
  try:
    ses_client().create_contact_list(
      ContactListName=CONTACT_LIST_NAME,
      Description='Confirmed NBA MVP Predictions newsletter subscribers.',
      Topics=[
        {
          'TopicName': TOPIC_NAME,
          'DisplayName': 'Weekly NBA MVP Predictions',
          'Description': 'Weekly predictions sent during the NBA regular season.',
          'DefaultSubscriptionStatus': 'OPT_OUT',
        }
      ],
    )
    return 'created'
  except ses_client().exceptions.AlreadyExistsException:
    return 'exists'


def subscribe_contact(email, source='web'):
  email = normalize_email(email)
  attributes = json.dumps({
    'source': source,
    'confirmed_at': datetime.now(timezone.utc).isoformat(),
  })
  preferences = [{'TopicName': TOPIC_NAME, 'SubscriptionStatus': 'OPT_IN'}]
  try:
    ses_client().create_contact(
      ContactListName=CONTACT_LIST_NAME,
      EmailAddress=email,
      TopicPreferences=preferences,
      UnsubscribeAll=False,
      AttributesData=attributes,
    )
  except ses_client().exceptions.AlreadyExistsException:
    ses_client().update_contact(
      ContactListName=CONTACT_LIST_NAME,
      EmailAddress=email,
      TopicPreferences=preferences,
      UnsubscribeAll=False,
      AttributesData=attributes,
    )
  return email


def list_contacts(status=None):
  contacts = []
  request = {'ContactListName': CONTACT_LIST_NAME, 'PageSize': 100}
  if status:
    request['Filter'] = {
      'FilteredStatus': status,
      'TopicFilter': {
        'TopicName': TOPIC_NAME,
        'UseDefaultIfPreferenceUnavailable': False,
      },
    }

  while True:
    response = ses_client().list_contacts(**request)
    contacts.extend(response.get('Contacts', []))
    next_token = response.get('NextToken')
    if not next_token:
      return contacts
    request['NextToken'] = next_token


def opted_in_contacts():
  return list_contacts('OPT_IN')


def contact_details(email):
  try:
    return ses_client().get_contact(
      ContactListName=CONTACT_LIST_NAME,
      EmailAddress=normalize_email(email),
    )
  except ClientError as exc:
    if exc.response.get('Error', {}).get('Code') == 'NotFoundException':
      return None
    raise
