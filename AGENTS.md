Agent: Do not modify this file unless explicitly requested

## Project Context
- This project is basically a python script that runs weekly during the NBA season and predicts the NBA MVP based on current season stats so far, using a machine learning model trained on previous season stats and results
- The output of the script is a weekly email sent to recipients containing a table of that week's predictions
- It was initially developed in 2022. In the final weekly prediction of the last 5 season (22, 23, 24, 25, 26) it has correctly predicted the NBA MVP
- It's deployed on an AWS EC2 instance

## Style Rules

Follow these style rules in your responses:
- No setup/payoff constructions. Don't use this pattern: concede something, comma, "and," then reveal. No "You were right, and I muddied it", "not quite, and the difference is the whole reason", "Yes, and here's the argument that actually decides it"
- No two-fragment pairs used for the same cadence ("Right shape, correctly deferred")
- No landing sentences and summary beats. No "That's the whole feature", "That's the real lesson", "Two things, and they're the point"
- No significance markers: real, actual, genuinely, exactly, precisely, whole, entire, the one X, that matter, specifically
- No tautologically obvious modifiers that can be left unspoken. No "worth knowing", "in the order I'd recommend"
- Headings summarize content, not the category. No headings that withold. "A tradeoff: cold starts add 200ms", not "The one tradeoff to know about"
- No analogies, metaphors, or figurative language. Ban "shape", "load-bearing", "leans on", "the next rung", "hand over". Describe the thing directly
- No performed honesty or candor. No "to be straight with you", "the honest answer", "what I really want you to see"
- No em dashes. No rule-of-three lists unless there are exactly three things
- Don't compare against a strawman baseline. No "you get X [good] instead of Y [bad thing no one mentioned]"
- No stakes inflation or predictions about the future. No "Do that and you're ahead of where I was for years", "You're building an archive. In two years it'll know things you don't"

## Develepment & Deployment
- TODO

## git Conventions
- Commit any changes you make unless I say otherwise
- If asked to build multiple features or fix multiple bugs at once, commit each feature and/or fix separately
- For bigger multi-step work, split distinct chunks into separate local commits when it makes sense (for example: research/docs in one commit, implementation in another)
- Prepend commit messages with "feat: " for features, "fix: " for bugfixes, "doc: " for readme and other docs changes, "chore: " for gitignore changes, admin tasks, file restructures. For major features, use "feat/feature-name: ". if you're not sure if a feature is "major", ask me. if you're not sure what to prepend with, ask me.
- Never push to remote or merge to main without explicit approval
- If I say I want to commit a change myself but ask you for a draft command, do not concat various commands with `&&` into one long and unreadable command (like `cd` and `git add` and `git commit`). just tell me which dir I should be in, and any other commands should be newline-separated
