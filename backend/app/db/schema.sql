-- 15 — Database Schema (PostgreSQL)
-- POC-scale schema. Matches 09_DATA_MODEL.md.

CREATE TABLE patient (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mock_abha_id TEXT,
    name TEXT,
    age INT,
    sex TEXT,
    contact TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE session (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patient(id),
    mode TEXT CHECK (mode IN ('general_medicine','ayush')),
    language TEXT CHECK (language IN ('hi','en')),
    status TEXT CHECK (status IN ('in_progress','submitted','reviewed','approved')) DEFAULT 'in_progress',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE consent (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES session(id),
    scope TEXT[],
    language TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE conversation_turn (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES session(id),
    turn_index INT,
    question TEXT,
    input_type TEXT CHECK (input_type IN ('voice_transcript','tapped_option')),
    raw_response TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE clinical_fact (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES session(id),
    ontology_path TEXT NOT NULL,
    value TEXT,
    source TEXT CHECK (source IN ('patient_interview','document','proxy_questionnaire')),
    source_reference UUID,
    confidence FLOAT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE document (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES session(id),
    doc_type TEXT,
    file_path TEXT,
    ocr_status TEXT CHECK (ocr_status IN ('pending','processing','done','failed')),
    uploaded_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE document_entity (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES document(id),
    entity_type TEXT,
    value JSONB,
    confidence FLOAT,
    extracted_date DATE,
    date_precision TEXT CHECK (date_precision IN ('exact','approximate','unknown')),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE timeline_event (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES session(id),
    source_fact_id UUID,
    source_document_entity_id UUID,
    event_date DATE,
    date_precision TEXT CHECK (date_precision IN ('exact','approximate','unknown')),
    description TEXT
);

CREATE TABLE clinical_flag (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES session(id),
    rule_id TEXT,
    message TEXT,
    priority TEXT CHECK (priority IN ('urgent','high','normal')),
    triggering_fact_ids UUID[],
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES session(id),
    subject TEXT,
    status TEXT CHECK (status IN ('consistent','conflict','out_of_range','missing','unverified')),
    contributing_fact_ids UUID[],
    physician_action TEXT CHECK (physician_action IN ('unset','verified','dismissed','escalated')) DEFAULT 'unset',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE clinical_summary (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES session(id),
    content JSONB,
    version INT DEFAULT 1,
    status TEXT CHECK (status IN ('draft','edited','approved')) DEFAULT 'draft',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE physician_review (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES session(id),
    physician_id TEXT,
    edits JSONB,
    decision TEXT CHECK (decision IN ('accept','amend','reject')),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE audit_event (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID,
    actor TEXT,
    action TEXT,
    entity TEXT,
    before_value JSONB,
    after_value JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
