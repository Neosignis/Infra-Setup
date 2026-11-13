-- PostgreSQL 16. Apply once with psql -v ON_ERROR_STOP=1.
-- This is metadata/rights schema, not a frame or transcript store.
BEGIN;

CREATE TABLE schema_migrations (
    version integer PRIMARY KEY,
    applied_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE tenants (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE memberships (
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    subject text NOT NULL,
    role text NOT NULL CHECK (role IN ('user','contributor','language_reviewer','ml_engineer','data_steward','org_admin')),
    PRIMARY KEY (tenant_id, subject, role)
);
CREATE TABLE contributors (
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    subject text NOT NULL,
    display_name text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, subject)
);
CREATE TABLE consent_grants (
    tenant_id uuid NOT NULL,
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    contributor_id uuid NOT NULL,
    document_version text NOT NULL,
    purpose text NOT NULL CHECK (purpose IN ('research_capture','training','likeness','motion','rendering','distribution')),
    evidence_object_key text NOT NULL,
    granted_at timestamptz NOT NULL,
    expires_at timestamptz,
    revoked_at timestamptz,
    PRIMARY KEY (tenant_id, id),
    FOREIGN KEY (tenant_id, contributor_id) REFERENCES contributors(tenant_id, id),
    CHECK (expires_at IS NULL OR expires_at > granted_at),
    CHECK (revoked_at IS NULL OR revoked_at >= granted_at)
);
CREATE TABLE assets (
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    contributor_id uuid,
    language text NOT NULL CHECK (language IN ('ase','nsi')),
    kind text NOT NULL CHECK (kind IN ('training_clip','phrase_clip','motion','identity','rig','evaluation_clip')),
    object_key text NOT NULL,
    object_version text NOT NULL,
    sha256 text NOT NULL CHECK (sha256 ~ '^[a-f0-9]{64}$'),
    rights_status text NOT NULL CHECK (rights_status IN ('pending','approved','withdrawn')),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, object_key, object_version),
    FOREIGN KEY (tenant_id, contributor_id) REFERENCES contributors(tenant_id, id)
);
CREATE TABLE asset_grants (
    tenant_id uuid NOT NULL,
    asset_id uuid NOT NULL,
    consent_id uuid NOT NULL,
    PRIMARY KEY (tenant_id, asset_id, consent_id),
    FOREIGN KEY (tenant_id, asset_id) REFERENCES assets(tenant_id, id),
    FOREIGN KEY (tenant_id, consent_id) REFERENCES consent_grants(tenant_id, id)
);
CREATE TABLE dataset_versions (
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    name text NOT NULL,
    version text NOT NULL,
    manifest_key text NOT NULL,
    manifest_sha256 text NOT NULL CHECK (manifest_sha256 ~ '^[a-f0-9]{64}$'),
    split_policy text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, name, version)
);
CREATE TABLE dataset_assets (
    tenant_id uuid NOT NULL,
    dataset_id uuid NOT NULL,
    asset_id uuid NOT NULL,
    split text NOT NULL CHECK (split IN ('train','validation','test')),
    PRIMARY KEY (tenant_id, dataset_id, asset_id),
    FOREIGN KEY (tenant_id, dataset_id) REFERENCES dataset_versions(tenant_id, id),
    FOREIGN KEY (tenant_id, asset_id) REFERENCES assets(tenant_id, id)
);
CREATE TABLE model_versions (
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    name text NOT NULL,
    version text NOT NULL,
    language text NOT NULL CHECK (language IN ('ase','nsi')),
    manifest_key text NOT NULL,
    sha256 text NOT NULL CHECK (sha256 ~ '^[a-f0-9]{64}$'),
    release_status text NOT NULL CHECK (release_status IN ('candidate','internal_demo','pilot','production','withdrawn')),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, name, version)
);
CREATE TABLE model_datasets (
    tenant_id uuid NOT NULL,
    model_id uuid NOT NULL,
    dataset_id uuid NOT NULL,
    PRIMARY KEY (tenant_id, model_id, dataset_id),
    FOREIGN KEY (tenant_id, model_id) REFERENCES model_versions(tenant_id, id),
    FOREIGN KEY (tenant_id, dataset_id) REFERENCES dataset_versions(tenant_id, id)
);
CREATE TABLE evaluations (
    tenant_id uuid NOT NULL,
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    model_id uuid NOT NULL,
    dataset_id uuid NOT NULL,
    report_key text NOT NULL,
    reviewer_subjects text[] NOT NULL,
    gate text NOT NULL CHECK (gate IN ('G1','G2','G3','G4','G5')),
    passed boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id),
    FOREIGN KEY (tenant_id, model_id) REFERENCES model_versions(tenant_id, id),
    FOREIGN KEY (tenant_id, dataset_id) REFERENCES dataset_versions(tenant_id, id)
);
CREATE TABLE sessions (
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    owner_subject text NOT NULL,
    language text NOT NULL CHECK (language IN ('ase','nsi')),
    recognition_model_id uuid,
    state text NOT NULL CHECK (state IN ('created','active','ended','failed')),
    created_at timestamptz NOT NULL DEFAULT now(),
    ended_at timestamptz,
    PRIMARY KEY (tenant_id, id),
    FOREIGN KEY (tenant_id, recognition_model_id) REFERENCES model_versions(tenant_id, id)
);
CREATE TABLE withdrawals (
    tenant_id uuid NOT NULL,
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    consent_id uuid NOT NULL,
    state text NOT NULL CHECK (state IN ('requested','frozen','tracing','deleting','review','completed','failed')),
    requested_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz,
    evidence_key text,
    PRIMARY KEY (tenant_id, id),
    FOREIGN KEY (tenant_id, consent_id) REFERENCES consent_grants(tenant_id, id)
);
CREATE TABLE render_usage (
    tenant_id uuid NOT NULL,
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    idempotency_key text NOT NULL,
    session_id uuid NOT NULL,
    asset_id uuid NOT NULL,
    contributor_id uuid NOT NULL,
    consent_id uuid NOT NULL,
    delivered_ms bigint NOT NULL CHECK (delivered_ms > 0),
    delivered_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, id),
    UNIQUE (tenant_id, idempotency_key),
    FOREIGN KEY (tenant_id, session_id) REFERENCES sessions(tenant_id, id),
    FOREIGN KEY (tenant_id, asset_id) REFERENCES assets(tenant_id, id),
    FOREIGN KEY (tenant_id, contributor_id) REFERENCES contributors(tenant_id, id),
    FOREIGN KEY (tenant_id, consent_id) REFERENCES consent_grants(tenant_id, id)
);

CREATE INDEX asset_contributor ON assets(tenant_id, contributor_id);
CREATE INDEX grant_contributor ON consent_grants(tenant_id, contributor_id);
CREATE INDEX grant_assets ON asset_grants(tenant_id, consent_id);
CREATE INDEX asset_datasets ON dataset_assets(tenant_id, asset_id);
CREATE INDEX dataset_models ON model_datasets(tenant_id, dataset_id);
CREATE INDEX session_owner ON sessions(tenant_id, owner_subject, created_at DESC);
CREATE INDEX withdrawal_queue ON withdrawals(tenant_id, state, requested_at);
CREATE INDEX contributor_usage ON render_usage(tenant_id, contributor_id, delivered_at);

-- Set app.tenant_id from server-verified membership inside every transaction.
-- Never use a superuser/owner/BYPASSRLS application role.
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenants FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON tenants
    USING (id = nullif(current_setting('app.tenant_id', true), '')::uuid)
    WITH CHECK (id = nullif(current_setting('app.tenant_id', true), '')::uuid);
DO $$
DECLARE table_name text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'memberships','contributors','consent_grants','assets','asset_grants',
        'dataset_versions','dataset_assets','model_versions','model_datasets',
        'evaluations','sessions','withdrawals','render_usage'
    ] LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', table_name);
        EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', table_name);
        EXECUTE format(
            'CREATE POLICY tenant_isolation ON %I USING (tenant_id = nullif(current_setting(''app.tenant_id'', true), '''')::uuid) WITH CHECK (tenant_id = nullif(current_setting(''app.tenant_id'', true), '''')::uuid)',
            table_name
        );
    END LOOP;
END $$;

INSERT INTO schema_migrations(version) VALUES (1);
COMMIT;
