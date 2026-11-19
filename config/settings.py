"""
Réglages du projet Univers Nature & Bien-être (Django 6.1).

En production (PythonAnywhere), créer un fichier .env à côté de manage.py
(modèle : .env.exemple) avec DJANGO_SECRET_KEY, DJANGO_DEBUG=0, DJANGO_ALLOWED_HOSTS…
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def _charger_env(fichier):
    """Lit un fichier .env simple (CLE=valeur par ligne). Les variables déjà définies sont prioritaires."""
    if not fichier.exists():
        return
    for ligne in fichier.read_text(encoding='utf-8').splitlines():
        ligne = ligne.strip()
        if ligne and not ligne.startswith('#') and '=' in ligne:
            cle, valeur = ligne.split('=', 1)
            os.environ.setdefault(cle.strip(), valeur.strip().strip('"').strip("'"))


_charger_env(BASE_DIR / '.env')


# ---------- Sécurité ----------
CLE_DEVELOPPEMENT = 'django-insecure-mi9g)szwie0yl9^$**suza!nvnyw@_n#w@-w&^!@vx4-&zx5$3'
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', CLE_DEVELOPPEMENT)  # la clé par défaut ne sert qu'en local
DEBUG = os.environ.get('DJANGO_DEBUG', '1') == '1'
ALLOWED_HOSTS = [h.strip() for h in os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if h.strip()]
CSRF_TRUSTED_ORIGINS = [f'https://{h}' for h in ALLOWED_HOSTS if h not in ('localhost', '127.0.0.1')]

if not DEBUG:
    if SECRET_KEY == CLE_DEVELOPPEMENT or len(SECRET_KEY) < 40:
        raise ImproperlyConfigured('En production, définissez une vraie DJANGO_SECRET_KEY dans le fichier .env.')
    # PythonAnywhere sert le site en HTTPS via un serveur intermédiaire : il le signale par cet en-tête.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 3600
    SECURE_CONTENT_TYPE_NOSNIFF = True


# ---------- Applications ----------
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    # Applications du projet
    'pages',
    'catalogue',
    'panier',
    'commandes',
    'comptes',
    'gestion',   # espace administrateur de la boutique (/gestion/)
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'pages.context_processors.boutique',
                'panier.context_processors.panier',
                'gestion.context_processors.compteurs',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# ---------- Base de données ----------
# SQLite pour le développement ; PostgreSQL conseillé en production.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        # DJANGO_DB permet d'utiliser une autre base (ex. une copie pour des essais)
        'NAME': os.environ.get('DJANGO_DB', BASE_DIR / 'db.sqlite3'),
    }
}


# ---------- Mots de passe ----------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LOGIN_URL = 'comptes:connexion'
LOGIN_REDIRECT_URL = 'comptes:espace'
LOGOUT_REDIRECT_URL = 'pages:accueil'


# ---------- Langue et fuseau horaire ----------
LANGUAGE_CODE = 'fr'
TIME_ZONE = 'Africa/Douala'
USE_I18N = True
USE_TZ = True


# ---------- Fichiers statiques (CSS, JS, images du thème) ----------
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# ---------- Fichiers téléversés (photos des produits) ----------
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ---------- Captures d'écran des paiements Mobile Money ----------
# Dossier PRIVÉ (pas d'adresse publique) : seule l'équipe les ouvre depuis /gestion/.
PREUVES_ROOT = Path(os.environ.get('DJANGO_PREUVES', BASE_DIR / 'prive' / 'preuves'))
TAILLE_MAX_CAPTURE = 5 * 1024 * 1024  # 5 Mo

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Les messages Django utilisent les couleurs d'alerte de Bootstrap (alert-danger, alert-success…)
from django.contrib.messages import constants as messages  # noqa: E402

MESSAGE_TAGS = {messages.ERROR: 'danger', messages.DEBUG: 'secondary'}


# ---------- E-mails ----------
# En local : affichés dans la console. En ligne : envoi SMTP (réglages EMAIL_* facultatifs dans .env,
# nécessaires seulement le jour où le site enverra des e-mails).
if DEBUG:
    MAILERS = {'default': {'BACKEND': 'django.core.mail.backends.console.EmailBackend'}}
else:
    MAILERS = {
        'default': {
            'BACKEND': 'django.core.mail.backends.smtp.EmailBackend',
            'OPTIONS': {
                'host': os.environ.get('EMAIL_HOST', 'localhost'),
                'port': int(os.environ.get('EMAIL_PORT', '587')),
                'username': os.environ.get('EMAIL_USER', ''),
                'password': os.environ.get('EMAIL_PASSWORD', ''),
                'use_tls': os.environ.get('EMAIL_USE_TLS', '1') == '1',
            },
        },
    }


# ---------- Informations de la boutique ----------
# À remplacer par les vraies coordonnées avant la mise en ligne.
BOUTIQUE = {
    'NOM': 'Univers Nature & Bien-être',
    'SLOGAN': "L'authenticité au naturel, le bien-être au quotidien",
    'TELEPHONE': '+237 6 00 00 00 00',
    'TELEPHONE_LIEN': '+237600000000',
    'WHATSAPP': '237600000000',          # numéro WhatsApp Business, sans « + » ni espaces
    'MOBILE_MONEY_NUMERO': '+237 6 00 00 00 00',
    'MOBILE_MONEY_NOM': 'Univers Nature & Bien-être',
    'EMAIL': 'contact@exemple.com',
    'ADRESSE': 'Douala, Cameroun',
    'HORAIRES_WHATSAPP': 'Du lundi au samedi, de 8 h à 19 h',
    'DEVISE': 'FCFA',
}
