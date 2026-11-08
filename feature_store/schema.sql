-- Schéma du feature store. Toutes les instructions sont idempotentes.

CREATE TABLE IF NOT EXISTS entities (
    entity_id   BIGINT PRIMARY KEY,
    entity_type TEXT NOT NULL DEFAULT 'client',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS feature_definitions (
    name        TEXT PRIMARY KEY,
    dtype       TEXT NOT NULL CHECK (dtype IN ('int', 'float', 'bool')),
    description TEXT NOT NULL,
    owner       TEXT NOT NULL,
    version     INTEGER NOT NULL DEFAULT 1,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Une version par jeu de variables calculé, liée à l'empreinte du fichier suivi par DVC.
CREATE TABLE IF NOT EXISTS feature_set_versions (
    version     TEXT PRIMARY KEY,
    data_hash   TEXT NOT NULL,
    params      JSONB NOT NULL DEFAULT '{}',
    n_entities  INTEGER NOT NULL,
    n_values    INTEGER NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Format long : une ligne par client, variable, date de calcul et version.
CREATE TABLE IF NOT EXISTS feature_values (
    version         TEXT NOT NULL REFERENCES feature_set_versions (version) ON DELETE CASCADE,
    entity_id       BIGINT NOT NULL REFERENCES entities (entity_id),
    feature_name    TEXT NOT NULL REFERENCES feature_definitions (name),
    event_timestamp TIMESTAMP NOT NULL,
    value           DOUBLE PRECISION,
    PRIMARY KEY (version, entity_id, feature_name, event_timestamp)
);
