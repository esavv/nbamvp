-- access db:
--   $ psql -U eriksavage -d postgres

-- list tables in db
\dt

-- quit psql
\q

-- Create the standings table
CREATE TABLE standings (
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

-- Insert some rows into the standings table
INSERT INTO standings (year, team, wins, losses, division, conference, win_pct)
VALUES (2024, 'Team.BOSTON_CELTICS', 63, 17, 'Division.ATLANTIC', 'Conference.EASTERN', 63::FLOAT / (63 + 17)),
       (2024, 'Team.NEW_YORK_KNICKS', 50, 32, 'Division.ATLANTIC', 'Conference.EASTERN', 50::FLOAT / (50 + 32));

-- Update the standings for an existing row in the table:
UPDATE standings
SET wins = 64,
    losses = 18, 
    win_pct = 64::FLOAT / (64 + 18)
WHERE
    year = 2024 AND
    team = 'Team.BOSTON_CELTICS';

-- Remove some rows
DELETE FROM standings
WHERE id in (1, 2);

-- Drop the table
DROP TABLE IF EXISTS standings;

