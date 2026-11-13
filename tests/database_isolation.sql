-- Throwaway PostgreSQL CI instance only; rolled back at the end.
BEGIN;
CREATE ROLE neosignis_test_app NOLOGIN NOBYPASSRLS;
GRANT USAGE ON SCHEMA public TO neosignis_test_app;
GRANT SELECT, INSERT ON tenants, sessions TO neosignis_test_app;
INSERT INTO tenants(id,name) VALUES
 ('11111111-1111-1111-1111-111111111111','fixture-one'),
 ('22222222-2222-2222-2222-222222222222','fixture-two');
SET LOCAL ROLE neosignis_test_app;
DO $$ BEGIN
 IF (SELECT count(*) FROM tenants) != 0 THEN RAISE EXCEPTION 'RLS must deny without context'; END IF;
END $$;
SELECT set_config('app.tenant_id','11111111-1111-1111-1111-111111111111',true);
DO $$ BEGIN
 IF (SELECT count(*) FROM tenants) != 1 THEN RAISE EXCEPTION 'RLS must expose one tenant only'; END IF;
 BEGIN
  INSERT INTO sessions(tenant_id,owner_subject,language,state)
  VALUES ('22222222-2222-2222-2222-222222222222','fixture','ase','created');
  RAISE EXCEPTION 'Cross-tenant insert incorrectly allowed';
 EXCEPTION WHEN insufficient_privilege THEN NULL;
 END;
END $$;
INSERT INTO sessions(tenant_id,owner_subject,language,state)
VALUES ('11111111-1111-1111-1111-111111111111','fixture','ase','created');
SELECT set_config('app.tenant_id','22222222-2222-2222-2222-222222222222',true);
DO $$ BEGIN
 IF (SELECT count(*) FROM sessions) != 0 THEN RAISE EXCEPTION 'Cross-tenant session visible'; END IF;
END $$;
ROLLBACK;
