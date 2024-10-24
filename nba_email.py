from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import csv, os, smtplib, ssl
import pretty_html_table
import pandas as pd

# Issue from 10/28/2022: https://stackoverflow.com/questions/72478573/how-to-send-an-email-using-python-after-googles-policy-update-on-not-allowing-j
#   Update: Fixed on 11/13/2022

def send_preseason_email(year, today, season_start, season_end, weeks_til_start, predict_start_date):
  print("\nEmail execution goes here!\n")
  port = 465  # For SSL
  smtp_server = "smtp.gmail.com"
  sender_email = "eriksmvppredictions@gmail.com"
  reader = csv.reader(open('pw.csv', 'r'))       # App Password for new email, generated on 11/14/2022
  password = next(reader)[0]
  subject = str(year) + " NBA MVP Predictions - Preseason"
  # Generate the email list
  email_list = 'test_emails.csv'
  reader = csv.reader(open(email_list, 'r'))
  bcc_emails = [row[0] for row in reader]

  # Create a multipart message and set headers
  message = MIMEMultipart() # MIMEMultipart("alternative")
  message["From"] = "Erik's MVP Predictions <" + sender_email + ">"
  message["Subject"] = subject

  # Get the empty email body template 
  with open('email_template_preseason.html', 'r') as template_file:
    html_template = template_file.read()

  # TODO: Populate the template with variables
  #html = html_template.format(table_html=table_html)

  # Add body to email
  body = MIMEText(html_template, "html")
  message.attach(body)

  # Convert message to string
  msg_body = message.as_string()

  # Do some SSL stuff
  context = ssl.create_default_context()
  context.check_hostname = False
  context.verify_mode = ssl.CERT_NONE

  # Send the email
  with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
    server.login(sender_email, password)
    server.sendmail(sender_email, bcc_emails, msg_body)

def send_nba_email(prediction_file, year, week, is_prod_email, is_last_week):
  port = 465  # For SSL
  smtp_server = "smtp.gmail.com"
  sender_email = "eriksmvppredictions@gmail.com"
  # sender_email = "eriksmvppredictor@gmail.com"  # The old email
  # receiver_email = "erikmsavage@gmail.com"      # Saving this for reference, but don't uncomment this.
  
  # reader = csv.reader(open('pw_old.csv', 'r'))  # App Password for old email, generated on 11/13/2022
  reader = csv.reader(open('pw.csv', 'r'))       # App Password for new email, generated on 11/14/2022
  password = next(reader)[0]

  subject = str(year) + " NBA MVP Predictions - Week " + str(week)
  if is_last_week:
    subject = str(year) + " NBA MVP Predictions - Final Week (Week " + str(week) + ")"
    
  if is_prod_email:     
    # Example subject: "2022 NBA MVP Predictions - Week 12"
    email_list = 'prod_emails.csv'
  else:
    subject = "[TEST] " + subject
    email_list = 'test_emails.csv'

  # Generate the email list
  reader = csv.reader(open(email_list, 'r'))
  bcc_emails = [row[0] for row in reader]

  # Create a multipart message and set headers
  message = MIMEMultipart() # MIMEMultipart("alternative")
  message["From"] = "Erik's MVP Predictions <" + sender_email + ">"
  #message["To"] = receiver_email
  message["Subject"] = subject

  # Build the table for the email...
  # Read csv using pandas and then convert the csv to html string
  # ... this code later will add into body
  df = pd.read_csv(prediction_file)
  df = df.head(n = 30)
  df['Rank'] = df['Rank'].astype(int)
  df['Predicted Votes'] = df['Predicted Votes'].astype(int)
  
  # Generate the table
  table_html = pretty_html_table.build_table(df, 'blue_light')

  # Get the empty email body template 
  with open('email_template.html', 'r') as template_file:
    html_template = template_file.read()

  # Add the table to the template
  html = html_template.format(table_html=table_html)

  # Save the table-populated hmtl for debugging & browser preview
  with open('email_body.html', 'w') as html_file:
    html_file.write(html)

  # Add body to email
  body = MIMEText(html, "html")
  message.attach(body)

  # Open csv file in binary mode
  with open(prediction_file, "rb") as attachment:
      # Add file as application/octet-stream
      # Email client can usually download this automatically as attachment
      part = MIMEBase("application", "octet-stream")
      part.set_payload(attachment.read())

  # Encode file in ASCII characters to send by email    
  encoders.encode_base64(part)

  # Add header as key/value pair to attachment part
  part.add_header(
      "Content-Disposition",
      f'attachment; filename="{os.path.basename(prediction_file)}"',
  )

  # Add attachment to message and convert message to string
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
