# Publish standalone JSON Translate Action to GitHub

```powershell
cd packages\json-translate-action
git init
git add action.yml README.md LICENSE assets scripts
git commit -m "feat: Routara JSON Translate Action v1.0.0"
gh repo create 36412749-collab/json-translate-action --public --source=. --remote=origin --push
git tag v1.0.0
git push origin v1.0.0
```

Then: GitHub Release v1.0.0 → **Publish to Marketplace** (Developer tools, Localization).
