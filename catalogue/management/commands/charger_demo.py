"""
Charge les catégories, les 6 produits du cahier des charges et 3 zones de livraison d'exemple.
Usage : python manage.py charger_demo
Les textes, prix et zones sont des EXEMPLES à remplacer par les vraies informations dans l'administration.
"""
from django.core.management.base import BaseCommand

from catalogue.models import Categorie, Produit
from commandes.models import ZoneLivraison

CATEGORIES = [
    ('soin-bien-etre', 'Soin & bien-être', 'Baumes pour les lèvres et le massage, préparés avec soin.', 1),
    ('entretien-domestique', 'Entretien domestique', 'Détergent, savon, vinaigre blanc et eau de Javel pour la maison.', 2),
]

PRECAUTION_GENERALE = 'Tenir hors de portée des enfants. Conserver à l’abri de la chaleur et de la lumière.'

PRODUITS = [
    dict(categorie='soin-bien-etre', slug='baume-a-levres', nom='Baume à lèvres', prix=1500, contenance='Stick de 5 g',
         description_courte='Nourrit et protège les lèvres sèches au quotidien.',
         description='Un baume onctueux qui nourrit et protège les lèvres. Texte d’exemple à remplacer.',
         composition='Exemple à remplacer par la composition réelle : beurre de karité, cire d’abeille, huile de coco.',
         utilisation='Appliquer sur les lèvres propres, aussi souvent que nécessaire.',
         precautions='Usage externe. Ne pas utiliser en cas d’allergie à l’un des ingrédients. ' + PRECAUTION_GENERALE,
         fait_main=True, naturel=True, populaire=True, stock=40),
    dict(categorie='soin-bien-etre', slug='baume-de-massage', nom='Baume de massage', prix=3500, prix_promo=3000,
         contenance='Pot de 100 g',
         description_courte='Un baume fondant pour des massages relaxants.',
         description='Un baume qui fond au contact de la peau, pour le massage du corps. Texte d’exemple à remplacer.',
         composition='Exemple à remplacer par la composition réelle.',
         utilisation='Prélever une noisette, chauffer entre les mains et masser jusqu’à pénétration.',
         precautions='Usage externe. Éviter le contact avec les yeux. Faire un essai sur une petite zone de peau avant la première utilisation. ' + PRECAUTION_GENERALE,
         fait_main=True, naturel=True, populaire=True, stock=25),
    dict(categorie='entretien-domestique', slug='detergent-liquide', nom='Détergent liquide', prix=2000, contenance='Bouteille de 1 L',
         description_courte='Nettoie efficacement le linge et les surfaces.',
         description='Détergent polyvalent pour la maison. Texte d’exemple à remplacer.',
         composition='Exemple à remplacer par la composition réelle et les mentions réglementaires de l’étiquette.',
         utilisation='Diluer selon l’usage : voir l’étiquette du produit.',
         precautions='Ne pas avaler. Éviter le contact avec les yeux ; en cas de contact, rincer abondamment à l’eau. ' + PRECAUTION_GENERALE,
         populaire=True, stock=30),
    dict(categorie='entretien-domestique', slug='savon-en-morceaux', nom='Savon en morceaux', prix=500, contenance='Morceau de 200 g',
         description_courte='Un savon solide pour le linge et la maison.',
         description='Savon solide traditionnel. Texte d’exemple à remplacer.',
         composition='Exemple à remplacer par la composition réelle.',
         utilisation='Frotter directement sur le linge mouillé ou dissoudre dans l’eau.',
         precautions='Éviter le contact avec les yeux. ' + PRECAUTION_GENERALE,
         fait_main=True, nouveaute=True, stock=100),
    dict(categorie='entretien-domestique', slug='vinaigre-blanc', nom='Vinaigre blanc', prix=1000, contenance='Bouteille de 1 L',
         description_courte='Détartre, dégraisse et désodorise naturellement.',
         description='Vinaigre blanc ménager pour le nettoyage. Texte d’exemple à remplacer.',
         composition='Exemple à remplacer : vinaigre d’alcool, degré d’acidité à préciser.',
         utilisation='Pur pour détartrer, dilué dans l’eau pour nettoyer les surfaces et les vitres.',
         precautions='Ne pas mélanger avec l’eau de Javel : dégagement de gaz toxique. Ne pas utiliser sur le marbre ni la pierre naturelle. ' + PRECAUTION_GENERALE,
         naturel=True, nouveaute=True, stock=50),
    dict(categorie='entretien-domestique', slug='eau-de-javel', nom='Eau de Javel', prix=800, contenance='Bouteille de 1 L',
         description_courte='Désinfecte et blanchit les surfaces et le linge.',
         description='Eau de Javel pour la désinfection de la maison. Texte d’exemple à remplacer.',
         composition='Exemple à remplacer : hypochlorite de sodium, concentration en chlore actif à préciser.',
         utilisation='Toujours diluer dans l’eau froide selon les doses indiquées sur l’étiquette.',
         precautions='DANGER. Ne jamais mélanger avec d’autres produits (vinaigre, acides, ammoniaque) : dégagement de gaz toxique. '
                     'Provoque des irritations de la peau et des yeux. Utiliser dans un endroit aéré. '
                     'En cas d’ingestion, ne pas faire vomir et consulter immédiatement un médecin. ' + PRECAUTION_GENERALE,
         stock=4),
]

ZONES = [
    ('Douala – centre-ville', 1000, '24 h', True, 1),
    ('Douala – périphérie', 1500, '24 à 48 h', True, 2),
    ('Autres villes (expédition)', 3000, '2 à 4 jours', False, 3),
]


class Command(BaseCommand):
    help = 'Charge des données d’exemple (catégories, 6 produits, zones de livraison).'

    def handle(self, *args, **options):
        categories = {}
        for slug, nom, description, ordre in CATEGORIES:
            categories[slug], _ = Categorie.objects.update_or_create(
                slug=slug, defaults={'nom': nom, 'description': description, 'ordre': ordre})

        for donnees in PRODUITS:
            donnees = dict(donnees)
            categorie = categories[donnees.pop('categorie')]
            slug = donnees.pop('slug')
            Produit.objects.update_or_create(slug=slug, defaults={**donnees, 'categorie': categorie,
                                                                  'fabricant': 'Univers Nature & Bien-être (à compléter)'})

        for nom, frais, delai, paiement_livraison, ordre in ZONES:
            ZoneLivraison.objects.update_or_create(nom=nom, defaults={
                'frais': frais, 'delai': delai, 'paiement_livraison': paiement_livraison, 'ordre': ordre})

        self.stdout.write(self.style.SUCCESS(
            f'{len(CATEGORIES)} catégories, {len(PRODUITS)} produits et {len(ZONES)} zones de livraison chargés.'))
