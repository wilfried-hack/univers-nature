"""Panier stocké dans la session du visiteur (pas besoin de compte pour remplir son panier)."""
from catalogue.models import Produit

CLE_SESSION = 'panier'


class Panier:
    def __init__(self, request):
        self.session = request.session
        self.donnees = self.session.get(CLE_SESSION, {})  # {"<id produit>": quantité}

    # ---------- Modification ----------
    def ajouter(self, produit, quantite=1):
        cle = str(produit.pk)
        nouvelle = self.donnees.get(cle, 0) + quantite
        self.donnees[cle] = max(1, min(nouvelle, produit.stock))
        self._sauver()

    def modifier(self, produit, quantite):
        cle = str(produit.pk)
        if quantite <= 0:
            self.donnees.pop(cle, None)
        else:
            self.donnees[cle] = min(quantite, produit.stock)
        self._sauver()

    def retirer(self, produit):
        self.donnees.pop(str(produit.pk), None)
        self._sauver()

    def vider(self):
        self.donnees = {}
        self._sauver()

    def _sauver(self):
        self.session[CLE_SESSION] = self.donnees
        self.session.modified = True

    # ---------- Lecture ----------
    def lignes(self):
        """Liste de dictionnaires {produit, quantite, prix, total}. Ignore les produits retirés du site."""
        produits = Produit.objects.visibles().filter(pk__in=self.donnees.keys())
        resultat = []
        for produit in produits:
            quantite = self.donnees[str(produit.pk)]
            resultat.append({
                'produit': produit,
                'quantite': quantite,
                'prix': produit.prix_actuel,
                'total': produit.prix_actuel * quantite,
            })
        return resultat

    def sous_total(self):
        return sum(ligne['total'] for ligne in self.lignes())

    def __len__(self):
        return sum(self.donnees.values())

