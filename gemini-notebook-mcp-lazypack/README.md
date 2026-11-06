# Gemini Notebook MCP lazy pack

Connects Claude Code or Cursor to Google's remote Gemini Notebook MCP server (`https://notebook.googleapis.com/mcp`) on Windows, macOS or Linux.

This is an unofficial helper. It contains no keys or tokens, and everyone who uses it signs in with their own Google account and project.

**Status:** not yet tested end to end against Google's live server. It passes offline tests with a fake server and a dry run on Windows up to the OAuth client step. The macOS and Linux paths have only had a syntax check on the launcher.

## Before you start

- A **personal** Google account (Workspace accounts aren't supported yet) that has signed in to <https://notebook.google.com> at least once
- A Google Cloud project
- Python 3.8 or newer
- Claude Code or Cursor

The setup offers to install the Google Cloud SDK if it's missing, using winget on Windows or Homebrew on macOS. On Linux, [install it yourself](https://cloud.google.com/sdk/docs/install) first.

## Run it

| System | How |
|---|---|
| Windows | Double-click `setup.cmd` |
| macOS or Linux | Run `bash setup.sh` in a terminal |

The setup walks you through each step:

1. Finds or installs `gcloud`, and signs you in
2. Asks which project to use, then enables the API
3. Finds your OAuth client file, or shows you how to create one
4. Opens the browser sign-in
5. Tests the connection
6. Registers the server with your MCP client

Restart your MCP client when it finishes.

## Create the OAuth client

Google's docs also describe signing in with `gcloud`'s built-in client, but when this pack was built Google answered that sign-in with "This app is blocked". So the pack uses your own client, which the docs also support. It's free, and the setup prints these links with your project filled in:

1. [Google Auth Platform](https://console.cloud.google.com/auth/overview): set up the consent screen with any app name and **External** as the audience.
2. [Audience](https://console.cloud.google.com/auth/audience): add yourself as a test user and leave the app in **Testing**.
3. [Data Access](https://console.cloud.google.com/auth/scopes): choose **Add or remove scopes**, then paste this under **Manually add scopes**:
   ```
   https://www.googleapis.com/auth/notebook
   ```
4. [Clients](https://console.cloud.google.com/auth/clients): create a **Desktop app** client and download the JSON to your Downloads folder.

Each computer needs this file for sign-in. Copy it privately, or create a separate client for each computer.

## Everyday use

**Claude Code** fetches a fresh token each time it connects, so there's nothing to maintain until the sign-in itself expires.

**Cursor** uses a fixed token, which lasts about an hour and is stored as plain text in `~/.cursor/mcp.json`. To renew it, run:

```
python3 ~/.gemini-notebook-mcp/gemini_notebook_mcp.py refresh
```

While your OAuth app is in **Testing**, Google usually ends the sign-in after about 7 days. To sign in again, run:

```
python3 ~/.gemini-notebook-mcp/gemini_notebook_mcp.py login
```

On Windows, use `py -3 "%USERPROFILE%\.gemini-notebook-mcp\gemini_notebook_mcp.py"` followed by `refresh` or `login`.

## Commands and options

| Command | What it does |
|---|---|
| `setup` | Runs the guided setup (the default) |
| `login` | Signs in again |
| `verify` | Tests the connection and lists the tools |
| `refresh` | Renews the Cursor token |
| `uninstall` | Removes the client entries and saved settings |

| Option | What it does |
|---|---|
| `--project ID` | Skips the project question |
| `--client-file PATH` | Uses this OAuth client file |
| `--client claude-code`, `cursor`, `both` or `none` | Chooses which client to configure. By default it uses Claude Code if found, otherwise Cursor |
| `--force-login` | Signs in again during setup |

## Troubleshooting

| What you see | What to do |
|---|---|
| "This app is blocked" | Check you're a test user, the scope was added, and you're using your own client file |
| "Google hasn't verified this app" | Expected for your own client. Choose **Advanced**, then continue. Don't do this for apps you didn't create |
| "Missing required parameter: scope" | The sign-in link was cut off. Run the setup again and use the tab it opens |
| A page saying a scope name is invalid or outside a "legacy API" | The scope address was opened like a web page. Close it and paste the address into the Data Access page instead |
| `WORKSPACE_ACCOUNT_NOT_SUPPORTED` | Sign in with a personal Google account |
| "Account not found" | Sign in once at <https://notebook.google.com> |
| HTTP 401, or the server stops connecting | Run the `login` command |

## Keep it safe

- Never share or commit your `client_secret*.json` file or `~/.cursor/mcp.json`. The setup warns you if the client file is in a cloud-synced folder.
- The script saves only your project ID, the client file's path and your chosen clients, in `~/.gemini-notebook-mcp/config.json`.
- `uninstall` doesn't delete your client file or change your Google Cloud project. To also remove the Google sign-in, run `gcloud auth application-default revoke`.
