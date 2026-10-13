-- Suppression dans l'ordre inverse des dépendances.
DROP TABLE IF EXISTS incident CASCADE;
DROP TABLE IF EXISTS trajet CASCADE;
DROP TABLE IF EXISTS utilisateur CASCADE;
DROP TABLE IF EXISTS station CASCADE;

-- ---------------------------------------------------------------
-- 1. Table station
-- ---------------------------------------------------------------
-- RG1 : identifiant unique, capacité entière strictement positive.
CREATE TABLE station (
    station_id            VARCHAR(10)   PRIMARY KEY,
    nom                   VARCHAR(100)  NOT NULL,
    commune               VARCHAR(50)   NOT NULL,
    capacite              INTEGER       NOT NULL,
    latitude              NUMERIC(8,5),
    longitude             NUMERIC(8,5),
    date_mise_en_service  DATE,
    CONSTRAINT ck_station_capacite CHECK (capacite > 0)
);

-- ---------------------------------------------------------------
-- 2. Table trajet
-- ---------------------------------------------------------------
-- RG2 : station de départ obligatoire et existante ; station d'arrivée
--       existante lorsqu'elle est renseignée.
-- RG3 : station d'arrivée inconnue autorisée (NULL).
-- RG4 : durée entière strictement positive.
-- RG5 : un abonné porte un usager_ref, un occasionnel n'en porte pas.
CREATE TABLE trajet (
    trajet_id          VARCHAR(12)  PRIMARY KEY,
    velo_id            VARCHAR(8)   NOT NULL,
    depart_horodatage  TIMESTAMP    NOT NULL,
    station_depart     VARCHAR(10)  NOT NULL REFERENCES station (station_id),
    station_arrivee    VARCHAR(10)  REFERENCES station (station_id),
    duree_secondes     INTEGER      NOT NULL,
    type_usager        VARCHAR(12)  NOT NULL,
    usager_ref         VARCHAR(9),
    CONSTRAINT ck_trajet_duree CHECK (duree_secondes > 0),
    CONSTRAINT ck_trajet_type_usager
        CHECK (type_usager IN ('abonne', 'occasionnel')),
    CONSTRAINT ck_trajet_usager_ref CHECK (
        (type_usager = 'abonne' AND usager_ref IS NOT NULL)
        OR (type_usager = 'occasionnel' AND usager_ref IS NULL)
    )
);

-- ---------------------------------------------------------------
-- 3. Table incident
-- ---------------------------------------------------------------
-- RG6 : un incident vise soit un vélo, soit une station existante.
-- RG7 : trois statuts possibles.
-- RG8 : date de résolution renseignée si et seulement si l'incident est
--       résolu, et postérieure ou égale à la date de signalement.
CREATE TABLE incident (
    incident_id       VARCHAR(12)   PRIMARY KEY,
    date_signalement  TIMESTAMP     NOT NULL,
    cible             VARCHAR(10)   NOT NULL,
    velo_id           VARCHAR(8),
    station_id        VARCHAR(10)   REFERENCES station (station_id),
    type_incident     VARCHAR(50)   NOT NULL,
    statut            VARCHAR(10)   NOT NULL,
    date_resolution   TIMESTAMP,
    technicien        VARCHAR(100),
    CONSTRAINT ck_incident_cible CHECK (
        (cible = 'velo' AND velo_id IS NOT NULL AND station_id IS NULL)
        OR (cible = 'station' AND station_id IS NOT NULL AND velo_id IS NULL)
    ),
    CONSTRAINT ck_incident_statut
        CHECK (statut IN ('ouvert', 'en_cours', 'resolu')),
    CONSTRAINT ck_incident_resolution_statut
        CHECK ((statut = 'resolu') = (date_resolution IS NOT NULL)),
    CONSTRAINT ck_incident_resolution_date
        CHECK (date_resolution IS NULL OR date_resolution >= date_signalement)
);

-- ---------------------------------------------------------------
-- 4. Table utilisateur
-- ---------------------------------------------------------------
-- Le mot de passe n'est jamais stocké en clair : hachage bcrypt.
CREATE TABLE utilisateur (
    id_utilisateur     SERIAL        PRIMARY KEY,
    username           VARCHAR(50)   NOT NULL UNIQUE,
    mot_de_passe_hash  VARCHAR(255)  NOT NULL,
    role               VARCHAR(20)   NOT NULL,
    CONSTRAINT ck_utilisateur_role CHECK (role IN ('exploitant', 'direction'))
);

-- ---------------------------------------------------------------
-- 5. Index utiles aux filtres et aux indicateurs
-- ---------------------------------------------------------------
-- Filtre GET /stations?commune=
CREATE INDEX idx_station_commune ON station (commune);

-- Filtre par période (GET /trajets, indicateur activité par jour)
CREATE INDEX idx_trajet_depart_horodatage ON trajet (depart_horodatage);

-- Filtre par station et indicateur stations actives
CREATE INDEX idx_trajet_station_depart ON trajet (station_depart);
CREATE INDEX idx_trajet_station_arrivee ON trajet (station_arrivee);

-- Filtre GET /incidents?statut= et tri par date de signalement
CREATE INDEX idx_incident_statut ON incident (statut);
CREATE INDEX idx_incident_date_signalement ON incident (date_signalement DESC);
