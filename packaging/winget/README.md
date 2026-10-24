# RL Stats sur winget

Identifiant : `benguedj.RLStats`. Une fois accepté, on installe avec :

```
winget install benguedj.RLStats
```

## Première soumission (une seule fois, à la main)

Les manifestes de la v1.5.0 sont dans `1.5.0/` (validés avec `winget validate --manifest packaging\winget\1.5.0`).

1. Forker https://github.com/microsoft/winget-pkgs sur ton compte.
2. Copier les 4 fichiers de `1.5.0/` dans `manifests/b/benguedj/RLStats/1.5.0/` de ton fork.
3. Ouvrir une pull request vers microsoft/winget-pkgs. Des vérifications automatiques tournent,
   puis un modérateur valide (en général quelques jours).

Variante en une commande, avec l'outil officiel de Microsoft (`winget install wingetcreate`) :

```
wingetcreate submit --token <jeton GitHub> packaging\winget\1.5.0
```

## Versions suivantes (automatique)

Le job `winget` de `.github/workflows/release.yml` propose chaque nouvelle release à winget.
Il s'active quand le secret de dépôt `WINGET_TOKEN` existe : un jeton GitHub "classic" avec le
droit `public_repo` (Settings > Developer settings > Personal access tokens), et le fork de
winget-pkgs ci-dessus sur ton compte.

## À savoir

- Le paquet est "portable" : winget dézippe `RL Stats.exe` dans son dossier et crée la commande
  `rlstats`. Les réglages restent dans `%APPDATA%\RL Stats`, comme avec le zip.
- La mise à jour intégrée à l'appli remplace l'exe sur place : elle marche aussi avec winget, mais
  `winget list` affichera l'ancienne version jusqu'au prochain `winget upgrade`.
