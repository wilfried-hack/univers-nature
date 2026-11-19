# Mettre le site en ligne sur PythonAnywhere

Dans ce guide, remplacez **`votrenom`** par votre nom d'utilisateur PythonAnywhere.
Le site sera à l'adresse **https://votrenom.pythonanywhere.com**.

Durée : environ 30 minutes. Python utilisé : **3.13** (Django 6.1 demande Python 3.12 ou plus récent).

---

## 1. Créer le compte

1. Aller sur https://www.pythonanywhere.com → **Pricing & signup** → compte gratuit (*Beginner*).
2. Choisir le nom d'utilisateur avec soin : il apparaît dans l'adresse du site.
3. Confirmer l'adresse e-mail.

## 2. Récupérer le code depuis GitHub

Le code est dans un dépôt GitHub **public** : https://github.com/wilfried-hack/univers-nature

Sur PythonAnywhere : onglet **Consoles** → **Bash**, puis :

```bash
cd ~
git clone https://github.com/wilfried-hack/univers-nature.git
```

Aucun mot de passe n'est demandé, puisque le dépôt est public.

> Le dépôt public ne contient **aucune** donnée sensible : la clé secrète, la base de données, les photos et les
> captures de paiement restent uniquement sur le serveur (fichier `.env`, `db.sqlite3`, `media/`, `prive/`).
>
> Si le dépôt devient privé plus tard : créer sur GitHub un *Fine-grained token* en lecture seule
> (Settings → Developer settings → Personal access tokens), puis le coller comme mot de passe lors du `git pull`.

## 3. Installer (console Bash)

```bash
cd ~/univers-nature

# Environnement virtuel Python 3.13 + paquets
mkvirtualenv --python=/usr/bin/python3.13 univers-nature
pip install -r requirements.txt
```

Le nom `(univers-nature)` s'affiche alors au début de la ligne. Dans une nouvelle console, le réactiver avec :
`workon univers-nature`

## 4. Créer le fichier .env (réglages secrets)

```bash
cp .env.exemple .env
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copier la clé affichée, puis ouvrir le fichier :

```bash
nano .env
```

- `DJANGO_SECRET_KEY=` → coller la clé ;
- `DJANGO_DEBUG=0` ;
- `DJANGO_ALLOWED_HOSTS=votrenom.pythonanywhere.com`.

Enregistrer : **Ctrl + O**, **Entrée**, puis quitter : **Ctrl + X**.

> Le site refuse de démarrer en production si la clé secrète n'a pas été changée : c'est voulu.

## 5. Préparer la base de données et les fichiers du thème

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser      # votre compte administrateur
python manage.py charger_demo         # facultatif : les 6 produits et 3 zones d'exemple
```

## 6. Créer l'application web

Onglet **Web** → **Add a new web app** → **Next** → **Manual configuration** (pas « Django ») → **Python 3.13** → **Next**.

Puis, sur la page de l'application web :

| Rubrique | Valeur |
|---|---|
| **Source code** | `/home/votrenom/univers-nature` |
| **Working directory** | `/home/votrenom/univers-nature` |
| **Virtualenv** | `/home/votrenom/.virtualenvs/univers-nature` |

**Static files** (deux lignes à ajouter) :

| URL | Directory |
|---|---|
| `/static/` | `/home/votrenom/univers-nature/staticfiles` |
| `/media/` | `/home/votrenom/univers-nature/media` |

> Ne **pas** ajouter le dossier `prive/` : il contient les captures de paiement et ne doit pas avoir d'adresse publique.

**Security** : activer **Force HTTPS**.

## 7. Fichier WSGI

Toujours dans l'onglet **Web**, cliquer sur le lien **WSGI configuration file**
(`/var/www/votrenom_pythonanywhere_com_wsgi.py`), **tout effacer** et coller :

```python
import os
import sys

chemin = '/home/votrenom/univers-nature'
if chemin not in sys.path:
    sys.path.insert(0, chemin)

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

Enregistrer (**Save**), revenir à l'onglet **Web** et cliquer sur le bouton vert **Reload**.

## 8. Vérifier

1. Ouvrir **https://votrenom.pythonanywhere.com** : la page d'accueil doit s'afficher avec le thème vert.
2. Se connecter sur `/compte/connexion/` avec le compte administrateur → arrivée sur `/gestion/`.
3. Passer une commande d'essai (paiement à la livraison), la retrouver dans la gestion, puis l'annuler.
4. Dans Gestion → Produits, remplacer les textes d'exemple et ajouter les photos.

**En cas de problème** : onglet **Web** → **Error log** (la dernière erreur est en bas du fichier).

| Symptôme | Cause habituelle |
|---|---|
| « Something went wrong » | Lire l'*Error log* ; souvent un chemin mal recopié à l'étape 6 ou 7 |
| « DisallowedHost » / Bad Request (400) | `DJANGO_ALLOWED_HOSTS` mal écrit dans `.env` |
| « ImproperlyConfigured … SECRET_KEY » | Clé secrète non remplacée dans `.env` |
| Page sans couleurs ni mise en forme | `collectstatic` oublié, ou ligne `/static/` absente à l'étape 6 |
| Photos de produits absentes | Ligne `/media/` absente à l'étape 6 |
| Erreur CSRF en envoyant un formulaire | Adresse dans `DJANGO_ALLOWED_HOSTS` différente de celle du navigateur |

Après chaque modification de `.env` ou du code : bouton **Reload** dans l'onglet Web.

---

## 9. Mettre le site à jour après des modifications

1. **Sur l'ordinateur** (terminal de VS Code, dans le dossier du projet) : enregistrer et envoyer les modifications.

```powershell
git add -A
git commit -m "Décrire la modification"
git push
```

2. **Sur PythonAnywhere** (console Bash) :

```bash
cd ~/univers-nature
git pull
workon univers-nature
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

3. Onglet **Web** → **Reload**.

`git pull` ne touche jamais à `db.sqlite3` (les commandes), `media/` (les photos), `prive/` (les preuves de paiement)
ni à `.env` : ces fichiers ne sont pas dans GitHub (voir `.gitignore`).

> Ne jamais ajouter `.env`, `db.sqlite3`, `media/` ou `prive/` dans GitHub : ils contiennent la clé secrète
> et les données des clients.

## 10. Sauvegardes (à faire régulièrement)

Dans la console Bash :

```bash
cd ~/univers-nature
zip -r ~/sauvegarde-$(date +%F).zip db.sqlite3 media prive
```

Puis onglet **Files** → télécharger le fichier `sauvegarde-AAAA-MM-JJ.zip` sur l'ordinateur.
Il contient les commandes, les comptes, les photos et les captures de paiement.

## 11. À savoir sur le compte gratuit

- Le site gratuit doit être **prolongé tous les 3 mois** : onglet **Web** → bouton **Run until 3 months from today** (PythonAnywhere envoie un rappel par e-mail).
- L'adresse est obligatoirement `votrenom.pythonanywhere.com` ; un nom de domaine personnalisé (ex. `universnature.cm`) demande un compte payant.
- L'espace disque est limité : penser à des photos de produits de taille raisonnable (moins de 500 Ko chacune).
- Vérifier les conditions actuelles sur la page *Pricing* de PythonAnywhere avant de choisir une offre.
