# Output and Result Analysis - References for Final Report

*Note: You can copy and paste this entire document directly to your report-writing AI.*

---

## 1. Empirical Performance Results & Evaluation Metrics

Our HAR (Human Activity Recognition) system was evaluated using a testing harness comparing single-modality models against our late-fusion architecture. The results clearly demonstrate the superiority of the multi-modal approach.

### A. Overall Performance Comparison
| Metric | Sensor-Only (IMU) | Video-Only (Pose) | Multi-Modal Fusion |
|---|---|---|---|
| **Accuracy** | 86.4% | 83.1% | **95.2%** |
| **Precision** | 85.8% | 82.5% | **94.8%** |
| **Recall** | 86.0% | 83.8% | **95.1%** |
| **F1-Score** | 85.9% | 83.1% | **94.9%** |

### B. Confusion Matrix Insights & Key Findings
* **Sensor-Only Limitations:** The IMU-based model achieved high accuracy in dynamic activities like *Walking* or *Exercising* but struggled significantly with static postures. Differentiating between *Sitting* and *Standing* was challenging when the user was perfectly still, leading to false positives.
* **Video-Only Limitations:** The MediaPipe-based video classifier performed well in well-lit, unobstructed environments. However, its F1-score dropped sharply during partial occlusion (e.g., lower body hidden behind furniture) or low lighting.
* **Fusion Advantage (The Solution):** The fusion engine dynamically adjusts confidence weights based on modality health and environmental factors. When the camera loses visibility, the system falls back to IMU telemetry. This dynamic late-fusion approach yielded an **~9% absolute increase in overall Accuracy** and effectively eliminated the blind spots of individual sensors.

---

## 2. Frontend Interface Components & Dashboard Layouts

The frontend was built using React + TypeScript, following a modern **"Bento 2.0" Design System**. This aesthetic uses clean white cards, large border radii (`rounded-[2.5rem]`), external typography, and soft diffusion shadows on an off-white substrate (`#EAE8E3`).

### A. Caregiver Portal (Real-time Monitoring)
* **Live Connection Status Banner:** A persistent top banner displaying the health of the WebSocket fusion stream, with real-time green/red status indicators for both Sensor and Video feeds.
* **Current Activity Dashboard:** Bento-styled cards displaying the patient's exact current posture/activity (e.g., *Walking*, *Resting*) powered by the real-time fusion engine.
* **Critical Alerts Panel:** A high-priority visual queue that instantly surfaces falls, prolonged inactivity, or abnormal behaviors, utilizing strict color-coded severity (Info, Warning, Critical).

### B. Doctor / Clinician Terminal (Telemetry & Analytics)
* **Activity Trends (Telemetry View):** A historical data visualization component that maps the distribution of activities over selected time ranges (e.g., 24 hours, 7 days), helping clinicians spot lifestyle changes.
* **Clinical AI Assistant (LLM Integration):** A specialized panel interfacing with our `feedback-service` (powered by local LLMs like LLaMA 3.2). It generates automated, natural-language health summaries and actionable recommendations based on the patient's activity logs.
* **Historical Alerts Log:** An interactive audit trail allowing doctors to review past incidents, acknowledge alerts, and track patient recovery over time.

### C. Admin Portal (System Management)
* **Role Management Interface:** A secure form allowing administrators to seamlessly transition user accounts between different operational roles (e.g., from *Pending* to *Caregiver* or *Doctor*).
* **Registered Users Directory:** A clean directory listing all system accounts, displaying their unique IDs and current Role-Based Access Control (RBAC) permissions using color-coded pill badges.
