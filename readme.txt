You're probably here before the next NBA season begins. Here are
some things you should do to get ready:

 - Add last season's voting results to /data/mvp_results/results_YYYY.csv
     To do this, go to this URL: https://www.basketball-reference.com/awards/awards_2022.html#mvp
     Replace '2022' in the URL with the last season end year
     Go to "Share & Export" -> "Get table as CSV (for Excel)"

 - Update the season schedule in predict_mvp.py:
        > 13 target_year  = 2023			# UPDATE!
        > 14 season_start = date(2022, 10, 19)		# UPDATE!
        > 15 season_end   = date(2023,  4,  9)		# UPDATE!
        > 16 delta = datetime.timedelta(weeks=1)
        > 17 
        > 18 train_start = 2000
        > 19 train_end   = 2021 			# UPDATE!
     Get this information from wikipedia. Example: https://en.wikipedia.org/wiki/2022-23_NBA_season

 - As of Nov 27, 2023: To do any testing, you can now run the application in development mode! Just do this:
    > python3 predict_mvp --mode 'dev'

    This ensures we email test_emails.csv instead of the actual user list, keeps the model run count low,
    and saves MVP predictions as dev files instead of production files.

 - TODO - Oct 3 2022: Verify that predict_mvp.py works for target year before the new year.

 - How to SSH into my ec2 instance:
    > ssh -i "nbamvp_ec2.pem" root@ec2-3-230-84-20.compute-1.amazonaws.com

 - Once I'm in there:
 -- How to view my cronjob:
    > vi /etc/cron.d/mycron
 -- How to view my cronjob logs:
    > vi /var/log/job1.log
    > vi /var/log/job2.log

 - How to manually zip my source for beanstalk deployment:
    > zip -r nbamvp_20240404_07.zip .ebextensions/ data/ crontab.txt email_body.html email_template.html eval_2021.py generate_data.py mvp_model.py nba_email.py predict_mvp.py preprocess_data.py prod_emails.csv pull_images.py pw.csv rank_progress.py ranking_chart.html ranking_chart.js readme.txt requirements.txt test_emails.csv
