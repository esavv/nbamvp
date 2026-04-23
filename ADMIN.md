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
     zip -r data_bundle.zip data/adv_stats/ data/email/ data/per_game_stats/ data/standings/ data/stats/
     scp -i your_key.pem data_bundle.zip ubuntu@your-instance-host:/home/ubuntu/nbamvp/

     # [remote] unzip the data (from /home/ubuntu/nbamvp)
     unzip -o data_bundle.zip
     rm data_bundle.zip

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
     # prod job: weekly Wednesdays 9am ET — use the venv’s interpreter explicitly
     0 9 * * 3 cd /home/ubuntu/nbamvp/src && /home/ubuntu/nbamvp/venv/bin/python predict_mvp.py --mode 'prod' >> /home/ubuntu/nbamvp/data/logs/prod_job.log
     ```
   - If you need a Python version newer than the system `python3`, install it (for example from [deadsnakes](https://launchpad.net/~deadsnakes/+archive/ubuntu/ppa) on LTS) and run that interpreter’s `-m venv /home/ubuntu/nbamvp/venv` instead of `python3 -m venv`.

3. **Copy AWS Results Back to Local**:  
   - Before deploying updated source code to AWS we need to ensure our local codebase has the lastest predictions from the existing deployment.
   - To copy AWS predictions back to local directory, run this locally:
     ```bash  
     scp -i nbamvp_ec2.pem ec2-user@ec2-34-230-90-208.compute-1.amazonaws.com:'/home/ec2-user/nbamvp/data/mvp_predictions/2025/predictions_2025_wk05*' data/mvp_predictions/2025/
     ```
   - Note: In the command above, update the source pattern ('...2024_wk23*') to target the right files