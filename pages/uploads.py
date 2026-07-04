"""
pages/uploads.py
Main scan upload page — handles both enhancement and diagnosis flows.
Doctor/Radiologist: results saved to DB, report available
Researcher: session-only, no DB writes, no report
"""

import streamlit as st
import os
import hashlib
import json
import io
from PIL import Image
from datetime import datetime
from modules.auth import require_auth, require_role, has_permission, get_current_user
from modules.audit import log_action, SCAN_UPLOADED, SCAN_ENHANCED, DIAGNOSIS_RUN, REPORT_GENERATED
from modules.brain_validator import validate_file_format, validate_image_for_diagnosis
from modules.dicom_handler import read_dicom, convert_to_pil
from modules.enhancement import apply_enhancements
from modules.ai_model import predict
from modules.gradcam import generate_gradcam, get_class_idx
from modules.encryption import encrypt_file_to_disk
from modules.database import execute_write, execute_query
from modules.report import generate_report


def show():
    require_auth()
    require_role("doctor", "radiologist", "researcher")

    user = get_current_user()
    role = user["role"]
    is_researcher = role == "researcher"

    st.markdown("""
        <style>
        .upload-title {
            font-size: 26px;
            font-weight: 700;
            color: #0d1b2a;
            margin-bottom: 4px;
        }
        .disclaimer {
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            border-radius: 8px;
            padding: 12px 16px;
            font-size: 13px;
            color: #856404;
            margin: 12px 0;
        }
        .human-review {
            background: #f8d7da;
            border-left: 4px solid #dc3545;
            border-radius: 8px;
            padding: 12px 16px;
            font-size: 13px;
            color: #721c24;
            margin: 12px 0;
        }
        </style>
    """, unsafe_allow_html=True)

    # ── Header ─────────────────────────────────────────────────
    st.markdown('<div class="upload-title">🧠 Scan Upload</div>', unsafe_allow_html=True)
    st.markdown(f"Logged in as **{user['full_name']}** ({role.capitalize()})")

    if is_researcher:
        st.info("🔬 Researcher mode — results are session-only and will not be stored.")

    st.divider()

    # ── Navigation ─────────────────────────────────────────────
    col_nav1, col_nav2, col_nav3 = st.columns([1, 1, 4])
    with col_nav1:
        if has_permission("can_view_history"):
            if st.button("📋 History", use_container_width=True):
                st.session_state.page = "history"
                st.rerun()
    with col_nav2:
        if st.button("🚪 Logout", use_container_width=True):
            from modules.auth import logout
            logout()

    st.divider()

    # ── File upload ────────────────────────────────────────────
    st.markdown("### Step 1 — Upload Scan")
    uploaded_file = st.file_uploader(
        "Accepted formats: DICOM (.dcm), PNG, JPG",
        type=["dcm", "dicom", "png", "jpg", "jpeg"],
        help="Upload a medical scan to enhance or diagnose"
    )

    if not uploaded_file:
        st.info("Upload a scan file to get started.")
        return

    # ── Validate format ────────────────────────────────────────
    is_valid_format, format_msg, file_format = validate_file_format(uploaded_file.name)
    if not is_valid_format:
        st.error(format_msg)
        return

    file_bytes = uploaded_file.read()
    file_hash  = hashlib.sha256(file_bytes).hexdigest()

    dicom_metadata = None
    if file_format == "dicom":
        dicom_result   = read_dicom(file_bytes)
        image          = dicom_result["image"]
        dicom_metadata = dicom_result["metadata"]
    else:
        image = convert_to_pil(file_bytes, file_format)

    st.success(f"✅ File uploaded: **{uploaded_file.name}** ({file_format.upper()})")
    st.markdown("**Original Scan:**")
    st.image(image, use_container_width=True)

    log_action(user["user_id"], user["username"], role, SCAN_UPLOADED,
            f"Uploaded {file_format.upper()} file: {uploaded_file.name}")

    st.divider()

    # ── Choose action ──────────────────────────────────────────
    st.markdown("### Step 2 — Choose Action")
    action = st.radio(
        "What would you like to do?",
        ["🔧 Image Enhancement", "🧠 AI Diagnosis"],
        horizontal=True
    )

    st.divider()

    # ══════════════════════════════════════════════════════════
    # PATH A — IMAGE ENHANCEMENT
    # ══════════════════════════════════════════════════════════
    if action == "🔧 Image Enhancement":
        st.markdown("### Step 3 — Select Enhancement Options")
        st.caption("You can select multiple options.")

        col1, col2 = st.columns(2)
        with col1:
            blur_flag     = st.checkbox("🔍 Remove Blur (Unsharp Masking)")
            noise_flag    = st.checkbox("🌫️ Remove Noise (Non-local Means)")
        with col2:
            artifact_flag = st.checkbox("⚡ Remove Artifacts (Morphological)")
            clahe_flag    = st.checkbox("✨ Auto Enhance (CLAHE)")

        if not any([blur_flag, noise_flag, artifact_flag, clahe_flag]):
            st.warning("Please select at least one enhancement option.")
            return

        if st.button("Apply Enhancement", use_container_width=True, type="primary"):
            with st.spinner("Applying enhancements..."):
                enhanced_image, applied = apply_enhancements(
                    image,
                    remove_blur_flag=blur_flag,
                    remove_noise_flag=noise_flag,
                    remove_artifacts_flag=artifact_flag,
                    auto_enhance_flag=clahe_flag,
                )

            st.success(f"✅ Applied: {', '.join(applied)}")

            st.markdown("### Before vs After")
            col_before, col_after = st.columns(2)
            with col_before:
                st.markdown("**Original**")
                st.image(image, use_container_width=True)
            with col_after:
                st.markdown("**Enhanced**")
                st.image(enhanced_image, use_container_width=True)

            st.session_state["enhanced_image"]      = enhanced_image
            st.session_state["enhancement_applied"] = applied

            if not is_researcher:
                os.makedirs("uploads/scans", exist_ok=True)
                save_path = f"uploads/scans/{user['username']}_{file_hash[:8]}.enc"
                encrypt_file_to_disk(file_bytes, save_path)
                scan_id = execute_write(
                    """INSERT INTO scans
                    (user_id, original_filename, file_format,
                    encrypted_file_path, file_hash, enhancement_applied)
                    VALUES (%s, %s, %s, %s, %s, %s)""",
                    (user["user_id"], uploaded_file.name, file_format,
                    save_path, file_hash, ",".join(applied))
                )
                st.session_state["current_scan_id"] = scan_id

            log_action(user["user_id"], user["username"], role, SCAN_ENHANCED,
                    f"Applied: {', '.join(applied)}")

            buf = io.BytesIO()
            enhanced_image.save(buf, format="PNG")
            st.download_button(
                label="⬇️ Download Enhanced Image",
                data=buf.getvalue(),
                file_name=f"enhanced_{uploaded_file.name.split('.')[0]}.png",
                mime="image/png"
            )

    # ══════════════════════════════════════════════════════════
    # PATH B — AI DIAGNOSIS
    # ══════════════════════════════════════════════════════════
    elif action == "🧠 AI Diagnosis":
        st.markdown("### Step 3 — AI Brain Tumor Diagnosis")

        is_valid_scan, scan_msg = validate_image_for_diagnosis(
            image, file_format, dicom_metadata
        )
        if not is_valid_scan:
            st.error(f"❌ {scan_msg}")
            st.warning("The AI diagnosis model only accepts brain MRI scans.")
            return

        diagnosis_image = st.session_state.get("enhanced_image", image)
        if "enhanced_image" in st.session_state:
            st.info("🔧 Using enhanced image for diagnosis.")

        st.markdown("""
            <div class="disclaimer">
            ⚠️ <strong>Disclaimer:</strong> This AI diagnosis is assistive only and
            is NOT a substitute for clinical judgment by a qualified medical professional.
            </div>
        """, unsafe_allow_html=True)

        if st.button("Run AI Diagnosis", use_container_width=True, type="primary"):
            with st.spinner("Running DenseNet121 inference..."):
                result = predict(diagnosis_image)

            with st.spinner("Generating Grad-CAM heatmap..."):
                class_idx = get_class_idx(result["predicted_class"])
                heatmap   = generate_gradcam(diagnosis_image, class_idx)

            # store in session immediately
            st.session_state["current_result"]  = result
            st.session_state["current_heatmap"] = heatmap
            st.session_state["current_image"]   = diagnosis_image

            # save to DB for doctor/radiologist
            if not is_researcher:
                if "current_scan_id" not in st.session_state:
                    os.makedirs("uploads/scans", exist_ok=True)
                    save_path = f"uploads/scans/{user['username']}_{file_hash[:8]}.enc"
                    encrypt_file_to_disk(file_bytes, save_path)
                    scan_id = execute_write(
                        """INSERT INTO scans
                        (user_id, original_filename, file_format,
                            encrypted_file_path, file_hash)
                        VALUES (%s, %s, %s, %s, %s)""",
                        (user["user_id"], uploaded_file.name, file_format,
                        save_path, file_hash)
                    )
                    st.session_state["current_scan_id"] = scan_id

                diagnosis_id = execute_write(
                    """INSERT INTO diagnoses
                    (scan_id, user_id, predicted_class, confidence_score,
                    class_probabilities, requires_human_review,
                    model_name, model_version, inference_time_ms)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        st.session_state["current_scan_id"],
                        user["user_id"],
                        result["predicted_class"],
                        result["confidence"],
                        json.dumps(result["all_probabilities"]),
                        result["requires_human_review"],
                        "DenseNet121", "v1.0",
                        result["inference_time_ms"]
                    )
                )
                st.session_state["current_diagnosis_id"] = diagnosis_id

                log_action(user["user_id"], user["username"], role, DIAGNOSIS_RUN,
                        f"Diagnosis: {result['predicted_class']} ({result['confidence']}%)")

        # ── Show results if available in session ───────────────
        result            = st.session_state.get("current_result")
        heatmap           = st.session_state.get("current_heatmap")
        diagnosis_image_s = st.session_state.get("current_image")
        diagnosis_id      = st.session_state.get("current_diagnosis_id")

        if result and heatmap and diagnosis_image_s:
            st.markdown("### Diagnosis Results")

            if result["requires_human_review"]:
                st.markdown("""
                    <div class="human-review">
                    🔴 <strong>Human Interpretation Required:</strong>
                    Confidence below 70% — must be reviewed by a clinician.
                    </div>
                """, unsafe_allow_html=True)

            col_r1, col_r2, col_r3 = st.columns(3)
            with col_r1:
                st.metric("Prediction", result["display_name"])
            with col_r2:
                st.metric("Confidence", f"{result['confidence']}%")
            with col_r3:
                st.metric("Inference Time", f"{result['inference_time_ms']}ms")

            col_scan, col_heat = st.columns(2)
            with col_scan:
                st.markdown("**Original Scan**")
                st.image(diagnosis_image_s, use_container_width=True)
            with col_heat:
                st.markdown("**Grad-CAM Heatmap**")
                st.image(heatmap, use_container_width=True)
                st.caption("Red = high attention | Blue = low attention")

            st.markdown("### Class Probabilities")
            probs = result["all_probabilities"]
            for class_name, prob in sorted(probs.items(), key=lambda x: x[1], reverse=True):
                is_predicted = class_name == result["predicted_class"]
                label = f"{'✅ ' if is_predicted else ''}{class_name.capitalize()}"
                st.progress(prob / 100, text=f"{label}: {prob}%")

            if is_researcher:
                with st.expander("🔬 Model Information (Researcher View)"):
                    st.write(f"**Model:** DenseNet121")
                    st.write(f"**Inference Time:** {result['inference_time_ms']}ms")
                    st.write(f"**Input Size:** 224x224")
                    st.write(f"**Classes:** glioma, meningioma, notumor, pituitary")
                    st.write(f"**Confidence Threshold:** 70%")
                    st.json(result["all_probabilities"])

            st.markdown("""
                <div class="disclaimer">
                ⚠️ <strong>AI Disclaimer:</strong> Results generated by DenseNet121
                trained on Kaggle brain tumor MRI dataset (94.38% accuracy).
                This tool is for assistive purposes only.
                </div>
            """, unsafe_allow_html=True)

            # ── Report generation (doctor/radiologist only) ────
            if has_permission("can_generate_report"):
                st.divider()
                st.markdown("### 📄 Generate Report")

                # show download button first if PDF already exists
                if st.session_state.get("current_pdf"):
                    st.success(f"✅ Report ready! ID: `{st.session_state.get('current_report_uuid', '')}`")
                    st.download_button(
                        label="⬇️ Download PDF Report",
                        data=st.session_state["current_pdf"],
                        file_name=f"painosis_report_{st.session_state.get('current_report_uuid', 'report')[:8]}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                    if st.button("🔄 Regenerate Report"):
                        st.session_state.pop("current_pdf", None)
                        st.session_state.pop("current_report_uuid", None)
                        st.rerun()
                else:
                    if st.button("📄 Generate PDF Report",
                                use_container_width=True,
                                type="primary"):
                        with st.spinner("Generating PDF..."):
                            pdf_bytes, report_uuid = generate_report(
                                doctor_name=user["full_name"],
                                doctor_role=user["role"],
                                diagnosis_result=result,
                                scan_image=diagnosis_image_s,
                                heatmap_image=heatmap,
                            )

                        if diagnosis_id:
                            existing = execute_query(
                                "SELECT report_uuid FROM reports WHERE diagnosis_id = %s",
                                (diagnosis_id,),
                                fetch_one=True
                            )
                            if not existing:
                                execute_write(
                                    """INSERT INTO reports
                                        (diagnosis_id, report_uuid, generated_by, generated_at)
                                        VALUES (%s, %s, %s, NOW())""",
                                    (diagnosis_id, report_uuid, user["user_id"])
                                )

                        log_action(user["user_id"], user["username"], role,
                                    REPORT_GENERATED, f"Report UUID: {report_uuid}")

                        st.session_state["current_pdf"]         = pdf_bytes
                        st.session_state["current_report_uuid"] = report_uuid
                        st.rerun()

            # ── Rediagnosis ────────────────────────────────────
            st.divider()
            st.markdown("### Rediagnosis")
            if st.button("🔄 Rediagnose Full Scan", use_container_width=True):
                for key in ["current_result", "current_heatmap", "current_image",
                            "current_diagnosis_id", "current_pdf", "current_report_uuid",
                            "current_scan_id"]:
                    st.session_state.pop(key, None)
                st.rerun()