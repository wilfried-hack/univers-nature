# Univers Nature & Bien-être — site Django

« L'authenticité au naturel, le bien-être au quotidien »

Boutique en ligne : **les commandes se passent uniquement sur le site**, **sans paiement en ligne** : le client paie **à la livraison** ou par **Mobile Money** avant l'expédition, puis envoie la référence ou une capture d'écran du transfert **sur le site**.

## Démarrer en local

Dans le terminal de VS Code, depuis le dossier `bien etre` :

```powershell
.\.venv\Scripts\Activate.ps1          # active le venv : (.venv) s'affiche
python manage.py migrate              # crée / met à jour la base de données
python manage.py charger_demo         # charge les 6 produits et 3 zones d'exemple
python manage.py createsuperuser      # crée votre compte administrateur
python manage.py runserver            # lance le site
```

Puis ouvrir :
- le site : http://127.0.0.1:8000/
- **l'espace de gestion** (administrateur) : http://127.0.0.1:8000/gestion/

Seuls les comptes « équipe » (`is_staff`) accèdent à `/gestion/`. Le compte créé avec `createsuperuser` en fait partie. Pour créer un autre compte administrateur : `python manage.py createsuperuser`.

Lancer les tests : `python manage.py test`

Sur un autre ordinateur : `python -m venv .venv`, activer, puis `pip install -r requirements.txt`.

## Structure du projet

```
bien etre/
├── manage.py               commandes Django (runserver, migrate, test…)
├── requirements.txt        paquets Python à installer
├── .venv/                  environnement virtuel (ne pas modifier)
├── config/                 réglages du projet
│   ├── settings.py         réglages + coordonnées de la boutique (BOUTIQUE = {...})
│   └── urls.py             adresses principales du site
├── pages/                  accueil, à propos, contact, CGV, confidentialité
├── catalogue/              catégories, produits, recherche, fiche produit
│   ├── templatetags/boutique.py   filtres {{ prix|fcfa }}, {% icone %}, {% lien_whatsapp %}
│   └── management/commands/charger_demo.py   données d'exemple
├── panier/                 panier gardé dans la session (sans compte)
├── commandes/              zones de livraison, commandes, modes de règlement, statistiques
├── comptes/                inscription, connexion, espace client
├── gestion/                espace administrateur (/gestion/) : tableau de bord, commandes,
│                           produits, catégories, zones, clients, statistiques
├── templates/              pages HTML
│   ├── base.html           site public : menu, pied de page, bouton WhatsApp
│   ├── gestion/base.html   espace de gestion : barre latérale
│   └── includes/           morceaux réutilisés (carte produit, contact, champ de formulaire…)
├── static/
│   ├── vendor/             Bootstrap 5.3.8 et Bootstrap Icons 1.13.1, installés en local
│   ├── css/site.css        thème du site public (couleurs nature par-dessus Bootstrap)
│   ├── css/gestion.css     thème de l'espace de gestion
│   └── js/, img/           scripts et logo
└── media/                  photos de produits envoyées depuis la gestion
prive/preuves/              captures d'écran des paiements : dossier PRIVÉ, sans adresse publique,
                            ouvert seulement depuis /gestion/ (à sauvegarder avec la base de données)
```

## Bootstrap (installé en local)

Bootstrap n'est pas chargé depuis Internet : ses fichiers sont copiés dans `static/vendor/`, le site fonctionne donc hors ligne.
Les couleurs de Bootstrap sont redéfinies au début de `static/css/site.css` (`--bs-primary`, etc.).
Les formulaires reçoivent automatiquement les classes Bootstrap grâce à `pages/bootstrap.py` (`BootstrapFormMixin`).

Pour mettre Bootstrap à jour plus tard (Node.js requis), dans un dossier temporaire :
```powershell
npm install bootstrap@5.3.8 bootstrap-icons@1.13.1
```
puis recopier `node_modules/bootstrap/dist/css/bootstrap.min.css`, `dist/js/bootstrap.bundle.min.js`
et `node_modules/bootstrap-icons/font/` (fichier CSS + dossier `fonts/`) dans `static/vendor/`.

Chaque application contient le même schéma :

| Fichier | Rôle |
|---|---|
| `models.py` | les données (tables de la base) |
| `views.py` | ce que fait chaque page |
| `urls.py` | les adresses des pages |
| `forms.py` | les formulaires |

## Avant la mise en ligne

1. **Coordonnées** : dans `config/settings.py`, remplacer le bloc `BOUTIQUE` (numéro WhatsApp, numéro Mobile Money, e-mail, adresse).
2. **Produits** : dans /gestion/produits/, remplacer les textes d'exemple (composition, précautions, prix, photos).
3. **Zones de livraison** : dans /gestion/zones/, ajuster les zones, les frais et l'option « paiement à la livraison accepté ».
4. **Logo** : remplacer `static/img/logo.svg`.
5. **Photo d'accueil** (facultatif) : placer une photo dans `static/img/hero.jpg`.
6. **CGV et confidentialité** : compléter et faire relire `templates/pages/cgv.html` et `confidentialite.html`.
7. **Production** : définir `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0` et `DJANGO_ALLOWED_HOSTS`, utiliser PostgreSQL, puis lancer `python manage.py collectstatic`.

## Traiter une commande (espace de gestion)

1. La commande arrive dans **Gestion → Commandes** (pastille orange dans le menu), statut « Reçue », paiement « En attente ».
2. Ouvrir la commande, puis **Écrire au client** (WhatsApp) ou **Appeler** pour la confirmer.
3. Mobile Money : le client envoie sur le site la référence du transfert et/ou une capture d'écran (carte « Preuves de paiement à vérifier » du tableau de bord, badge « Preuve à vérifier » dans les commandes). Vérifier que l'argent est bien arrivé sur le compte — une capture peut être falsifiée — puis passer le paiement à « Payée ».
4. Faire avancer le statut : confirmée, en préparation, expédiée, livrée. Avec le paiement à la livraison, « Livrée » passe automatiquement la commande en « Payée ».
5. « Annulée » remet automatiquement les produits en stock. Une commande annulée ne peut plus être modifiée.
6. Dans les tableaux, le bouton **Mettre à jour** change le statut sans ouvrir la commande.
