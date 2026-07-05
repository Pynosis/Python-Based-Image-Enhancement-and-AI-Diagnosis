"""
pages/history.py
Shows past scans and diagnoses for doctor/radiologist.
Researcher cannot access this page.
"""

import streamlit as st
import json
from datetime import datetime
from modules.auth import require_auth, require_role, has_permission, get_current_user
from modules.database import execute_query
from modules.audit import log_action, REPORT_DOWNLOADED
from modules.report import generate_report
from modules.encryption import decrypt_file_from_disk
from PIL import Image
import io


def get_scan_history(user_id: int) -> list:
    return execute_query(
        """SELECT 
            s.id as scan_id,
            s.original_filename,
            s.file_format,
            s.enhancement_applied,
            s.uploaded_at,
            d.id as diagnosis_id,
            d.predicted_class,
            d.confidence_score,
            d.class_probabilities,
            d.requires_human_review,
            d.inference_time_ms,
            d.created_at as diagnosed_at,
            r.report_uuid
            FROM scans s
            LEFT JOIN diagnoses d ON d.scan_id = s.id
            LEFT JOIN reports r ON r.diagnosis_id = d.id
            WHERE s.user_id = %s
            ORDER BY s.uploaded_at DESC""",
        (user_id,),
        fetch_all=True
    )


def show():
    require_auth()
    require_role("doctor", "radiologist")

    user = get_current_user()

    st.markdown("""
        <style>
        .history-title {
            font-size: 24px;
            font-weight: 700;
            color: #0d1b2a;
            margin-bottom: 4px;
        }
        .badge {
            display: inline-block;
            padding: 2px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
        }
        [data-testid="stMetric"] {
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            padding: 12px;
        }
        </style>
    """, unsafe_allow_html=True)

    # ── Header ─────────────────────────────────────────────────
    st.markdown('<div class="history-title">📋 Scan History</div>',
                unsafe_allow_html=True)
    st.markdown(f"**{user['full_name']}** ({user['role'].capitalize()})")
    st.divider()

    # ── Navigation ─────────────────────────────────────────────
    col_nav1, col_nav2, col_nav3 = st.columns([1, 1, 4])
    with col_nav1:
        if st.button("📤 Upload New", use_container_width=True):
            st.session_state.page = "upload"
            st.rerun()
    with col_nav2:
        if st.button("🚪 Logout", use_container_width=True):
            from modules.auth import logout
            logout()

    st.divider()

    # ── Fetch history ──────────────────────────────────────────
    records = get_scan_history(user["user_id"])

    if not records:
        st.info("No scan history found. Upload a scan to get started.")
        return

    # ── Summary stats ──────────────────────────────────────────
    total_scans     = len(records)
    total_diagnoses = sum(1 for r in records if r["diagnosis_id"])
    total_reports   = sum(1 for r in records if r["report_uuid"])
    review_needed   = sum(1 for r in records if r["requires_human_review"])

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Scans", total_scans)
    with col2:
        st.metric("Diagnoses Run", total_diagnoses)
    with col3:
        st.metric("Reports Generated", total_reports)
    with col4:
        st.metric("⚠ Review Needed", review_needed)

    st.divider()

    # ── Filter ─────────────────────────────────────────────────
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filter_class = st.selectbox(
            "Filter by diagnosis",
            ["All", "glioma", "meningioma", "notumor", "pituitary", "Not diagnosed"]
        )
    with col_f2:
        filter_review = st.checkbox("Show only scans needing human review")

    # apply filters
    filtered = records
    if filter_class != "All":
        if filter_class == "Not diagnosed":
            filtered = [r for r in filtered if not r["diagnosis_id"]]
        else:
            filtered = [r for r in filtered if r["predicted_class"] == filter_class]
    if filter_review:
        filtered = [r for r in filtered if r["requires_human_review"]]

    st.markdown(f"Showing **{len(filtered)}** records")
    st.divider()

    # ── Records ────────────────────────────────────────────────
    for i, record in enumerate(filtered):
        # build expander title
        date_str = record["uploaded_at"].strftime("%Y-%m-%d %H:%M") if record["uploaded_at"] else "Unknown"

        if record["predicted_class"]:
            status_icon = "🔴" if record["requires_human_review"] else "🟢"
            title = f"{status_icon} {record['original_filename']} — {record['predicted_class'].capitalize()} ({record['confidence_score']}%) — {date_str}"
        else:
            title = f"📁 {record['original_filename']} — No diagnosis — {date_str}"

        with st.expander(title):
            col_a, col_b = st.columns(2)

            # ── Scan info ──────────────────────────────────────
            with col_a:
                st.markdown("**Scan Details**")
                st.write(f"**File:** {record['original_filename']}")
                st.write(f"**Format:** {record['file_format'].upper()}")
                st.write(f"**Uploaded:** {date_str}")
                if record["enhancement_applied"]:
                    st.write(f"**Enhanced:** {record['enhancement_applied']}")
                else:
                    st.write("**Enhanced:** No")

            # ── Diagnosis info ─────────────────────────────────
            with col_b:
                if record["diagnosis_id"]:
                    st.markdown("**Diagnosis Details**")
                    st.write(f"**Result:** {record['predicted_class'].capitalize()}")
                    st.write(f"**Confidence:** {record['confidence_score']}%")
                    st.write(f"**Diagnosed:** {record['diagnosed_at'].strftime('%Y-%m-%d %H:%M') if record['diagnosed_at'] else 'Unknown'}")
                    st.write(f"**Inference Time:** {record['inference_time_ms']}ms")

                    if record["requires_human_review"]:
                        st.warning("⚠ Human review required")

                    if record["report_uuid"]:
                        st.write(f"**Report ID:** `{record['report_uuid'][:8]}...`")
                else:
                    st.info("No diagnosis run for this scan.")

            # ── Probability breakdown ──────────────────────────
            if record["class_probabilities"]:
                st.markdown("**Class Probabilities**")
                try:
                    probs = json.loads(record["class_probabilities"])
                    for class_name, prob in sorted(probs.items(), key=lambda x: x[1], reverse=True):
                        is_predicted = class_name == record["predicted_class"]
                        label = f"{'✅ ' if is_predicted else ''}{class_name.capitalize()}"
                        st.progress(prob / 100, text=f"{label}: {prob}%")
                except:
                    pass

            st.markdown("---")

            # ── Actions ────────────────────────────────────────
            col_act1, col_act2, col_act3 = st.columns(3)

            # rediagnose button
            with col_act1:
                if st.button("🔄 Rediagnose",
                             key=f"rediag_{record['scan_id']}_{i}",
                             use_container_width=True):
                    st.session_state["rediagnose_scan_id"] = record["scan_id"]
                    st.session_state.page = "upload"
                    st.rerun()

            # regenerate report
            with col_act2:
                if record["diagnosis_id"] and has_permission("can_generate_report"):
                    if st.button("📄 Get Report",
                                 key=f"report_{record['diagnosis_id']}_{i}",
                                 use_container_width=True):
                        with st.spinner("Generating report..."):
                            # build result dict from DB record
                            result_dict = {
                                "predicted_class":      record["predicted_class"],
                                "display_name":         record["predicted_class"].capitalize(),
                                "confidence":           float(record["confidence_score"]),
                                "all_probabilities":    json.loads(record["class_probabilities"] or "{}"),
                                "requires_human_review": bool(record["requires_human_review"]),
                                "inference_time_ms":    record["inference_time_ms"] or 0,
                            }

                            # create blank heatmap placeholder if no image available
                            placeholder = Image.new("RGB", (224, 224), color=(30, 30, 30))

                            pdf_bytes, report_uuid = generate_report(
                                doctor_name=user["full_name"],
                                doctor_role=user["role"],
                                diagnosis_result=result_dict,
                                scan_image=placeholder,
                                heatmap_image=placeholder,
                                report_uuid=record["report_uuid"]
                            )

                        st.session_state[f"hist_pdf_{i}"]  = pdf_bytes
                        st.session_state[f"hist_uuid_{i}"] = report_uuid

                        log_action(user["user_id"], user["username"], user["role"],
                                   REPORT_DOWNLOADED,
                                   f"Re-downloaded report from history: {report_uuid}")
                        st.rerun()

            # download if generated
            if st.session_state.get(f"hist_pdf_{i}"):
                with col_act3:
                    st.download_button(
                        label="⬇️ Download",
                        data=st.session_state[f"hist_pdf_{i}"],
                        file_name=f"report_{st.session_state.get(f'hist_uuid_{i}', 'report')[:8]}.pdf",
                        mime="application/pdf",
                        key=f"dl_{i}",
                        use_container_width=True
                    )
