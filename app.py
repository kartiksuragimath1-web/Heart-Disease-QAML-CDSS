from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    send_from_directory
)

import os
import uuid
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

from src.prediction import predict_heart_disease
from src.extraction_service import save_extracted_features
from src.prediction_service import predict_from_extraction

from auth import register_patient, authenticate_user
from database import get_db_connection

app = Flask(__name__)
def create_system_log(action, description, user_id=None):
    connection = get_db_connection()

    if connection is None:
        return

    cursor = connection.cursor()

    try:
        ip_address = request.remote_addr

        cursor.execute("""
            INSERT INTO system_logs
            (user_id, action, description, ip_address)
            VALUES (%s, %s, %s, %s)
        """, (
            user_id,
            action,
            description,
            ip_address
        ))

        connection.commit()

    except Exception as e:
        connection.rollback()
        print("System log error:", e)

    finally:
        cursor.close()
        connection.close()
# ============================================================
# FILE UPLOAD CONFIGURATION
# ============================================================

BASE_UPLOAD_FOLDER = "uploads"

UPLOAD_FOLDERS = {
    "ECG": "uploads/ecg",
    "BLOOD_TEST": "uploads/blood_reports",
    "ECHO": "uploads/echo",
    "STRESS_TEST": "uploads/stress_test",
    "OTHER": "uploads/other"
}

ALLOWED_EXTENSIONS = {"pdf"}

def allowed_file(filename):
    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )



# Required for Flask sessions

app.secret_key = os.getenv("FLASK_SECRET_KEY")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():
    return render_template("index.html")

# ============================================================
# SEPARATE ROLE AUTHENTICATION
# ============================================================


# ============================================================
# PATIENT LOGIN
# ============================================================

@app.route("/patient/login", methods=["GET", "POST"])
def patient_login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter email and password.", "danger")
            return redirect(url_for("patient_login"))

        connection = get_db_connection()

        if connection is None:
            flash("Database connection failed.", "danger")
            return redirect(url_for("patient_login"))

        cursor = connection.cursor(dictionary=True)

        try:

            cursor.execute(
                """
                SELECT *
                FROM users
                WHERE email = %s
                AND role = 'patient'
                AND is_active = 1
                LIMIT 1
                """,
                (email,)
            )

            user = cursor.fetchone()

            if user and check_password_hash(
                user["password_hash"],
                password
            ):

                session.clear()

                session["user_id"] = user["user_id"]
                session["full_name"] = user["full_name"]
                session["email"] = user["email"]
                session["role"] = "patient"

                flash("Patient login successful.", "success")

                return redirect(
                    url_for("patient_dashboard")
                )

            flash(
                "Invalid patient email or password.",
                "danger"
            )

        except Exception as e:

            print("Patient login error:", e)

            flash(
                "Unable to process login.",
                "danger"
            )

        finally:

            cursor.close()
            connection.close()

    return render_template("patient_login.html")


# ============================================================
# PATIENT REGISTER
# ============================================================

@app.route("/patient/register", methods=["GET", "POST"])
def patient_register():

    if request.method == "POST":

        full_name = request.form.get(
            "full_name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        if not full_name or not email or not password:

            flash(
                "Please fill all required fields.",
                "danger"
            )

            return redirect(
                url_for("patient_register")
            )

        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "danger"
            )

            return redirect(
                url_for("patient_register")
            )

        if len(password) < 6:

            flash(
                "Password must contain at least 6 characters.",
                "danger"
            )

            return redirect(
                url_for("patient_register")
            )

        connection = get_db_connection()

        if connection is None:

            flash(
                "Database connection failed.",
                "danger"
            )

            return redirect(
                url_for("patient_register")
            )

        cursor = connection.cursor(dictionary=True)

        try:

            cursor.execute(
                """
                SELECT user_id
                FROM users
                WHERE email = %s
                LIMIT 1
                """,
                (email,)
            )

            existing_user = cursor.fetchone()

            if existing_user:

                flash(
                    "An account with this email already exists.",
                    "danger"
                )

                return redirect(
                    url_for("patient_register")
                )

            password_hash = generate_password_hash(
                password
            )

            cursor.execute(
                """
                INSERT INTO users
                (
                    full_name,
                    email,
                    password_hash,
                    phone,
                    role,
                    is_active
                )
                VALUES
                (%s, %s, %s, %s, 'patient', 1)
                """,
                (
                    full_name,
                    email,
                    password_hash,
                    phone
                )
            )

            connection.commit()

            flash(
                "Patient account created successfully. Please login.",
                "success"
            )

            return redirect(
                url_for("patient_login")
            )

        except Exception as e:

            connection.rollback()

            print("Patient registration error:", e)

            flash(
                "Unable to create patient account.",
                "danger"
            )

        finally:

            cursor.close()
            connection.close()

    return render_template("patient_register.html")


# ============================================================
# DOCTOR LOGIN
# ============================================================

@app.route("/doctor/login", methods=["GET", "POST"])
def doctor_login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        if not email or not password:

            flash(
                "Please enter email and password.",
                "danger"
            )

            return redirect(
                url_for("doctor_login")
            )

        connection = get_db_connection()

        if connection is None:

            flash(
                "Database connection failed.",
                "danger"
            )

            return redirect(
                url_for("doctor_login")
            )

        cursor = connection.cursor(dictionary=True)

        try:

            cursor.execute(
                """
                SELECT
                    u.*,
                    d.verification_status
                FROM users u
                LEFT JOIN doctors d
                    ON u.user_id = d.user_id
                WHERE u.email = %s
                AND u.role = 'doctor'
                AND u.is_active = 1
                LIMIT 1
                """,
                (email,)
            )

            user = cursor.fetchone()

            if user and user["verification_status"] != "VERIFIED":
                flash(
                    "Your doctor account is not verified by the administrator.",
                    "warning"
                )
                return redirect(url_for("doctor_login"))

            if user and check_password_hash(
                user["password_hash"],
                password
            ):

                session.clear()

                session["user_id"] = user["user_id"]
                session["full_name"] = user["full_name"]
                session["email"] = user["email"]
                session["role"] = "doctor"

                flash(
                    "Doctor login successful.",
                    "success"
                )

                return redirect(
                    url_for("doctor_dashboard")
                )

            flash(
                "Invalid doctor email or password.",
                "danger"
            )

        except Exception as e:

            print("Doctor login error:", e)

            flash(
                "Unable to process login.",
                "danger"
            )

        finally:

            cursor.close()
            connection.close()

    return render_template("doctor_login.html")


# ============================================================
# DOCTOR REGISTER
# ============================================================

@app.route("/doctor/register", methods=["GET", "POST"])
def doctor_register():

    if request.method == "POST":

        full_name = request.form.get(
            "full_name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        medical_license_number = request.form.get(
            "medical_license_number",
            ""
        ).strip()

        specialization = request.form.get(
            "specialization",
            ""
        ).strip()

        qualification = request.form.get(
            "qualification",
            ""
        ).strip()

        hospital_name = request.form.get(
            "hospital_name",
            ""
        ).strip()

        experience_years = request.form.get(
            "experience_years",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        if (
            not full_name
            or not email
            or not password
            or not medical_license_number
        ):

            flash(
                "Please fill all required fields.",
                "danger"
            )

            return redirect(
                url_for("doctor_register")
            )

        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "danger"
            )

            return redirect(
                url_for("doctor_register")
            )

        if len(password) < 6:

            flash(
                "Password must contain at least 6 characters.",
                "danger"
            )

            return redirect(
                url_for("doctor_register")
            )
        if experience_years:
            try:
                experience_years_value = int(experience_years)

                if experience_years_value < 0 or experience_years_value > 80:
                    flash(
                        "Experience must be between 0 and 80 years.",
                        "danger"
                    )
                    return redirect(
                        url_for("doctor_register")
                    )

            except ValueError:
                flash(
                    "Experience must be a valid number.",
                    "danger"
                )
                return redirect(
                    url_for("doctor_register")
                )
        else:
            experience_years_value = None
        

        connection = get_db_connection()

        if connection is None:

            flash(
                "Database connection failed.",
                "danger"
            )

            return redirect(
                url_for("doctor_register")
            )

        cursor = connection.cursor(dictionary=True)

        try:

            cursor.execute(
                """
                SELECT user_id
                FROM users
                WHERE email = %s
                LIMIT 1
                """,
                (email,)
            )

            existing_user = cursor.fetchone()

            if existing_user:

                flash(
                    "An account with this email already exists.",
                    "danger"
                )

                return redirect(
                    url_for("doctor_register")
                )
            cursor.execute(
                """
                SELECT doctor_id
                FROM doctors
                WHERE medical_license_number = %s
                LIMIT 1
                """,
                (medical_license_number,)
            )

            existing_license = cursor.fetchone()

            if existing_license:

                flash(
                    "A doctor account with this medical license number already exists.",
                    "danger"
                )

                return redirect(
                    url_for("doctor_register")
                )

            password_hash = generate_password_hash(
                password
            )

            cursor.execute(
                """
                INSERT INTO users
                (
                    full_name,
                    email,
                    password_hash,
                    phone,
                    role,
                    is_active
                )
                VALUES
                (%s, %s, %s, %s, 'doctor', 1)
                """,
                (
                    full_name,
                    email,
                    password_hash,
                    phone
                )
            )

            user_id = cursor.lastrowid

            cursor.execute(
                """
                INSERT INTO doctors
                (
                    user_id,
                    specialization,
                    medical_license_number,
                    qualification,
                    hospital_name,
                    experience_years,
                    verification_status
                )
                VALUES
                (%s, %s, %s, %s, %s, %s, 'PENDING')
                """,
                (
                    user_id,
                    specialization or None,
                    medical_license_number,
                    qualification or None,
                    hospital_name or None,
                    experience_years_value
                )
            )

            connection.commit()

            flash(
                "Doctor account created successfully. Please login.",
                "success"
            )

            return redirect(
                url_for("doctor_login")
            )

        except Exception as e:

            connection.rollback()

            print("Doctor registration error:", e)

            flash(
                "Unable to create doctor account.",
                "danger"
            )

        finally:

            cursor.close()
            connection.close()

    return render_template("doctor_register.html")


# ============================================================
# ADMIN REGISTRATION
# ============================================================

@app.route("/admin/register", methods=["GET", "POST"])
def admin_register():

    if request.method == "POST":

        full_name = request.form.get(
            "full_name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        if not full_name or not email or not password:

            flash(
                "Please fill all required fields.",
                "danger"
            )

            return redirect(
                url_for("admin_register")
            )

        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "danger"
            )

            return redirect(
                url_for("admin_register")
            )

        if len(password) < 8:

            flash(
                "Password must contain at least 8 characters.",
                "danger"
            )

            return redirect(
                url_for("admin_register")
            )

        connection = get_db_connection()

        if connection is None:

            flash(
                "Database connection failed.",
                "danger"
            )

            return redirect(
                url_for("admin_register")
            )

        cursor = connection.cursor(dictionary=True)

        try:

            cursor.execute(
                """
                SELECT user_id
                FROM users
                WHERE email = %s
                LIMIT 1
                """,
                (email,)
            )

            existing_user = cursor.fetchone()

            if existing_user:

                flash(
                    "An account with this email already exists.",
                    "danger"
                )

                return redirect(
                    url_for("admin_register")
                )

            password_hash = generate_password_hash(
                password
            )

            cursor.execute(
                """
                INSERT INTO users
                (
                    full_name,
                    email,
                    password_hash,
                    phone,
                    role,
                    is_active
                )
                VALUES
                (%s, %s, %s, %s, 'admin', 1)
                """,
                (
                    full_name,
                    email,
                    password_hash,
                    phone
                )
            )

            connection.commit()

            flash(
                "Admin account created successfully. Please login.",
                "success"
            )

            return redirect(
                url_for("admin_login")
            )

        except Exception as e:

            connection.rollback()

            print(
                "Admin registration error:",
                e
            )

            flash(
                "Unable to create admin account.",
                "danger"
            )

        finally:

            cursor.close()
            connection.close()

    return render_template(
        "admin_register.html"
    )

# ============================================================
# ADMIN LOGIN
# ============================================================

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        if not email or not password:

            flash(
                "Please enter email and password.",
                "danger"
            )

            return redirect(
                url_for("admin_login")
            )

        connection = get_db_connection()

        if connection is None:

            flash(
                "Database connection failed.",
                "danger"
            )

            return redirect(
                url_for("admin_login")
            )

        cursor = connection.cursor(dictionary=True)

        try:

            cursor.execute(
                """
                SELECT *
                FROM users
                WHERE email = %s
                AND role = 'admin'
                AND is_active = 1
                LIMIT 1
                """,
                (email,)
            )

            user = cursor.fetchone()

            if user and check_password_hash(
                user["password_hash"],
                password
            ):

                session.clear()

                session["user_id"] = user["user_id"]
                session["full_name"] = user["full_name"]
                session["email"] = user["email"]
                session["role"] = "admin"

                create_system_log(
                    "ADMIN_LOGIN",
                    "Admin logged into the system.",
                    user["user_id"]
                )

                flash(
                    "Admin login successful.",
                    "success"
                )

                return redirect(
                    url_for("admin_dashboard")
                )

            flash(
                "Invalid admin email or password.",
                "danger"
            )

        except Exception as e:

            print("Admin login error:", e)

            flash(
                "Unable to process login.",
                "danger"
            )

        finally:

            cursor.close()
            connection.close()

    return render_template("admin_login.html")
# ============================================================
# PATIENT REGISTRATION
# ============================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        full_name = request.form["full_name"].strip()
        email = request.form["email"].strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if not full_name or not email or not password:
            flash("Please fill all required fields.", "danger")
            return redirect(url_for("register"))

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("register"))

        if len(password) < 8:
            flash(
                "Password must contain at least 8 characters.",
                "danger"
            )
            return redirect(url_for("register"))

        success, message = register_patient(
            full_name=full_name,
            email=email,
            password=password,
            phone=phone
        )

        if success:
            flash(
                "Registration successful. Please login.",
                "success"
            )
            return redirect(url_for("login"))

        flash(message, "danger")

    return render_template("register.html")


# ============================================================
# LOGIN
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"].strip().lower()
        password = request.form["password"]

        user = authenticate_user(email, password)

        if user:

            session.clear()

            session["user_id"] = user["user_id"]
            session["full_name"] = user["full_name"]
            session["email"] = user["email"]
            session["role"] = user["role"]

            flash("Login successful.", "success")

            # -----------------------------
            # Role based redirection
            # -----------------------------

            if user["role"] == "patient":
                return redirect(
                    url_for("patient_dashboard")
                )

            elif user["role"] == "doctor":
                return redirect(
                    url_for("doctor_dashboard")
                )

            elif user["role"] == "admin":
                return redirect(
                    url_for("admin_dashboard")
                )

        flash(
            "Invalid email or password.",
            "danger"
        )

    return render_template("login.html")


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(url_for("login"))


# ============================================================
# PATIENT DASHBOARD
# ============================================================

@app.route("/patient/dashboard")
def patient_dashboard():

    # ========================================================
    # LOGIN CHECK
    # ========================================================

    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("login"))

    if session.get("role") != "patient":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    patient_id = session["user_id"]

    # ========================================================
    # DATABASE CONNECTION
    # ========================================================

    connection = get_db_connection()

    if connection is None:
        flash("Unable to connect to database.", "danger")

        return render_template(
            "patient_dashboard.html",
            name=session.get("full_name"),
            total_reports=0,
            total_predictions=0,
            latest_prediction=None,
            doctor_reviews=0,
            recent_assessments=[]
        )

    cursor = connection.cursor(dictionary=True)

    try:

        # ====================================================
        # 1. TOTAL MEDICAL REPORTS
        # ====================================================

        cursor.execute(
            """
            SELECT COUNT(*) AS total_reports
            FROM medical_reports
            WHERE patient_id = %s
            """,
            (patient_id,)
        )

        report_result = cursor.fetchone()

        total_reports = report_result["total_reports"] or 0


        # ====================================================
        # 2. TOTAL AI PREDICTIONS
        # ====================================================

        cursor.execute(
            """
            SELECT COUNT(*) AS total_predictions
            FROM predictions p
            JOIN extracted_features e
                ON p.extraction_id = e.extraction_id
            JOIN medical_reports m
                ON e.report_id = m.report_id
            WHERE m.patient_id = %s
            AND p.prediction_status = 'COMPLETED'
            """,
            (patient_id,)
        )

        prediction_result = cursor.fetchone()

        total_predictions = (
            prediction_result["total_predictions"] or 0
        )


        # ====================================================
        # 3. LATEST PREDICTION
        # ====================================================

        cursor.execute(
            """
            SELECT
                p.prediction_id,
                p.prediction_result,
                p.risk_probability,
                p.risk_level,
                p.model_name,
                p.model_version,
                p.prediction_status,
                p.created_at
            FROM predictions p
            JOIN extracted_features e
                ON p.extraction_id = e.extraction_id
            JOIN medical_reports m
                ON e.report_id = m.report_id
            WHERE m.patient_id = %s
            AND p.prediction_status = 'COMPLETED'
            ORDER BY p.created_at DESC
            LIMIT 1
            """,
            (patient_id,)
        )

        latest_prediction = cursor.fetchone()


        # ====================================================
        # 4. CONVERT PROBABILITY TO PERCENTAGE
        # ====================================================

        if latest_prediction:

            latest_prediction["risk_probability_percent"] = round(
                float(
                    latest_prediction["risk_probability"]
                ) * 100,
                2
            )


        # ====================================================
        # 5. DOCTOR REVIEWS
        # ====================================================
        #
        # We first try to read doctor review information.
        # If the review table/module is not ready yet,
        # dashboard will safely show 0.
        #

        doctor_reviews = 0

        cursor.execute(
            """
            SELECT COUNT(*) AS doctor_reviews
            FROM doctor_reviews dr
            JOIN predictions p
                ON dr.prediction_id = p.prediction_id
            JOIN extracted_features e
                ON p.extraction_id = e.extraction_id
            JOIN medical_reports m
                ON e.report_id = m.report_id
            WHERE m.patient_id = %s
            AND dr.review_status = 'REVIEWED'
            """,
            (patient_id,)
        )

        review_result = cursor.fetchone()

        doctor_reviews = (
            review_result["doctor_reviews"] or 0
        )

        # ====================================================
        # 6. RECENT ASSESSMENTS
        # ====================================================

        cursor.execute(
            """
            SELECT
                p.prediction_id,
                p.prediction_result,
                p.risk_probability,
                p.risk_level,
                p.model_name,
                p.model_version,
                p.prediction_status,
                p.created_at,

                m.original_file_name,
                m.report_type

            FROM predictions p

            JOIN extracted_features e
                ON p.extraction_id = e.extraction_id

            JOIN medical_reports m
                ON e.report_id = m.report_id

            WHERE m.patient_id = %s

            ORDER BY p.created_at DESC

            LIMIT 5
            """,
            (patient_id,)
        )

        recent_assessments = cursor.fetchall()


        # ====================================================
        # 7. CONVERT PROBABILITIES
        # ====================================================

        for assessment in recent_assessments:

            assessment["risk_probability_percent"] = round(
                float(
                    assessment["risk_probability"]
                ) * 100,
                2
            )


        # ====================================================
        # 8. SEND DATA TO HTML
        # ====================================================

        return render_template(
            "patient_dashboard.html",

            name=session.get("full_name"),

            total_reports=total_reports,

            total_predictions=total_predictions,

            latest_prediction=latest_prediction,

            doctor_reviews=doctor_reviews,

            recent_assessments=recent_assessments
        )


    except Exception as e:

        print(
            "Patient dashboard database error:",
            e
        )

        flash(
            "Unable to load dashboard information.",
            "danger"
        )

        return render_template(
            "patient_dashboard.html",

            name=session.get("full_name"),

            total_reports=0,

            total_predictions=0,

            latest_prediction=None,

            doctor_reviews=0,

            recent_assessments=[]
        )


    finally:

        cursor.close()
        connection.close()


# ============================================================
# PATIENT MEDICAL REPORTS
# ============================================================

@app.route("/patient/reports")
def patient_reports():

    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("login"))

    if session.get("role") != "patient":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    connection = get_db_connection()

    if connection is None:
        flash("Unable to connect to database.", "danger")
        return redirect(url_for("patient_dashboard"))

    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                report_id,
                report_type,
                original_file_name,
                processing_status,
                uploaded_at
            FROM medical_reports
            WHERE patient_id = %s
            ORDER BY uploaded_at DESC
            """,
            (session["user_id"],)
        )

        reports = cursor.fetchall()

        return render_template(
            "patient_reports.html",
            name=session.get("full_name"),
            reports=reports
        )

    except Exception as e:

        print("Patient reports error:", e)

        flash(
            "Unable to load medical reports.",
            "danger"
        )

        return redirect(url_for("patient_dashboard"))

    finally:

        cursor.close()
        connection.close()
# ============================================================
# PATIENT VIEW MEDICAL REPORT
# ============================================================

@app.route("/patient/report/<int:report_id>")
def patient_view_report(report_id):

    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("login"))

    if session.get("role") != "patient":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    connection = get_db_connection()

    if connection is None:
        flash("Unable to connect to database.", "danger")
        return redirect(url_for("patient_reports"))

    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                report_id,
                stored_file_name,
                original_file_name
            FROM medical_reports
            WHERE report_id = %s
              AND patient_id = %s
            """,
            (report_id, session["user_id"])
        )

        report = cursor.fetchone()

        if not report:
            flash("Medical report not found.", "danger")
            return redirect(url_for("patient_reports"))

        return send_from_directory(
            "uploads/ecg",
            report["stored_file_name"],
            as_attachment=False
        )

    except Exception as e:

        print("Patient report view error:", e)

        flash(
            "Unable to open medical report.",
            "danger"
        )

        return redirect(url_for("patient_reports"))

    finally:

        cursor.close()
        connection.close()

# ============================================================
# PATIENT RISK INSIGHTS
# ============================================================

@app.route("/patient/risk-insights")
def patient_risk_insights():

    # ========================================================
    # LOGIN CHECK
    # ========================================================

    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("login"))

    if session.get("role") != "patient":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    patient_id = session["user_id"]

    connection = get_db_connection()

    if connection is None:
        flash("Unable to connect to database.", "danger")
        return render_template(
            "patient_risk_insights.html",
            name=session.get("full_name"),
            latest_prediction=None,
            total_predictions=0,
            low_risk_count=0,
            moderate_risk_count=0,
            high_risk_count=0
        )

    cursor = connection.cursor(dictionary=True)

    try:

        # ====================================================
        # 1. LATEST COMPLETED AI ASSESSMENT
        # ====================================================

        cursor.execute(
            """
            SELECT
                p.prediction_id,
                p.extraction_id,
                p.prediction_result,
                p.risk_probability,
                p.risk_level,
                p.model_name,
                p.model_version,
                p.prediction_status,
                p.qaml_prediction,
                p.qaml_quantum_score,
                p.created_at,

                m.report_id,
                m.report_type,
                m.original_file_name

            FROM predictions p

            JOIN extracted_features e
                ON p.extraction_id = e.extraction_id

            JOIN medical_reports m
                ON e.report_id = m.report_id

            WHERE m.patient_id = %s
              AND p.prediction_status = 'COMPLETED'

            ORDER BY p.created_at DESC

            LIMIT 1
            """,
            (patient_id,)
        )

        latest_prediction = cursor.fetchone()

        if latest_prediction:
            latest_prediction["risk_probability_percent"] = round(
                float(latest_prediction["risk_probability"]) * 100,
                2
            )

        # ====================================================
        # 2. TOTAL COMPLETED ASSESSMENTS
        # ====================================================

        cursor.execute(
            """
            SELECT COUNT(*) AS total_predictions
            FROM predictions p

            JOIN extracted_features e
                ON p.extraction_id = e.extraction_id

            JOIN medical_reports m
                ON e.report_id = m.report_id

            WHERE m.patient_id = %s
              AND p.prediction_status = 'COMPLETED'
            """,
            (patient_id,)
        )

        total_predictions = cursor.fetchone()["total_predictions"] or 0

        # ====================================================
        # 3. RISK LEVEL SUMMARY
        # ====================================================

        cursor.execute(
            """
            SELECT
                risk_level,
                COUNT(*) AS risk_count

            FROM predictions p

            JOIN extracted_features e
                ON p.extraction_id = e.extraction_id

            JOIN medical_reports m
                ON e.report_id = m.report_id

            WHERE m.patient_id = %s
              AND p.prediction_status = 'COMPLETED'

            GROUP BY risk_level
            """,
            (patient_id,)
        )

        risk_summary = cursor.fetchall()

        low_risk_count = 0
        moderate_risk_count = 0
        high_risk_count = 0

        for row in risk_summary:

            if row["risk_level"] == "LOW":
                low_risk_count = row["risk_count"]

            elif row["risk_level"] == "MODERATE":
                moderate_risk_count = row["risk_count"]

            elif row["risk_level"] == "HIGH":
                high_risk_count = row["risk_count"]

        # ====================================================
        # 4. SEND DATA TO PAGE
        # ====================================================

        return render_template(
            "patient_risk_insights.html",

            name=session.get("full_name"),

            latest_prediction=latest_prediction,

            total_predictions=total_predictions,

            low_risk_count=low_risk_count,

            moderate_risk_count=moderate_risk_count,

            high_risk_count=high_risk_count
        )

    except Exception as e:

        print(
            "Patient risk insights database error:",
            e
        )

        flash(
            "Unable to load risk insights.",
            "danger"
        )

        return render_template(
            "patient_risk_insights.html",

            name=session.get("full_name"),

            latest_prediction=None,

            total_predictions=0,

            low_risk_count=0,

            moderate_risk_count=0,

            high_risk_count=0
        )

    finally:

        cursor.close()
        connection.close()
# ============================================================
# PATIENT DOCTOR REVIEWS
# ============================================================
@app.route("/patient/prediction-history")
def patient_prediction_history():

    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("login"))

    if session.get("role") != "patient":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    connection = get_db_connection()

    if connection is None:
        flash("Unable to connect to database.", "danger")
        return redirect(url_for("patient_dashboard"))

    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                p.prediction_id,
                p.risk_probability,
                p.risk_level,
                p.model_name,
                p.model_version,
                p.prediction_status,
                p.created_at,

                e.extraction_id,

                m.report_id,
                m.report_type,
                m.original_file_name

            FROM predictions p

            JOIN extracted_features e
                ON p.extraction_id = e.extraction_id

            JOIN medical_reports m
                ON e.report_id = m.report_id

            WHERE m.patient_id = %s

            ORDER BY p.created_at DESC
            """,
            (session["user_id"],)
        )

        predictions = cursor.fetchall()
        

        return render_template(
            "prediction_history.html",
            name=session.get("full_name"),
            predictions=predictions
        )

    except Exception as e:
        print("Prediction history error:", e)
        flash("Unable to load prediction history.", "danger")
        return redirect(url_for("patient_dashboard"))

    finally:
        cursor.close()
        connection.close()


@app.route("/patient/doctor-reviews")
def patient_doctor_reviews():

    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("login"))

    if session.get("role") != "patient":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    connection = get_db_connection()

    if connection is None:
        flash("Unable to connect to database.", "danger")
        return redirect(url_for("patient_dashboard"))

    cursor = connection.cursor(dictionary=True)

    try:

        # ========================================================
        # AI PREDICTION BASED DOCTOR REVIEWS
        # ========================================================

        cursor.execute(
            """
            SELECT
                dr.review_id,
                dr.review_status,
                dr.doctor_decision,
                dr.diagnosis_notes,
                dr.recommendations,
                dr.prediction_agreement,
                dr.reviewed_at,

                p.prediction_id,
                p.extraction_id,
                p.risk_probability,
                p.risk_level,
                p.model_name,
                p.model_version,
                p.qaml_prediction,
                p.qaml_quantum_score,
                p.created_at,

                m.report_id,
                m.report_type,
                m.original_file_name,

                'AI_PREDICTION' AS review_source

            FROM predictions p

            LEFT JOIN doctor_reviews dr
                ON dr.prediction_id = p.prediction_id

            JOIN extracted_features e
                ON p.extraction_id = e.extraction_id

            JOIN medical_reports m
                ON e.report_id = m.report_id

            WHERE m.patient_id = %s
                AND p.prediction_status = 'COMPLETED'
            """,
            (session["user_id"],)
        )

        prediction_reviews = cursor.fetchall()

        # Prepare display fields for AI reviews
        for review in prediction_reviews:

            review["display_review_status"] = (
                review["review_status"]
                if review["review_status"]
                else "PENDING"
            )

            if review["risk_probability"] is not None:
                review["risk_probability_percent"] = round(
                    float(review["risk_probability"]) * 100,
                    2
                )
            else:
                review["risk_probability_percent"] = None

            if review["created_at"] is not None:
                review["prediction_date"] = review["created_at"]
            else:
                review["prediction_date"] = "Not available"

            review["patient_name"] = session.get(
                "full_name",
                "Patient"
            )


        # ========================================================
        # REPORT-ONLY DOCTOR REVIEWS
        # ========================================================

        cursor.execute(
            """
            SELECT
                rdr.review_id,
                rdr.review_status,
                rdr.doctor_decision,
                rdr.diagnosis_notes,
                rdr.recommendations,

                NULL AS prediction_agreement,
                rdr.reviewed_at,

                NULL AS prediction_id,
                NULL AS extraction_id,
                NULL AS risk_probability,
                NULL AS risk_level,
                NULL AS model_name,
                NULL AS model_version,
                NULL AS qaml_prediction,
                NULL AS qaml_quantum_score,
                NULL AS created_at,

                m.report_id,
                m.report_type,
                m.original_file_name,

                'REPORT_REVIEW' AS review_source

            FROM report_doctor_reviews rdr

            JOIN medical_reports m
                ON rdr.report_id = m.report_id

            WHERE m.patient_id = %s
              AND rdr.review_status = 'REVIEWED'
            """,
            (session["user_id"],)
        )

        report_reviews = cursor.fetchall()

        # Prepare display fields for report-only reviews
        for review in report_reviews:

            review["display_review_status"] = review["review_status"]

            review["risk_probability_percent"] = None
            review["prediction_date"] = review["reviewed_at"]

            review["patient_name"] = session.get(
                "full_name",
                "Patient"
            )


        # ========================================================
        # COMBINE BOTH REVIEW TYPES
        # ========================================================

        reviews = prediction_reviews + report_reviews

        # Latest reviews first
        reviews.sort(
            key=lambda review: review["reviewed_at"] or "",
            reverse=True
        )

        return render_template(
            "doctor_clinical_reviews.html",
            name=session.get("full_name"),
            reviews=reviews
        )

    except Exception as e:

        print(
            "Patient doctor reviews error:",
            e
        )

        flash(
            "Unable to load doctor reviews.",
            "danger"
        )

        return redirect(
            url_for("patient_dashboard")
        )

    finally:

        cursor.close()
        connection.close()

# ============================================================
# DOCTOR DASHBOARD
# ============================================================
@app.route("/doctor/predictions")
def doctor_predictions():

    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("login"))

    if session.get("role") != "doctor":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    connection = get_db_connection()

    if connection is None:
        flash("Unable to connect to database.", "danger")
        return redirect(url_for("doctor_dashboard"))

    cursor = connection.cursor(dictionary=True)

    try:
                # ====================================================
        # VERIFY DOCTOR PROFILE
        # ====================================================

        cursor.execute(
            """
            SELECT
                doctor_id,
                verification_status
            FROM doctors
            WHERE user_id = %s
            LIMIT 1
            """,
            (session["user_id"],)
        )

        doctor = cursor.fetchone()

        if doctor is None:
            flash(
                "Doctor profile not found.",
                "danger"
            )
            return redirect(
                url_for("doctor_dashboard")
            )

        if doctor["verification_status"] != "VERIFIED":
            flash(
                "Access denied. Your doctor profile is not verified.",
                "danger"
            )
            return redirect(
                url_for("doctor_dashboard")
            )

        cursor.execute(
            """
            SELECT
                p.prediction_id,
                p.prediction_result,
                p.risk_probability,
                p.risk_level,
                p.model_name,
                p.model_version,
                p.prediction_status,
                p.created_at,

                e.extraction_id,

                m.report_id,
                m.report_type,
                m.original_file_name,

                u.user_id AS patient_id,
                u.full_name AS patient_name

            FROM predictions p

            JOIN extracted_features e
                ON p.extraction_id = e.extraction_id

            JOIN medical_reports m
                ON e.report_id = m.report_id

            JOIN users u
                ON m.patient_id = u.user_id

            WHERE p.prediction_status = 'COMPLETED'

            ORDER BY p.created_at DESC
            """
        )

        predictions = cursor.fetchall()

        return render_template(
            "doctor_predictions.html",
            name=session.get("full_name"),
            predictions=predictions
        )

    except Exception as e:
        print("Doctor predictions error:", e)
        flash("Unable to load AI predictions.", "danger")
        return redirect(url_for("doctor_dashboard"))

    finally:
        cursor.close()
        connection.close()

# ============================================================
# DOCTOR QAML RESULTS
# ============================================================

@app.route("/doctor/qaml-results")
def doctor_qaml_results():

    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("login"))

    if session.get("role") != "doctor":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    connection = get_db_connection()

    if connection is None:
        flash("Unable to connect to database.", "danger")
        return redirect(url_for("doctor_dashboard"))

    cursor = connection.cursor(dictionary=True)

    try:

        # ====================================================
        # VERIFY DOCTOR PROFILE
        # ====================================================

        cursor.execute(
            """
            SELECT
                doctor_id,
                verification_status
            FROM doctors
            WHERE user_id = %s
            LIMIT 1
            """,
            (session["user_id"],)
        )

        doctor = cursor.fetchone()

        if doctor is None:
            flash("Doctor profile not found.", "danger")
            return redirect(url_for("doctor_dashboard"))

        if doctor["verification_status"] != "VERIFIED":
            flash(
                "Access denied. Your doctor profile is not verified.",
                "danger"
            )
            return redirect(url_for("doctor_dashboard"))

        # ====================================================
        # GET QAML RESULTS
        # ====================================================

        cursor.execute(
            """
            SELECT
                p.prediction_id,
                p.prediction_result,
                p.risk_probability,
                p.risk_level,
                p.model_name,
                p.model_version,
                p.prediction_status,
                p.qaml_prediction,
                p.qaml_quantum_score,
                p.created_at,

                e.extraction_id,

                m.report_id,
                m.report_type,
                m.original_file_name,

                u.user_id AS patient_id,
                u.full_name AS patient_name

            FROM predictions p

            JOIN extracted_features e
                ON p.extraction_id = e.extraction_id

            JOIN medical_reports m
                ON e.report_id = m.report_id

            JOIN users u
                ON m.patient_id = u.user_id

            WHERE p.prediction_status = 'COMPLETED'

            ORDER BY p.created_at DESC
            """
        )

        qaml_results = cursor.fetchall()

        # ====================================================
        # CALCULATE DISPLAY VALUES
        # ====================================================

        for result in qaml_results:

            if result["risk_probability"] is not None:
                result["risk_probability_percent"] = round(
                    float(result["risk_probability"]) * 100,
                    2
                )
            else:
                result["risk_probability_percent"] = 0

        # ====================================================
        # SEND DATA TO HTML
        # ====================================================

        return render_template(
            "doctor_qaml_results.html",
            name=session.get("full_name"),
            qaml_results=qaml_results
        )

    except Exception as e:

        print(
            "Doctor QAML results error:",
            e
        )

        flash(
            "Unable to load QAML results.",
            "danger"
        )

        return redirect(
            url_for("doctor_dashboard")
        )

    finally:

        cursor.close()
        connection.close()

@app.route("/doctor/reports")
def doctor_reports():

    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("login"))

    if session.get("role") != "doctor":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    connection = get_db_connection()

    if connection is None:
        flash("Unable to connect to database.", "danger")
        return redirect(url_for("doctor_dashboard"))

    cursor = connection.cursor(dictionary=True)

    try:
                # ====================================================
        # VERIFY DOCTOR PROFILE
        # ====================================================

        cursor.execute(
            """
            SELECT
                doctor_id,
                verification_status
            FROM doctors
            WHERE user_id = %s
            LIMIT 1
            """,
            (session["user_id"],)
        )

        doctor = cursor.fetchone()

        if doctor is None:
            flash(
                "Doctor profile not found.",
                "danger"
            )
            return redirect(
                url_for("home")
            )

        if doctor["verification_status"] != "VERIFIED":
            flash(
                "Access denied. Your doctor profile is not verified.",
                "danger"
            )
            return redirect(
                url_for("home")
            )

        cursor.execute(
            """
            SELECT
                m.report_id,
                m.patient_id,
                m.report_type,
                m.original_file_name,
                m.processing_status,
                m.uploaded_at,

                u.full_name AS patient_name,

                e.extraction_id,
                e.validation_status,
                e.extraction_method,
                e.extraction_confidence

            FROM medical_reports m

            JOIN users u
                ON m.patient_id = u.user_id

            LEFT JOIN extracted_features e
                ON m.report_id = e.report_id

            ORDER BY m.uploaded_at DESC
            """
        )

        reports = cursor.fetchall()

        return render_template(
            "doctor_reports.html",
            name=session.get("full_name"),
            reports=reports
        )

    except Exception as e:
        print("Doctor reports error:", e)
        flash("Unable to load medical reports.", "danger")
        return redirect(url_for("doctor_dashboard"))

    finally:
        cursor.close()
        connection.close()

@app.route("/doctor/report/<int:report_id>")
def doctor_view_report(report_id):

    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("login"))

    if session.get("role") != "doctor":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    connection = get_db_connection()

    if connection is None:
        flash("Unable to connect to database.", "danger")
        return redirect(url_for("doctor_reports"))

    cursor = connection.cursor(dictionary=True)

    try:

        # Verify that the logged-in user has a verified doctor profile
        cursor.execute(
            """
            SELECT
                doctor_id,
                verification_status
            FROM doctors
            WHERE user_id = %s
            LIMIT 1
            """,
            (session["user_id"],)
        )

        doctor = cursor.fetchone()

        if not doctor:
            flash("Doctor profile not found.", "danger")
            return redirect(url_for("doctor_dashboard"))

        if doctor["verification_status"] != "VERIFIED":
            flash(
                "Access denied. Your doctor profile is not verified.",
                "danger"
            )
            return redirect(url_for("doctor_dashboard"))

        # Get the requested medical report
        cursor.execute(
            """
            SELECT
                report_id,
                stored_file_name,
                original_file_name,
                report_type
            FROM medical_reports
            WHERE report_id = %s
            LIMIT 1
            """,
            (report_id,)
        )

        report = cursor.fetchone()

        if not report:
            flash("Medical report not found.", "danger")
            return redirect(url_for("doctor_reports"))

        # Determine the upload folder from the report type
        report_type = (report["report_type"] or "ECG").upper()

        upload_folders = {
            "ECG": "uploads/ecg",
            "BLOOD_TEST": "uploads/blood_reports",
            "ECHO": "uploads/echo",
            "STRESS_TEST": "uploads/stress_test",
            "OTHER": "uploads/other"
        }

        upload_folder = upload_folders.get(
            report_type,
            "uploads/ecg"
        )

        return send_from_directory(
            upload_folder,
            report["stored_file_name"],
            as_attachment=False
        )

    except Exception as e:

        print("Doctor report view error:", e)

        flash(
            "Unable to open medical report.",
            "danger"
        )

        return redirect(url_for("doctor_reports"))

    finally:

        cursor.close()
        connection.close()
@app.route("/doctor/report/<int:report_id>/review")
def doctor_report_review(report_id):

    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("login"))

    if session.get("role") != "doctor":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    connection = get_db_connection()

    if connection is None:
        flash("Unable to connect to database.", "danger")
        return redirect(url_for("doctor_reports"))

    cursor = connection.cursor(dictionary=True)

    try:
        # Get logged-in doctor's doctor_id
        cursor.execute(
            """
            SELECT
                doctor_id,
                verification_status
            FROM doctors
            WHERE user_id = %s
            LIMIT 1
            """,
            (session["user_id"],)
        )

        doctor = cursor.fetchone()

        if not doctor:
            flash("Doctor profile not found.", "danger")
            return redirect(url_for("doctor_dashboard"))

        if doctor["verification_status"] != "VERIFIED":
            flash(
                "Access denied. Your doctor profile is not verified.",
                "danger"
            )
            return redirect(url_for("doctor_dashboard"))

        doctor_id = doctor["doctor_id"]
        # Get report and extracted clinical information
        cursor.execute(
            """
            SELECT
                m.report_id,
                m.patient_id,
                m.original_file_name,
                m.report_type,
                m.processing_status,
                m.uploaded_at,

                u.full_name AS patient_name,
                u.email AS patient_email,
                u.phone AS patient_phone,

                e.extraction_id,
                e.age,
                e.sex,
                e.chest_pain_type,
                e.resting_bp,
                e.cholesterol,
                e.fasting_blood_sugar,
                e.resting_ecg,
                e.max_heart_rate,
                e.exercise_angina,
                e.oldpeak,
                e.st_slope,

                e.ecg_quality,
                e.ventricular_rate,
                e.pr_interval,
                e.qrs_duration,
                e.qtc_interval,
                e.cardiac_axis,
                e.sinus_rhythm,
                e.av_conduction,

                e.extraction_method,
                e.validation_status,
                e.extraction_confidence,
                e.doctor_verified,
                e.extracted_at

            FROM medical_reports m

            JOIN users u
                ON m.patient_id = u.user_id

            LEFT JOIN extracted_features e
                ON m.report_id = e.report_id

            WHERE m.report_id = %s
            AND (
                e.validation_status = 'NEEDS_REVIEW'
                OR m.processing_status = 'NEEDS_REVIEW'
            )

            LIMIT 1
            """,
            (report_id,)
        )

        report = cursor.fetchone()

        if not report:
            flash("Medical report not found.", "danger")
            return redirect(url_for("doctor_reports"))

        # Get existing report-based doctor review
        cursor.execute(
            """
            SELECT
                review_id,
                review_status,
                doctor_decision,
                diagnosis_notes,
                recommendations,
                reviewed_at
            FROM report_doctor_reviews
            WHERE report_id = %s
              AND doctor_id = %s
            ORDER BY review_id DESC
            LIMIT 1
            """,
            (report_id, doctor_id)
        )

        doctor_review = cursor.fetchone()

        return render_template(
            "doctor_report_review.html",
            name=session.get("full_name"),
            report=report,
            doctor_review=doctor_review
        )

    except Exception as e:

        print("Doctor report review error:", e)

        flash("Unable to load report review.", "danger")

        return redirect(url_for("doctor_reports"))

    finally:

        cursor.close()
        connection.close()

@app.route("/doctor/report/<int:report_id>/review/submit", methods=["POST"])
def submit_report_doctor_review(report_id):

    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("login"))

    if session.get("role") != "doctor":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    doctor_decision = request.form.get("doctor_decision", "").strip()
    diagnosis_notes = request.form.get("diagnosis_notes", "").strip()
    recommendations = request.form.get("recommendations", "").strip()

    allowed_decisions = [
        "LOW_RISK",
        "MODERATE_RISK",
        "HIGH_RISK",
        "INCONCLUSIVE"
    ]

    if doctor_decision not in allowed_decisions:
        flash("Please select a valid clinical decision.", "warning")
        return redirect(
            url_for(
                "doctor_report_review",
                report_id=report_id
            )
        )

    connection = get_db_connection()

    if connection is None:
        flash("Unable to connect to database.", "danger")
        return redirect(url_for("doctor_reports"))

    cursor = connection.cursor(dictionary=True)

    try:
                # ====================================================
        # VERIFY DOCTOR PROFILE
        # ====================================================

        cursor.execute(
            """
            SELECT
                doctor_id,
                verification_status
            FROM doctors
            WHERE user_id = %s
            LIMIT 1
            """,
            (session["user_id"],)
        )

        doctor = cursor.fetchone()

        if doctor is None:
            flash(
                "Doctor profile not found.",
                "danger"
            )
            return redirect(
                url_for("doctor_dashboard")
            )

        if doctor["verification_status"] != "VERIFIED":
            flash(
                "Access denied. Your doctor profile is not verified.",
                "danger"
            )
            return redirect(
                url_for("doctor_dashboard")
            )

        doctor_id = doctor["doctor_id"]


        # Verify that the medical report exists and requires review
        cursor.execute(
            """
            SELECT
                m.report_id
            FROM medical_reports m
            LEFT JOIN extracted_features e
                ON m.report_id = e.report_id
            WHERE m.report_id = %s
            AND (
                e.validation_status = 'NEEDS_REVIEW'
                OR m.processing_status = 'NEEDS_REVIEW'
            )
            LIMIT 1
            """,
            (report_id,)
        )

        report = cursor.fetchone()

        if not report:
            flash("Medical report not found.", "danger")
            return redirect(url_for("doctor_reports"))

        # Check whether this doctor already reviewed this report
        cursor.execute(
            """
            SELECT review_id
            FROM report_doctor_reviews
            WHERE report_id = %s
              AND doctor_id = %s
            ORDER BY review_id DESC
            LIMIT 1
            """,
            (report_id, doctor_id)
        )

        existing_review = cursor.fetchone()

        if existing_review:

            cursor.execute(
                """
                UPDATE report_doctor_reviews
                SET
                    review_status = 'REVIEWED',
                    doctor_decision = %s,
                    diagnosis_notes = %s,
                    recommendations = %s,
                    reviewed_at = CURRENT_TIMESTAMP
                WHERE review_id = %s
                """,
                (
                    doctor_decision,
                    diagnosis_notes,
                    recommendations,
                    existing_review["review_id"]
                )
            )

        else:

            cursor.execute(
                """
                INSERT INTO report_doctor_reviews
                (
                    report_id,
                    doctor_id,
                    review_status,
                    doctor_decision,
                    diagnosis_notes,
                    recommendations,
                    reviewed_at
                )
                VALUES
                (
                    %s,
                    %s,
                    'REVIEWED',
                    %s,
                    %s,
                    %s,
                    CURRENT_TIMESTAMP
                )
                """,
                (
                    report_id,
                    doctor_id,
                    doctor_decision,
                    diagnosis_notes,
                    recommendations
                )
            )
        # ============================================================
        # VALIDATE EXTRACTED FEATURES BEFORE MARKING REPORT PROCESSED
        # ============================================================

        cursor.execute(
            """
            SELECT
                age,
                sex,
                chest_pain_type,
                resting_bp,
                cholesterol,
                fasting_blood_sugar,
                resting_ecg,
                max_heart_rate,
                exercise_angina,
                oldpeak,
                st_slope
            FROM extracted_features
            WHERE report_id = %s
            LIMIT 1
            """,
            (report_id,)
        )

        extracted = cursor.fetchone()

        required_features = [
            "age",
            "sex",
            "chest_pain_type",
            "resting_bp",
            "cholesterol",
            "fasting_blood_sugar",
            "resting_ecg",
            "max_heart_rate",
            "exercise_angina",
            "oldpeak",
            "st_slope"
        ]

        missing_features = [
            feature
            for feature in required_features
            if extracted is None or extracted.get(feature) is None
        ]

        if missing_features:
            # Do NOT allow incomplete extraction to become VALID.
            cursor.execute(
                """
                UPDATE medical_reports
                SET processing_status = 'NEEDS_REVIEW'
                WHERE report_id = %s
                """,
                (report_id,)
            )

            cursor.execute(
                """
                UPDATE extracted_features
                SET validation_status = 'NEEDS_REVIEW',
                    doctor_verified = 0
                WHERE report_id = %s
                """,
                (report_id,)
            )

            connection.commit()

            flash(
                "Doctor review saved, but the report still requires "
                "feature verification. Missing: "
                + ", ".join(missing_features),
                "warning"
            )

            return redirect(
                url_for(
                    "doctor_features"
                )
            )

        # All 11 model-required features are available.
        cursor.execute(
            """
            UPDATE medical_reports
            SET processing_status = 'PROCESSED'
            WHERE report_id = %s
            """,
            (report_id,)
        )

        cursor.execute(
            """
            UPDATE extracted_features
            SET validation_status = 'VALID',
                doctor_verified = 1
            WHERE report_id = %s
            """,
            (report_id,)
        )
        connection.commit()

        flash(
            "Doctor review submitted successfully.",
            "success"
        )

        return redirect(
            url_for(
                "doctor_report_review",
                report_id=report_id
            )
        )

    except Exception as e:

        connection.rollback()

        print("Report doctor review error:", e)

        flash(
            "Unable to save doctor review.",
            "danger"
        )

        return redirect(
            url_for(
                "doctor_report_review",
                report_id=report_id
            )
        )

    finally:

        cursor.close()
        connection.close()

@app.route("/doctor/features")
def doctor_features():

    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("login"))

    if session.get("role") != "doctor":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    connection = get_db_connection()

    if connection is None:
        flash("Unable to connect to database.", "danger")
        return redirect(url_for("doctor_dashboard"))

    cursor = connection.cursor(dictionary=True)

    try:
                # ====================================================
        # VERIFY DOCTOR PROFILE
        # ====================================================

        cursor.execute(
            """
            SELECT
                doctor_id,
                verification_status
            FROM doctors
            WHERE user_id = %s
            LIMIT 1
            """,
            (session["user_id"],)
        )

        doctor = cursor.fetchone()

        if doctor is None:
            flash(
                "Doctor profile not found.",
                "danger"
            )
            return redirect(
                url_for("doctor_dashboard")
            )

        if doctor["verification_status"] != "VERIFIED":
            flash(
                "Access denied. Your doctor profile is not verified.",
                "danger"
            )
            return redirect(
                url_for("doctor_dashboard")
            )

        cursor.execute(
            """
            SELECT
                e.extraction_id,
                e.report_id,

                e.age,
                e.sex,
                e.chest_pain_type,
                e.resting_bp,
                e.cholesterol,
                e.fasting_blood_sugar,
                e.resting_ecg,
                e.max_heart_rate,
                e.exercise_angina,
                e.oldpeak,
                e.st_slope,

                e.ecg_quality,
                e.ventricular_rate,
                e.pr_interval,
                e.qrs_duration,
                e.qtc_interval,
                e.cardiac_axis,
                e.sinus_rhythm,
                e.av_conduction,

                e.extraction_method,
                e.validation_status,
                e.extraction_confidence,
                e.doctor_verified,
                e.extracted_at,

                m.report_type,
                m.original_file_name,

                u.user_id AS patient_id,
                u.full_name AS patient_name

            FROM extracted_features e

            JOIN medical_reports m
                ON e.report_id = m.report_id

            JOIN users u
                ON m.patient_id = u.user_id

            ORDER BY e.extracted_at DESC
            """
        )

        features = cursor.fetchall()

        return render_template(
            "doctor_features.html",
            name=session.get("full_name"),
            features=features
        )

    except Exception as e:
        print("Doctor features error:", e)
        flash("Unable to load clinical features.", "danger")
        return redirect(url_for("doctor_dashboard"))

    finally:
        cursor.close()
        connection.close()


@app.route("/doctor/features/<int:extraction_id>/verify", methods=["POST"])
def verify_clinical_features(extraction_id):

    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("login"))

    if session.get("role") != "doctor":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    connection = get_db_connection()

    if connection is None:
        flash("Unable to connect to database.", "danger")
        return redirect(url_for("doctor_features"))

    cursor = connection.cursor(dictionary=True)

    try:
        # ============================================================
        # VERIFY DOCTOR PROFILE
        # ============================================================

        cursor.execute(
            """
            SELECT
                doctor_id,
                verification_status
            FROM doctors
            WHERE user_id = %s
            LIMIT 1
            """,
            (session["user_id"],)
        )

        doctor = cursor.fetchone()

        if doctor is None:
            flash("Doctor profile not found.", "danger")
            return redirect(url_for("doctor_dashboard"))

        if doctor["verification_status"] != "VERIFIED":
            flash(
                "Access denied. Your doctor profile is not verified.",
                "danger"
            )
            return redirect(url_for("doctor_dashboard"))

        # ============================================================
        # GET CURRENT EXTRACTION
        # ============================================================

        cursor.execute(
            """
            SELECT
                e.extraction_id,
                e.report_id,
                m.patient_id,
                e.age,
                e.sex,
                e.chest_pain_type,
                e.resting_bp,
                e.cholesterol,
                e.fasting_blood_sugar,
                e.resting_ecg,
                e.max_heart_rate,
                e.exercise_angina,
                e.oldpeak,
                e.st_slope
            FROM extracted_features e
            JOIN medical_reports m
                ON e.report_id = m.report_id
            WHERE e.extraction_id = %s
            LIMIT 1
            """,
            (extraction_id,)
        )

        extraction = cursor.fetchone()

        if not extraction:
            flash("Clinical feature record not found.", "danger")
            return redirect(url_for("doctor_features"))

        # ============================================================
        # READ VALUES ENTERED / VERIFIED BY DOCTOR
        # ============================================================

        field_names = [
            "age",
            "sex",
            "chest_pain_type",
            "resting_bp",
            "cholesterol",
            "fasting_blood_sugar",
            "resting_ecg",
            "max_heart_rate",
            "exercise_angina",
            "oldpeak",
            "st_slope"
        ]

        submitted_values = {}
        
        for field in field_names:
            value = request.form.get(field, "").strip()

            if value == "":
                submitted_values[field] = None
            else:
                try:
                    submitted_values[field] = float(value)
                except ValueError:
                    flash(
                        f"Invalid value entered for {field}.",
                        "warning"
                    )
                    return redirect(url_for("doctor_features"))

        # ============================================================
        # CHECK THAT ALL 11 MODEL FEATURES ARE AVAILABLE
        # ============================================================

        missing_fields = [
            field
            for field in field_names
            if submitted_values[field] is None
        ]

        if missing_fields:
            flash(
                "Verification blocked. Missing required clinical features: "
                + ", ".join(missing_fields),
                "warning"
            )
            return redirect(url_for("doctor_features"))

        # ============================================================
        # SAVE DOCTOR-VERIFIED VALUES
        # ============================================================

        cursor.execute(
            """
            UPDATE extracted_features
            SET
                age = %s,
                sex = %s,
                chest_pain_type = %s,
                resting_bp = %s,
                cholesterol = %s,
                fasting_blood_sugar = %s,
                resting_ecg = %s,
                max_heart_rate = %s,
                exercise_angina = %s,
                oldpeak = %s,
                st_slope = %s,
                doctor_verified = 1,
                validation_status = 'VALID'
            WHERE extraction_id = %s
            """,
            (
                submitted_values["age"],
                submitted_values["sex"],
                submitted_values["chest_pain_type"],
                submitted_values["resting_bp"],
                submitted_values["cholesterol"],
                submitted_values["fasting_blood_sugar"],
                submitted_values["resting_ecg"],
                submitted_values["max_heart_rate"],
                submitted_values["exercise_angina"],
                submitted_values["oldpeak"],
                submitted_values["st_slope"],
                extraction_id
            )
        )

        # ============================================================
        # MARK REPORT AS PROCESSED
        # ============================================================

        cursor.execute(
            """
            UPDATE medical_reports
            SET processing_status = 'PROCESSED'
            WHERE report_id = %s
            """,
            (extraction["report_id"],)
        )

        connection.commit()

        
        
        

        # ============================================================
        # RUN AI PREDICTION AFTER SUCCESSFUL FEATURE VERIFICATION
        # ============================================================

        prediction_success = predict_from_extraction(
            extraction["patient_id"],
            extraction_id
        )

        if prediction_success:
            flash(
                "Clinical features verified and AI assessment generated successfully.",
                "success"
            )
        else:
            flash(
                "Clinical features verified, but AI assessment could not be generated.",
                "warning"
            )

        return redirect(url_for("doctor_features"))

    except Exception as e:

        connection.rollback()

        print("Clinical feature verification error:", e)

        flash(
            "Unable to verify clinical features.",
            "danger"
        )

        return redirect(url_for("doctor_features"))

    finally:
        cursor.close()
        connection.close()

@app.route("/doctor/dashboard")
def doctor_dashboard():

    # ========================================================
    # LOGIN CHECK
    # ========================================================

    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("login"))

    if session.get("role") != "doctor":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    connection = get_db_connection()

    if connection is None:
        flash("Unable to connect to database.", "danger")

        return render_template(
            "doctor_dashboard.html",
            name=session.get("full_name"),
            total_patients=0,
            total_reports=0,
            total_predictions=0,
            pending_reviews=0,
            high_risk_cases=0,
            recent_cases=[]
        )

    cursor = connection.cursor(dictionary=True)

    try:
                # ====================================================
        # VERIFY DOCTOR PROFILE
        # ====================================================

        cursor.execute(
            """
            SELECT
                doctor_id,
                verification_status
            FROM doctors
            WHERE user_id = %s
            LIMIT 1
            """,
            (session["user_id"],)
        )

        doctor = cursor.fetchone()

        if doctor is None:
            flash(
                "Doctor profile not found.",
                "danger"
            )
            return redirect(
                url_for("home")
            )

        if doctor["verification_status"] != "VERIFIED":
            flash(
                "Access denied. Your doctor profile is not verified.",
                "danger"
            )
            return redirect(
                url_for("home")
            )

        # ====================================================
        # 1. TOTAL PATIENTS
        # ====================================================

        cursor.execute(
            """
            SELECT COUNT(*) AS total_patients
            FROM users
            WHERE role = 'patient'
            """
        )

        result = cursor.fetchone()

        total_patients = result["total_patients"] or 0


        # ====================================================
        # 2. TOTAL MEDICAL REPORTS
        # ====================================================

        cursor.execute(
            """
            SELECT COUNT(*) AS total_reports
            FROM medical_reports
            """
        )

        result = cursor.fetchone()

        total_reports = result["total_reports"] or 0


        # ====================================================
        # 3. TOTAL COMPLETED PREDICTIONS
        # ====================================================

        cursor.execute(
            """
            SELECT COUNT(*) AS total_predictions
            FROM predictions
            WHERE prediction_status = 'COMPLETED'
            """
        )

        result = cursor.fetchone()

        total_predictions = result["total_predictions"] or 0


        # ====================================================
        # 4. HIGH RISK CASES
        # ====================================================

        cursor.execute(
            """
            SELECT COUNT(*) AS high_risk_cases
            FROM predictions
            WHERE prediction_status = 'COMPLETED'
            AND risk_level = 'HIGH'
            """
        )

        result = cursor.fetchone()

        high_risk_cases = result["high_risk_cases"] or 0

        # ====================================================
        # 5. PENDING REVIEWS
        # ====================================================

        cursor.execute(
            """
            SELECT COUNT(*) AS pending_reviews
            FROM predictions p
            WHERE p.prediction_status = 'COMPLETED'
            AND NOT EXISTS (
                SELECT 1
                FROM doctor_reviews dr
                WHERE dr.prediction_id = p.prediction_id
                AND dr.review_status = 'REVIEWED'
            )
            """
        )

        pending_result = cursor.fetchone()

        pending_reviews = pending_result["pending_reviews"] or 0


        # ====================================================
        # 6. RECENT PATIENT CASES
        # ====================================================

        cursor.execute(
            """
            SELECT
                p.prediction_id,
                p.prediction_result,
                p.risk_probability,
                p.risk_level,
                p.model_name,
                p.model_version,
                p.prediction_status,
                p.created_at,

                m.report_id,
                m.original_file_name,
                m.report_type,

                u.user_id,
                u.full_name,
                u.email

            FROM predictions p

            JOIN extracted_features e
                ON p.extraction_id = e.extraction_id

            JOIN medical_reports m
                ON e.report_id = m.report_id

            JOIN users u
                ON m.patient_id = u.user_id

            WHERE p.prediction_status = 'COMPLETED'

            ORDER BY p.created_at DESC

            LIMIT 10
            """
        )

        recent_cases = cursor.fetchall()


        # ====================================================
        # 7. CONVERT PROBABILITY
        # ====================================================

        for case in recent_cases:

            case["risk_probability_percent"] = round(
                float(case["risk_probability"]) * 100,
                2
            )


        # ====================================================
        # 8. SEND DATA TO HTML
        # ====================================================

        return render_template(
            "doctor_dashboard.html",

            name=session.get("full_name"),

            total_patients=total_patients,

            total_reports=total_reports,

            total_predictions=total_predictions,

            pending_reviews=pending_reviews,

            high_risk_cases=high_risk_cases,

            recent_cases=recent_cases
        )


    except Exception as e:

        print(
            "Doctor dashboard database error:",
            e
        )

        flash(
            "Unable to load doctor dashboard.",
            "danger"
        )

        return render_template(
            "doctor_dashboard.html",

            name=session.get("full_name"),

            total_patients=0,

            total_reports=0,

            total_predictions=0,

            pending_reviews=0,

            high_risk_cases=0,

            recent_cases=[]
        )


    finally:

        cursor.close()
        connection.close()

# ============================================================
# DOCTOR PATIENTS
# ============================================================

@app.route("/doctor/patients")
def doctor_patients():

    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("login"))

    if session.get("role") != "doctor":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    connection = get_db_connection()

    if connection is None:
        flash("Unable to connect to database.", "danger")
        return redirect(url_for("doctor_dashboard"))

    cursor = connection.cursor(dictionary=True)

    try:

        # ====================================================
        # VERIFY DOCTOR PROFILE
        # ====================================================

        cursor.execute(
            """
            SELECT
                doctor_id,
                verification_status
            FROM doctors
            WHERE user_id = %s
            LIMIT 1
            """,
            (session["user_id"],)
        )

        doctor = cursor.fetchone()

        if doctor is None:
            flash("Doctor profile not found.", "danger")
            return redirect(url_for("doctor_dashboard"))

        if doctor["verification_status"] != "VERIFIED":
            flash(
                "Access denied. Your doctor profile is not verified.",
                "danger"
            )
            return redirect(url_for("doctor_dashboard"))

        # ====================================================
        # GET PATIENTS
        # ====================================================

        cursor.execute(
            """
            SELECT
                u.user_id,
                u.full_name,
                u.email,
                u.phone,
                u.created_at,

                COUNT(DISTINCT m.report_id) AS total_reports,

                COUNT(DISTINCT p.prediction_id) AS total_predictions,

                MAX(p.created_at) AS latest_assessment

            FROM users u

            LEFT JOIN medical_reports m
                ON u.user_id = m.patient_id

            LEFT JOIN extracted_features e
                ON m.report_id = e.report_id

            LEFT JOIN predictions p
                ON e.extraction_id = p.extraction_id
                AND p.prediction_status = 'COMPLETED'

            WHERE u.role = 'patient'

            GROUP BY
                u.user_id,
                u.full_name,
                u.email,
                u.phone,
                u.created_at

            ORDER BY
                u.created_at DESC
            """
        )

        patients = cursor.fetchall()

        # ====================================================
        # SEND DATA TO HTML
        # ====================================================

        return render_template(
            "doctor_patients.html",
            patients=patients,
            name=session.get("full_name")
        )

    except Exception as e:

        print(
            "Doctor patients database error:",
            e
        )

        flash(
            "Unable to load patients.",
            "danger"
        )

        return redirect(
            url_for("doctor_dashboard")
        )

    finally:

        cursor.close()
        connection.close()

# ============================================================
# DOCTOR CASE DETAILS
# ============================================================

@app.route("/doctor/case/<int:prediction_id>")
def doctor_case_details(prediction_id):

    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("login"))

    if session.get("role") != "doctor":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    connection = get_db_connection()

    if connection is None:
        flash("Unable to connect to database.", "danger")
        return redirect(url_for("doctor_dashboard"))

    cursor = connection.cursor(dictionary=True)

    try:

        # ====================================================
        # VERIFY DOCTOR PROFILE
        # ====================================================

        cursor.execute(
            """
            SELECT
                doctor_id,
                verification_status
            FROM doctors
            WHERE user_id = %s
            LIMIT 1
            """,
            (session["user_id"],)
        )

        doctor = cursor.fetchone()

        if doctor is None:
            flash(
                "Doctor profile not found.",
                "danger"
            )
            return redirect(
                url_for("doctor_dashboard")
            )

        if doctor["verification_status"] != "VERIFIED":
            flash(
                "Access denied. Your doctor profile is not verified.",
                "danger"
            )
            return redirect(
                url_for("doctor_dashboard")
            )

        doctor_id = doctor["doctor_id"]

        # ====================================================
        # GET PATIENT CASE
        # ====================================================

        cursor.execute(
            """
            SELECT
                p.prediction_id,
                p.prediction_result,
                p.risk_probability,
                p.qaml_prediction,
                p.qaml_quantum_score,
                p.risk_level,
                p.model_name,
                p.model_version,
                p.prediction_status,
                p.created_at,

                m.report_id,
                m.original_file_name,
                m.report_type,
                m.file_path,
                m.processing_status,

                u.user_id,
                u.full_name,
                u.email,
                u.phone,

                e.extraction_id,
                e.age,
                e.sex,
                e.chest_pain_type,
                e.resting_bp,
                e.cholesterol,
                e.fasting_blood_sugar,
                e.resting_ecg,
                e.max_heart_rate,
                e.exercise_angina,
                e.oldpeak,
                e.st_slope,
                e.extraction_method,
                e.validation_status AS extraction_status

            FROM predictions p

            JOIN extracted_features e
                ON p.extraction_id = e.extraction_id

            JOIN medical_reports m
                ON e.report_id = m.report_id

            JOIN users u
                ON m.patient_id = u.user_id

            WHERE p.prediction_id = %s

            LIMIT 1
            """,
            (prediction_id,)
        )

        case = cursor.fetchone()

        if case is None:
            flash(
                "Patient case not found.",
                "danger"
            )
            return redirect(
                url_for("doctor_dashboard")
            )

        # ====================================================
        # GET EXISTING DOCTOR REVIEW
        # ====================================================

        cursor.execute(
            """
            SELECT
                review_id,
                review_status,
                doctor_decision,
                diagnosis_notes,
                recommendations,
                prediction_agreement,
                reviewed_at

            FROM doctor_reviews

            WHERE prediction_id = %s
              AND doctor_id = %s

            ORDER BY review_id DESC

            LIMIT 1
            """,
            (
                prediction_id,
                doctor_id
            )
        )

        doctor_review = cursor.fetchone()

        

        # ====================================================
        # CALCULATE DISPLAY VALUES
        # ====================================================

        case["risk_probability_percent"] = round(
            float(case["risk_probability"]) * 100,
            2
        )

        if case["prediction_result"] == 1:

            case["prediction_label"] = (
                "Heart Disease Risk Detected"
            )

        else:

            case["prediction_label"] = (
                "No Heart Disease Risk Detected"
            )

        # ====================================================
        # RENDER CASE
        # ====================================================

        return render_template(
            "doctor_case_details.html",
            case=case,
            doctor_review=doctor_review,
            name=session.get("full_name")
        )

    except Exception as e:

        print(
            "Doctor case details error:",
            e
        )

        flash(
            "Unable to load patient case.",
            "danger"
        )

        return redirect(
            url_for("doctor_dashboard")
        )

    finally:

        cursor.close()
        connection.close()
# ============================================================
# DOCTOR CLINICAL REVIEW
# ============================================================

@app.route("/doctor/case/<int:prediction_id>/review", methods=["POST"])
def submit_doctor_review(prediction_id):

    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("login"))

    if session.get("role") != "doctor":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    connection = get_db_connection()

    if connection is None:
        flash("Unable to connect to database.", "danger")
        return redirect(
            url_for(
                "doctor_case_details",
                prediction_id=prediction_id
            )
        )

    cursor = connection.cursor(dictionary=True)

    try:

        # ====================================================
        # VERIFY DOCTOR PROFILE
        # ====================================================

        cursor.execute(
            """
            SELECT
                doctor_id,
                verification_status
            FROM doctors
            WHERE user_id = %s
            LIMIT 1
            """,
            (session["user_id"],)
        )

        doctor = cursor.fetchone()

        if doctor is None:
            flash(
                "Doctor profile not found.",
                "danger"
            )
            return redirect(
                url_for("doctor_dashboard")
            )

        if doctor["verification_status"] != "VERIFIED":
            flash(
                "Access denied. Your doctor profile is not verified.",
                "danger"
            )
            return redirect(
                url_for("doctor_dashboard")
            )

        doctor_id = doctor["doctor_id"]

        # ====================================================
        # VERIFY PREDICTION EXISTS
        # ====================================================

        cursor.execute(
            """
            SELECT prediction_id
            FROM predictions
            WHERE prediction_id = %s
            LIMIT 1
            """,
            (prediction_id,)
        )

        prediction = cursor.fetchone()

        if prediction is None:
            flash(
                "Prediction record not found.",
                "danger"
            )
            return redirect(
                url_for("doctor_dashboard")
            )

        # ====================================================
        # GET FORM DATA
        # ====================================================

        doctor_decision = request.form.get(
            "doctor_decision",
            ""
        ).strip()

        diagnosis_notes = request.form.get(
            "diagnosis_notes",
            ""
        ).strip()

        recommendations = request.form.get(
            "recommendations",
            ""
        ).strip()

        prediction_agreement = request.form.get(
            "prediction_agreement"
        )

        # ====================================================
        # VALIDATE DECISION
        # ====================================================

        allowed_decisions = [
            "LOW_RISK",
            "MODERATE_RISK",
            "HIGH_RISK",
            "INCONCLUSIVE"
        ]

        if doctor_decision not in allowed_decisions:

            flash(
                "Please select a valid clinical decision.",
                "danger"
            )

            return redirect(
                url_for(
                    "doctor_case_details",
                    prediction_id=prediction_id
                )
            )

        # ====================================================
        # CONVERT AGREEMENT TO INTEGER
        # ====================================================

        if prediction_agreement == "YES":
            agreement_value = 1

        elif prediction_agreement == "NO":
            agreement_value = 0

        else:
            agreement_value = None

        # ====================================================
        # CHECK EXISTING REVIEW
        # ====================================================

        cursor.execute(
            """
            SELECT review_id
            FROM doctor_reviews
            WHERE prediction_id = %s
              AND doctor_id = %s
            ORDER BY review_id DESC
            LIMIT 1
            """,
            (
                prediction_id,
                doctor_id
            )
        )

        existing_review = cursor.fetchone()

        if existing_review:

            # =================================================
            # UPDATE EXISTING REVIEW
            # =================================================

            cursor.execute(
                """
                UPDATE doctor_reviews
                SET
                    review_status = 'REVIEWED',
                    doctor_decision = %s,
                    diagnosis_notes = %s,
                    recommendations = %s,
                    prediction_agreement = %s,
                    reviewed_at = CURRENT_TIMESTAMP
                WHERE review_id = %s
                """,
                (
                    doctor_decision,
                    diagnosis_notes,
                    recommendations,
                    agreement_value,
                    existing_review["review_id"]
                )
            )

        else:

            # =================================================
            # CREATE NEW REVIEW
            # =================================================

            cursor.execute(
                """
                INSERT INTO doctor_reviews
                (
                    prediction_id,
                    doctor_id,
                    review_status,
                    doctor_decision,
                    diagnosis_notes,
                    recommendations,
                    prediction_agreement,
                    reviewed_at
                )
                VALUES
                (
                    %s,
                    %s,
                    'REVIEWED',
                    %s,
                    %s,
                    %s,
                    %s,
                    CURRENT_TIMESTAMP
                )
                """,
                (
                    prediction_id,
                    doctor_id,
                    doctor_decision,
                    diagnosis_notes,
                    recommendations,
                    agreement_value
                )
            )

        connection.commit()

        flash(
            "Doctor clinical review saved successfully.",
            "success"
        )

        return redirect(
            url_for(
                "doctor_case_details",
                prediction_id=prediction_id
            )
        )

    except Exception as e:

        connection.rollback()

        print(
            "Doctor review error:",
            e
        )

        flash(
            "Unable to save doctor review.",
            "danger"
        )

        return redirect(
            url_for(
                "doctor_case_details",
                prediction_id=prediction_id
            )
        )

    finally:

        cursor.close()
        connection.close()

# ============================================================
# DOCTOR REVIEWS
# ============================================================

@app.route("/doctor/reviews")
def doctor_reviews():

    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("login"))

    if session.get("role") != "doctor":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    connection = get_db_connection()

    if connection is None:
        flash("Unable to connect to database.", "danger")
        return redirect(url_for("doctor_dashboard"))

    cursor = connection.cursor(dictionary=True)

    try:

        # ====================================================
        # VERIFY DOCTOR PROFILE
        # ====================================================

        cursor.execute(
            """
            SELECT
                doctor_id,
                verification_status
            FROM doctors
            WHERE user_id = %s
            LIMIT 1
            """,
            (session["user_id"],)
        )

        doctor = cursor.fetchone()

        if doctor is None:
            flash("Doctor profile not found.", "danger")
            return redirect(url_for("doctor_dashboard"))

        if doctor["verification_status"] != "VERIFIED":
            flash(
                "Access denied. Your doctor profile is not verified.",
                "danger"
            )
            return redirect(url_for("doctor_dashboard"))

        doctor_id = doctor["doctor_id"]

        # ====================================================
        # GET PREDICTIONS + REVIEW STATUS
        # ====================================================

        cursor.execute(
            """
            SELECT
                p.prediction_id,
                p.prediction_result,
                p.risk_probability,
                p.risk_level,
                p.model_name,
                p.model_version,
                p.prediction_status,
                p.qaml_prediction,
                p.qaml_quantum_score,
                p.created_at AS prediction_date,

                e.extraction_id,

                m.report_id,
                m.report_type,
                m.original_file_name,

                u.user_id AS patient_id,
                u.full_name AS patient_name,

                dr.review_id,
                dr.review_status,
                dr.doctor_decision,
                dr.diagnosis_notes,
                dr.recommendations,
                dr.prediction_agreement,
                dr.reviewed_at

            FROM predictions p

            JOIN extracted_features e
                ON p.extraction_id = e.extraction_id

            JOIN medical_reports m
                ON e.report_id = m.report_id

            JOIN users u
                ON m.patient_id = u.user_id

            LEFT JOIN doctor_reviews dr
                ON p.prediction_id = dr.prediction_id
                AND dr.doctor_id = %s

            WHERE p.prediction_status = 'COMPLETED'

            ORDER BY
                CASE
                    WHEN dr.review_status = 'REVIEWED'
                    THEN 1
                    ELSE 0
                END,
                p.created_at DESC
            """,
            (doctor_id,)
        )

        reviews = cursor.fetchall()

        # ====================================================
        # DISPLAY VALUES
        # ====================================================

        for review in reviews:

            if review["risk_probability"] is not None:

                review["risk_probability_percent"] = round(
                    float(review["risk_probability"]) * 100,
                    2
                )

            else:

                review["risk_probability_percent"] = 0

            if review["review_status"] == "REVIEWED":

                review["display_review_status"] = "REVIEWED"

            else:

                review["display_review_status"] = "PENDING"

        # ====================================================
        # SEND DATA TO HTML
        # ====================================================

        return render_template(
            "doctor_review_queue.html",
            name=session.get("full_name"),
            reviews=reviews
        )

    except Exception as e:

        print(
            "Doctor reviews error:",
            e
        )

        flash(
            "Unable to load clinical reviews.",
            "danger"
        )

        return redirect(
            url_for("doctor_dashboard")
        )

    finally:

        cursor.close()
        connection.close()

# ============================================================
# ADMIN DASHBOARD
# ============================================================
@app.route("/admin/dashboard")
def admin_dashboard():

    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    connection = get_db_connection()

    if connection is None:
        flash("Unable to connect to database.", "danger")
        return redirect(url_for("home"))

    cursor = connection.cursor(dictionary=True)

    try:

        # Total Patients
        cursor.execute(
            """
            SELECT COUNT(*) AS total_patients
            FROM users
            WHERE role = 'patient'
            """
        )
        total_patients = cursor.fetchone()["total_patients"]

        # Total Doctors
        cursor.execute(
            """
            SELECT COUNT(*) AS total_doctors
            FROM users
            WHERE role = 'doctor'
            """
        )
        total_doctors = cursor.fetchone()["total_doctors"]

        # Verified Doctors
        cursor.execute(
            """
            SELECT COUNT(*) AS verified_doctors
            FROM doctors
            WHERE verification_status = 'VERIFIED'
            """
        )
        verified_doctors = cursor.fetchone()["verified_doctors"]

        # Total Predictions
        cursor.execute(
            """
            SELECT COUNT(*) AS total_predictions
            FROM predictions
            """
        )
        total_predictions = cursor.fetchone()["total_predictions"]

        # Total Medical Reports
        cursor.execute(
            """
            SELECT COUNT(*) AS total_reports
            FROM medical_reports
            """
        )
        total_reports = cursor.fetchone()["total_reports"]

        # Pending Doctor Reviews
        cursor.execute(
            """
            SELECT COUNT(*) AS pending_reviews
            FROM predictions p
            WHERE p.prediction_status = 'COMPLETED'
            AND NOT EXISTS (
                SELECT 1
                FROM doctor_reviews dr
                WHERE dr.prediction_id = p.prediction_id
                AND dr.review_status = 'REVIEWED'
            )
            """
        )
        pending_reviews = cursor.fetchone()["pending_reviews"]

        return render_template(
            "admin_dashboard.html",
            name=session.get("full_name"),
            total_patients=total_patients,
            total_doctors=total_doctors,
            verified_doctors=verified_doctors,
            total_predictions=total_predictions,
            total_reports=total_reports,
            pending_reviews=pending_reviews
        )

    except Exception as e:

        print("Admin dashboard error:", e)

        flash(
            "Unable to load admin dashboard.",
            "danger"
        )

        return redirect(url_for("home"))

    finally:

        cursor.close()
        connection.close()

# ============================================================
# UPLOAD MEDICAL REPORT
# ============================================================
@app.route("/upload-report", methods=["GET", "POST"])
def upload_report():

    # ========================================================
    # LOGIN REQUIRED
    # ========================================================

    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("login"))

    if session.get("role") != "patient":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    # ========================================================
    # SHOW UPLOAD PAGE
    # ========================================================

    if request.method == "GET":
        return render_template("upload_report.html")

    # ========================================================
    # GET FORM DATA
    # ========================================================

    report_type = request.form.get("report_type")

    uploaded_file = request.files.get("report_file")
    



    if not report_type:
        flash("Please select a report type.", "danger")
        return redirect(request.url)

    if uploaded_file is None:
        flash("Please select a file.", "danger")
        return redirect(request.url)

    if uploaded_file.filename == "":
        flash("Please select a file.", "danger")
        return redirect(request.url)

    # Validate actual PDF file signature
    uploaded_file.stream.seek(0)
    file_signature = uploaded_file.stream.read(5)
    uploaded_file.stream.seek(0)

    if file_signature != b"%PDF-":
        flash(
            "Invalid PDF file. Please upload a valid PDF medical report.",
            "danger"
        )
        return redirect(request.url)

    # ========================================================
    # FILE VALIDATION
    # ========================================================

    if not allowed_file(uploaded_file.filename):
        flash(
            "Invalid file type. Only PDF medical reports are supported.",
            "danger"
        )
        return redirect(request.url)
    # ========================================================
    # SECURE ORIGINAL FILE NAME
    # ========================================================

    original_filename = secure_filename(
        uploaded_file.filename
    )

    extension = (
        original_filename
        .rsplit(".", 1)[1]
        .lower()
    )

    # ========================================================
    # GENERATE UNIQUE FILE NAME
    # ========================================================

    unique_filename = (
        str(uuid.uuid4())
        + "."
        + extension
    )

    # ========================================================
    # SELECT UPLOAD FOLDER
    # ========================================================

    folder = UPLOAD_FOLDERS.get(
        report_type,
        "uploads/other"
    )

    os.makedirs(
        folder,
        exist_ok=True
    )

    # ========================================================
    # COMPLETE FILE PATH
    # ========================================================

    filepath = os.path.join(
        folder,
        unique_filename
    )

    # ========================================================
    # SAVE FILE
    # ========================================================

    try:

        uploaded_file.save(filepath)

        file_size = os.path.getsize(
            filepath
        )

    except Exception as e:

        print(
            "File save error:",
            e
        )

        flash(
            "Unable to save uploaded file.",
            "danger"
        )

        return redirect(request.url)

    # ========================================================
    # SAVE REPORT INFORMATION
    # ========================================================

    connection = get_db_connection()

    if connection is None:

        flash(
            "Database connection failed.",
            "danger"
        )

        return redirect(request.url)

    cursor = connection.cursor()

    report_id = None

    try:

        patient_id = session["user_id"]

        cursor.execute(
            """
            INSERT INTO medical_reports
            (
                patient_id,
                report_type,
                original_file_name,
                stored_file_name,
                file_path,
                file_type,
                file_size,
                processing_status
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            """,
            (
                patient_id,
                report_type,
                original_filename,
                unique_filename,
                filepath,
                extension,
                file_size,
                "PROCESSING"
            )
        )

        connection.commit()

        report_id = cursor.lastrowid

        print(
            f"Medical report saved. "
            f"Report ID: {report_id}"
        )

    except Exception as e:

        connection.rollback()

        print(
            "Medical report database error:",
            e
        )

        flash(
            "Unable to save report information.",
            "danger"
        )

        return redirect(request.url)

    finally:

        cursor.close()
        connection.close()

    # ========================================================
    # AI PROCESSING
    # ========================================================

    # Currently automatic processing is enabled for PDF.
    # OCR/image processing will be added in the next stage.

    if extension == "pdf":

        try:

            extraction_id = save_extracted_features(
                report_id,
                filepath
            )

            if not extraction_id:

                raise Exception(
                    "Feature extraction failed."
                )

            # ------------------------------------------------
            # Update report status based on extraction
            # ------------------------------------------------

            connection = get_db_connection()

            if connection:

                cursor = connection.cursor()

                cursor.execute(
                    """
                    SELECT validation_status
                    FROM extracted_features
                    WHERE extraction_id = %s
                    """,
                    (extraction_id,)
                )

                extraction = cursor.fetchone()

                cursor.close()
                connection.close()

                if extraction:

                    validation_status = extraction[0]

                else:

                    validation_status = (
                        "NEEDS_REVIEW"
                    )

            else:

                validation_status = (
                    "NEEDS_REVIEW"
                )

            # ------------------------------------------------
            # Run ML only when extraction is VALID
            # ------------------------------------------------

            if validation_status == "VALID":

                prediction_success = (
                    predict_from_extraction(
                        patient_id=session["user_id"],
                        extraction_id=extraction_id
                    )
                )

                if prediction_success:

                    connection = get_db_connection()

                    if connection:

                        cursor = connection.cursor()

                        cursor.execute(
                            """
                            UPDATE medical_reports
                            SET processing_status = 'PROCESSED'
                            WHERE report_id = %s
                            """,
                            (report_id,)
                        )

                        connection.commit()

                        cursor.close()
                        connection.close()

                    return redirect(
                        url_for(
                            "prediction_result",
                            extraction_id=extraction_id
                        )
                    )

            else:

                connection = get_db_connection()

                if connection:

                    cursor = connection.cursor()

                    cursor.execute(
                        """
                        UPDATE medical_reports
                        SET processing_status = 'NEEDS_REVIEW'
                        WHERE report_id = %s
                        """,
                        (report_id,)
                    )

                    connection.commit()

                    cursor.close()
                    connection.close()

                flash(
                    "Report uploaded, but some clinical "
                    "features require review before prediction.",
                    "warning"
                )

                return redirect(
                    url_for("patient_dashboard")
                )

        except Exception as e:

            print(
                "AI processing error:",
                e
            )

            connection = get_db_connection()

            if connection:

                cursor = connection.cursor()

                cursor.execute(
                    """
                    UPDATE medical_reports
                    SET processing_status = 'FAILED'
                    WHERE report_id = %s
                    """,
                    (report_id,)
                )

                connection.commit()

                cursor.close()
                connection.close()

            flash(
                "Report uploaded, but AI processing failed.",
                "danger"
            )

            return redirect(
                url_for("patient_dashboard")
            )



    return redirect(
        url_for("patient_dashboard")
    )



@app.route("/prediction-result/<int:extraction_id>")
def prediction_result(extraction_id):

    # ========================================================
    # LOGIN REQUIRED
    # ========================================================

    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("login"))

    if session.get("role") != "patient":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    connection = get_db_connection()

    if connection is None:
        flash("Database connection failed.", "danger")
        return redirect(url_for("patient_dashboard"))

    cursor = connection.cursor(dictionary=True)

    try:

        # ====================================================
        # LOAD EXTRACTION + REPORT
        # ====================================================

        cursor.execute(
            """
            SELECT
                e.extraction_id,
                e.report_id,

                e.age,
                e.sex,
                e.chest_pain_type,
                e.resting_bp,
                e.cholesterol,
                e.fasting_blood_sugar,
                e.resting_ecg,
                e.max_heart_rate,
                e.exercise_angina,
                e.oldpeak,
                e.st_slope,

                e.ecg_quality,
                e.ventricular_rate,
                e.pr_interval,
                e.qrs_duration,
                e.qtc_interval,
                e.cardiac_axis,
                e.sinus_rhythm,
                e.av_conduction,

                e.extraction_confidence,
                e.validation_status,

                m.report_id AS medical_report_id,
                m.report_type,
                m.original_file_name,
                m.processing_status

            FROM extracted_features e

            INNER JOIN medical_reports m
                ON e.report_id = m.report_id

            WHERE
                e.extraction_id = %s
                AND m.patient_id = %s

            LIMIT 1
            """,
            (
                extraction_id,
                session["user_id"]
            )
        )

        extraction = cursor.fetchone()

        if extraction is None:
            flash(
                "Assessment information not found.",
                "danger"
            )
            return redirect(
                url_for("patient_dashboard")
            )

        report = {
            "report_id": extraction["report_id"],
            "report_type": extraction["report_type"],
            "processing_status": extraction["processing_status"],
            "original_file_name": extraction["original_file_name"],
        }
        # ====================================================
        # LOAD AI PREDICTION IF ONE EXISTS
        # ====================================================

        cursor.execute(
            """
            SELECT
                p.prediction_id,
                p.extraction_id,
                p.prediction_result,
                p.risk_probability,
                p.qaml_prediction,
                p.qaml_quantum_score,
                p.risk_level,
                p.model_name,
                p.model_version,
                p.prediction_status,
                p.created_at

            FROM predictions p

            WHERE
                p.extraction_id = %s
                AND p.patient_id = %s

            ORDER BY p.prediction_id DESC

            LIMIT 1
            """,
            (
                extraction_id,
                session["user_id"]
            )
        )

        prediction = cursor.fetchone()

        # ====================================================
        # AI PREDICTION EXISTS
        # ====================================================

        if prediction is not None:

            # Add extraction information to prediction object
            prediction.update({
                "extraction_id": extraction["extraction_id"],
                "report_id": extraction["report_id"],
                "report_type": extraction["report_type"],
                "original_file_name": extraction["original_file_name"],
                "processing_status": extraction["processing_status"],

                "age": extraction["age"],
                "sex": extraction["sex"],
                "chest_pain_type": extraction["chest_pain_type"],
                "resting_bp": extraction["resting_bp"],
                "cholesterol": extraction["cholesterol"],
                "fasting_blood_sugar": extraction["fasting_blood_sugar"],
                "resting_ecg": extraction["resting_ecg"],
                "max_heart_rate": extraction["max_heart_rate"],
                "exercise_angina": extraction["exercise_angina"],
                "oldpeak": extraction["oldpeak"],
                "st_slope": extraction["st_slope"],

                "extraction_confidence":
                    extraction["extraction_confidence"],

                "validation_status":
                    extraction["validation_status"]
            })

            # =================================================
            # DOCTOR REVIEW OF AI PREDICTION
            # =================================================

            cursor.execute(
                """
                SELECT
                    review_status,
                    doctor_decision,
                    diagnosis_notes,
                    recommendations,
                    prediction_agreement,
                    reviewed_at

                FROM doctor_reviews

                WHERE prediction_id = %s

                ORDER BY review_id DESC

                LIMIT 1
                """,
                (prediction["prediction_id"],)
            )

            prediction["doctor_review"] = cursor.fetchone()

            # Convert probability to percentage
            prediction["risk_probability_percent"] = round(
                float(prediction["risk_probability"]) * 100,
                2
            )

            # Human-readable result
            if prediction["prediction_result"] == 1:
                prediction["result_text"] = (
                    "Heart Disease Risk Detected"
                )
            else:
                prediction["result_text"] = (
                    "No Heart Disease Risk Detected"
                )

            return render_template(
                "prediction_result.html",
                prediction=prediction,
                report=report,
                assessment_state="AI_PREDICTION",
                name=session.get("full_name")
            )

        # ====================================================
        # NO AI PREDICTION
        # ====================================================
        # This is expected when extraction is NEEDS_REVIEW.
        # AI prediction must NOT be generated from incomplete
        # or unvalidated clinical information.
        # ====================================================

        if extraction["validation_status"] == "NEEDS_REVIEW":

            cursor.execute(
                """
                SELECT
                    review_id,
                    review_status,
                    doctor_decision,
                    diagnosis_notes,
                    recommendations,
                    reviewed_at

                FROM report_doctor_reviews

                WHERE report_id = %s

                ORDER BY review_id DESC

                LIMIT 1
                """,
                (extraction["report_id"],)
            )

            report_review = cursor.fetchone()

            return render_template(
                "prediction_result.html",
                prediction=None,
                extraction=extraction,
                report=report,
                report_review=report_review,
                assessment_state=(
                    "DOCTOR_REVIEW_COMPLETED"
                    if report_review
                    else "DOCTOR_REVIEW_REQUIRED"
                ),
                name=session.get("full_name")
            )

        # ====================================================
        # SAFE FALLBACK FOR INCONSISTENT DATA
        # ====================================================

        flash(
            "This assessment cannot currently be displayed because "
            "its prediction state is inconsistent.",
            "warning"
        )

        return redirect(
            url_for("patient_dashboard")
        )

    except Exception as e:

        print(
            "Prediction result error:",
            e
        )

        flash(
            "Unable to load assessment result.",
            "danger"
        )

        return redirect(
            url_for("patient_dashboard")
        )

    finally:

        cursor.close()
        connection.close()

# ============================================================
# HEART DISEASE PREDICTION
# Existing ML pipeline preserved
# ============================================================


@app.route("/admin/patients")
def admin_patients():

    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    connection = get_db_connection()

    if connection is None:
        flash("Database connection failed.", "danger")
        return redirect(url_for("admin_dashboard"))

    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                user_id,
                full_name,
                email,
                phone,
                is_active,
                created_at
            FROM users
            WHERE role = 'patient'
            ORDER BY created_at DESC
        """)

        patients = cursor.fetchall()

    except Exception as e:
        print("Admin patients error:", e)
        flash("Unable to load patients.", "danger")
        patients = []

    finally:
        cursor.close()
        connection.close()

    return render_template(
        "admin_patients.html",
        patients=patients,
        name=session.get("full_name")
    )

@app.route("/admin/doctors")
def admin_doctors():

    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    connection = get_db_connection()

    if connection is None:
        flash("Database connection failed.", "danger")
        return redirect(url_for("admin_dashboard"))

    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                u.user_id,
                u.full_name,
                u.email,
                u.phone,
                u.is_active,
                u.created_at,
                d.doctor_id,
                d.specialization,
                d.medical_license_number,
                d.qualification,
                d.hospital_name,
                d.experience_years,
                d.verification_status
            FROM users u
            LEFT JOIN doctors d
                ON u.user_id = d.user_id
            WHERE u.role = 'doctor'
            ORDER BY u.created_at DESC
        """)

        doctors = cursor.fetchall()

    except Exception as e:
        print("Admin doctors error:", e)
        flash("Unable to load doctors.", "danger")
        doctors = []

    finally:
        cursor.close()
        connection.close()

    return render_template(
        "admin_doctors.html",
        doctors=doctors,
        name=session.get("full_name")
    )

@app.route("/admin/verify-doctors")
def verify_doctors():

    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    connection = get_db_connection()

    if connection is None:
        flash("Database connection failed.", "danger")
        return redirect(url_for("admin_dashboard"))

    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                d.doctor_id,
                u.user_id,
                u.full_name,
                u.email,
                u.phone,
                d.specialization,
                d.medical_license_number,
                d.qualification,
                d.hospital_name,
                d.experience_years,
                d.verification_status,
                d.created_at
            FROM doctors d
            INNER JOIN users u
                ON d.user_id = u.user_id
            WHERE u.role = 'doctor'
            ORDER BY
                CASE
                    WHEN d.verification_status = 'PENDING' THEN 1
                    WHEN d.verification_status = 'VERIFIED' THEN 2
                    WHEN d.verification_status = 'REJECTED' THEN 3
                    ELSE 4
                END,
                d.created_at DESC
        """)

        doctors = cursor.fetchall()

    except Exception as e:
        print("Verify doctors error:", e)
        flash("Unable to load doctor verification records.", "danger")
        doctors = []

    finally:
        cursor.close()
        connection.close()

    return render_template(
        "admin_verify_doctors.html",
        doctors=doctors,
        name=session.get("full_name")
    )

@app.route("/admin/verify-doctor/<int:doctor_id>/<action>", methods=["POST"])
def admin_verify_doctor(doctor_id, action):

    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    if action not in ["verify", "reject"]:
        flash("Invalid verification action.", "danger")
        return redirect(url_for("verify_doctors"))

    new_status = "VERIFIED" if action == "verify" else "REJECTED"

    connection = get_db_connection()

    if connection is None:
        flash("Database connection failed.", "danger")
        return redirect(url_for("verify_doctors"))

    cursor = connection.cursor()

    try:
        cursor.execute("""
            UPDATE doctors
            SET verification_status = %s
            WHERE doctor_id = %s
        """, (new_status, doctor_id))

        if cursor.rowcount == 0:
            flash("Doctor profile not found.", "danger")
        else:
            connection.commit()

            if action == "verify":
                flash("Doctor verified successfully.", "success")
            else:
                flash("Doctor rejected successfully.", "warning")

    except Exception as e:
        connection.rollback()
        print("Doctor verification error:", e)
        flash("Unable to update doctor verification status.", "danger")

    finally:
        cursor.close()
        connection.close()

    return redirect(url_for("verify_doctors"))

@app.route("/admin/predictions")
def admin_predictions():

    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    connection = get_db_connection()

    if connection is None:
        flash("Database connection failed.", "danger")
        return redirect(url_for("admin_dashboard"))

    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                p.prediction_id,
                p.patient_id,
                u.full_name AS patient_name,
                p.extraction_id,
                p.model_name,
                p.model_version,
                p.prediction_result,
                p.risk_probability,
                p.risk_level,
                p.prediction_status,
                p.qaml_prediction,
                p.qaml_quantum_score,
                p.created_at
            FROM predictions p
            LEFT JOIN users u
                ON p.patient_id = u.user_id
            ORDER BY p.created_at DESC
        """)

        predictions = cursor.fetchall()

    except Exception as e:
        print("Admin predictions error:", e)
        flash("Unable to load prediction records.", "danger")
        predictions = []

    finally:
        cursor.close()
        connection.close()

    return render_template(
        "admin_predictions.html",
        predictions=predictions,
        name=session.get("full_name")
    )

@app.route("/admin/model-info")
def admin_model_info():

    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    return render_template(
        "admin_model_info.html",
        name=session.get("full_name")
    )

@app.route("/admin/logs")
def admin_logs():

    if "user_id" not in session:
        flash("Please login first.", "danger")
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        flash("Access denied.", "danger")
        return redirect(url_for("home"))

    connection = get_db_connection()

    if connection is None:
        flash("Database connection failed.", "danger")
        return redirect(url_for("admin_dashboard"))

    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                l.log_id,
                l.user_id,
                u.full_name,
                u.role,
                l.action,
                l.description,
                l.ip_address,
                l.created_at
            FROM system_logs l
            LEFT JOIN users u
                ON l.user_id = u.user_id
            ORDER BY l.created_at DESC
        """)

        logs = cursor.fetchall()

    except Exception as e:
        print("Admin logs error:", e)
        flash("Unable to load system logs.", "danger")
        logs = []

    finally:
        cursor.close()
        connection.close()

    return render_template(
        "admin_logs.html",
        logs=logs,
        name=session.get("full_name")
    )

# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":
    app.run(debug=False)
