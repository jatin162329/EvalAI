from flask import Flask, render_template, request, redirect, url_for, session, send_file
import os
import json
import re
from werkzeug.utils import secure_filename
from reportlab.pdfgen import canvas

from evaluator import evaluate_assignment


app = Flask(__name__)
app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "evalai-demo-secret-key"
)


# ============================================================
# FOLDERS
# ============================================================

UPLOAD_FOLDER = "uploads"
REPORT_FOLDER = "reports"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORT_FOLDER, exist_ok=True)


# ============================================================
# DATA FILES
# ============================================================

SCORES_FILE = "scores.json"
SUBMISSIONS_FILE = "submissions.json"
EVALUATIONS_FILE = "evaluations.json"
ASSIGNMENTS_FILE = "assignments.json"


# ============================================================
# TEACHERS
# ============================================================

TEACHERS = {

    "T001": {
        "name": "Dr. Sharma",
        "department": "Artificial Intelligence & Machine Learning"
    },

    "T002": {
        "name": "Prof. Kumar",
        "department": "Artificial Intelligence & Machine Learning"
    }

}


# ============================================================
# STUDENTS
# ============================================================

STUDENTS = {

    "RA001": {
        "name": "Arjun",
        "section": "C",
        "department": "Artificial Intelligence & Machine Learning"
    },

    "RA002": {
        "name": "Priya",
        "section": "F",
        "department": "Artificial Intelligence & Machine Learning"
    },

    "RA003": {
        "name": "Rahul",
        "section": "H",
        "department": "Artificial Intelligence & Machine Learning"
    },

    "RA004": {
        "name": "Kiran",
        "section": "C",
        "department": "Artificial Intelligence & Machine Learning"
    },

    "RA005": {
        "name": "Sneha",
        "section": "C",
        "department": "Artificial Intelligence & Machine Learning"
    },

    "RA006": {
        "name": "Ananya",
        "section": "F",
        "department": "Artificial Intelligence & Machine Learning"
    },

    "RA007": {
        "name": "Rohit",
        "section": "F",
        "department": "Artificial Intelligence & Machine Learning"
    },

    "RA008": {
        "name": "Varun",
        "section": "H",
        "department": "Artificial Intelligence & Machine Learning"
    },

    "RA009": {
        "name": "Neha",
        "section": "H",
        "department": "Artificial Intelligence & Machine Learning"
    }

}


# ============================================================
# DEFAULT SCORES
# ============================================================

DEFAULT_SCORES = {

    "Arjun": 9,
    "Priya": 8,
    "Rahul": 7,
    "Kiran": 9,
    "Sneha": 8,
    "Ananya": 7,
    "Rohit": 9,
    "Varun": 8,
    "Neha": 7

}


# ============================================================
# JSON FUNCTIONS
# ============================================================

def load_json(filename, default):

    if not os.path.exists(filename):
        return default

    try:

        with open(
            filename,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except:

        return default


def save_json(filename, data):

    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=4
        )


def load_assignments():
    return load_json(ASSIGNMENTS_FILE, {})


def save_assignments(assignments):
    save_json(ASSIGNMENTS_FILE, assignments)


def load_scores():

    return load_json(
        SCORES_FILE,
        DEFAULT_SCORES.copy()
    )


def save_scores(scores):

    save_json(
        SCORES_FILE,
        scores
    )


# ============================================================
# INITIALIZE SCORES
# ============================================================

if not os.path.exists(SCORES_FILE):

    save_scores(
        DEFAULT_SCORES
    )


# ============================================================
# LOGIN HELPERS
# ============================================================

def teacher_logged_in():

    return session.get("role") == "teacher"


def student_logged_in():

    return session.get("role") == "student"


# ============================================================
# ============================================================
# SUBMISSION / EVALUATION HELPERS
# ============================================================

def normalize_records(records):

    normalized = {}

    for registration, value in records.items():

        if not isinstance(value, dict):
            continue

        # Old format:
        # {"RA001": {"assignment_id": "A001", ...}}
        if "assignment_id" in value:

            assignment_id = value.get("assignment_id")

            if assignment_id:
                normalized.setdefault(registration, {})[assignment_id] = value

        else:
            # New format:
            # {"RA001": {"A001": {...}, "A002": {...}}}
            normalized[registration] = value

    return normalized


def load_submissions():

    raw = load_json(
        SUBMISSIONS_FILE,
        {}
    )

    normalized = normalize_records(raw)

    # Automatically upgrade old submission data on disk.
    if normalized != raw:
        save_json(SUBMISSIONS_FILE, normalized)

    return normalized


def save_submissions(submissions):

    save_json(
        SUBMISSIONS_FILE,
        submissions
    )


def load_evaluations():

    raw = load_json(
        EVALUATIONS_FILE,
        {}
    )

    normalized = normalize_records(raw)

    if normalized != raw:
        save_json(EVALUATIONS_FILE, normalized)

    return normalized


def save_evaluations(evaluations):

    save_json(
        EVALUATIONS_FILE,
        evaluations
    )


def get_student_submission(registration, assignment_id):

    submissions = load_submissions()

    return submissions.get(
        registration,
        {}
    ).get(assignment_id)


def get_student_evaluation(registration, assignment_id):

    evaluations = load_evaluations()

    return evaluations.get(
        registration,
        {}
    ).get(assignment_id)


def get_assignment_status(registration, assignment_id):

    submission = get_student_submission(
        registration,
        assignment_id
    )

    evaluation = get_student_evaluation(
        registration,
        assignment_id
    )

    if not submission:
        return "Not Submitted"

    if evaluation:

        if evaluation.get(
            "manual_updated",
            False
        ):
            return "Evaluation Updated"

        return "Submitted / Evaluated"

    return "Submitted / Pending Evaluation"


def get_submission_status(registration):
    """Overall student status used by the teacher dashboard."""

    assignments = load_assignments()

    student_assignments = [
        assignment
        for assignment in assignments.values()
        if assignment_has_section(
            assignment,
            STUDENTS.get(registration, {}).get("section")
        )
        and assignment.get("published", False)
    ]

    if not student_assignments:
        return "Not Submitted"

    statuses = [
        get_assignment_status(
            registration,
            assignment["id"]
        )
        for assignment in student_assignments
    ]

    if any(status == "Evaluation Updated" for status in statuses):
        return "Evaluation Updated"

    if any(status == "Submitted / Evaluated" for status in statuses):
        return "Submitted / Evaluated"

    if any(status == "Submitted / Pending Evaluation" for status in statuses):
        return "Submitted / Pending Evaluation"

    return "Not Submitted"



# ============================================================
# REPORT HELPERS
# ============================================================

def build_demo_report(score, total_marks=10):
    """Create visible feedback when an older evaluation has no report text."""

    try:
        score = float(score)
    except (TypeError, ValueError):
        score = 0

    try:
        total_marks = float(total_marks)
    except (TypeError, ValueError):
        total_marks = 10

    if total_marks <= 0:
        total_marks = 10

    percentage = round((score / total_marks) * 100, 1)

    return f"""EVALAI - ASSIGNMENT EVALUATION
================================

EVALUATION SUMMARY
------------------
Total Marks: {score:g} / {total_marks:g}
Percentage: {percentage:g}%


QUESTION-WISE EVALUATION
------------------------
The submission has been evaluated successfully.

The final score recorded by EvalAI is shown above.


STRENGTHS
---------
- The assignment was submitted successfully.
- The submission has been evaluated.


WEAK TOPICS
-----------
- Review the questions where marks were lost.
- Strengthen explanations and supporting examples.


SUGGESTIONS
-----------
- Review the evaluation carefully.
- Give clearer explanations in future answers.
- Add relevant examples wherever appropriate.


OVERALL FEEDBACK
----------------
Your assignment has been evaluated. Use the score and
feedback to improve your next submission.
"""


def select_student_evaluation(registration, assignment_id=None):
    """Return an evaluation from either old or assignment-based storage."""

    evaluations = load_evaluations()
    raw = evaluations.get(registration)

    if not isinstance(raw, dict) or not raw:
        return None

    # Old format:
    # RA001 -> {"assignment_id": "A001", "result": "...", ...}
    if "assignment_id" in raw:
        return raw

    # New format:
    # RA001 -> {"A001": {...}, "A002": {...}}
    if assignment_id:
        selected = raw.get(str(assignment_id).strip().upper())
        if isinstance(selected, dict):
            return selected
        return None

    selected = None

    for item in raw.values():
        if isinstance(item, dict):
            selected = item

    return selected


def ensure_evaluation_report(evaluation, score=None, total_marks=10):
    """Guarantee that the report area receives visible text."""

    if not evaluation:
        return None

    evaluation = evaluation.copy()

    report = evaluation.get("result")

    if report is None or not str(report).strip():

        if score is None:
            score = evaluation.get(
                "final_score",
                evaluation.get("score", 0)
            )

        evaluation["result"] = build_demo_report(
            score,
            total_marks
        )

    return evaluation


# HOME
# ============================================================

@app.route("/")
def home():

    return render_template(
        "login.html"
    )


# ============================================================
# TEACHER LOGIN
# ============================================================

@app.route(
    "/teacher-login",
    methods=["GET", "POST"]
)
def teacher_login():

    if request.method == "GET":

        return render_template(
            "teacher_login.html"
        )


    teacher_id = request.form.get(
        "teacher_id",
        ""
    ).strip().upper()


    if teacher_id in TEACHERS:

        session.clear()

        session["role"] = "teacher"

        session["teacher_id"] = teacher_id

        session["teacher_name"] = TEACHERS[
            teacher_id
        ]["name"]


        return redirect(
            url_for("dashboard")
        )


    return render_template(

        "teacher_login.html",

        error="Invalid Teacher ID. Please enter T001 or T002."

    )


# ============================================================
# STUDENT LOGIN
# ============================================================

@app.route(
    "/student-login",
    methods=["GET", "POST"]
)
def student_login():

    if request.method == "GET":

        return render_template(
            "student_login.html"
        )


    registration = request.form.get(
        "registration_number",
        ""
    ).strip().upper()


    if registration in STUDENTS:

        session.clear()

        session["role"] = "student"

        session["registration"] = registration

        session["student_name"] = STUDENTS[
            registration
        ]["name"]

        session["section"] = STUDENTS[
            registration
        ]["section"]


        return redirect(
            url_for("student_dashboard")
        )


    return render_template(

        "student_login.html",

        error="Invalid Registration Number. Try RA001 to RA009."

    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("home")
    )


# ============================================================
# TEACHER DASHBOARD
# ============================================================

def get_assignment_sections(assignment):
    """Return all sections assigned to this assignment.

    New assignments store a list in `sections`. Older assignments stored
    one section in `section`, so both formats continue to work.
    """
    sections = assignment.get("sections")
    if isinstance(sections, str):
        sections = [sections]
    if not isinstance(sections, list):
        legacy = assignment.get("section", "")
        sections = [legacy] if legacy else []

    cleaned = []
    for section in sections:
        value = str(section).strip().upper()
        if value in ["C", "F", "H"] and value not in cleaned:
            cleaned.append(value)
    return cleaned


def assignment_has_section(assignment, section):
    return str(section).strip().upper() in get_assignment_sections(assignment)


def assignment_section_label(assignment):
    return ", ".join(get_assignment_sections(assignment)) or "—"


def build_teacher_assignment_cards():

    assignments = load_assignments()
    submissions = load_submissions()
    evaluations = load_evaluations()

    cards = []
    current_teacher_id = session.get("teacher_id")

    for assignment_id, assignment in assignments.items():
        if not assignment.get("published", False):
            continue
        if current_teacher_id and assignment.get("teacher_id") != current_teacher_id:
            continue

        sections = get_assignment_sections(assignment)
        section_cards = []
        total_students = 0
        total_submitted = 0
        total_evaluated = 0

        for section in sections:
            section_students = [
                registration
                for registration, student in STUDENTS.items()
                if student.get("section") == section
            ]

            submitted = sum(
                1 for registration in section_students
                if submissions.get(registration, {}).get(assignment_id)
            )
            evaluated = sum(
                1 for registration in section_students
                if evaluations.get(registration, {}).get(assignment_id)
            )
            total = len(section_students)
            pending = max(submitted - evaluated, 0)
            not_submitted = max(total - submitted, 0)

            section_cards.append({
                "section": section,
                "total_students": total,
                "submitted": submitted,
                "evaluated": evaluated,
                "pending": pending,
                "not_submitted": not_submitted
            })

            total_students += total
            total_submitted += submitted
            total_evaluated += evaluated

        cards.append({
            "id": assignment_id,
            "subject": assignment.get("subject", ""),
            "title": assignment.get("title", "Untitled Assignment"),
            "section": assignment_section_label(assignment),
            "sections": sections,
            "section_cards": section_cards,
            "total_marks": assignment.get("total_marks", 0),
            "teacher_name": assignment.get("teacher_name", ""),
            "teacher_id": assignment.get("teacher_id", ""),
            "submitted": total_submitted,
            "evaluated": total_evaluated,
            "pending": max(total_submitted - total_evaluated, 0),
            "not_submitted": max(total_students - total_submitted, 0),
            "total_students": total_students
        })

    cards.sort(key=lambda item: item["id"])
    return cards


@app.route("/dashboard")
def dashboard():

    if not teacher_logged_in():
        return redirect(url_for("home"))

    scores = load_scores()
    students = []

    for registration, data in STUDENTS.items():
        students.append({
            "registration": registration,
            "name": data["name"],
            "section": data["section"],
            "score": scores.get(data["name"]),
            "status": get_submission_status(registration)
        })

    total_students = len(students)

    submitted_count = sum(
        1 for student in students
        if student["status"] != "Not Submitted"
    )

    evaluated_count = sum(
        1 for student in students
        if student["status"] in ["Submitted / Evaluated", "Evaluation Updated"]
    )

    evaluated_scores = [
        student["score"]
        for student in students
        if student["status"] in ["Submitted / Evaluated", "Evaluation Updated"]
        and student["score"] is not None
    ]

    average_score = (
        round(sum(evaluated_scores) / len(evaluated_scores), 1)
        if evaluated_scores else 0
    )

    section_stats = []

    for section_name in ["C", "F", "H"]:
        section_students = [
            student for student in students
            if student["section"] == section_name
        ]

        section_submitted = sum(
            1 for student in section_students
            if student["status"] != "Not Submitted"
        )

        section_scores = [
            student["score"] for student in section_students
            if student["status"] in ["Submitted / Evaluated", "Evaluation Updated"]
            and student["score"] is not None
        ]

        section_average = (
            round(sum(section_scores) / len(section_scores), 1)
            if section_scores else 0
        )

        section_stats.append({
            "name": section_name,
            "total": len(section_students),
            "submitted": section_submitted,
            "average": section_average
        })

    assignment_cards = build_teacher_assignment_cards()

    return render_template(
        "dashboard.html",
        students=students,
        total_students=total_students,
        submitted_count=submitted_count,
        evaluated_count=evaluated_count,
        average_score=average_score,
        section_stats=section_stats,
        assignments=assignment_cards,
        assignment_count=len(assignment_cards)
    )


@app.route("/teacher-assignments")
def teacher_assignments():

    if not teacher_logged_in():
        return redirect(url_for("home"))

    assignment_cards = build_teacher_assignment_cards()

    total_submitted = sum(item["submitted"] for item in assignment_cards)
    total_evaluated = sum(item["evaluated"] for item in assignment_cards)
    total_pending = sum(item["pending"] for item in assignment_cards)

    return render_template(
        "teacher_assignments.html",
        assignments=assignment_cards,
        assignment_count=len(assignment_cards),
        total_submitted=total_submitted,
        total_evaluated=total_evaluated,
        total_pending=total_pending
    )


# ============================================================
# TEACHER ASSIGNMENT DETAIL
# ============================================================

@app.route("/teacher-assignment/<assignment_id>")
def teacher_assignment_detail(assignment_id):

    if not teacher_logged_in():
        return redirect(url_for("home"))

    assignment_id = assignment_id.upper()
    assignments = load_assignments()
    assignment = assignments.get(assignment_id)

    if not assignment:
        return "Assignment not found."
    if assignment.get("teacher_id") != session.get("teacher_id"):
        return "You are not allowed to access this assignment."
    if not assignment.get("published", False):
        return "This assignment is not available."

    sections = get_assignment_sections(assignment)
    submissions = load_submissions()
    evaluations = load_evaluations()
    section_data = []
    assignment_students = []

    total_students = submitted = evaluated = 0
    all_scores = []

    for section in sections:
        students = []
        for registration, student in STUDENTS.items():
            if student.get("section") != section:
                continue

            submission = submissions.get(registration, {}).get(assignment_id)
            evaluation = evaluations.get(registration, {}).get(assignment_id)
            status = (
                "Evaluated" if evaluation else "Submitted / Pending Evaluation"
            ) if submission else "Not Submitted"

            score = None
            percentage = None
            if evaluation:
                score = evaluation.get("final_score", evaluation.get("score"))
                percentage = evaluation.get("final_percentage", evaluation.get("percentage"))
                if score is not None:
                    try:
                        all_scores.append(float(score))
                    except (TypeError, ValueError):
                        pass

            student_record = {
                "registration": registration,
                "name": student.get("name", ""),
                "section": section,
                "status": status,
                "submission": submission,
                "evaluation": evaluation,
                "score": score,
                "percentage": percentage
            }
            students.append(student_record)
            assignment_students.append(student_record)

        section_submitted = sum(1 for item in students if item["submission"])
        section_evaluated = sum(1 for item in students if item["evaluation"])
        section_pending = section_submitted - section_evaluated
        section_not_submitted = len(students) - section_submitted
        section_scores = [
            float(item["score"]) for item in students
            if item["score"] is not None
        ]

        section_data.append({
            "section": section,
            "students": students,
            "total_students": len(students),
            "submitted": section_submitted,
            "evaluated": section_evaluated,
            "pending": section_pending,
            "not_submitted": section_not_submitted,
            "average": round(sum(section_scores) / len(section_scores), 1) if section_scores else 0
        })

        total_students += len(students)
        submitted += section_submitted
        evaluated += section_evaluated

    pending = submitted - evaluated
    not_submitted = total_students - submitted
    average = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0
    highest = max(all_scores) if all_scores else 0
    lowest = min(all_scores) if all_scores else 0

    return render_template(
        "teacher_assignment_detail.html",
        assignment=assignment,
        sections=sections,
        section_data=section_data,
        students=assignment_students,
        total_students=total_students,
        submitted=submitted,
        evaluated=evaluated,
        pending=pending,
        not_submitted=not_submitted,
        average=average,
        highest=highest,
        lowest=lowest
    )


@app.route("/teacher-question-paper/<assignment_id>")
def teacher_question_paper(assignment_id):

    if not teacher_logged_in():
        return redirect(url_for("home"))

    assignment_id = assignment_id.upper()
    assignment = load_assignments().get(assignment_id)

    if not assignment:
        return "Assignment not found."

    if assignment.get("teacher_id") != session.get("teacher_id"):
        return "You are not allowed to access this question paper."

    question_path = assignment.get("question_paper_path")

    if not question_path or not os.path.exists(question_path):
        return "Question paper file not found."

    return send_file(question_path, as_attachment=False)


@app.route("/teacher-submission/<registration>/<assignment_id>")
def teacher_submission(registration, assignment_id):

    if not teacher_logged_in():
        return redirect(url_for("home"))

    registration = registration.upper()
    assignment_id = assignment_id.upper()

    if registration not in STUDENTS:
        return "Student not found."

    assignments = load_assignments()
    assignment = assignments.get(assignment_id)

    if not assignment:
        return "Assignment not found."

    if assignment.get("teacher_id") != session.get("teacher_id"):
        return "You are not allowed to access this submission."

    submission = get_student_submission(registration, assignment_id)

    if not submission:
        return "This student has not submitted this assignment."

    answer_path = submission.get("path")

    if not answer_path or not os.path.exists(answer_path):
        return "Submitted PDF could not be found."

    return send_file(answer_path, as_attachment=False)


# ============================================================
# CREATE ASSIGNMENT
# ============================================================

@app.route("/create-assignment")
def create_assignment():

    if not teacher_logged_in():

        return redirect(
            url_for("home")
        )


    return render_template(
        "create_assignment.html"
    )


# ============================================================
# PUBLISH ASSIGNMENT
# ============================================================

@app.route(
    "/publish-assignment",
    methods=["POST"]
)
def publish_assignment():

    if not teacher_logged_in():
        return redirect(url_for("home"))

    subject = request.form.get("subject", "").strip()
    assignment_title = request.form.get("assignment_title", "").strip()
    selected_sections = [
        value.strip().upper()
        for value in request.form.getlist("sections")
        if value.strip()
    ]
    selected_sections = list(dict.fromkeys(selected_sections))
    question_paper = request.files.get("question_paper")

    if not subject:
        return "Please enter the subject."
    if not assignment_title:
        return "Please enter an assignment title."
    if not selected_sections or any(section not in ["C", "F", "H"] for section in selected_sections):
        return "Please select at least one valid section."
    if not question_paper or not question_paper.filename:
        return "Please upload the question paper."
    if not question_paper.filename.lower().endswith(".pdf"):
        return "Only PDF question papers are allowed."

    try:
        definition = int(request.form.get("definition", 2))
        explanation = int(request.form.get("explanation", 4))
        example = int(request.form.get("example", 2))
        diagram = int(request.form.get("diagram", 2))
    except ValueError:
        return "Rubric marks must be valid numbers."

    if any(mark < 0 for mark in [definition, explanation, example, diagram]):
        return "Rubric marks cannot be negative."

    total_marks = definition + explanation + example + diagram
    if total_marks <= 0:
        return "Total marks must be greater than zero."

    assignments = load_assignments()
    used_numbers = []
    for key in assignments:
        match = re.fullmatch(r"A(\d+)", str(key).upper())
        if match:
            used_numbers.append(int(match.group(1)))
    assignment_number = max(used_numbers, default=0) + 1
    assignment_id = "A" + str(assignment_number).zfill(3)

    original_filename = secure_filename(question_paper.filename)
    saved_filename = assignment_id + "_" + original_filename
    question_path = os.path.join(UPLOAD_FOLDER, saved_filename)
    question_paper.save(question_path)

    assignments[assignment_id] = {
        "id": assignment_id,
        "subject": subject,
        "title": assignment_title,
        "section": selected_sections[0],  # legacy compatibility
        "sections": selected_sections,
        "question_paper": original_filename,
        "question_paper_path": question_path,
        "rubric": {
            "definition": definition,
            "explanation": explanation,
            "example": example,
            "diagram": diagram
        },
        "total_marks": total_marks,
        "teacher_id": session.get("teacher_id"),
        "teacher_name": session.get("teacher_name"),
        "published": True
    }

    save_assignments(assignments)
    return redirect(url_for("teacher_assignments"))


@app.route(
    "/assignment-question-paper/<assignment_id>"
)
def assignment_question_paper(
    assignment_id
):

    if not student_logged_in():

        return redirect(
            url_for("home")
        )


    assignments = load_assignments()


    assignment = assignments.get(
        assignment_id
    )


    if not assignment:

        return "Assignment not found."


    if not assignment.get(
        "published",
        False
    ):

        return "This assignment is not available."


    student_registration = session.get(
        "registration"
    )


    student_section = STUDENTS[
        student_registration
    ]["section"]


    if not assignment_has_section(assignment, student_section):

        return "You are not allowed to access this assignment."


    question_path = assignment.get(
        "question_paper_path"
    )


    if (
        not question_path
        or not os.path.exists(question_path)
    ):

        return "Question paper file not found."


    return send_file(

        question_path,

        as_attachment=False

    )


# ============================================================
# MANUAL EVALUATION PAGE
# ============================================================

@app.route("/evaluate-assignment")
def evaluate_assignment_page():

    if not teacher_logged_in():
        return redirect(url_for("home"))

    return redirect(url_for("teacher_assignments"))


# ============================================================
# DOWNLOAD REPORT
# ============================================================

@app.route("/download-report")
def download_report():

    """Generate and download an assignment-specific PDF report.

    The report uses the exact evaluation stored for the requested
    student + assignment. Students can download their own report;
    teachers can download a report by supplying registration and
    assignment_id in the URL.
    """

    if not teacher_logged_in() and not student_logged_in():
        return redirect(url_for("home"))

    # --------------------------------------------------------
    # Identify the student.
    # --------------------------------------------------------
    if student_logged_in():
        registration = session.get("registration", "").strip().upper()
    else:
        registration = request.args.get(
            "registration",
            ""
        ).strip().upper()

    if registration not in STUDENTS:
        return "Student registration is missing or invalid."

    # --------------------------------------------------------
    # Identify the assignment.
    # --------------------------------------------------------
    assignment_id = request.args.get(
        "assignment_id",
        ""
    ).strip().upper()

    assignments = load_assignments()

    # If no assignment was supplied, use the latest assignment for which
    # this student has an evaluation.
    if not assignment_id:
        evaluations = load_evaluations().get(
            registration,
            {}
        )

        if isinstance(evaluations, dict):
            assignment_keys = [
                key
                for key, value in evaluations.items()
                if isinstance(value, dict)
                and key in assignments
            ]

            if assignment_keys:
                assignment_id = assignment_keys[-1]

    if not assignment_id:
        return "No evaluated assignment was found for this student."

    assignment = assignments.get(assignment_id)

    if not assignment:
        return "Assignment not found."

    if not assignment.get("published", False):
        return "This assignment is not available."

    # Teachers may only download reports for their own assignments.
    if teacher_logged_in():
        if assignment.get("teacher_id") != session.get("teacher_id"):
            return "You are not allowed to download this report."

    # Students may only download reports belonging to their own account.
    if student_logged_in():
        logged_in_registration = session.get("registration", "").strip().upper()

        if registration != logged_in_registration:
            return "You are not allowed to download another student's report."

        student_section = STUDENTS[registration].get("section")
        if not assignment_has_section(
            assignment,
            student_section
        ):
            return "You are not allowed to download this report."

    evaluation = get_student_evaluation(
        registration,
        assignment_id
    )

    if not evaluation:
        return "This assignment has not been evaluated yet."

    total_marks = float(
        assignment.get(
            "total_marks",
            10
        ) or 10
    )

    score = evaluation.get(
        "final_score",
        evaluation.get(
            "score",
            0
        )
    )

    percentage = evaluation.get(
        "final_percentage",
        evaluation.get(
            "percentage",
            0
        )
    )

    try:
        score = float(score)
    except (TypeError, ValueError):
        score = 0.0

    try:
        percentage = float(percentage)
    except (TypeError, ValueError):
        percentage = round(
            (score / total_marks) * 100,
            1
        ) if total_marks else 0.0

    result_text = str(
        evaluation.get(
            "result",
            ""
        ) or ""
    ).strip()

    if not result_text:
        result_text = build_demo_report(
            score,
            total_marks
        )

    student = STUDENTS[registration]

    # --------------------------------------------------------
    # Create a unique assignment-specific PDF.
    # --------------------------------------------------------
    report_filename = (
        "EvalAI_"
        + assignment_id
        + "_"
        + registration
        + "_Report.pdf"
    )

    report_path = os.path.join(
        REPORT_FOLDER,
        report_filename
    )

    c = canvas.Canvas(
        report_path
    )

    page_width, page_height = c._pagesize

    left = 55
    right = page_width - 55
    top = page_height - 55
    bottom = 55
    y = top

    def new_page():
        nonlocal y
        c.showPage()
        y = top

    def draw_wrapped(text, font="Helvetica", size=10.5, gap=15):
        """Draw wrapped text and automatically create new pages."""
        nonlocal y

        text = str(text)

        c.setFont(
            font,
            size
        )

        # Approximate characters per line for the standard Helvetica font.
        max_chars = 92 if size <= 11 else 70

        for paragraph in text.split("\n"):
            paragraph = paragraph.rstrip()

            if not paragraph:
                y -= gap
                if y < bottom:
                    new_page()
                continue

            words = paragraph.split()
            current_line = ""

            for word in words:
                test_line = (
                    word
                    if not current_line
                    else current_line + " " + word
                )

                if len(test_line) <= max_chars:
                    current_line = test_line
                else:
                    c.drawString(
                        left,
                        y,
                        current_line
                    )
                    y -= gap

                    if y < bottom:
                        new_page()

                    current_line = word

            if current_line:
                c.drawString(
                    left,
                    y,
                    current_line
                )
                y -= gap

                if y < bottom:
                    new_page()

    # --------------------------------------------------------
    # Report header.
    # --------------------------------------------------------
    c.setFillColorRGB(
        0.43,
        0.28,
        0.20
    )

    c.setFont(
        "Helvetica-Bold",
        20
    )

    c.drawString(
        left,
        y,
        "EvalAI - Assignment Evaluation Report"
    )

    y -= 32

    c.setFillColorRGB(
        0,
        0,
        0
    )

    c.setFont(
        "Helvetica",
        11
    )

    draw_wrapped(
        f"Assignment: {assignment.get('title', 'Assignment')}",
        "Helvetica-Bold",
        11,
        16
    )

    draw_wrapped(
        f"Assignment ID: {assignment_id}",
        "Helvetica",
        11,
        16
    )

    draw_wrapped(
        f"Subject: {assignment.get('subject', '')}",
        "Helvetica",
        11,
        16
    )

    draw_wrapped(
        f"Student: {student.get('name', '')} ({registration})",
        "Helvetica",
        11,
        16
    )

    draw_wrapped(
        f"Section: {student.get('section', '')}",
        "Helvetica",
        11,
        16
    )

    y -= 8

    c.setFillColorRGB(
        0.43,
        0.28,
        0.20
    )

    c.setFont(
        "Helvetica-Bold",
        14
    )

    c.drawString(
        left,
        y,
        "FINAL RESULT"
    )

    y -= 23

    c.setFillColorRGB(
        0,
        0,
        0
    )

    draw_wrapped(
        f"Total Marks: {score:g} / {total_marks:g}",
        "Helvetica-Bold",
        12,
        18
    )

    draw_wrapped(
        f"Percentage: {percentage:g}%",
        "Helvetica-Bold",
        12,
        18
    )

    y -= 8

    c.setFillColorRGB(
        0.43,
        0.28,
        0.20
    )

    c.setFont(
        "Helvetica-Bold",
        14
    )

    c.drawString(
        left,
        y,
        "EVALUATION DETAILS"
    )

    y -= 23

    c.setFillColorRGB(
        0,
        0,
        0
    )

    draw_wrapped(
        result_text,
        "Helvetica",
        10.5,
        15
    )

    y -= 10

    c.setFillColorRGB(
        0.43,
        0.28,
        0.20
    )

    c.setFont(
        "Helvetica-Bold",
        9
    )

    c.drawString(
        left,
        y,
        "Generated by EvalAI"
    )

    c.save()

    return send_file(
        report_path,
        as_attachment=True,
        download_name=report_filename,
        mimetype="application/pdf"
    )


# SECTION
# ============================================================

@app.route(
    "/section/<section_name>"
)
def section(section_name):

    if not teacher_logged_in():
        return redirect(url_for("home"))

    section_name = str(section_name).strip().upper()
    assignments = load_assignments()

    section_students = []

    for registration, data in STUDENTS.items():

        if data.get("section", "").upper() != section_name:
            continue

        latest_submission = None
        latest_evaluation = None
        latest_assignment = None

        # Use the latest published assignment assigned to this section.
        # Evaluation/submission records are always read using the exact
        # assignment ID so one assignment cannot leak into another.
        for assignment in assignments.values():
            if not assignment.get("published", False):
                continue
            if assignment.get("teacher_id") != session.get("teacher_id"):
                continue
            if not assignment_has_section(assignment, section_name):
                continue

            latest_assignment = assignment
            latest_submission = get_student_submission(
                registration,
                assignment.get("id")
            )
            latest_evaluation = get_student_evaluation(
                registration,
                assignment.get("id")
            )

        if latest_assignment is None:
            status = "Not Submitted"
            score = None
            percentage = None
        elif latest_submission is None:
            status = "Not Submitted"
            score = None
            percentage = None
        elif latest_evaluation:
            score = latest_evaluation.get(
                "final_score",
                latest_evaluation.get("score")
            )
            total_marks = float(
                latest_assignment.get("total_marks", 10) or 10
            )
            try:
                score = float(score)
            except (TypeError, ValueError):
                score = 0.0

            percentage = latest_evaluation.get(
                "final_percentage",
                latest_evaluation.get("percentage")
            )
            try:
                percentage = float(percentage)
            except (TypeError, ValueError):
                percentage = round((score / total_marks) * 100, 1) if total_marks else 0

            status = (
                "Evaluation Updated"
                if latest_evaluation.get("manual_updated", False)
                else "Submitted / Evaluated"
            )
        else:
            status = "Submitted / Pending Evaluation"
            score = None
            percentage = None

        section_students.append({
            "registration": registration,
            "name": data["name"],
            "section": data["section"],
            "score": score,
            "percentage": percentage,
            "status": status,
            "assignment_id": latest_assignment.get("id") if latest_assignment else None
        })

    submitted = sum(
        1
        for student in section_students
        if student["status"] != "Not Submitted"
    )

    evaluated = sum(
        1
        for student in section_students
        if student["status"] in [
            "Submitted / Evaluated",
            "Evaluation Updated"
        ]
    )

    evaluated_scores = [
        student["percentage"]
        for student in section_students
        if student["status"] in [
            "Submitted / Evaluated",
            "Evaluation Updated"
        ]
        and student["percentage"] is not None
    ]

    average = round(
        sum(evaluated_scores) / len(evaluated_scores),
        1
    ) if evaluated_scores else 0

    highest = max(evaluated_scores) if evaluated_scores else 0
    lowest = min(evaluated_scores) if evaluated_scores else 0
    total_students = len(section_students)
    submission_rate = round((submitted / total_students) * 100, 1) if total_students else 0

    return render_template(
        "section.html",
        section=section_name,
        students=section_students,
        total=total_students,
        submitted=submitted,
        evaluated=evaluated,
        average=average,
        highest=highest,
        lowest=lowest,
        submission_rate=submission_rate
    )


# ============================================================
# ============================================================
# STUDENT DETAILS
# ============================================================

@app.route(
    "/student/<student_name>/<section_name>"
)
def student_details(
    student_name,
    section_name
):

    if not teacher_logged_in():
        return redirect(url_for("home"))

    student = None
    registration = None

    for reg, data in STUDENTS.items():

        if (
            data["name"].lower() == student_name.lower()
            and data["section"].upper() == section_name.upper()
        ):
            student = data.copy()
            registration = reg
            break

    if not student:
        return "Student not found."

    # Optional assignment selector. This lets the teacher open/evaluate
    # one specific assignment without losing the multi-assignment workflow.
    selected_assignment_id = request.args.get("assignment_id", "").strip().upper()

    scores = load_scores()
    assignments = load_assignments()

    student["registration"] = registration
    student["score"] = scores.get(student["name"])
    student["status"] = get_submission_status(registration)

    student_assignments = []

    for assignment in assignments.values():

        if (
            assignment_has_section(assignment, student["section"])
            and assignment.get("published", False)
        ):

            assignment_copy = assignment.copy()
            assignment_id = assignment_copy["id"]

            assignment_copy["status"] = get_assignment_status(
                registration,
                assignment_id
            )

            assignment_copy["submission"] = get_student_submission(
                registration,
                assignment_id
            )

            assignment_copy["evaluation"] = get_student_evaluation(
                registration,
                assignment_id
            )

            student_assignments.append(assignment_copy)

    latest_submission = None
    latest_evaluation = None
    latest_total_marks = 10
    selected_assignment = None

    # If a specific assignment was requested, use that exact record.
    # Otherwise preserve the existing behaviour and show the latest
    # submitted/evaluated assignment.
    if selected_assignment_id:
        for item in student_assignments:
            if item.get("id") == selected_assignment_id:
                selected_assignment = item
                latest_submission = item.get("submission")
                latest_evaluation = item.get("evaluation")
                latest_total_marks = item.get("total_marks", 10)
                break
    else:
        for item in student_assignments:
            if item.get("submission"):
                selected_assignment = item
                latest_submission = item.get("submission")
                latest_evaluation = item.get("evaluation")
                latest_total_marks = item.get("total_marks", 10)

    # Only fall back to the latest evaluation when no specific assignment
    # was requested. If the teacher/student opened A002, never show A001's
    # evaluation on the A002 page.
    if latest_evaluation is None and not selected_assignment_id:
        latest_evaluation = select_student_evaluation(
            registration,
            None
        )

    if latest_evaluation:

        display_score = latest_evaluation.get(
            "final_score",
            latest_evaluation.get(
                "score",
                student.get("score", 0)
            )
        )

        display_percentage = latest_evaluation.get(
            "final_percentage",
            latest_evaluation.get(
                "percentage",
                (
                    (display_score / latest_total_marks) * 100
                    if display_score is not None
                    else 0
                )
            )
        )

        latest_evaluation = ensure_evaluation_report(
            latest_evaluation,
            display_score,
            latest_total_marks
        )

    else:

        # When a specific assignment is selected but has not been evaluated,
        # do not leak the student's score from another assignment.
        if selected_assignment_id:
            display_score = None
            display_percentage = 0
        else:
            display_score = student.get("score")

            display_percentage = (
                (display_score / latest_total_marks) * 100
                if display_score is not None
                else 0
            )

    return render_template(
        "student.html",
        student=student,
        student_assignments=student_assignments,
        score=display_score,
        percentage=display_percentage,
        evaluation=latest_evaluation,
        submission=latest_submission,
        selected_assignment_id=selected_assignment_id,
        assignment=selected_assignment,
        assignment_total_marks=latest_total_marks
    )


@app.route(
    "/update-score",
    methods=["POST"]
)
def update_score():

    if not teacher_logged_in():
        return redirect(url_for("home"))

    registration = request.form.get("registration", "").strip().upper()
    assignment_id = request.form.get("assignment_id", "").strip().upper()

    try:
        new_score = float(request.form.get("score", 0))
    except (TypeError, ValueError):
        return "Invalid score."

    if registration not in STUDENTS:
        return "Student not found."

    assignments = load_assignments()

    # Manual score changes must always target one exact assignment.
    # This prevents an old/latest evaluation from being changed accidentally.
    if not assignment_id:
        return "Assignment ID is required to update a score."

    if assignment_id:
        assignment = assignments.get(assignment_id)
        if not assignment:
            return "Assignment not found."

        if assignment.get("teacher_id") != session.get("teacher_id"):
            return "You are not allowed to update this assignment."

        if not assignment_has_section(
            assignment,
            STUDENTS[registration]["section"]
        ):
            return "This student is not assigned to this assignment."

        existing_evaluation = get_student_evaluation(
            registration,
            assignment_id
        )
        if not existing_evaluation:
            return "This assignment has not been evaluated yet."

        total_marks = float(assignment.get("total_marks", 10) or 10)
    if new_score < 0 or new_score > total_marks:
        return f"Score must be between 0 and {total_marks:g}."

    student_name = STUDENTS[registration]["name"]

    # Keep the legacy scores.json value as the student's latest score so
    # existing dashboard/section pages continue to work.
    scores = load_scores()
    scores[student_name] = new_score
    save_scores(scores)

    evaluations = load_evaluations()

    if assignment_id:
        evaluations.setdefault(registration, {})

        # Normalize a legacy single-evaluation record before writing the
        # assignment-specific record.
        if "assignment_id" in evaluations[registration]:
            legacy = evaluations[registration]
            evaluations[registration] = {
                str(legacy.get("assignment_id")): legacy
            }

        evaluation = evaluations[registration].get(assignment_id, {})
        evaluation["assignment_id"] = assignment_id
        evaluation["final_score"] = new_score
        evaluation["final_percentage"] = round(
            (new_score / total_marks) * 100,
            1
        )
        evaluation["manual_updated"] = True

        # Preserve the original AI/demo report if it exists.
        if not evaluation.get("result"):
            evaluation = ensure_evaluation_report(
                evaluation,
                new_score,
                total_marks
            )

        evaluations[registration][assignment_id] = evaluation
        save_evaluations(evaluations)

        submissions = load_submissions()
        if registration in submissions and assignment_id in submissions[registration]:
            submissions[registration][assignment_id]["manual_updated"] = True
            submissions[registration][assignment_id]["evaluated"] = True
            save_submissions(submissions)

    return redirect(
        url_for(
            "student_details",
            student_name=student_name,
            section_name=STUDENTS[registration]["section"],
            assignment_id=assignment_id
        )
    )


# ============================================================
# ============================================================
# STUDENT DASHBOARD
# ============================================================

@app.route("/student-dashboard")
def student_dashboard():

    if not student_logged_in():
        return redirect(url_for("home"))

    registration = session.get("registration")
    student = STUDENTS.get(registration)

    if not student:
        session.clear()
        return redirect(url_for("student_login"))

    assignments = load_assignments()
    scores = load_scores()

    student_assignments = []

    for assignment in assignments.values():

        if (
            assignment_has_section(assignment, student["section"])
            and assignment.get("published", False)
        ):

            assignment_copy = assignment.copy()
            assignment_id = assignment_copy["id"]
            assignment_copy["status"] = get_assignment_status(
                registration,
                assignment_id
            )
            assignment_copy["submission"] = get_student_submission(
                registration,
                assignment_id
            )
            assignment_copy["evaluation"] = get_student_evaluation(
                registration,
                assignment_id
            )
            student_assignments.append(assignment_copy)

    submitted_count = sum(
        1
        for assignment in student_assignments
        if assignment["status"] != "Not Submitted"
    )

    evaluated_count = sum(
        1
        for assignment in student_assignments
        if assignment["status"] in [
            "Submitted / Evaluated",
            "Evaluation Updated"
        ]
    )

    return render_template(
        "student_dashboard.html",
        student={
            "registration": registration,
            "name": student["name"],
            "section": student["section"],
            "department": student["department"],
            "score": scores.get(student["name"]),
            "status": get_submission_status(registration)
        },
        assignments=student_assignments,
        submitted_count=submitted_count,
        evaluated_count=evaluated_count,
        total_assignments=len(student_assignments)
    )


# ============================================================
# MY ASSIGNMENTS
# ============================================================

@app.route("/my-assignments")
def my_assignments():

    if not student_logged_in():
        return redirect(url_for("home"))

    registration = session.get("registration")
    student = STUDENTS.get(registration)

    if not student:
        session.clear()
        return redirect(url_for("student_login"))

    assignments = load_assignments()
    student_assignments = []

    for assignment in assignments.values():

        if (
            assignment_has_section(assignment, student["section"])
            and assignment.get("published", False)
        ):

            assignment_copy = assignment.copy()
            assignment_id = assignment_copy["id"]
            assignment_copy["status"] = get_assignment_status(
                registration,
                assignment_id
            )
            assignment_copy["submission"] = get_student_submission(
                registration,
                assignment_id
            )
            assignment_copy["evaluation"] = get_student_evaluation(
                registration,
                assignment_id
            )
            student_assignments.append(assignment_copy)

    return render_template(
        "my_assignments.html",
        student={
            "registration": registration,
            "name": student["name"],
            "section": student["section"],
            "department": student["department"]
        },
        assignments=student_assignments
    )


# STUDENT SUBMISSION
# ============================================================

@app.route(
    "/submit-assignment",
    methods=["POST"]
)
def submit_assignment():

    if not student_logged_in():

        return redirect(
            url_for("home")
        )


    registration = session.get(
        "registration"
    )


    student_answer = request.files.get(
        "student_answer"
    )


    assignment_id = request.form.get(
        "assignment_id",
        ""
    ).strip()


    if not assignment_id:

        return "Assignment ID is missing."


    assignments = load_assignments()


    assignment = assignments.get(
        assignment_id
    )


    if not assignment:

        return "Assignment not found."


    student_section = STUDENTS[
        registration
    ]["section"]


    if not assignment_has_section(assignment, student_section):

        return "You cannot submit this assignment."


    if not student_answer:

        return "Please select your answer PDF."


    if not student_answer.filename:

        return "Please select your answer PDF."


    if not student_answer.filename.lower().endswith(
        ".pdf"
    ):

        return "Only PDF answer files are allowed."


    # ========================================================
    # SAVE ANSWER
    # ========================================================

    original_filename = secure_filename(
        student_answer.filename
    )


    saved_filename = (

        registration
        + "_"
        + assignment_id
        + "_"
        + original_filename

    )


    answer_path = os.path.join(

        UPLOAD_FOLDER,

        saved_filename

    )


    student_answer.save(
        answer_path
    )


    # ========================================================
    # SAVE SUBMISSION
    # ========================================================

    submissions = load_submissions()

    submissions.setdefault(
        registration,
        {}
    )

    submissions[registration][assignment_id] = {

        "assignment_id": assignment_id,

        "assignment_title": assignment.get("title"),

        "filename": original_filename,

        "saved_filename": saved_filename,

        "path": answer_path,

        "submitted": True,

        "evaluated": False,

        "manual_updated": False

    }

    # If the student resubmits this assignment, clear its previous evaluation.
    evaluations = load_evaluations()
    if registration in evaluations:
        evaluations[registration].pop(assignment_id, None)
        save_evaluations(evaluations)

    save_submissions(submissions)


    return redirect(

        url_for(
            "student_dashboard"
        )

    )


# ============================================================
# STUDENT RESULT
# ============================================================

@app.route("/my-result")
def my_result():

    if not student_logged_in():
        return redirect(url_for("home"))

    registration = session.get("registration")
    student = STUDENTS.get(registration)

    if not student:
        session.clear()
        return redirect(url_for("student_login"))

    assignments = load_assignments()
    selected_assignment_id = request.args.get("assignment_id", "").strip().upper()
    selected_assignment = None
    submission = None
    evaluation = None
    total_marks = 10

    if selected_assignment_id:
        selected_assignment = assignments.get(selected_assignment_id)
        if not selected_assignment:
            return "Assignment not found."
        if not selected_assignment.get("published", False):
            return "This assignment is not available."
        if not assignment_has_section(selected_assignment, student["section"]):
            return "You are not allowed to access this assignment."

        submission = get_student_submission(registration, selected_assignment_id)
        evaluation = get_student_evaluation(registration, selected_assignment_id)
        total_marks = float(selected_assignment.get("total_marks", 10) or 10)

    else:
        for assignment in assignments.values():
            if (
                assignment.get("published", False)
                and assignment_has_section(assignment, student["section"])
            ):
                candidate_submission = get_student_submission(registration, assignment["id"])
                if candidate_submission:
                    selected_assignment = assignment
                    selected_assignment_id = assignment["id"]
                    submission = candidate_submission
                    evaluation = get_student_evaluation(registration, selected_assignment_id)
                    total_marks = float(assignment.get("total_marks", 10) or 10)

    if evaluation:
        final_score = evaluation.get("final_score", evaluation.get("score", 0))
        try:
            final_score = float(final_score)
        except (TypeError, ValueError):
            final_score = 0.0

        final_percentage = evaluation.get("final_percentage", evaluation.get("percentage"))
        if final_percentage is None:
            final_percentage = round((final_score / total_marks) * 100, 1) if total_marks else 0

        evaluation = ensure_evaluation_report(evaluation, final_score, total_marks)
    else:
        final_score = None
        final_percentage = 0

    status = (
        get_assignment_status(registration, selected_assignment_id)
        if selected_assignment_id
        else "Not Submitted"
    )

    return render_template(
        "student_result.html",
        student={
            "registration": registration,
            "name": student["name"],
            "section": student["section"],
            "department": student["department"]
        },
        score=final_score,
        percentage=final_percentage,
        evaluation=evaluation,
        status=status,
        assignment_id=selected_assignment_id,
        assignment=selected_assignment,
        submission=submission,
        total_marks=total_marks
    )


@app.route(
    "/evaluate-student/<registration>/<assignment_id>",
    methods=["POST"]
)
def evaluate_student(registration, assignment_id):

    if not teacher_logged_in():
        return redirect(url_for("home"))

    registration = registration.upper()
    assignment_id = assignment_id.upper()

    if registration not in STUDENTS:
        return "Student not found."

    submissions = load_submissions()
    submission = get_student_submission(
        registration,
        assignment_id
    )

    if not submission:
        return "This student has not submitted this assignment."

    answer_path = submission.get("path")

    if not answer_path or not os.path.exists(answer_path):
        return "Submitted PDF could not be found."

    assignments = load_assignments()
    assignment = assignments.get(assignment_id)

    if not assignment:
        return "Assignment not found."

    # A teacher may evaluate only assignments created by that teacher.
    if assignment.get("teacher_id") != session.get("teacher_id"):
        return "You are not allowed to evaluate this assignment."

    # The student must belong to one of the sections receiving this assignment.
    if not assignment_has_section(
        assignment,
        STUDENTS[registration]["section"]
    ):
        return "This student is not assigned to this assignment."

    question_paper_path = assignment.get("question_paper_path")
    rubric = assignment.get(
        "rubric",
        {
            "definition": 2,
            "explanation": 4,
            "example": 2,
            "diagram": 2
        }
    )

    if not question_paper_path or not os.path.exists(question_paper_path):
        return "Question paper could not be found."

    result = evaluate_assignment(
        question_paper_path,
        answer_path,
        rubric
    )

    # Extract the calculated score from the evaluator report.
    score = 0
    percentage = 0

    score_match = re.search(
        r"TOTAL MARKS:\s*([0-9]+(?:\.[0-9]+)?)\s*/\s*([0-9]+(?:\.[0-9]+)?)",
        result
    )

    percentage_match = re.search(
        r"PERCENTAGE:\s*([0-9]+(?:\.[0-9]+)?)%",
        result
    )

    if score_match:
        score = float(score_match.group(1))

    if percentage_match:
        percentage = float(percentage_match.group(1))

    evaluations = load_evaluations()
    evaluations.setdefault(registration, {})

    evaluations[registration][assignment_id] = {
        "assignment_id": assignment_id,
        "result": result,
        "score": score,
        "percentage": percentage,
        "final_score": score,
        "final_percentage": percentage,
        "manual_updated": False
    }

    save_evaluations(evaluations)

    submissions[registration][assignment_id]["evaluated"] = True
    save_submissions(submissions)

    # Keep the existing student score as the latest evaluated score for
    # compatibility with the teacher dashboard.
    student_name = STUDENTS[registration]["name"]
    scores = load_scores()
    scores[student_name] = score
    save_scores(scores)

    return redirect(
        url_for(
            "student_details",
            student_name=student_name,
            section_name=STUDENTS[registration]["section"],
            assignment_id=assignment_id
        )
    )


# RUN
# ============================================================

if __name__ == "__main__":

    app.run(

        debug=True,

        host="127.0.0.1",

        port=5000

    )