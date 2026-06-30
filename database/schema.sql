CREATE DATABASE IF NOT EXISTS painosis
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE painosis;

CREATE TABLE users (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    username            VARCHAR(50)  NOT NULL UNIQUE,
    email               VARCHAR(120) NOT NULL UNIQUE,
    password_hash       VARCHAR(255) NOT NULL,
    full_name           VARCHAR(120) NOT NULL,
    role                ENUM('admin', 'doctor', 'radiologist', 'researcher') NOT NULL,

    -- PMDC verification (doctor / radiologist only)
    pmdc_license_number     VARCHAR(50)  NULL,
    pmdc_license_file_path  VARCHAR(255) NULL,   -- encrypted file stored on disk, path saved here
    is_approved              BOOLEAN NOT NULL DEFAULT FALSE,
    rejection_reason         VARCHAR(255) NULL,
    approved_by               INT NULL,            -- admin user_id who approved/rejected
    approved_at               DATETIME NULL,

    -- account status
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,

    -- session management (strict, single active session per user)
    session_token        VARCHAR(500) NULL,
    last_login            DATETIME NULL,
    last_activity          DATETIME NULL,

    created_at           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_users_approved_by
        FOREIGN KEY (approved_by) REFERENCES users(id)
        ON DELETE SET NULL,

    INDEX idx_users_role (role),
    INDEX idx_users_approval_status (role, is_approved),
    INDEX idx_users_active (is_active)
);

-- Researchers don't need PMDC, doctors/radiologists do.
-- This is enforced in application code (not DB constraint) since
-- MySQL CHECK constraints with ENUM conditions get messy — keep
-- the validation in auth.py at registration time.


-- ------------------------------------------------------------
-- 2. AUDIT LOGS
-- Tracks every significant action by every user.
-- Survives user deletion via username_snapshot + SET NULL.
-- Admin-only access, enforced in application layer.
-- ------------------------------------------------------------
CREATE TABLE audit_logs (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    user_id           INT NULL,                  -- nullable: user may be deleted later
    username_snapshot VARCHAR(50) NOT NULL,       -- preserved even after user deletion
    role_snapshot     VARCHAR(20) NOT NULL,       -- role at time of action
    action            VARCHAR(50) NOT NULL,       -- e.g. LOGIN_SUCCESS, DIAGNOSIS_RUN, REPORT_DOWNLOADED
    detail            TEXT NULL,                  -- free-text context, never raw scan/patient data
    ip_address        VARCHAR(45) NULL,           -- supports IPv6
    timestamp         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_audit_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE SET NULL,

    INDEX idx_audit_user (user_id),
    INDEX idx_audit_action (action),
    INDEX idx_audit_timestamp (timestamp)
);


-- ------------------------------------------------------------
-- 3. SCANS
-- Only doctor/radiologist uploads are persisted.
-- Researcher uploads are session-only and NEVER written here.
-- All file paths point to encrypted files on disk; DB never
-- stores raw pixel data.
-- ------------------------------------------------------------
CREATE TABLE scans (
    id                    INT AUTO_INCREMENT PRIMARY KEY,
    user_id               INT NOT NULL,
    original_filename     VARCHAR(255) NOT NULL,
    file_format           ENUM('dicom', 'png', 'jpg', 'jpeg') NOT NULL,
    encrypted_file_path   VARCHAR(255) NOT NULL,   -- Fernet-encrypted file on disk
    file_hash             VARCHAR(64) NOT NULL,     -- SHA-256, for integrity checks

    -- enhancement metadata (nullable — not every scan is enhanced)
    enhancement_applied   SET('blur_removal','noise_removal','artifact_removal','auto_enhance') NULL,
    enhanced_file_path    VARCHAR(255) NULL,

    -- DICOM-specific metadata (NULL for png/jpg)
    dicom_modality        VARCHAR(10) NULL,         -- e.g. 'MR'
    dicom_body_part       VARCHAR(50) NULL,         -- e.g. 'BRAIN'

    uploaded_at            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_scans_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE,

    INDEX idx_scans_user (user_id),
    INDEX idx_scans_uploaded (uploaded_at)
);


-- ------------------------------------------------------------
-- 4. DIAGNOSES
-- One row per inference run (including rediagnosis — each
-- rediagnosis creates a NEW row, never overwrites).
-- Only linked to scans table, so researcher diagnoses
-- (which have no scan row) never reach this table either.
-- ------------------------------------------------------------
CREATE TABLE diagnoses (
    id                      INT AUTO_INCREMENT PRIMARY KEY,
    scan_id                 INT NOT NULL,
    user_id                 INT NOT NULL,            -- redundant but useful for fast filtering

    predicted_class         ENUM('glioma','meningioma','pituitary','no_tumor') NOT NULL,
    confidence_score         DECIMAL(5,2) NOT NULL,    -- e.g. 87.34
    class_probabilities       JSON NOT NULL,             -- full softmax breakdown, all 4 classes
    requires_human_review     BOOLEAN NOT NULL DEFAULT FALSE,  -- TRUE if confidence < 70%

    gradcam_file_path        VARCHAR(255) NULL,

    -- ROI rediagnosis support
    is_roi_diagnosis          BOOLEAN NOT NULL DEFAULT FALSE,
    roi_x1 INT NULL, roi_y1 INT NULL, roi_x2 INT NULL, roi_y2 INT NULL,
    parent_diagnosis_id        INT NULL,    -- links ROI rediagnosis back to the original full-scan diagnosis

    model_name                VARCHAR(50) NOT NULL DEFAULT 'DenseNet121',
    model_version              VARCHAR(20) NOT NULL DEFAULT 'v1.0',
    inference_time_ms           INT NULL,

    created_at                 DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_diagnoses_scan
        FOREIGN KEY (scan_id) REFERENCES scans(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_diagnoses_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_diagnoses_parent
        FOREIGN KEY (parent_diagnosis_id) REFERENCES diagnoses(id)
        ON DELETE SET NULL,

    INDEX idx_diagnoses_scan (scan_id),
    INDEX idx_diagnoses_user (user_id),
    INDEX idx_diagnoses_confidence (confidence_score)
);


-- ------------------------------------------------------------
-- 5. REPORTS
-- Metadata only — the actual PDF is generated on-demand in
-- memory and streamed via st.download_button. We never store
-- a plaintext PDF on disk. This table just proves a report
-- WAS generated, by whom, when, and gives it a trackable UUID.
-- ------------------------------------------------------------
CREATE TABLE reports (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    diagnosis_id      INT NOT NULL,
    report_uuid       CHAR(36) NOT NULL UNIQUE,    -- the trackable ID, also embedded as QR in the PDF
    generated_by      INT NOT NULL,                 -- doctor/radiologist user_id
    generated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_reports_diagnosis
        FOREIGN KEY (diagnosis_id) REFERENCES diagnoses(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_reports_user
        FOREIGN KEY (generated_by) REFERENCES users(id)
        ON DELETE CASCADE,

    INDEX idx_reports_uuid (report_uuid),
    INDEX idx_reports_user (generated_by)
);


-- ------------------------------------------------------------
-- Seed reference: roles allowed without PMDC are enforced in
-- application code at registration (auth.py), not here.
-- ------------------------------------------------------------
