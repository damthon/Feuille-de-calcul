"""Sérialisation JSON générique des dataclasses gelées de ``donnees``.

Un point unique de conversion vers/depuis des structures JSON-compatibles :
deux implémentations séparées — une pour l'export, une pour le chargement de
projet — finiraient par diverger sur un type oublié. La reconstruction
(``depuis_jsonable``) s'appuie sur les annotations de type des dataclasses,
qui font foi.
"""

from __future__ import annotations

import types
from dataclasses import fields, is_dataclass
from enum import Enum
from typing import Any, Mapping, get_args, get_origin, get_type_hints


def vers_jsonable(valeur: Any) -> Any:
    """Convertit une dataclass (éventuellement imbriquée) en structure JSON-compatible."""
    if is_dataclass(valeur) and not isinstance(valeur, type):
        return {f.name: vers_jsonable(getattr(valeur, f.name)) for f in fields(valeur)}
    if isinstance(valeur, Enum):
        return valeur.value
    if isinstance(valeur, Mapping):
        return {str(cle): vers_jsonable(v) for cle, v in valeur.items()}
    if isinstance(valeur, (list, tuple)):
        return [vers_jsonable(v) for v in valeur]
    return valeur


def _est_optionnel(type_cible: Any) -> bool:
    return get_origin(type_cible) is types.UnionType and type(None) in get_args(type_cible)


def _type_non_none(type_cible: Any) -> Any:
    (autre,) = (a for a in get_args(type_cible) if a is not type(None))
    return autre


def depuis_jsonable(type_cible: Any, valeur: Any) -> Any:
    """Reconstruit une valeur typée (dataclass, Enum, tuple…) depuis du JSON décodé."""
    if valeur is None:
        return None
    if _est_optionnel(type_cible):
        return depuis_jsonable(_type_non_none(type_cible), valeur)

    if is_dataclass(type_cible):
        indices = get_type_hints(type_cible)
        arguments = {
            f.name: depuis_jsonable(indices[f.name], valeur[f.name])
            for f in fields(type_cible)
            if f.name in valeur
        }
        return type_cible(**arguments)

    if isinstance(type_cible, type) and issubclass(type_cible, Enum):
        return type_cible(valeur)

    origine = get_origin(type_cible)
    arguments_type = get_args(type_cible)

    if origine in (tuple, list):
        if arguments_type and arguments_type[-1] is Ellipsis:
            type_element = arguments_type[0]
        elif arguments_type:
            type_element = arguments_type[0]
        else:
            type_element = Any
        return tuple(depuis_jsonable(type_element, v) for v in valeur)

    if origine is not None and isinstance(origine, type) and issubclass(origine, Mapping):
        return dict(valeur)

    return valeur
