# epilint

Formateur et vérificateur du coding style C d’Epitech.

## Installation en une ligne

Python 3.9 ou plus récent et un accès au dépôt GitHub sont nécessaires :

```bash
git clone https://github.com/Lluciocc/epilint.git && cd epilint && sudo bash install.sh
```

La commande installe `epilint` dans `/usr/local/bin`. Vérification :

```bash
epilint --help
```

Pour installer sans `sudo` dans `~/.local/bin` :

```bash
PREFIX="$HOME/.local" bash install.sh
```

Ajoute `~/.local/bin` à ton `PATH` si nécessaire.

## Utilisation

```bash
epilint --fix -f -v fichier.c
```

`-v` affiche les numéros des lignes avant/après, les caractères modifiés en couleur, et rend les espaces (`·`) et tabulations (`⇥`) visibles. Pour prévisualiser sans écrire : `epilint --diff -f -v fichier.c`. Les couleurs sont automatiques dans un terminal ; utilise `--color=always` pour les conserver dans une redirection ou `--color=never` pour les désactiver.
