# Schéma de données

Base PostgreSQL `veloville`, créée par `sql/schema.sql` (script rejouable :
il supprime puis recrée les tables).

## MLD

Notation : clé primaire en **gras**, clé étrangère précédée de `#`.

- STATION (**station_id**, nom, commune, capacite, latitude, longitude,
  date_mise_en_service)
- TRAJET (**trajet_id**, velo_id, depart_horodatage, #station_depart,
  #station_arrivee, duree_secondes, type_usager, usager_ref)
- INCIDENT (**incident_id**, date_signalement, cible, velo_id, #station_id,
  type_incident, statut, date_resolution, technicien)
- UTILISATEUR (**id_utilisateur**, username, mot_de_passe_hash, role)

Relations :

- une station est la station de départ de 0 ou plusieurs trajets ; un
  trajet a exactement une station de départ ;
- une station est la station d'arrivée de 0 ou plusieurs trajets ; un
  trajet a 0 ou 1 station d'arrivée (vide si le vélo n'est pas encore
  restitué) ;
- une station est visée par 0 ou plusieurs incidents ; un incident vise 0
  ou 1 station (il peut viser un vélo à la place) ;
- la table `utilisateur` n'est liée à aucune autre.

Les vélos n'ont pas de table : `velo_id` est un simple texte.

## Tables et contraintes

### station

| Colonne | Type | Contrainte |
|---|---|---|
| station_id | VARCHAR(10) | clé primaire |
| nom | VARCHAR(100) | obligatoire |
| commune | VARCHAR(50) | obligatoire |
| capacite | INTEGER | obligatoire, `ck_station_capacite` : > 0 |
| latitude, longitude | NUMERIC(8,5) | facultatives |
| date_mise_en_service | DATE | facultative |

### trajet

| Colonne | Type | Contrainte |
|---|---|---|
| trajet_id | VARCHAR(12) | clé primaire |
| velo_id | VARCHAR(8) | obligatoire |
| depart_horodatage | TIMESTAMP | obligatoire |
| station_depart | VARCHAR(10) | obligatoire, clé étrangère vers `station` |
| station_arrivee | VARCHAR(10) | facultative, clé étrangère vers `station` |
| duree_secondes | INTEGER | obligatoire, `ck_trajet_duree` : > 0 |
| type_usager | VARCHAR(12) | obligatoire, `ck_trajet_type_usager` : `abonne` ou `occasionnel` |
| usager_ref | VARCHAR(9) | `ck_trajet_usager_ref` : renseigné pour un abonné, vide pour un occasionnel |

### incident

| Colonne | Type | Contrainte |
|---|---|---|
| incident_id | VARCHAR(12) | clé primaire |
| date_signalement | TIMESTAMP | obligatoire |
| cible | VARCHAR(10) | obligatoire, `ck_incident_cible` (voir RG6) |
| velo_id | VARCHAR(8) | facultatif |
| station_id | VARCHAR(10) | facultatif, clé étrangère vers `station` |
| type_incident | VARCHAR(50) | obligatoire |
| statut | VARCHAR(10) | obligatoire, `ck_incident_statut` : `ouvert`, `en_cours` ou `resolu` |
| date_resolution | TIMESTAMP | `ck_incident_resolution_statut` et `ck_incident_resolution_date` (voir RG8) |
| technicien | VARCHAR(100) | facultatif |

### utilisateur

| Colonne | Type | Contrainte |
|---|---|---|
| id_utilisateur | SERIAL | clé primaire |
| username | VARCHAR(50) | obligatoire, unique |
| mot_de_passe_hash | VARCHAR(255) | obligatoire (hachage bcrypt, jamais le mot de passe en clair) |
| role | VARCHAR(20) | obligatoire, `ck_utilisateur_role` : `exploitant` ou `direction` |

### Index

Des index accélèrent les filtres et les indicateurs : `station(commune)`,
`trajet(depart_horodatage)`, `trajet(station_depart)`,
`trajet(station_arrivee)`, `incident(statut)` et
`incident(date_signalement)`.

## Règles de gestion

Chaque règle est vérifiée à deux endroits : par l'import
(`api/services/fiabilisation.py`), qui rejette proprement la ligne et la
note dans le journal, et par le schéma, qui empêche toute donnée invalide
d'entrer en base, même sans passer par l'import.

| Règle | Dans le schéma | Dans l'import |
|---|---|---|
| **RG1** : station identifiée de façon unique, capacité > 0 | clé primaire `station_id`, `ck_station_capacite` | `verifier_identifiant_unique`, `verifier_capacite` |
| **RG2** : station de départ obligatoire et existante, station d'arrivée existante si renseignée | `station_depart` NOT NULL, clés étrangères | `verifier_station` |
| **RG3** : station d'arrivée inconnue autorisée | `station_arrivee` peut être vide | `verifier_station` renvoie `None` pour une arrivée vide |
| **RG4** : durée entière > 0 | `ck_trajet_duree` | `verifier_duree` |
| **RG5** : pseudonyme pour un abonné, pas pour un occasionnel | `ck_trajet_usager_ref` | `verifier_usager` |
| **RG6** : un incident vise soit un vélo, soit une station existante | `ck_incident_cible`, clé étrangère `station_id` | `verifier_cible`, `verifier_station` |
| **RG7** : trois statuts possibles, transitions limitées | `ck_incident_statut` | `normaliser_statut` ; les transitions sont contrôlées par l'API (`PUT /incidents/{incident_id}/statut`) |
| **RG8** : date de résolution si et seulement si résolu, pas avant le signalement ; technicien attendu | `ck_incident_resolution_statut`, `ck_incident_resolution_date` | `verifier_resolution` ; technicien absent : avertissement (`signaler_technicien_absent`), sans rejet |

RG3 est aussi appliquée par l'indicateur « stations actives » : un trajet
sans station d'arrivée ne compte comme arrivée pour aucune station.

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
