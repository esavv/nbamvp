# Admin Documentation

## Running the Application

1. **Add Last Season's Voting Results**:
   - TODO: Automate this.
   - Navigate to the following URL:  
     `https://www.basketball-reference.com/awards/awards_YYYY.html#mvp`  
   - Replace `YYYY` with the last season's end year. Example: [2024 MVP Results](https://www.basketball-reference.com/awards/awards_2024.html#mvp)
   - Use "Share & Export" → "Get table as CSV (for Excel)" to download the data.  
   - Save it as `/data/mvp_results/results_YYYY.csv`.  

2. **Dev Mode**:  
   - To run the application in dev mode:
     ```bash  
     python3 predict_mvp --mode 'dev'  
     ```
   - Dev mode trains a weaker model, saves results as dev files instead of prod files, and emails results to admin users.

3. **Preview the Weekly Email**:
   - Render an email from an existing production prediction without regenerating data or sending anything:
     ```bash
     venv/bin/python src/preview_nba_email.py --season 2026 --week 25
     open static/html/email_body.html
     ```
   - Omit `--week` to use the latest available prediction for the selected season.
   - To send the preview only to the administrator stored in SSM Parameter Store:
     ```bash
     venv/bin/python src/preview_nba_email.py --season 2026 --week 25 --send
     ```
   - From a local machine, use a restricted AWS profile and override the SSM administrator address:
     ```bash
     AWS_PROFILE=nbamvp-dev \
     ADMIN_EMAIL=you@example.com \
     venv/bin/python src/preview_nba_email.py --season 2026 --week 25 --send
     ```
   - The local profile only needs the policy in `web/deploy/local-dev-iam-policy.json`. Replace `<AWS_ACCOUNT_ID>` and `<VERIFIED_ADMIN_EMAIL>` before creating the policy. While SES is sandboxed, IAM must authorize both the sending domain identity and the verified recipient identity.
   - The preview command cannot send to the production recipient list. Set `WEBAPP_URL` to override the default `https://nba-mvp.com` link when needed.

## Amazon SES Email Management

The application sends from `predictions@nba-mvp.com` through SES in `us-east-1`. Public subscribers are stored in the `nba-mvp-prod` contact list under the `weekly-predictions` topic. Administrative and test emails are sent directly to the address stored at `/nbamvp/admin-email` in SSM Parameter Store.

1. **Required SSM parameters**:
   - `/nbamvp/admin-email`: `String` containing the verified administrator email.
   - `/nbamvp/subscription-token-secret`: `SecureString` containing a random secret of at least 32 bytes. Generate a value locally with:
     ```bash
     python3 -c "import secrets; print(secrets.token_urlsafe(48))"
     ```

2. **Create the subscriber list and topic**:
   ```bash
   venv/bin/python src/manage_subscribers.py setup
   ```

3. **Review subscribers**:
   ```bash
   venv/bin/python src/manage_subscribers.py list
   venv/bin/python src/manage_subscribers.py list --status OPT_IN
   ```

4. **Import previously consenting recipients**:
   ```bash
   venv/bin/python src/manage_subscribers.py import-csv --file data/email/prod_emails.csv --dry-run
   venv/bin/python src/manage_subscribers.py import-csv --file data/email/prod_emails.csv
   ```

5. **EC2 permissions**:
   - Replace `<AWS_ACCOUNT_ID>` in `web/deploy/iam-policy.json`.
   - Create a customer-managed IAM policy from that file and attach it to the EC2 instance role.
   - Do not create SES SMTP credentials or store AWS access keys on the instance.

## Python Env Management

1. **Create & Manage Python Virtual Environment**:  
    ```bash  
    # Create a virtual environment from main project directory
    python3 -m venv venv

    # Activate the virtual environment
    source venv/bin/activate

    # Deactivate it when done with the current session
    deactivate

    # If the terminal prompt gets messed up after deactivating
    export PS1="\h:\W \u$ "
    ```

## AWS Management

1. **Enable SSH Access for an EC2 Instance**:  
   - After creating an EC2 keypair and having it auto-downloaded, run this command locally:
     ```bash  
     ssh-keygen -y -f your_key.pem
     ```
   - Copy the output of that command and log into your instance via EC2 Instance Connect (via the EC2 web console)
   - Once logged into your instance, open `.ssh/authorized_keys` & paste the output you copied into the first line of the file (above any pre-existing content)

2. **Set up and run the app on a fresh EC2 Instance**:  
   - On an Ubuntu EC2 instance (e.g. Ubuntu Server LTS), use a dedicated project directory and virtualenv under `/home/ubuntu/nbamvp` so this app’s Python and packages stay isolated from anything else on the host (for example another API’s venv).
     ```bash  
     # [local] SSH into the instance
     ssh -i aws_ec2.pem ubuntu@ec2-3-94-191-77.compute-1.amazonaws.com

     # [remote] packages: git, Python with venv support, headers for wheels that compile C extensions
     sudo apt update
     sudo apt install -y git python3 python3-venv python3-dev unzip cron

     # [remote] clone into the project path (adjust URL if you use a fork)
     cd /home/ubuntu
     git clone https://github.com/esavv/nbamvp.git
     cd nbamvp

     # [local] copy over the data bundle
     BUNDLE="data_bundle_$(date +%Y%m%d%H%M%S).zip"
     zip -r "$BUNDLE" data/adv_stats/ data/email/ data/per_game_stats/ data/standings/ data/stats/
     scp -i aws_ec2.pem "$BUNDLE" ubuntu@ec2-3-94-191-77.compute-1.amazonaws.com:/home/ubuntu/nbamvp/

     # [remote] unzip the data (from /home/ubuntu/nbamvp); assumes at most one data_bundle_*.zip in the dir
     unzip -o data_bundle_*.zip
     rm data_bundle_*.zip
     mkdir -p /home/ubuntu/nbamvp/data/logs

     # [remote] isolated venv for nbamvp only (not shared with other apps on the same host)
     python3 -m venv /home/ubuntu/nbamvp/venv
     source /home/ubuntu/nbamvp/venv/bin/activate
     pip install --upgrade pip
     pip install -r requirements.txt
     deactivate

     # [remote] schedule prod runs with cron (Ubuntu service unit is `cron`)
     sudo systemctl enable cron
     sudo systemctl start cron
     systemctl status cron

     crontab -e

     CRON_TZ=America/New_York
     # prod job: weekly Wednesdays 9am ET
     0 9 * * 3 cd /home/ubuntu/nbamvp/src && /home/ubuntu/nbamvp/venv/bin/python predict_mvp.py --mode 'prod' >> /home/ubuntu/nbamvp/data/logs/prod_job.log 2>&1
     ```
   - If you need a Python version newer than the system `python3`, install it (for example from [deadsnakes](https://launchpad.net/~deadsnakes/+archive/ubuntu/ppa) on LTS) and run that interpreter’s `-m venv /home/ubuntu/nbamvp/venv` instead of `python3 -m venv`.

3. **Copy AWS Results Back to Local**:  
   - Before deploying updated source code to AWS we need to ensure our local codebase has the lastest predictions from the existing deployment.
   - To copy AWS predictions back to local directory, run this locally:
     ```bash  
     scp -i nbamvp_ec2.pem ec2-user@ec2-34-230-90-208.compute-1.amazonaws.com:'/home/ec2-user/nbamvp/data/mvp_predictions/2025/predictions_2025_wk05*' data/mvp_predictions/2025/
     ```
   - Note: In the command above, update the source pattern ('...2024_wk23*') to target the right files