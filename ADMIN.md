# Admin Documentation

## Running the Application

1. **Add Last Season's Voting Results**:
   - TODO: Automate this.
   - Navigate to the following URL:  
     `https://www.basketball-reference.com/awards/awards_YYYY.html#mvp`  
   - Replace `YYYY` with the last season's end year. Example: [2024 MVP Results](https://www.basketball-reference.com/awards/awards_2024.html#mvp)
   - Use "Share & Export" → "Get table as CSV (for Excel)" to download the data.  
   - Save it as `/data/mvp_results/results_YYYY.csv`.  

2. **Update the Season Schedule**:
   - TODO: Automate this.
   - Modify the following lines in `predict_mvp.py`:  
     ```python  
     season_start = date(2022, 10, 19)  # UPDATE!  
     season_end   = date(2023, 4, 9)    # UPDATE!  
     ```  
   - Get season start and end dates from Wikipedia. Example: [2022-2023 NBA Season](https://en.wikipedia.org/wiki/2022-23_NBA_season).

3. **Dev Mode**:  
   - To run the application in dev mode:
     ```bash  
     python3 predict_mvp --mode 'dev'  
     ```
   - Dev mode trains a weaker model, saves results as dev files instead of prod files, and emails results to admin users.

## AWS Management

1. **Enable SSH Access for an EC2 Instance**:  
   - After creating an EC2 keypair and having it auto-downloaded, run this command locally:
     ```bash  
     ssh-keygen -y -f your_key.pem
     ```
   - Copy the output of that command and log into your instance via EC2 Instance Connect (via the EC2 web console)
   - Once logged into your instance, open `.ssh/authorized_keys` & paste the output you copied into the first line of the file (above any pre-existing content)

2. **SSH into an EC2 Instance**:  
   - Run this command locally:
     ```bash  
     ssh -i "nbamvp_ec2.pem" root@ec2-3-230-84-20.compute-1.amazonaws.com
     ```

3. **Find Project Files in Beanstalk EC2 Instance**:  
   - Source code: `/var/app/current`
   - Cronjobs: `/etc/cron.d/mycron`
   - Cronjob logs:
     ```bash  
     /var/log/dev_job.log
     /var/log/prod_job.log
     ```

4. **Prepare Source Code for AWS Beanstalk Deployment**:  
   - Manually zip my source for beanstalk deployment:
     ```bash  
     zip -r nbamvp_20241025_01.zip .ebextensions/ data/adv_stats/ data/email/ data/mvp_predictions/2025/predictions* data/mvp_results/ data/per_game_stats/ data standings/ data/stats/ src/ static/ crontab.txt Procfile readme.txt requirements.txt webapp.py
     ```
   - Note: Update "data/mvp_predictions/2025/predictions*" for the current NBA season year

5. **Upgrade Dependencies on EC2 Instance**:  
   - When redeploying to AWS, you may need to manually reinstall / upgrade basketball_reference_web_scraper on the EC2 instance.
   - After logging in, run something like:
     ```bash  
     pip install --upgrade basketball_reference_web_scraper
     ```
   - To test it on EB, be sure to use python3.11 and not python3.
   - TODO: Try including the package in requirements.txt and see if EB installs it correctly

6. **Copy AWS Results Back to Local**:  
   - Before deploying updated source code to AWS we need to ensure our local codebase has the lastest predictions from the existing deployment.
   - To copy AWS predictions back to local directory, run this locally:
     ```bash  
     scp -i "nbamvp_ec2.pem" root@ec2-3-230-84-20.compute-1.amazonaws.com:'/var/app/current/data/mvp_predictions/2025/predictions_2025_wk05*' data/mvp_predictions/2025/
     ```
   - Note: In the command above, update the source pattern ('...2024_wk23*') to target the right files