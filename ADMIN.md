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
   - On an instance with this AMI: Amazon Linux 2023 kernel-6.1 AMI:
     ```bash  
     # [local] ssh into the instance
     ssh -i nbamvp_ec2.pem ec2-user@ec2-34-230-90-208.compute-1.amazonaws.com

     # [remote] clone the repo
     sudo yum install git -y
     git clone https://github.com/esavv/nbamvp.git

     # [local] copy over the data
     zip -r data_20250924_01.zip data/adv_stats/ data/email/ data/per_game_stats/ data/standings/ data/stats/
     scp -i nbamvp_ec2.pem -r data_20250924_01.zip ec2-user@ec2-34-230-90-208.compute-1.amazonaws.com:/home/ec2-user/nbamvp

     # [remote] unzip the data
     unzip data_20250924_01.zip
     rm data_20250924_01.zip

     # [remote] install correct python version, create venv and install requirements
     sudo dnf install -y python3.11 python3.11-devel
     python3.11 -m venv venv
     source venv/bin/activate
     pip install -r requirements.txt

     # [remote] launch the app by installing & setting up the cronjob
     # install
     sudo dnf install cronie -y
     sudo systemctl enable crond
     sudo systemctl start crond

     # check status
     systemctl status crond

     # configure cronjob
     crontab -e

     CRON_TZ=America/New_York
     # test job that runs every day at 9:05am
     5 9 * * * cd /home/ec2-user/nbamvp && source venv/bin/activate && cd src && python predict_mvp.py --mode 'dev' >> /home/ec2-user/nbamvp/data/logs/dev_job.log && deactivate
     # prod job that runs once a week on wednesdays starting at 9am locally (and runs every hour again for rest of the day just in case)
     0 9-23 * * 3 cd /home/ec2-user/nbamvp && source venv/bin/activate && cd src && python predict_mvp.py --mode 'prod' >> /home/ec2-user/nbamvp/data/logs/dev_job.log && deactivate
     ```

3. **Copy AWS Results Back to Local**:  
   - Before deploying updated source code to AWS we need to ensure our local codebase has the lastest predictions from the existing deployment.
   - To copy AWS predictions back to local directory, run this locally:
     ```bash  
     scp -i nbamvp_ec2.pem ec2-user@ec2-34-230-90-208.compute-1.amazonaws.com:'/home/ec2-user/nbamvp/data/mvp_predictions/2025/predictions_2025_wk05*' data/mvp_predictions/2025/
     ```
   - Note: In the command above, update the source pattern ('...2024_wk23*') to target the right files