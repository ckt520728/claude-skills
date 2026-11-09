# Pitfalls: connecting Claude, ChatGPT and Gemini by subscription login

Each item was hit or measured in a real session (Windows 11, PowerShell 5.1 and Git Bash, Python 3.12, Codex CLI 0.166, Gemini CLI 0.67).

## Login and auth

1. **Login needs a human and a browser.** An agent cannot complete `gemini` Login with Google. Ask the user to type `! gemini`.
2. **Codex login can already exist.** Run `codex login status` first. It printed "Logged in using ChatGPT" and no setup was needed.
3. **Gemini login state is hard to read.** No `oauth_creds.json` existed, yet a call authenticated. Do not use that file as the status check. One real call is the test.
4. **A subscription is not the same as a quota for every model.** Gemini returned 429 "input tokens per day limit exceeded on Free Tier" with limit 0 for `gemini-4-argon`. The CLI saw a free-tier account. Verify the model on the CLI itself, not only on the API list.
5. **An API key in the environment can silently win.** Gemini CLI prefers `GEMINI_API_KEY` or `GOOGLE_API_KEY` if set. Check with `[bool][Environment]::GetEnvironmentVariable("GEMINI_API_KEY")` (never print the value).

## Calling the CLIs

6. **Gemini headless exits 55 in an untrusted folder.** A fresh temp dir is untrusted. Pass `--skip-trust` (or set `GEMINI_CLI_TRUST_WORKSPACE=true`). Without it the approval mode is also overridden to default.
7. **`--ignore-user-config` changes Codex's effort.** The user's `model_reasoning_effort = "xhigh"` was ignored and the banner said "reasoning effort: none". Set effort explicitly with `-c model_reasoning_effort=high`.
8. **Codex effort value needs no quotes.** `-c key=value` falls back to a literal string if TOML parsing fails, and quotes get mangled by the `.cmd` shim on Windows.
9. **Pass the prompt on stdin, not as an argument.** Long prompts and non-ASCII text break command-line quoting. Use `-` for Codex and `-p "<short instruction>"` for Gemini.
10. **Codex writes the answer to `-o FILE`; stdout is a log.** Read the file. The "tokens used" line is in the log.
11. **Each call is stateless.** Resend the transcript. Even a one-word reply cost about 7.6k tokens on Codex (system and tool overhead), so many small calls are wasteful.
12. **Latency.** A call takes seconds to minutes and starts a process. A 16-game judge tournament on ChatGPT took about 5.5 minutes. Budget wall-clock time, not only money.
13. **Run in an empty temp dir with a read-only sandbox.** Prompts contain scraped text; the agent must have nothing to read or change.

## Budget and honesty

14. **A subscription call costs 0, so `--budget` stops binding.** This departs from a "spending limit must be real" rule. Log it as a deviation and use the plan's own limit.
15. **Cheap models fail as planners.** Haiku as planner returned malformed JSON ("Expecting ',' delimiter"). Use Sonnet or higher for the plan; Haiku is fine as an executor.
16. **More audit loops are not always better.** With a strict independent auditor, three loops ended at score 0.55 and the two-loop run at 0.76. When the evidence set cannot meet the auditor's bar, add evidence, not loops.
17. **Feedback can raise the bar.** Passing the audit findings back as feedback made the auditor ask for more (cited sample sizes, numeric seeds) than the sources could supply.

## Windows and tooling

18. **Console code page.** Printing non-ASCII text raised `UnicodeEncodeError: 'cp950' codec can't encode character`. Set `PYTHONIOENCODING=utf-8` or reconfigure stdout.
19. **PowerShell 5.1 marks stderr as an error.** `git clone` printing "Cloning into..." to stderr showed as `NativeCommandError` and exit 255 even though it worked. Check the result, not the first red text.
20. **`shutil.which` is needed for npm shims.** `codex` and `gemini` are `.cmd` files on Windows.
21. **Non-zero exit does not mean a crash.** A research run that ends NEEDS_REVIEW exits 1, and the harness reports the task as failed. Read the log's final status.
22. **Background servers can be reaped.** A dashboard started in the background was stopped when the machine ran low on memory. Restart it only when memory is free.
23. **Keep venvs and git clones off Google Drive.** Clone to a local disk and write to the Drive once at the end.
24. **A first `uv run` downloads about 150 MB** (claude-agent-sdk). "Connection refused" in the browser during that time is not a bug.
