---
name: release
description: Publier une nouvelle version de RL Stats (numero de version, commit, tag, push qui declenche la CI GitHub). A utiliser quand l'utilisateur demande une release, une nouvelle version, ou "publie".
---

# Publier une version de RL Stats

Argument optionnel : le numero de version (`1.6.4`) ou le type (`patch`, `minor`). Par defaut : patch
pour une correction, minor pour une nouvelle fonction visible.

## 1. Verifier

- `git status` : rien d'inattendu (pas de `stats.json`, `matches.json`, `.log`, `dist/`).
- `.venv\Scripts\python.exe -m py_compile rl_stats.pyw designs.py ui_windows.py popup_menu.py history.py i18n.py obs_server.py`
- Si une fonction visible a change : README a jour en anglais **et** dans la section "En francais".

## 2. Version

Changer uniquement `APP_VERSION = "X.Y.Z"` dans `rl_stats.pyw`. Le `.spec`, le MSIX et la CI la
lisent la. Le dernier tag : `git describe --tags --abbrev=0`.

## 3. Commit

Message en francais sans accents :

```
vX.Y.Z : description courte

Paragraphe facultatif qui explique le changement pour l'utilisateur.
```

Les notes de la release GitHub sont generees depuis les commits : la premiere ligne doit parler a
un joueur, pas a un developpeur.

Ecrire le message dans un fichier du scratchpad et committer avec `git commit -F <fichier>` : sous
PowerShell 5.1, un message passe avec `-m` et qui contient des guillemets est coupe en plusieurs
arguments et le commit echoue. Verifier ensuite avec `git log -1` que le commit existe et que
`APP_VERSION` y est bien la nouvelle version.

## 4. Confirmer, puis publier

**Demander confirmation avant de pousser** : le tag publie la release pour tous les utilisateurs
(mise a jour automatique dans l'appli, winget).

Une commande a la fois, en s'arretant a la premiere erreur (jamais de `;` qui enchaine quoi qu'il
arrive) :

```
git push origin main
git tag vX.Y.Z
git push origin vX.Y.Z
```

La CI echoue si le tag ne correspond pas a `APP_VERSION` (rien n'est publie). Pour corriger un tag
pousse sur le mauvais commit : `git push origin --delete vX.Y.Z`, `git tag -d vX.Y.Z`, puis retagger.

## 5. Apres

- Suivre la CI. `gh` n'est pas connecte sur ce PC : passer par l'API publique, par exemple
  `(Invoke-RestMethod "https://api.github.com/repos/benguedj/RL_Stats/actions/runs?per_page=3").workflow_runs`
  (champs `head_branch`, `status`, `conclusion`, `id`). La CI dure quelques minutes.
- Verifier la release : `Invoke-RestMethod https://api.github.com/repos/benguedj/RL_Stats/releases/tags/vX.Y.Z`
  (`assets` doit contenir `RL Stats.zip` et `SHA256SUMS.txt`).
- Rappeler a l'utilisateur, s'il veut mettre a jour le Microsoft Store : telecharger l'artefact
  `rl-stats-msix` du run (onglet Actions sur GitHub, `https://github.com/benguedj/RL_Stats/actions/runs/<id>`)
  et le soumettre dans Partner Center.
