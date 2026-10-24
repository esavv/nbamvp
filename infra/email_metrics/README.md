# Email metrics

## Resources

All resources use `us-east-1` in account `420664293578`.

- SES configuration set: `nbamvp-email-metrics`, event destination `posthog`.
- SNS topic: `nbamvp-email-metrics`, with one Lambda subscription.
- Lambda function and IAM role: `nbamvp-email-metrics`.
- SSM Standard SecureString: `/nbamvp/email-metrics`. It contains the PostHog project key, ingestion host, and a random recipient-ID secret. The role can read only this parameter. It has no CloudWatch Logs permissions.
- Existing managed policy `nbamvp-ses`: add only the new configuration-set ARN to its send permission. Keep all other permissions unchanged.

The domain's SES default, identities, contact list, suppression settings, EC2 instances, networking, and services are unchanged. No CloudWatch log group, alarm, dead-letter queue, database, or custom tracking domain is created. AWS still supplies standard service metrics and default delivery retries. Those are not a custom logging or recovery service.

## Events and privacy

The function maps SES events to `email_sent`, `email_delivered`, `email_opened`, `email_link_clicked`, `email_bounced`, `email_complaint_received`, and `email_unsubscribed`.

Each event has a stable HMAC recipient ID, SES message ID, source, and available `message_type`, `audience`, `season`, and `week` tags. Bounces add `bounce_type` and `bounce_subtype`. Clicks add `link_type`: `view_prediction`, `confirm_subscription`, `unsubscribe`, or `other`. URLs, query strings, tokens, email addresses, subjects, IP addresses, and user agents are not sent to PostHog. SES/SNS notifications still contain recipient and email metadata inside AWS.

Opens and clicks are approximate. SES bot likelihood is included when available. SES-managed unsubscribe URLs might not produce click events; the authoritative unsubscribe event is a subscription preference change from opted in to opted out. Direct contact edits through the API or console are not covered by this email-event path. Subscribe confirmations keep their existing app events.

PostHog event UUIDs are stable for SNS redelivery. Person profiles are disabled. These email IDs are not joined to browser IDs. `email_sent` means SES accepted the message, not delivery. Admin messages use `admin_notification`; weekly admin previews use `weekly_prediction` with audience `admin`.

## Application deployment (not done by setup)

1. Deploy the committed Python changes to `/home/ubuntu/nbamvp` with your usual release process.
2. Check that `.env` and cron do not override `SES_CONFIGURATION_SET` with an empty or different value. The new default is `nbamvp-email-metrics`, so neither needs a new variable.
3. Restart `nbamvp-web.service` to load backend changes. No EC2 reboot, frontend build, or new application dependency is required. The next weekly CLI process loads the changes automatically.
4. Send an admin-only email first. Check delivery, links, and events in PostHog before the next subscriber send.

Set `SES_CONFIGURATION_SET` to an empty string to disable tracking for a process. The web service reads `.env`; cron needs its own environment override. No historical metrics can be recovered for emails sent without this configuration set.

## Infrastructure setup or update

Use a temporary AWS CLI login profile. Install `boto3` and `botocore[crt]` in the local Python environment. Run `venv/bin/python infra/email_metrics/setup.py --profile nbamvp` with a JSON object on standard input containing `api_key` and `host`. Use the ingestion host `https://us.i.posthog.com` or `https://eu.i.posthog.com`. Supply secrets through a secure pipe, not shell arguments or a committed file.

The script creates or updates only the named resources. It retains the recipient secret on reruns. It updates Lambda code but does not replace an existing function's runtime configuration or IAM trust policy. An IAM policy can have at most five versions; review old versions manually if a later update reaches that limit. It does not deploy or restart EC2 applications.

## Optional work, not included

- CloudWatch logs, alarms, and custom dashboards.
- Dead-letter queue, longer event retention, and replay tools.
- Custom HTTPS tracking domain.
- PostHog dashboards, funnels, and browser/email identity linking.
- Additional events for rejects, rendering failures, delivery delays, or direct contact-list edits.
- Infrastructure-as-code stack management beyond this small setup script.

SES, SNS, Lambda, PostHog ingestion, and Parameter Store API usage remain subject to their normal pricing and quotas. This setup does not promise zero cost.
