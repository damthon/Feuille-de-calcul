"""Application des conditions d'appui au modèle éléments finis.

Pied (nœud 0) : translations toujours bloquées (w0 = u0 = 0 — la semelle ne
translate pas dans ce modèle). Rotation bloquée pour un encastrement
parfait ; élastique (ressort kθ ajouté à la rigidité globale) pour un
encastrement élastique. Tête (dernier nœud) : translation horizontale
bloquée si appuyée par la dalle, sinon libre ; la rotation en tête est
toujours libre.
"""

from __future__ import annotations

from mur_contre_terre.donnees.appuis import ConditionsAppui, TypeAppuiPied, TypeAppuiTete
from mur_contre_terre.donnees.geometrie import Geometrie
from mur_contre_terre.donnees.sol import Sol
from mur_contre_terre.geotechnique.appui_elastique import rigidite_rotation
from mur_contre_terre.mecanique.maillage import Maillage


def dofs_bloques(appuis: ConditionsAppui, maillage: Maillage) -> list[int]:
    """Degrés de liberté globaux à valeur imposée nulle."""
    noeud_pied, noeud_tete = 0, maillage.nb_noeuds - 1
    bloques = [3 * noeud_pied, 3 * noeud_pied + 1]  # w0, u0
    if appuis.pied is TypeAppuiPied.ENCASTREMENT:
        bloques.append(3 * noeud_pied + 2)  # θ0
    if appuis.tete is TypeAppuiTete.APPUI_DALLE:
        bloques.append(3 * noeud_tete + 1)  # u_tête
    return sorted(bloques)


def rigidite_ressort_pied(appuis: ConditionsAppui, sol: Sol, geometrie: Geometrie) -> float | None:
    """kθ [N·m/rad] à ajouter au DOF de rotation du pied, ``None`` si encastrement parfait."""
    if appuis.pied is not TypeAppuiPied.RESSORT:
        return None
    if appuis.k_theta is not None:
        return appuis.k_theta
    if sol.ks is None:
        raise ValueError(
            "Sol.ks (ou ConditionsAppui.k_theta saisi manuellement) est requis "
            "pour un encastrement élastique au pied"
        )
    return rigidite_rotation(sol.ks, geometrie.largeur_semelle)
