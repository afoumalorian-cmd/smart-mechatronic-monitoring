"""Define the shared SQLite schema for telemetry storage."""


SCHEMA = """
CREATE TABLE IF NOT EXISTS import_runs (
    import_id TEXT PRIMARY KEY,
    imported_at_utc TEXT NOT NULL,
    source_file TEXT NOT NULL,
    records_read INTEGER NOT NULL CHECK (records_read >= 0),
    records_inserted INTEGER NOT NULL CHECK (records_inserted >= 0),
    duplicates_skipped INTEGER NOT NULL CHECK (duplicates_skipped >= 0),
    CHECK (records_read = records_inserted + duplicates_skipped)
);

CREATE TABLE IF NOT EXISTS measurements (
    measurement_id INTEGER PRIMARY KEY,
    import_id TEXT REFERENCES import_runs(import_id),
    source_line INTEGER,
    session_id TEXT NOT NULL,
    received_at_utc TEXT NOT NULL,
    device_id TEXT NOT NULL,
    sequence INTEGER NOT NULL CHECK (sequence >= 0),
    uptime_ms INTEGER NOT NULL CHECK (uptime_ms >= 0),
    sensor TEXT NOT NULL CHECK (sensor = 'dht22'),
    status TEXT NOT NULL CHECK (status = 'ok'),
    temperature_c REAL NOT NULL
        CHECK (temperature_c BETWEEN -40 AND 80),
    humidity_pct REAL NOT NULL
        CHECK (humidity_pct BETWEEN 0 AND 100),
    CHECK (
        (import_id IS NULL AND source_line IS NULL)
        OR
        (
            import_id IS NOT NULL
            AND source_line IS NOT NULL
            AND source_line > 0
        )
    ),
    UNIQUE (session_id, device_id, sequence)
);

CREATE INDEX IF NOT EXISTS idx_measurements_device_time
ON measurements (device_id, received_at_utc);

CREATE TABLE IF NOT EXISTS mqtt_receipts (
    receipt_id TEXT PRIMARY KEY,
    consumer_run_id TEXT NOT NULL,
    mqtt_received_at_utc TEXT NOT NULL,
    topic TEXT NOT NULL,
    qos INTEGER NOT NULL CHECK (qos IN (0, 1, 2)),
    mqtt_mid INTEGER NOT NULL,
    mqtt_dup INTEGER NOT NULL CHECK (mqtt_dup IN (0, 1)),
    mqtt_retain INTEGER NOT NULL CHECK (mqtt_retain IN (0, 1)),
    payload BLOB NOT NULL,
    outcome TEXT NOT NULL CHECK (
        outcome IN (
            'inserted',
            'duplicate',
            'conflict',
            'sensor_error',
            'invalid'
        )
    ),
    details_json TEXT NOT NULL,
    measurement_id INTEGER REFERENCES measurements(measurement_id),
    CHECK (
        (
            outcome IN ('inserted', 'duplicate', 'conflict')
            AND measurement_id IS NOT NULL
        )
        OR
        (
            outcome IN ('sensor_error', 'invalid')
            AND measurement_id IS NULL
        )
    )
);

CREATE INDEX IF NOT EXISTS idx_mqtt_receipts_run_time
ON mqtt_receipts (consumer_run_id, mqtt_received_at_utc);
"""


def initialize_database(connection):
    """Create or migrate the schema atomically on an idle connection."""
    if connection.in_transaction:
        raise ValueError("Schema initialization requires no active transaction.")

    # Rebuilding a referenced table requires disabling foreign keys outside
    # the transaction. Check all references before committing the migration.
    connection.execute("PRAGMA foreign_keys = OFF")

    try:
        connection.execute("BEGIN IMMEDIATE")

        columns = {
            row[1]: row
            for row in connection.execute(
                "PRAGMA table_info(measurements)"
            )
        }

        needs_migration = bool(columns) and (
            columns["import_id"][3] or columns["source_line"][3]
        )

        if needs_migration:
            # Reuse the current definition for the replacement table.
            table_start = SCHEMA.index(
                "CREATE TABLE IF NOT EXISTS measurements ("
            )
            table_end = SCHEMA.index(";", table_start) + 1
            replacement_sql = SCHEMA[table_start:table_end].replace(
                "CREATE TABLE IF NOT EXISTS measurements (",
                "CREATE TABLE measurements_phase7 (",
                1,
            )
            connection.execute(replacement_sql)

            # Preserve primary keys and all existing measurement values.
            connection.execute(
                """
                INSERT INTO measurements_phase7 (
                    measurement_id, import_id, source_line,
                    session_id, received_at_utc, device_id, sequence,
                    uptime_ms, sensor, status, temperature_c, humidity_pct
                )
                SELECT
                    measurement_id, import_id, source_line,
                    session_id, received_at_utc, device_id, sequence,
                    uptime_ms, sensor, status, temperature_c, humidity_pct
                FROM measurements
                """
            )

            connection.execute("DROP TABLE measurements")
            connection.execute(
                "ALTER TABLE measurements_phase7 RENAME TO measurements"
            )

        # These schema statements contain no embedded semicolons.
        # Avoid executescript(), which would commit the active transaction.
        for statement in SCHEMA.split(";"):
            if statement.strip():
                connection.execute(statement)

        violations = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()
        if violations:
            raise ValueError(
                f"Foreign key violations during initialization: {violations}"
            )

        connection.commit()

    except BaseException:
        # Also roll back if the user interrupts the migration.
        connection.rollback()
        raise

    finally:
        connection.execute("PRAGMA foreign_keys = ON")