# epilint

Formateur et vérificateur du coding style C d’Epitech.

## Installation en une ligne

Python 3.9 ou plus récent et une clé SSH GitHub autorisée sont nécessaires :

```bash
git clone git@github.com:Lluciocc/epilint.git && cd epilint && sudo bash install.sh
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
