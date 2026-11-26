# Secret Santa

Make a draw on your computer, inspect the master list, and publish encrypted assignments on GitHub Pages. Each person gets a different link, which contains the key to their assignment. The organizer can see all assignments.

## Setup

Install Python and then, in this folder, run:

```powershell
python -m pip install -r requirements.txt
```

Create a GitHub repository and push this project. In its GitHub **Settings → Pages**, under **Build and deployment**, choose **Deploy from a branch**, select your default branch and the **/docs** folder, and save. After GitHub publishes it, copy the HTTPS site URL shown there. For a project repository it normally looks like `https://USERNAME.github.io/REPOSITORY/`. This setup is generally needed once. GitHub Pages serves static files; it does not execute the Python script.

## Participants and draw

Names with spaces need quotes. Exclusions are mutual: neither person can draw the other. Self-matches are always excluded.

```powershell
python secret_santa.py add Alice Bob "Charlie Brown" Diana
python secret_santa.py exclude Alice Bob
python secret_santa.py list
python secret_santa.py draw --url https://USERNAME.github.io/REPOSITORY/
```

Use `remove NAME` to remove a participant, or `unexclude NAME NAME` to undo an exclusion. The tool reports if no valid draw is possible. The matching is randomized, though valid matchings are not guaranteed to be equally likely.

The draw creates two files:

- `private/<draw-id>.json` contains the entire master list and all links. Keep it safe: anyone with this file can see every assignment. Keep a backup if you want recovery later.
- `docs/draws/<draw-id>.json` contains encrypted assignments and is safe to publish without the links.

Review the private file, then commit and push the new file under `docs/draws/`. Wait for GitHub Pages to redeploy, test one link, and privately send each participant their own complete link. Existing draws stay available when you create a new one. The links work repeatedly; GitHub Pages cannot enforce one-time access or expiry. Anyone who gets a link can reveal that assignment, so do not post links publicly. Avoid posting a link in a place that previews or archives links if that exposure is a concern.

`participants.json` and `private/` are ignored by Git, but verify changes with `git status` before each commit. Never force-add or publish them. Anyone who has access to your computer or backups may be able to read them. GitHub Pages is public, including when the repository is private, so the hosted files must not contain plaintext assignments or link keys. The reveal page decrypts locally in the browser; the link fragment containing the key is not sent in the HTTP request. Keep the code and publishing access trusted: someone who can change the page could alter it to capture keys or assignments.

If a link leaks, create a fresh draw and send new links. Removing old public files cannot revoke copies that were already downloaded.
