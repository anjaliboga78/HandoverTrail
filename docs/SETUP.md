# Setup on your laptop (Windows, Mac or Linux)

## 1. Install the tools (one time)
1. **Python 3.10 or newer** from python.org. On Windows, tick **"Add Python to PATH"** in the installer.
2. **VS Code** (optional but handy) from code.visualstudio.com.
3. **Git** from git-scm.com (needed later to put your code on GitHub).

Check in a terminal: `python --version` (on Mac/Linux you may need `python3 --version`).

## 2. Get the project
1. Download `handovertrail.zip` and **Extract** it (right-click > Extract All).
2. Open the extracted `handovertrail` folder in VS Code (File > Open Folder), then open a terminal (Terminal > New Terminal).
   Or open Command Prompt/PowerShell and `cd` into the folder.

## 3. Create an isolated environment and install the libraries
Windows (Command Prompt):
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
Windows PowerShell: if activation is blocked, run once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then `venv\Scripts\Activate.ps1`.

Mac/Linux:
```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
You should now see `(venv)` at the start of the terminal line.

## 4. Run the tests (about 5 seconds)
```
python -m unittest discover -s tests -v
```
Every line should say `ok`. If something fails, copy the error and ask for help.

## 5. Start the app
```
streamlit run app.py
```
Your browser opens at http://localhost:8501. If it does not, open that address yourself. Stop the app with Ctrl+C.

## 6. First minute inside the app
1. Left sidebar: you are **Riya (Lead)**. Page **1. Connect** > **Load the demo project**.
2. **2. Reconstruct and verify** > **Run extraction**.
3. **3. Review and approve** > **Approve all verified items...** > **Approve handover and share**.
4. Sidebar: switch to **Aman** (Intern) and look at **4. Handover**. Then **Karan** (Core), then back to Riya for **7. Audit log**.

## 7. Optional: use a real language model
1. Copy `.env.example` to a new file named `.env`.
2. Set `LLM_PROVIDER=anthropic` (or `openai` / `gemini`) and the matching `..._API_KEY=` line. Never commit `.env`.
3. Restart the app. On page 2 it now says which model is used. If the key is wrong or the service fails, the app tells you and falls back to the offline extractor for that source.
This path could not be tested without internet in the build environment, so test it once with your own key and tell us if anything needs fixing.

**Test the connection** (from the project folder, with `.env` filled in):
```
python -m core.llm            # sends one tiny request and prints OK or the exact error
python -m core.llm --models   # Gemini only: lists the model names your key can use (for GEMINI_MODEL)
```
Errors show the real HTTP status and the provider's own message, e.g. `404` = wrong `GEMINI_MODEL`, `400/401/403` = key problem, `429` = quota/rate limit, `500/503` = Google is busy (retried automatically). Your key is never printed or logged.

## 8. Put it on GitHub (the brief requires a repository)
```
git init
git add .
git commit -m "Round 2: working HandoverTrail MVP"
```
Create an empty repository on github.com, then run the two lines GitHub shows (`git remote add origin ...` and `git push -u origin main`). Make it public, or give the judges access. Commit often while you build: the commit history proves you worked inside the build window.

## 9. Put it online (judges need a link)
1. Push the code to GitHub (above).
2. Go to share.streamlit.io, sign in with GitHub, **New app**, choose your repository, main file `app.py`.
3. If you use an AI key, add it under **Advanced settings > Secrets** as `ANTHROPIC_API_KEY = "..."` and `LLM_PROVIDER = "anthropic"`. Never put keys in the repository.
4. The free host forgets the database when it restarts, so keep the **Load the demo project** button as your reset.

## 10. Make it safe for anyone to use (public link)
Locally the app uses one shared database. For a public link, turn on **public mode** so every visitor gets a private,
temporary workspace (deleted after 24 hours) and nobody can see or reset anyone else's data.
In Streamlit Cloud: **Advanced settings > Secrets**, add:
```
HT_PUBLIC = "1"
```
In public mode visitors use the free offline extractor, so strangers cannot spend your AI key. To allow the AI model for
visitors anyway (your own risk and cost), also set `HT_PUBLIC_LLM = "1"`. Uploads are limited to 2 MB per file.
Tell visitors to use only made-up or permitted data.

## Common problems
| Problem | Fix |
|---|---|
| `python` is not recognized | Reinstall Python and tick "Add Python to PATH", or use `py` instead of `python` on Windows |
| `streamlit` is not recognized | The environment is not active. Run the activate line again |
| Port 8501 busy | `streamlit run app.py --server.port 8502` |
| `pip install` fails | Check internet; try `python -m pip install --upgrade pip` first |
| Page looks unstyled | Hard refresh the browser (Ctrl+Shift+R) |
