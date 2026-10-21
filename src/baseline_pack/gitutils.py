"""Push to GitHub from Colab without printing the token."""
import subprocess
from google.colab import userdata


def git_push(message):
    token = userdata.get("GITHUB_TOKEN")
    origin = subprocess.run(["git", "remote", "get-url", "origin"],
                            capture_output=True, text=True).stdout.strip()
    user = origin.split("github.com/")[1].split("/")[0]
    url = origin.replace("https://", f"https://{user}:{token}@")
    for cmd in (["git", "add", "-A"], ["git", "commit", "-m", message], ["git", "push", url, "HEAD:main"]):
        r = subprocess.run(cmd, capture_output=True, text=True)
        print(" ".join(cmd[:2]), "→", (r.stdout + r.stderr).replace(token, "***").strip()[:400])
