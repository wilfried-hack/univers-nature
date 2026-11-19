// Le menu mobile, les accordéons et les alertes sont gérés par Bootstrap (bootstrap.bundle.min.js).
(function () {
  // Ombre de l'en-tête au défilement (repris du thème d'origine)
  var entete = document.querySelector('.un-entete');
  if (entete) {
    var maj = function () { entete.classList.toggle('is-scrolled', window.scrollY > 8); };
    window.addEventListener('scroll', maj, { passive: true });
    maj();
  }

  // Page commande : affiche les frais de la zone choisie et le total.
  var zone = document.getElementById('id_zone');
  var recap = document.querySelector('[data-sous-total]');
  if (zone && recap) {
    var sousTotal = parseInt(recap.dataset.sousTotal, 10) || 0;
    var fraisEl = document.querySelector('[data-frais]');
    var totalEl = document.querySelector('[data-total]');
    var donnees = document.getElementById('frais-zones');
    var fraisParZone = donnees ? JSON.parse(donnees.textContent) : {};
    var format = function (n) { return n.toLocaleString('fr-FR').replace(/\s/g, ' ') + ' FCFA'; };
    var majTotal = function () {
      var frais = parseInt(fraisParZone[zone.value], 10);
      if (isNaN(frais)) { fraisEl.textContent = 'Selon la zone'; totalEl.textContent = format(sousTotal); return; }
      fraisEl.textContent = format(frais);
      totalEl.textContent = format(sousTotal + frais);
    };
    zone.addEventListener('change', majTotal);
    majTotal();
  }
})();
