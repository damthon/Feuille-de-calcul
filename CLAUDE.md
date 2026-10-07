# Feuille-de-calcul

Outils de calcul d'ingénieur civil (bureau IngPhi SA), en Python, selon les normes SIA.
Langue du projet : **français** (code, commentaires, commits, documentation).

## Contenu du dépôt

| Dossier | Rôle |
|---|---|
| `Mur contre terre/` | Application principale : vérification d'un mur de sous-sol en béton armé (SIA 260/261/262/267). Voir son `README.md` et `docs/plan-conception.html`. |
| `Retrait et armature minimale/` | Futur outil ; contient seulement les feuilles Excel source pour l'instant. |
| `outils/convertir_normes.py` | Conversion locale des normes PDF en Markdown (Marker), en vue d'un LLM local. |
| `normes_pdf/`, `normes_md/` | Normes SIA (PDF et Markdown converti). **Ignorés par git** (droit d'auteur). |
| `.claude/skills/` | Skills de projet : `verification-normative`, `tests-reference`, `rapport-calcul`, `release-pyinstaller`. |

## Règle impérative : droit d'auteur des normes

Les normes SIA sont protégées. **Ne jamais lire, afficher ni extraire le texte** des fichiers de
`normes_pdf/` ou `normes_md/`, ni les committer. L'utilisateur les exploite lui-même avec le script
et un LLM local.
- Seule exception : `261-C1_2023_f.pdf` (rectificatif de 3 pages), autorisé comme fichier de test.
- Pour déboguer, se limiter aux métadonnées (taille, nombre de pages, rotation des pages, polices)
  ou demander à l'utilisateur de vérifier lui-même le rendu.

## Mur contre terre — état

Paquet `mur-contre-terre` v0.3.0, Python ≥ 3.11, `numpy` seul obligatoire. Lots 1 à 11 terminés
(données, poussée des terres, EF, combinaisons, flexion composée, non-linéaire, note de calcul,
interface, export PDF/Excel, exécutable Windows + CI). **Reste : lot 12**, validation contre les cas
de référence Excel du bureau (skill `tests-reference`).

```bash
cd "Mur contre terre" && python -m venv .venv && .venv\Scripts\Activate.ps1
pip install -e ".[dev]" && python -m pytest
```

Flux git : branches `claude/...` fusionnées dans `main` par pull request.

## Conversion des normes (travail en cours, octobre 2026)

### Objectif
Convertir les normes en Markdown propre, puis les découper **par paragraphe/article de norme**
(numéros `4.3.2.1`…) avec métadonnées (norme, article, titre, section parente), pour une
recherche par un LLM local (RAG).

### Environnement installé sur le poste
- **Venv Marker** : `C:\mk` (chemin court obligatoire sous Windows). Lancer le script avec
  `C:\mk\Scripts\python.exe outils\convertir_normes.py [SRC DEST] [--ocr] [--force]`.
- PyTorch installé en **version CPU** (`2.14.1+cpu`) alors que le PC a une **NVIDIA RTX 500 Ada
  (4 Go)** : la conversion est lente (~1 min pour 3 pages, plusieurs heures pour les grosses
  normes). Installer torch CUDA accélérerait fortement — proposé, pas encore fait.
- Modèles Marker téléchargés (cache `~/.cache/huggingface` et `%LOCALAPPDATA%\datalab`).
- **Ollama 0.35.1** : `qwen2.5:14b` (texte), `bge-m3` (embeddings), `mistral`, et
  `qwen2.5vl:7b` (vision, téléchargé pour `marker --use_llm`).

### Comportement actuel du script (modifications non committées)
- Ignore les PDF ayant déjà un `.md` dans `normes_md/<nom>/` ; `--force` pour reconvertir.
- Traite les PDF **du plus léger au plus lourd** ; relit le dossier avant chaque PDF (les fichiers
  ajoutés en cours de route sont pris en compte).
- Bloque la mise en veille (`SetThreadExecutionState` avec *display required* : sur ce PC en
  **veille moderne S0**, seul « écran requis » empêche la veille ; l'écran reste allumé).
- **Redresse les pages tournées** (`/Rotate`) via pypdfium2 avant Marker : sinon Marker lit le
  texte verticalement, lettre par lettre (`P<br>a<br>g<br>e`). Concerne 261-C1 (1 page) et
  surtout SIA 103 (50 pages sur 84).
- Remplace les `<br>` restants (retours à la ligne dans les cellules) par des espaces.
  Limite connue : un mot coupé en fin de ligne devient « rap port ».

### Problème ouvert : gras et barré dans les tableaux
Important pour les rectificatifs (texte fautif **barré et en gras**, correction **gras italique**).
- Le gras est bien codé dans le PDF (police `Arial-BoldMT`, poids 690), mais Marker le perd
  dans les cellules de tableau.
- Le barré n'est pas une propriété de police : ce sont des traits vectoriels ; Marker ne le
  détecte pas.
- Essai `--use_llm --llm_service marker.services.ollama.OllamaService --ollama_model qwen2.5vl:7b`
  sur 261-C1 : 3 min 44, tableau inchangé. Le prompt de Marker (`LLMTableProcessor.table_rewriting_prompt`)
  ne demande pas la mise en forme, et `get_cell_text` supprime toute balise hors
  `br, i, b, span, math` (donc `<s>`/`<del>` seraient perdus). Une erreur 400 d'Ollama apparaît
  aussi sur `LLMSectionHeaderProcessor` (sans conséquence, Marker ignore l'échec).
- Piste en cours (non testée, interrompue) : passer via `--config_json` un
  `table_rewriting_prompt` modifié exigeant `<b>`/`<i>` et `~~texte~~` pour le barré.
- Alternative : post-traitement maison avec pypdfium2 (gras = poids de police ≥ 600 ;
  barré = trait fin traversant le milieu des caractères) puis insertion de `**`/`~~` dans le
  Markdown. Plus rapide, mais fragile si le même texte apparaît plusieurs fois.

### Étapes suivantes
1. Trancher la méthode gras/barré (prompt LLM personnalisé ou post-traitement) et la tester sur 261-C1.
2. Faire valider par l'utilisateur la conversion d'une norme complète (p. ex. 260).
3. Écrire le découpage par article de norme (JSON/Markdown par bloc) pour l'indexation `bge-m3`
   et l'interrogation par `qwen2.5:14b`.

### Contraintes du poste (conversions longues la nuit)
- Laisser le PC **branché, couvercle ouvert** ; le verrouillage (Win+L) est sans risque.
- Le 05.10.2026, la conversion a été interrompue par la veille (18 h 06) puis tuée par des
  **redémarrages Windows Update** (01 h 44 et 01 h 51) : suspendre les mises à jour avant une
  longue conversion.
