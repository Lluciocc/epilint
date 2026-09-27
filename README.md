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

`-v` affiche les lignes modifiées et les règles corrigées. Pour prévisualiser sans écrire : `epilint --diff -f -v fichier.c`.
