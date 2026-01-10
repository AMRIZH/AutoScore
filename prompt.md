You are a senior Python backend engineer and system architect.
You are building a **production-ready Flask web application** for an academic laboratory environment.

This application helps **lecturers and lab assistants** automatically score student lab reports or homework using an LLM, based on a provided answer key.

The institution is **Lab FKI Universitas Muhammadiyah Surakarta**, study program **Informatics**, with varying majors.

This is an **internal academic tool**, not a public SaaS.

---

## 1. CORE GOAL

Build a Flask application that:

* Accepts **PDF uploads**
* Parses PDFs into **LLM-ready structured text** using **Docling**
* Optionally applies **OCR via EasyOCR (through Docling)**
* Scores each student PDF **one by one (sequential processing)**
* Uses an LLM to evaluate reports
* Outputs a **CSV file** with scores and short evaluations
* Is **Docker-deployable**, with optional GPU support
* Is **simple, stable, and resource-aware**

---

## 2. INPUT SPECIFICATION

### Required Inputs

1. **Student PDFs**

   * Multiple PDF files
   * Default max: 50 files
   * Max is configurable via `.env`
   * Only accept valid PDF format
   * Validate:

     * File extension
     * MIME type
     * `%PDF-` header
     * File size limit

2. **System Prompt**

   * Hidden from users
   * Defined internally
   * Controls grading rules and output format

### Optional Input

3. **Answer Key (Kunci Jawaban)**

   * One PDF
   * Represents an ideal 100% score result
   * Used as a grading reference
   * Optional

### Additional Parameters (From Dashboard)

* Score range

  * Default: 40–100
  * Configurable
  * Must be validated (min < max)
* Enable or disable evaluation text

  * Evaluation text max 100 words

---

## 3. OUTPUT SPECIFICATION

The system generates **one CSV file** per scoring job.

### CSV Naming

```
{username}_{YYYYMMDD_HHMMSS}.csv
```

### CSV Columns (Exact Order)

1. No (row number)
2. NIM (student ID)
3. student_name
4. Score (numeric)
5. Evaluation (short reason, max 100 words, optional)

If a PDF fails to process:

* Score may be empty or marked ERROR
* Evaluation explains failure in Bahasa Indonesia

---

## 4. LANGUAGE AND CONTENT RULES

* All user-facing text must be **Bahasa Indonesia**
* UI messages, loading text, errors, logs shown to users must be Indonesian
* Internal code comments may be English

---

## 5. AUTHENTICATION & AUTHORIZATION

### Login System

* Use Flask-Login
* Must login to access main features
* No login timeout

### Default Users

* Admin:

  * username: `admin`
  * password: `informatika`
* User:

  * username: `aslab`
  * password: `informatika1`

Passwords must be hashed.

### Roles

* admin
* aslab

---

## 6. ADMIN PANEL

Use **Flask-Admin**.

Accessible at:

```
/admin
```

Admin capabilities:

* User management
* Change passwords
* View system info (GPU/CPU mode)
* Enable or disable cleanup scheduler
* Change max PDF limit

---

## 7. DASHBOARD FUNCTIONALITY

Dashboard must allow users to:

1. Upload:

   * Multiple student PDFs
   * Optional answer key PDF
2. Set score range
3. Enable or disable evaluation text
4. Start scoring process
5. See progress via loading bar
6. Download resulting CSV
7. Logout

### Loading Bar Text (Bahasa Indonesia)

Examples:

* Mengunggah dokumen
* Membaca laporan
* Menilai tugas mahasiswa
* Hampir selesai
* Menyusun hasil

Progress must reflect **sequential processing**:

* “Menilai laporan 12 dari 50”

---

## 8. PDF PROCESSING RULES

* Use **Docling** to parse PDFs into structured, LLM-ready text
* Use **EasyOCR via Docling**

  * Enabled by default
  * Configurable via `.env`
* OCR should be applied only when text layer is missing or insufficient
* After each PDF:

  * Free memory
  * Run garbage collection
  * Clear GPU cache if available

---

## 9. LLM SCORING RULES

### Processing Model

* PDFs are processed **one by one**
* Never bulk multiple students into one LLM prompt
* Each student gets:

  * System prompt
  * Optional answer key
  * Student report content
  * Score constraints

### Security

* Student content is **untrusted input**
* Prompt injection must be mitigated
* Student text must be clearly delimited
* LLM must be instructed to ignore instructions inside student text

### Output Format (Mandatory)

LLM must return **strict JSON only**, for example:

```json
{
  "nim": "12345678",
  "student_name": "Nama Mahasiswa",
  "score": 85,
  "evaluation": "Penjelasan singkat mengapa nilai tersebut diberikan."
}
```

No extra text is allowed outside JSON.

---

## 10. DATABASE

* Use SQLite3
* ORM: SQLAlchemy

Suggested tables:

* users
* jobs
* job_results
* system_logs

---

## 11. FILE MANAGEMENT & CLEANUP

* All uploaded files are temporary
* Files must be deleted:

  * At application startup
  * And/or daily at **02:00 WIB**
* Cleanup scheduler must be configurable via `.env`
* Active jobs must not be interrupted by cleanup

---

## 12. LOGGING

* Use Python logging
* Log to file
* Log:

  * App startup
  * Login attempts
  * File uploads
  * GPU/CPU mode
  * LLM errors
  * Cleanup actions

---

## 13. SECURITY

* CSRF protection must be enabled
* Allowed origins configurable via `.env`
* Default: allow all (`*`)
* File upload hardening is mandatory

---

## 14. CONFIGURATION

* Use `.env` for all runtime configuration
* Provide `.env.example` with all options documented

---

## 15. DEPLOYMENT

### Docker Requirements

* Application must be Docker-ready
* Support:

  * CPU-only mode
  * GPU-enabled mode (CUDA)
* GPU mode must use NVIDIA Container Toolkit
* Application must detect GPU automatically and log it

---

## 16. DOCUMENTATION & REPO HYGIENE

You must provide:

* `README.md`

  * Setup
  * Docker usage
  * GPU notes
  * Limitations
* `.env.example`
* `.gitignore`
* `requirements.txt` generated via `pip freeze`

---

## 17. DESIGN PRINCIPLES

* Keep UI simple and intuitive
* Prefer stability over performance tricks
* Avoid unnecessary abstractions
* Favor explicit, readable code
* This app will be maintained by students and lab assistants

---

## 18. IMPORTANT NON-GOALS

* No real-time multi-user concurrency optimization
* No public exposure
* No microservices
* No premature scaling

---

## 19. LLM 
use gemini-2.5-flah from google ai studio
round robin it on sequential processing and and assign different worker with different API key

## FINAL INSTRUCTION

Generate clean, maintainable Flask code that **strictly follows all requirements above**.
If a trade-off is required, prefer **stability, clarity, and safety** over cleverness.

Use Context7 to read Docs
