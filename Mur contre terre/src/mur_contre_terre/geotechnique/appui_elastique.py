"""Encastrement élastique au pied — modèle de Winkler.

kθ = ks·B³/12 par mètre de mur (§4 du cahier des charges), avec le
contrôle de compression intégrale de la semelle : le modèle n'est valable
que si l'excentricité de l'effort normal en fondation reste dans le noyau
central (e ≤ B/6).
"""

from __future__ import annotations


def rigidite_rotation(ks: float, largeur_semelle: float) -> float:
    """kθ [N·m/rad, par mètre de mur] — modèle de Winkler, kθ = ks·B³/12."""
    if ks <= 0:
        raise ValueError(f"ks doit être strictement positif (reçu {ks})")
    if largeur_semelle <= 0:
        raise ValueError(f"largeur_semelle doit être strictement positive (reçu {largeur_semelle})")
    return ks * largeur_semelle**3 / 12.0


def semelle_entierement_comprimee(n: float, moment: float, largeur_semelle: float) -> bool:
    """Vrai si l'excentricité e = |M|/N reste dans le noyau central (e ≤ B/6).

    ``n`` est l'effort normal transmis à la semelle [N], positif en
    compression ; ``moment`` [N·m] est le moment en fondation.
    """
    if largeur_semelle <= 0:
        raise ValueError(f"largeur_semelle doit être strictement positive (reçu {largeur_semelle})")
    if n <= 0:
        return False
    excentricite = abs(moment) / n
    return excentricite <= largeur_semelle / 6.0
