# Admin Documentation

## Scripts

- `predict_mvp.py`: Main entrypoint and coordinates all other scripts. Runs weekly.
- `generate_data.py`: Pulls the latest NBA stats using the `basketball_reference_web_scraper` package.
- `mvp_model.py`: Trains the ML models used to make predictions.
- `preprocess_data.py`: Prepares the data for model training.
- `nba_email.py`: Emails results to users.
- `season_dates.py`: Fetches next season dates from Wikipedia after the current season ends.

## Running the Application

1. **Last Season's Voting Results**:
   - During postseason and preseason runs, the application checks for last season's MVP voting results at:
     `https://www.basketball-reference.com/awards/awards_YYYY.html#mvp`
   - If `/data/mvp_results/results_YYYY.csv` already exists, it is left unchanged.
   - Otherwise, the application downloads and validates the MVP table before saving it.
   - The postseason and preseason administrator emails report the season checked, fetch status, source URL, and CSV update result.

2. **Dev Mode**:  
   - To run the application in dev mode:
     ```bash
     python3 predict_mvp --mode 'dev'  
     ```
   - Dev mode trains a weaker model, saves results as dev files instead of prod files, and emails results to admin users.

## Python Env Management

1. **Create & Manage Python Virtual Environment**:  
   - Run these commands from the main project directory. `mise` selects the latest Python 3.12 patch release for this repository without changing the system Python.
     ```bash
     # Configure and install Python 3.12 for this repository
     mise use python@3.12

     # Create a virtual environment with the mise-managed Python
     mise exec -- python -m venv venv

     # Activate the virtual environment
     source venv/bin/activate

     # Confirm the virtual environment uses Python 3.12
     python --version

     # Install the project and web backend dependencies
     python -m pip install --upgrade pip
     python -m pip install -r requirements.txt
     python -m pip install -r web/backend/requirements.txt

     # Deactivate it when done with the current session
     deactivate
     ```
   - For later setup runs, use `mise install` to install the Python version recorded in `mise.toml`, then recreate the virtual environment with `mise exec -- python -m venv venv`.

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
     zip -r "$BUNDLE" data/adv_stats/ data/per_game_stats/ data/standings/ data/stats/
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

3. **Deploy frontend updates to EC2**:
   - SSH into the instance, then run:
     ```bash
     cd /home/ubuntu/nbamvp
     git pull --ff-only
     cd web/frontend
     npm ci
     npm run build
     ```
   - `npm ci` installs the exact versions in `package-lock.json`. The build replaces `web/frontend/dist`, which FastAPI serves directly. A backend restart is not required for frontend-only changes.
   - Confirm that the deployed site responds, then check it in a browser:
     ```bash
     curl --fail --show-error --silent --output /dev/null https://nba-mvp.com
     ```

4. **Copy AWS Results Back to Local**:
   - Before deploying updated source code to AWS we need to ensure our local codebase has the lastest predictions from the existing deployment.
   - To copy AWS predictions back to local directory, run this locally:
     ```bash  
     scp -i aws_ec2.pem ec2-user@ec2-3-94-191-77.compute-1.amazonaws.com:'/home/ec2-user/nbamvp/data/mvp_predictions/2025/predictions_2025_wk05*' data/mvp_predictions/2025/
     ```
   - Note: In the command above, update the source pattern ('...2024_wk23*') to target the right files

## Previewing the Webapp

While the backend and Vite development server are running, open [http://localhost:5173/preview](http://localhost:5173/preview) to select and view each web app status. This route and its fixtures are available only in development and are excluded from production builds.

## Previewing Emails

Generate the complete preview gallery from existing prediction data and fixed admin-email fixtures:

```bash
venv/bin/python src/preview_emails.py
open static/html/previews/index.html
```

Generated user and administrator emails are separated under `static/html/previews/user` and `static/html/previews/admin`. Preseason and postseason previews include every combination of successful and unavailable season-date and voting-result fetches.

Generate one admin-email state with explicit source results:

```bash
venv/bin/python src/preview_emails.py preseason --season-dates-state success --voting-results-state not-found
venv/bin/python src/preview_emails.py postseason --season-dates-state not-found --voting-results-state success
```

Generate one email type or select a weekly prediction:

```bash
venv/bin/python src/preview_emails.py subscription
venv/bin/python src/preview_emails.py error
venv/bin/python src/preview_emails.py weekly --season 2026 --week 25 --final-week
```

This command has no send option. It does not use SES, SSM, Wikipedia, or Basketball Reference.

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
