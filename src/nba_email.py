from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import csv, os, smtplib, ssl
import pretty_html_table
import pandas as pd

port = 465  # For SSL
smtp_server = "smtp.gmail.com"
sender_email = "eriksmvppredictions@gmail.com"
pw_file = '../data/email/pw.csv'
reader = csv.reader(open(pw_file, 'r'))       # App Password for new email, generated on 11/14/2022
password = next(reader)[0]
message = MIMEMultipart() # MIMEMultipart("alternative")
message["From"] = "Erik's MVP Predictions <" + sender_email + ">"

def send_nba_email(prediction_file, year, week, mode, is_last_week):
  subject = str(year) + " NBA MVP Predictions - Week " + str(week)
  if is_last_week:
    subject = str(year) + " NBA MVP Predictions - Final Week (Week " + str(week) + ")"
    
  if mode == 'prod':     
    # Example subject: "2022 NBA MVP Predictions - Week 12"
    email_list = '../data/email/prod_emails.csv'
  else:
    subject = "[TEST] " + subject
    email_list = '../data/email/test_emails.csv'

  # Read, trim, and format the predictions table for the email body
  df = pd.read_csv(prediction_file)
  df = df.head(n = 30)
  df['Rank'] = df['Rank'].astype(int)
  df['Predicted Votes'] = df['Predicted Votes'].astype(int)
  table_html = pretty_html_table.build_table(df, 'blue_light')

  # Populate the email template with the formatted predictions table
  email_template_path = '../static/html/email_template.html'
  with open(email_template_path, 'r') as template_file:
    html_template = template_file.read()
  html = html_template.format(table_html=table_html)

  # Save the email body hmtl for debugging & browser preview
  email_body_path = '../static/html/email_body.html'
  with open(email_body_path, 'w') as html_file:
    html_file.write(html)

  # Prepare the predictions csv file as an attachment
  with open(prediction_file, "rb") as attachment:
      # Add file as application/octet-stream
      # Email client can usually download this automatically as attachment
      part = MIMEBase("application", "octet-stream")
      part.set_payload(attachment.read())
  encoders.encode_base64(part)
  part.add_header(
      "Content-Disposition",
      f'attachment; filename="{os.path.basename(prediction_file)}"',
  )

  finalize_email(email_list, subject, html, part)

def send_preseason_email(year, season_start, season_end, weeks_til_start, predict_start_date):
  if weeks_til_start == 1:
    subject = str(year) + " NBA MVP Preseason: First Prediction in " + str(weeks_til_start) + " Week!"
  else: 
    subject = str(year) + " NBA MVP Preseason: First Prediction in " + str(weeks_til_start) + " Weeks!"
  email_list = '../data/email/test_emails.csv'

  # Get the empty email body template 
  email_template_preseason_path = '../static/html/email_template_preseason.html'
  with open(email_template_preseason_path, 'r') as template_file:
    html_template = template_file.read()

  # Populate the template with variables
  html = html_template.format(season_start=season_start, season_end=season_end, predict_start_date=predict_start_date)

  finalize_email(email_list, subject, html)

def send_error_email(year, week, traceback_str):
  print("\nSending an error email notification!\n")

  subject = "ERROR: " + str(year) + " NBA MVP Predictions - Week " + str(week)

  email_list = '../data/email/test_emails.csv'

  # Get the empty email body template 
  email_template_preseason_path = '../static/html/email_template_error.html'
  with open(email_template_preseason_path, 'r') as template_file:
    html_template = template_file.read()

  # Populate the template with variables
  html = html_template.replace("{traceback_str}", traceback_str)

  finalize_email(email_list, subject, html)

def finalize_email(email_list, subject, html, part=None):
  reader = csv.reader(open(email_list, 'r'))
  bcc_emails = [row[0] for row in reader]

  message["Subject"] = subject
  body = MIMEText(html, "html")
  message.attach(body)
  if part:
    message.attach(part)
  msg_body = message.as_string()

  # Do some SSL stuff
  context = ssl.create_default_context()
  context.check_hostname = False
  context.verify_mode = ssl.CERT_NONE

  # Send the email
  with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
    server.login(sender_email, password)
    server.sendmail(sender_email, bcc_emails, msg_body)
