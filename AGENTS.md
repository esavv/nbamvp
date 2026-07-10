Agent: Do not modify this file unless explicitly requested

## Project Context
- This project is basically a python script that runs weekly during the NBA season and predicts the NBA MVP based on current season stats so far, using a machine learning model trained on previous season stats and results
- The output of the script is a weekly email sent to recipients containing a table of that week's predictions
- It was initially developed in 2022. In the final weekly prediction of the last 5 season (22, 23, 24, 25, 26) it has correctly predicted the NBA MVP
- It's deployed on an AWS EC2 instance

## Develepment & Deployment
- TODO

## git Conventions
- Commit any changes you make unless I say otherwise
- If asked to build multiple features or fix multiple bugs at once, commit each feature and/or fix separately
- For bigger multi-step work, split distinct chunks into separate local commits when it makes sense (for example: research/docs in one commit, implementation in another)
- Prepend commit messages with "feat: " for features, "fix: " for bugfixes, "doc: " for readme and other docs changes, "chore: " for gitignore changes, admin tasks, file restructures. For major features, use "feat/feature-name: ". if you're not sure if a feature is "major", ask me. if you're not sure what to prepend with, ask me.
- Never push to remote or merge to main without explicit approval
- If I say I want to commit a change myself but ask you for a draft command, do not concat various commands with `&&` into one long and unreadable command (like `cd` and `git add` and `git commit`). just tell me which dir I should be in, and any other commands should be newline-separated
