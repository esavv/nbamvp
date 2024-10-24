How this app works:
 - predict_mvp.py: Contains the main() function that runs the app, which is scheduled to run weekly. Calls the other scripts
 - generate_data.py: Pulls the latest NBA stats from the basketball_reference_web_scraper library.
 - mvp_model.py: Trains the models used to make MVP predictions
 - preprocess_data.py: Is called by mvp_model.py to do some data wrangling before model training
 - nba_email.py: Emails the prediction results to users

Some instructions for managing this app:
 - Add last season's voting results to /data/mvp_results/results_YYYY.csv
     To do this, go to this URL: https://www.basketball-reference.com/awards/awards_2022.html#mvp
     Replace '2022' in the URL with the last season end year
     Go to "Share & Export" -> "Get table as CSV (for Excel)"

 - Update the season schedule in predict_mvp.py:
        > 28 season_start = date(2022, 10, 19)		# UPDATE!
        > 29 season_end   = date(2023,  4,  9)		# UPDATE!
     Get this information from wikipedia. Example: https://en.wikipedia.org/wiki/2022-23_NBA_season

 - (Nov 27, 2023) How to run the application in dev mode:
    > python3 predict_mvp --mode 'dev'

    This ensures we email test_emails.csv instead of the actual user list, keeps the model run count low,
    and saves MVP predictions as dev files instead of production files.

 - How to SSH into my ec2 instance:
    > ssh -i "nbamvp_ec2.pem" root@ec2-3-230-84-20.compute-1.amazonaws.com

 - How to set up ec2 instance for SSH access:
    - After creating an EC2 keypair and having it auto-downloaded, run this comman locally:
      > ssh-keygen -y -f your_key.pem
    - Copy the output of that command and log into your instance via EC2 Instance Connect (via the EC2 web console)
    - Open this file on your ec2 instance:
      > vi .ssh/authorized_keys
    - And paste the output you copied earlier into the first line of the file (above any pre-existing content)

 - Once I'm in there:
 -- How to view my source code:
    > cd /var/app/current
 -- How to view my cronjob:
    > vi /etc/cron.d/mycron
 -- How to view my cronjob logs:
    > vi /var/log/dev_job.log
    > vi /var/log/prod_job.log

 - How to manually zip my source for beanstalk deployment:
   Note: Update "data/mvp_predictions/2025/predictions*" for the current NBA season year
    > zip -r nbamvp_20241024_01.zip .ebextensions/ data/adv_stats/ data/mvp_predictions/2025/predictions* data/mvp_results data/per_game_stats/ data/standings/ data/stats/ img/ crontab.txt email_body.html email_template_preseason.html email_template.html eval_2021.py generate_data.py index.html mvp_model.py nba_email.py predict_mvp.py preprocess_data.py Procfile prod_emails.csv pull_images.py pw.csv rank_progress.py ranking_chart.html ranking_chart.js readme.txt requirements.txt test_emails.csv webapp.py

 - How to copy predictions in AWS back to local directory (which I'll need to do before I deploy updated source code to AWS, to make sure my local source code has the most up-to-date predictions)
   Note: in the command below, I need to update the source pattern ('...2024_wk23*') to target the right files
    > scp -i "nbamvp_ec2.pem" root@ec2-3-230-84-20.compute-1.amazonaws.com:'/var/app/current/data/mvp_predictions/2024/predictions_2024_wk23*' data/mvp_predictions/2024/
