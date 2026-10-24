"""Create the minimal email metrics resources. See README.md before use."""

import argparse
import io
import json
from pathlib import Path
import secrets
import sys
import time
import zipfile

import boto3


NAME = 'nbamvp-email-metrics'
PARAMETER = '/nbamvp/email-metrics'
REGION = 'us-east-1'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', default='nbamvp')
    args = parser.parse_args()
    # Input contains the project key. Never print it or pass it as a CLI argument.
    config = json.load(sys.stdin)
    if not config.get('api_key', '').startswith('phc_'):
        raise ValueError('A PostHog project API key is required')
    if config.get('host') not in {'https://us.i.posthog.com', 'https://eu.i.posthog.com'}:
        raise ValueError('Use the PostHog ingestion host for the project region')

    session = boto3.Session(profile_name=args.profile, region_name=REGION)
    account = session.client('sts').get_caller_identity()['Account']
    ssm = session.client('ssm')
    iam = session.client('iam')
    sns = session.client('sns')
    ses = session.client('sesv2')
    lam = session.client('lambda')
    parameter_arn = f'arn:aws:ssm:{REGION}:{account}:parameter{PARAMETER}'
    function_arn = f'arn:aws:lambda:{REGION}:{account}:function:{NAME}'
    config_arn = f'arn:aws:ses:{REGION}:{account}:configuration-set/{NAME}'

    try:
        existing = ssm.get_parameter(Name=PARAMETER, WithDecryption=True)
        config['recipient_secret'] = json.loads(existing['Parameter']['Value'])['recipient_secret']
    except ssm.exceptions.ParameterNotFound:
        config['recipient_secret'] = secrets.token_hex(32)
    ssm.put_parameter(Name=PARAMETER, Type='SecureString', Value=json.dumps(config), Overwrite=True)

    trust = {'Version': '2012-10-17', 'Statement': [{
        'Effect': 'Allow', 'Principal': {'Service': 'lambda.amazonaws.com'}, 'Action': 'sts:AssumeRole',
    }]}
    try:
        role = iam.create_role(RoleName=NAME, AssumeRolePolicyDocument=json.dumps(trust))['Role']
    except iam.exceptions.EntityAlreadyExistsException:
        role = iam.get_role(RoleName=NAME)['Role']
    # No CloudWatch Logs permissions. SSM uses the account's default SSM KMS key.
    iam.put_role_policy(RoleName=NAME, PolicyName='ReadEmailMetricsConfiguration', PolicyDocument=json.dumps({
        'Version': '2012-10-17', 'Statement': [{
            'Effect': 'Allow', 'Action': 'ssm:GetParameter', 'Resource': parameter_arn,
        }],
    }))

    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
        bundle.write(Path(__file__).with_name('handler.py'), 'handler.py')
    try:
        lam.get_function(FunctionName=NAME)
    except lam.exceptions.ResourceNotFoundException:
        for attempt in range(12):
            try:
                lam.create_function(
                    FunctionName=NAME, Runtime='python3.12', Role=role['Arn'], Handler='handler.handler',
                    Code={'ZipFile': archive.getvalue()}, Timeout=30, MemorySize=128,
                    Environment={'Variables': {'CONFIG_PARAMETER': PARAMETER}},
                )
                break
            except lam.exceptions.InvalidParameterValueException:
                if attempt == 11:
                    raise
                time.sleep(5)
    else:
        lam.update_function_code(FunctionName=NAME, ZipFile=archive.getvalue())
    lam.get_waiter('function_active_v2').wait(FunctionName=NAME)

    topic = sns.create_topic(Name=NAME)['TopicArn']
    sns.set_topic_attributes(TopicArn=topic, AttributeName='Policy', AttributeValue=json.dumps({
        'Version': '2012-10-17', 'Statement': [{
            'Effect': 'Allow', 'Principal': {'Service': 'ses.amazonaws.com'},
            'Action': 'sns:Publish', 'Resource': topic,
            'Condition': {'StringEquals': {'AWS:SourceAccount': account}, 'ArnEquals': {'AWS:SourceArn': config_arn}},
        }],
    }))
    try:
        lam.add_permission(FunctionName=NAME, StatementId='AllowSesMetricsTopic', Action='lambda:InvokeFunction',
                           Principal='sns.amazonaws.com', SourceArn=topic, SourceAccount=account)
    except lam.exceptions.ResourceConflictException:
        pass
    sns.subscribe(TopicArn=topic, Protocol='lambda', Endpoint=function_arn)
    try:
        ses.create_configuration_set(ConfigurationSetName=NAME)
    except ses.exceptions.AlreadyExistsException:
        pass
    destination = {
        'Enabled': True,
        'MatchingEventTypes': ['SEND', 'DELIVERY', 'OPEN', 'CLICK', 'BOUNCE', 'COMPLAINT', 'SUBSCRIPTION'],
        'SnsDestination': {'TopicArn': topic},
    }
    current = ses.get_configuration_set_event_destinations(ConfigurationSetName=NAME).get('EventDestinations', [])
    method = ses.update_configuration_set_event_destination if any(item['Name'] == 'posthog' for item in current) else ses.create_configuration_set_event_destination
    method(ConfigurationSetName=NAME, EventDestinationName='posthog', EventDestination=destination)

    # Extend only this app's existing send permission; retain every other statement.
    policy_arn = f'arn:aws:iam::{account}:policy/nbamvp-ses'
    version = iam.get_policy(PolicyArn=policy_arn)['Policy']['DefaultVersionId']
    document = iam.get_policy_version(PolicyArn=policy_arn, VersionId=version)['PolicyVersion']['Document']
    statement = next(item for item in document['Statement'] if item.get('Sid') == 'SendFromNbaMvpDomain')
    resources = statement['Resource']
    if isinstance(resources, str):
        resources = [resources]
    if config_arn not in resources:
        statement['Resource'] = [*resources, config_arn]
        iam.create_policy_version(PolicyArn=policy_arn, PolicyDocument=json.dumps(document), SetAsDefault=True)
    print(f'Ready: SES configuration set, SNS topic, Lambda and IAM role {NAME}; SSM {PARAMETER}.')
    print('No EC2 deployment or SES identity default change was made.')


if __name__ == '__main__':
    main()
