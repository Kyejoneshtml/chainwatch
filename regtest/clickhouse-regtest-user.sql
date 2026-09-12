-- Regtest-only counterpart to schema/ingestor-user.sql.example, applied by
-- regtest/ingestor-rollback-test.sh against the disposable clickhouse-regtest
-- container (see docker-compose.regtest.yml). Same reasoning as that file:
-- 'default' is restricted to true localhost by the image's own
-- default-user.xml and can't be reached through the published host port.
--
-- Weak hardcoded credentials, deliberately: this container holds no real
-- data, is destroyed at the end of every test run, and has no connection to
-- mainnet or any public network -- the same posture already accepted for
-- regtest/bitcoin-regtest.conf's RPC password.
--
-- Same grants the live ingestor user has after stage 5, so this test
-- actually exercises the real privilege boundary -- if the ALTER UPDATE
-- grant were missing here, the invalidation step would fail exactly as it
-- would in production.

CREATE USER IF NOT EXISTS ingestor
IDENTIFIED WITH plaintext_password BY 'regtestonly';

GRANT SELECT, INSERT ON chainwatch.* TO ingestor;
GRANT ALTER UPDATE ON chainwatch.alerts TO ingestor;
