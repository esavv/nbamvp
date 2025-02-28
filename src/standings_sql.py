# Run this from the /src directory!
import csv, os, psycopg2
from basketball_reference_web_scraper import client as br
import pandas as pd

# Connect to local PostgreSQL database
conn = psycopg2.connect(
    dbname="postgres",
    user="eriksavage",
    host="localhost",
    port="5432"
)
cur = conn.cursor()

# Create the table
def createStandingsTable(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS standings (
            id SERIAL PRIMARY KEY,
            year INTEGER,
            team TEXT,
            wins INTEGER,
            losses INTEGER,
            division TEXT,
            conference TEXT,
            win_pct FLOAT,
            CONSTRAINT unique_year_team UNIQUE (year, team)
        );
    """)
    print("Table created successfully.")
    return

def populateStandingsFromCSV(cur):
    standings_dir = '../data/standings'
    for filename in os.listdir(standings_dir):
        if filename.endswith(".csv"):  # Only process .csv files
            year = int(filename.split('_')[1].split('.')[0])

            # Open the CSV file and read data
            with open(os.path.join(standings_dir, filename), newline='', encoding='utf-8') as csvfile:
                csvreader = csv.DictReader(csvfile)
                
                for row in csvreader:
                    # Extract values from CSV
                    team = row['team']
                    wins = int(row['wins'])
                    losses = int(row['losses'])
                    division = row['division']
                    conference = row['conference']
                    win_pct = wins / (wins + losses)
                    
                    # Insert the data into the standings table
                    cur.execute("""
                        INSERT INTO standings (year, team, wins, losses, division, conference, win_pct)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (year, team, wins, losses, division, conference, win_pct))

def populateStandingsFromBBRef(cur, start_year, end_year):
    for year in range(start_year, end_year + 1):
        standings_dict = br.standings(season_end_year=year)
        standings_df = pd.DataFrame.from_dict(standings_dict)

        standings_df['team'] = standings_df['team'].astype(str).str.replace('Team.', '', regex=False)
        standings_df['division'] = standings_df['division'].astype(str).str.replace('Division.', '', regex=False)
        standings_df['conference'] = standings_df['conference'].astype(str).str.replace('Conference.', '', regex=False)
        # Loop through the rows of the dataframe and insert data into PostgreSQL
        for _, row in standings_df.iterrows():
            team = row['team']
            wins = int(row['wins'])
            losses = int(row['losses'])
            division = row['division']
            conference = row['conference']
            win_pct = wins / (wins + losses)
            
            # Insert the data into the standings table
            cur.execute("""
                INSERT INTO standings (year, team, wins, losses, division, conference, win_pct)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (year, team, wins, losses, division, conference, win_pct))
    print("Data inserted successfully.")
    return

def updateStandingsFromBBRef(cur, year):
    standings_dict = br.standings(season_end_year=year)
    standings_df = pd.DataFrame.from_dict(standings_dict)

    standings_df['team'] = standings_df['team'].astype(str).str.replace('Team.', '', regex=False)
    # Loop through the rows of the dataframe and insert data into PostgreSQL
    for _, row in standings_df.iterrows():
        team = row['team']
        wins = int(row['wins'])
        losses = int(row['losses'])
        win_pct = wins / (wins + losses)
        
        # Insert the data into the standings table
        cur.execute("""
            UPDATE standings
            SET wins = %s,
                losses = %s, 
                win_pct = %s
            WHERE
                year = %s AND
                team = %s;
        """, (wins, losses, win_pct, year, team))
    print("Data updated successfully.")
    return

# createStandingsTable(cur)
# populateStandingsFromBBRef(cur, 1998, 2025)
# updateStandingsFromBBRef(cur, 2025)

# Commit changes to the database and close the cursor and connection
conn.commit()
cur.close()
conn.close()