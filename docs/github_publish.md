# Publish on GitHub

This is a **prepared local repository**, not an online publication. Before making it public, review [PUBLIC_RELEASE_NOTES.md](../PUBLIC_RELEASE_NOTES.md) (including the GPU UUID and workspace paths inside the original raw evidence ZIP), choose the intended license and confirm that all artifacts may be shared.

## Browser method (on Mac/PC)

1. Sign in to GitHub and open https://github.com/new.
2. Repository owner: your personal account; name: `vllm-workload-adaptive-scheduling`. Choose **Public** only after privacy and license review. Create an **empty repository** (do not auto-add README, license, or .gitignore).
3. Extract the supplied ZIP. In the new repo, choose **uploading an existing file** / **Add file → Upload files**, and drag the *contents* of the extracted `vllm-workload-adaptive-scheduling` folder (including subfolders) into the upload area. On macOS, hidden files such as `.gitignore` can be revealed in Finder with Cmd+Shift+Period.
4. Commit `Add independent vLLM scheduling research and archived pilot evidence` to `main` and open the repo URL in a signed-out/incognito browser to verify it is truly public.

## Terminal method (on Mac/PC)

```bash
cd ~/Downloads/vllm-workload-adaptive-scheduling
git init -b main
git add .
git commit -m "Add independent vLLM scheduling research and archived pilot evidence"
# First create an empty public repository at https://github.com/new.
git remote add origin https://github.com/Afreen-Shaik446/vllm-workload-adaptive-scheduling.git
git push -u origin main
```

GitHub may prompt you to sign in using your configured authentication method. A GitHub personal access token (not an account password) is needed if using HTTPS basic credentials without a credential manager.

## After publication

Run `python -m pytest -q tests` and `python tools/verify_pilot.py --out recompute-output` on a fresh clone. Check the results and add the repository URL to your GitHub profile README. Do not present a GitHub code repository as a peer-reviewed paper.
