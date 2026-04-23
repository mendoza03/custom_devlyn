CREATE SEQUENCE IF NOT EXISTS raw_request_id_seq;
CREATE SEQUENCE IF NOT EXISTS normalized_event_id_seq;
CREATE SEQUENCE IF NOT EXISTS event_quarantine_id_seq;
CREATE SEQUENCE IF NOT EXISTS processing_error_id_seq;
CREATE SEQUENCE IF NOT EXISTS outbox_sync_id_seq;

CREATE TABLE IF NOT EXISTS raw_request (
    id bigint NOT NULL DEFAULT nextval('raw_request_id_seq'),
    received_at_utc timestamptz NOT NULL,
    ingest_id uuid NOT NULL,
    source_ip inet,
    source_port integer,
    listener_port integer NOT NULL,
    method text NOT NULL,
    path text NOT NULL,
    query text NOT NULL DEFAULT '',
    headers_jsonb jsonb NOT NULL DEFAULT '{}'::jsonb,
    body_jsonb jsonb,
    body_raw text,
    payload_hash text NOT NULL,
    event_kind_detected text NOT NULL,
    device_id_hint text,
    device_model_hint text,
    created_at timestamptz NOT NULL DEFAULT now()
) PARTITION BY RANGE (received_at_utc);

CREATE TABLE IF NOT EXISTS normalized_event (
    id bigint NOT NULL DEFAULT nextval('normalized_event_id_seq'),
    raw_request_id bigint NOT NULL,
    raw_received_at_utc timestamptz NOT NULL,
    event_occurred_at_utc timestamptz NOT NULL,
    event_kind text NOT NULL,
    device_id_resolved text,
    source_ip inet,
    listener_port integer,
    user_id_on_device text,
    card_name text,
    door_name text,
    direction text,
    granted boolean,
    error_code integer,
    method_code integer,
    reader_id text,
    card_no text,
    user_type_code integer,
    door_index integer,
    block_id bigint,
    stream_index integer,
    body_jsonb jsonb,
    dedup_key text NOT NULL,
    identity_resolution text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
) PARTITION BY RANGE (event_occurred_at_utc);

CREATE TABLE IF NOT EXISTS raw_request_registry (
    ingest_id uuid PRIMARY KEY,
    received_at_utc timestamptz NOT NULL,
    raw_request_id bigint NOT NULL,
    payload_hash text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS normalized_event_registry (
    dedup_key text PRIMARY KEY,
    event_occurred_at_utc timestamptz NOT NULL,
    normalized_event_id bigint NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS device_registry (
    device_id text PRIMARY KEY,
    device_model text,
    site_code text,
    expected_port integer,
    status text NOT NULL DEFAULT 'learning',
    first_seen_at timestamptz NOT NULL,
    last_seen_at timestamptz NOT NULL,
    last_heartbeat_at timestamptz,
    last_event_at timestamptz,
    last_source_ip inet,
    last_listener_port integer,
    learning_mode boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS device_status (
    device_id text PRIMARY KEY REFERENCES device_registry(device_id) ON DELETE CASCADE,
    last_seen_at timestamptz,
    last_heartbeat_at timestamptz,
    last_event_at timestamptz,
    last_event_kind text,
    status text NOT NULL DEFAULT 'learning',
    heartbeat_interval_seconds integer,
    stale_since timestamptz,
    offline_since timestamptz,
    last_source_ip inet,
    last_listener_port integer,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS event_quarantine (
    id bigint PRIMARY KEY DEFAULT nextval('event_quarantine_id_seq'),
    raw_request_id bigint NOT NULL,
    raw_received_at_utc timestamptz NOT NULL,
    source_ip inet,
    listener_port integer,
    payload_hash text,
    reason text NOT NULL,
    candidate_device_id text,
    event_kind text NOT NULL,
    body_jsonb jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS processing_error (
    id bigint PRIMARY KEY DEFAULT nextval('processing_error_id_seq'),
    stage text NOT NULL,
    ingest_id uuid,
    raw_request_id bigint,
    raw_received_at_utc timestamptz,
    error_message text NOT NULL,
    payload_jsonb jsonb,
    retryable boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS outbox_sync (
    id bigint PRIMARY KEY DEFAULT nextval('outbox_sync_id_seq'),
    normalized_event_id bigint NOT NULL,
    event_occurred_at_utc timestamptz NOT NULL,
    target text NOT NULL DEFAULT 'odoo',
    status text NOT NULL DEFAULT 'pending',
    payload_jsonb jsonb NOT NULL,
    available_at timestamptz NOT NULL DEFAULT now(),
    processed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_raw_request_received_at ON raw_request (received_at_utc DESC);
CREATE INDEX IF NOT EXISTS idx_raw_request_source_ip ON raw_request (source_ip, listener_port, received_at_utc DESC);
CREATE INDEX IF NOT EXISTS idx_raw_request_payload_hash ON raw_request (payload_hash);
CREATE INDEX IF NOT EXISTS idx_raw_request_event_kind ON raw_request (event_kind_detected, received_at_utc DESC);
CREATE INDEX IF NOT EXISTS idx_raw_request_device_hint ON raw_request (device_id_hint, received_at_utc DESC);

CREATE INDEX IF NOT EXISTS idx_normalized_event_occurred_at ON normalized_event (event_occurred_at_utc DESC);
CREATE INDEX IF NOT EXISTS idx_normalized_event_device_id ON normalized_event (device_id_resolved, event_occurred_at_utc DESC);
CREATE INDEX IF NOT EXISTS idx_normalized_event_user_id ON normalized_event (user_id_on_device, event_occurred_at_utc DESC);
CREATE INDEX IF NOT EXISTS idx_normalized_event_kind ON normalized_event (event_kind, event_occurred_at_utc DESC);
CREATE INDEX IF NOT EXISTS idx_normalized_event_reader ON normalized_event (reader_id, event_occurred_at_utc DESC);

CREATE INDEX IF NOT EXISTS idx_device_registry_last_source ON device_registry (last_source_ip, last_listener_port, last_heartbeat_at DESC);
CREATE INDEX IF NOT EXISTS idx_device_status_status ON device_status (status, last_heartbeat_at DESC);
CREATE INDEX IF NOT EXISTS idx_quarantine_created_at ON event_quarantine (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_processing_error_created_at ON processing_error (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_outbox_sync_status ON outbox_sync (status, available_at);
