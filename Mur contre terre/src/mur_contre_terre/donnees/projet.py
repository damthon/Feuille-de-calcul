"""Projet — agrège toutes les données d'entrée, se sauvegarde en JSON (.mct)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from mur_contre_terre.donnees.appuis import ConditionsAppui
from mur_contre_terre.donnees.charges import CasDeCharge
from mur_contre_terre.donnees.geometrie import Geometrie
from mur_contre_terre.donnees.materiaux import Materiaux
from mur_contre_terre.donnees.serialisation import depuis_jsonable, vers_jsonable
from mur_contre_terre.donnees.sol import Sol

FORMAT_PROJET = 1


def _pas_de_charge_defaut() -> tuple[float, ...]:
    return tuple(i / 20 for i in range(1, 21))  # 5 %, 10 %, …, 100 %


@dataclass(frozen=True)
class Projet:
    nom: str
    geometrie: Geometrie
    sol: Sol
    appuis: ConditionsAppui
    materiaux: Materiaux
    charges: tuple[CasDeCharge, ...] = field(default_factory=tuple)
    finesse_maillage: float = 0.25
    tolerance_convergence: float = 1e-3
    iterations_max: int = 50
    pas_de_charge: tuple[float, ...] = field(default_factory=_pas_de_charge_defaut)

    def __post_init__(self) -> None:
        if self.finesse_maillage <= 0:
            raise ValueError(f"Projet.finesse_maillage doit être strictement positif (reçu {self.finesse_maillage})")
        if self.finesse_maillage > self.geometrie.hauteur:
            raise ValueError("Projet.finesse_maillage ne peut pas dépasser la hauteur du mur")
        if self.tolerance_convergence <= 0:
            raise ValueError(
                f"Projet.tolerance_convergence doit être strictement positive (reçu {self.tolerance_convergence})"
            )
        if self.iterations_max <= 0:
            raise ValueError(f"Projet.iterations_max doit être strictement positif (reçu {self.iterations_max})")
        if any(not 0.0 < p <= 1.0 for p in self.pas_de_charge):
            raise ValueError("Projet.pas_de_charge doit contenir des fractions dans ]0, 1]")
        if self.appuis.pied.value == "ressort" and self.sol.ks is None and self.appuis.k_theta is None:
            raise ValueError(
                "Sol.ks (ou ConditionsAppui.k_theta saisi manuellement) est requis "
                "quand ConditionsAppui.pied est un encastrement élastique"
            )

    def sauvegarder(self, chemin: str | Path) -> None:
        """Écrit le projet en JSON (extension conventionnelle ``.mct``)."""
        enveloppe = {"format": FORMAT_PROJET, "projet": vers_jsonable(self)}
        Path(chemin).write_text(json.dumps(enveloppe, indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def charger(cls, chemin: str | Path) -> "Projet":
        """Relit un projet depuis un fichier écrit par ``sauvegarder``."""
        enveloppe = json.loads(Path(chemin).read_text(encoding="utf-8"))
        format_lu = enveloppe.get("format")
        if format_lu != FORMAT_PROJET:
            raise ValueError(f"Format de fichier projet non supporté : {format_lu!r}")
        return depuis_jsonable(cls, enveloppe["projet"])
