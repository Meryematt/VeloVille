# Schéma de données

> Les sections MLD, description des tables et règles de gestion seront
> complétées avec la documentation (Travail 5).

## Audit des données sources

Les trois exports CSV (`data/`) ont été analysés avant l'import : valeurs
distinctes de chaque colonne, unicité des identifiants, lignes en double,
références entre fichiers et cohérence des dates. Les défauts trouvés sont
listés ci-dessous avec le nombre de lignes concernées et le traitement
retenu.

Rappel de la politique de traitement :

- **normalisation** : la valeur est corrigée sans ambiguïté, la ligne est
  importée et la correction est notée dans le journal ;
- **rejet** : la ligne viole une règle de gestion, elle n'est pas importée
  et le motif est noté dans le journal ;
- **doublon écarté** : la ligne est strictement identique à une ligne déjà
  lue, elle n'est importée qu'une fois.

### stations.csv (120 lignes)

Aucun défaut trouvé : identifiants uniques au format `S` + 3 chiffres,
capacités positives, coordonnées et dates au bon format. Les 120 stations
sont importées.

### trajets.csv (2 030 lignes)

| Défaut | Lignes | Exemple | Traitement |
|---|---|---|---|
| Ligne en double (strictement identique) | 12 | T480073 | Doublon écarté |
| Identifiant de vélo en minuscule | 6 | `v1281` | Normalisé en `V1281` |
| Horodatage au format JJ/MM/AAAA HH:MM | 5 | `24/08/2026 11:01` | Normalisé en `2026-08-24 11:01:00` |
| Station d'arrivée inexistante | 7 | `S999` | Rejet (RG2) |
| Durée nulle ou négative | 9 | `0`, `-45`, `-120` | Rejet (RG4) |
| Station d'arrivée vide | 23 | T480004 | Conservé, ce n'est pas un défaut (RG3) |
| Station de départ = station d'arrivée | 15 | — | Conservé, une boucle est un trajet valide |

Remarques :

- le trajet T480596 est à la fois en double et de durée négative : la
  copie est écartée comme doublon, puis la première occurrence est rejetée ;
- le trajet T480152 a un horodatage JJ/MM/AAAA **et** une arrivée `S999` :
  il est rejeté et seul le motif du rejet figure dans le journal (d'où 4
  normalisations d'horodatage dans le journal pour 5 lignes concernées) ;
- aucun trajet ne viole la règle abonné / pseudonyme (RG5).

### incidents.csv (180 lignes)

| Défaut | Lignes | Exemple | Traitement |
|---|---|---|---|
| Statut avec une casse ou un espace différents | 125 | `Ouvert`, `RESOLU`, `En cours` | Normalisé en `ouvert`, `resolu`, `en_cours` |
| Date de résolution antérieure au signalement | 3 | I2026-0028, I2026-0124, I2026-0178 | Rejet (RG8) |
| Technicien absent sur un incident en cours ou résolu | 25 | I2026-0011 | Importé avec avertissement (RG8) |

Remarques :

- 7 écritures différentes du statut ont été trouvées pour 3 valeurs
  attendues ; 124 normalisations figurent dans le journal, la 125e ligne
  (I2026-0028) étant rejetée ;
- 3 incidents ouverts n'ont pas de technicien : c'est normal, ils ne sont
  pas encore pris en charge ;
- aucun incident ne vise à la fois un vélo et une station, ni une station
  inexistante (RG6).

### Bilan de l'import

| Fichier | Lignes CSV | Importées | Rejetées | Doublons écartés |
|---|---|---|---|---|
| stations.csv | 120 | 120 | 0 | 0 |
| trajets.csv | 2 030 | 2 002 | 16 | 12 |
| incidents.csv | 180 | 177 | 3 | 0 |


### Journal des rejets et avertissements

Chemin : `docs/journal-import.csv`, régénéré à chaque exécution de
`python scripts/importer.py`.

Chaque ligne contient : fichier source, identifiant, colonne, valeur,
motif, décision (`rejet`, `normalisation` ou `doublon écarté`). Le journal
compte 190 lignes : 19 rejets, 12 doublons écartés et 159 normalisations.

### Vérifications après import

| Vérification | Résultat |
|---|---|
| Deux exécutions de l'import donnent les mêmes comptages (120 / 2 002 / 177) | OK |
| Trajets ou incidents référençant une station absente | 0 |
| Trajets de durée nulle ou négative | 0 |
| Incidents de statut hors `ouvert`, `en_cours`, `resolu` | 0 |
| Trajets sans station d'arrivée, conservés (RG3) | 22 |
| Les fonctions de `fiabilisation.py` s'exécutent sans base de données | OK (tests unitaires) |

Les 23 trajets sans arrivée du CSV deviennent 22 en base : l'un d'eux
(T481636) est une ligne en double.
