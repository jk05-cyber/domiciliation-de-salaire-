# Salary Detection Pipeline

Projet Python de détection de salaire probable à partir de 3 fichiers CSV mensuels de mouvements bancaires.

## Arborescence

```text
salary_detection_pipeline/
├── input/
│   ├── novembre.csv
│   ├── decembre.csv
│   └── janvier.csv
├── output/
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── io_utils.py
│   ├── preprocessing.py
│   ├── feature_engineering.py
│   ├── scoring.py
│   ├── pipeline.py
│   └── main.py
├── tests/
│   └── test_pipeline.py
├── requirements.txt
├── README.md
└── run.py
```

## Où déposer les CSV

Déposez les trois fichiers métier dans le dossier `input/` avec exactement ces noms :

- `input/novembre.csv`
- `input/decembre.csv`
- `input/janvier.csv`

Les fichiers peuvent utiliser `;` ou `,` comme séparateur. Le pipeline gère également :

- les espaces parasites dans les noms de colonnes
- les montants avec virgule ou point décimal
- les dates au format `jour/mois/année`

## Colonnes attendues

Les CSV doivent contenir au minimum :

- `Identifiant SAB`
- `Libelle Court Segment`
- `ID Mouvement`
- `Libelle Mouvement`
- `Code Siege`
- `Date Operation`
- `Montant Devise Local`

## Installation

Python 3.11+ est recommandé.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Exécution du pipeline

Depuis la racine du projet :

```bash
python run.py
```

## Fichiers générés

Le pipeline crée automatiquement le dossier `output/` si nécessaire, puis génère :

- `output/salaires_estimes.csv`
- `output/candidats_salaires.csv`
- `output/summary.json`

### `salaires_estimes.csv`

Fichier principal avec une ligne par client :

- meilleur candidat retenu
- score métier
- statut final
- salaire estimé
- niveau de confiance

Les clients sans candidat créditeur exploitable restent présents avec `statut = NON_DETERMINE`.

### `candidats_salaires.csv`

Fichier détaillé intermédiaire contenant toutes les combinaisons `client + émetteur` avec les features calculées et le scoring.

### `summary.json`

Synthèse de volumétrie et de répartition des statuts.

## Logique métier

Le pipeline :

1. charge automatiquement les 3 fichiers
2. concatène les données
3. standardise les colonnes
4. filtre uniquement les crédits
5. normalise les libellés en `emetteur_normalise`
6. agrège les flux récurrents par client et émetteur
7. applique un score métier
8. retient le meilleur candidat par client

## Tests

Pour exécuter les tests :

```bash
python -m unittest discover -s tests
```

## Notes

- Les fichiers présents dans `input/` sont des placeholders avec en-têtes pour faciliter le démarrage.
- Le code est structuré pour être lisible, maintenable et industrialisable.

