"""Create and review the SES list or migrate confirmed newsletter subscribers."""

import argparse
import csv
import json
from pathlib import Path

import ses_service


def setup_list(_args):
  result = ses_service.create_contact_list()
  print(f'Contact list {ses_service.CONTACT_LIST_NAME}: {result}')
  print(f'Topic: {ses_service.TOPIC_NAME}')


def list_subscribers(args):
  contacts = ses_service.list_contacts(args.status)
  print(f'{len(contacts)} contact(s) in {ses_service.CONTACT_LIST_NAME}')
  for contact in contacts:
    details = ses_service.contact_details(contact['EmailAddress']) or {}
    attributes = details.get('AttributesData', '')
    try:
      attributes = json.loads(attributes) if attributes else {}
    except json.JSONDecodeError:
      attributes = {'raw': attributes}
    topic_status = next(
      (
        item['SubscriptionStatus']
        for item in contact.get('TopicPreferences', [])
        if item['TopicName'] == ses_service.TOPIC_NAME
      ),
      'DEFAULT',
    )
    updated = contact.get('LastUpdatedTimestamp')
    updated_text = updated.isoformat() if updated else ''
    print(
      f"{contact['EmailAddress']}\t{topic_status}\t"
      f"unsubscribed_all={contact.get('UnsubscribeAll', False)}\t"
      f'updated={updated_text}\tattributes={json.dumps(attributes, sort_keys=True)}'
    )


def add_subscriber(args):
  email = ses_service.normalize_email(args.email)
  if args.dry_run:
    print(f'Would opt in: {email}')
    return
  ses_service.subscribe_contact(email, source=args.source)
  print(f'Opted in: {email}')


def import_subscribers(args):
  path = Path(args.file).expanduser().resolve()
  addresses = []
  with path.open(newline='', encoding='utf-8-sig') as handle:
    for row in csv.reader(handle):
      if not row or not row[0].strip() or row[0].strip().lower() == 'email':
        continue
      addresses.append(ses_service.normalize_email(row[0].strip()))

  addresses = sorted(set(addresses))
  for email in addresses:
    if args.dry_run:
      print(f'Would opt in: {email}')
    else:
      ses_service.subscribe_contact(email, source='legacy-csv-import')
      print(f'Opted in: {email}')
  print(f'{"Reviewed" if args.dry_run else "Imported"} {len(addresses)} unique address(es).')


def parse_args():
  parser = argparse.ArgumentParser(description='Manage NBA MVP newsletter subscribers in Amazon SES.')
  subparsers = parser.add_subparsers(dest='command', required=True)

  setup_parser = subparsers.add_parser('setup', help='Create the SES contact list and topic.')
  setup_parser.set_defaults(handler=setup_list)

  list_parser = subparsers.add_parser('list', help='List and review SES contacts.')
  list_parser.add_argument('--status', choices=['OPT_IN', 'OPT_OUT'], help='Filter by topic status.')
  list_parser.set_defaults(handler=list_subscribers)

  add_parser = subparsers.add_parser('add', help='Add one previously confirmed subscriber.')
  add_parser.add_argument('--email', required=True)
  add_parser.add_argument('--source', default='manual')
  add_parser.add_argument('--dry-run', action='store_true')
  add_parser.set_defaults(handler=add_subscriber)

  import_parser = subparsers.add_parser('import-csv', help='Import previously consenting subscribers.')
  import_parser.add_argument('--file', required=True)
  import_parser.add_argument('--dry-run', action='store_true')
  import_parser.set_defaults(handler=import_subscribers)

  return parser.parse_args()


def main():
  args = parse_args()
  args.handler(args)


if __name__ == '__main__':
  main()
