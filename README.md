# EvalAI

AI Assignment Evaluation Platform for Teachers and Students.

EvalAI is a web-based assignment management and evaluation system designed to simplify the process of distributing assignments, collecting student submissions, evaluating answers, and providing performance feedback.

---

## 🚀 Overview

EvalAI provides separate portals for teachers and students.

Teachers can:

- Create assignments
- Assign assignments to multiple sections
- Upload question papers
- Define custom marking rubrics
- Monitor student submissions
- Evaluate student answers
- Manually adjust final marks
- View section and assignment statistics
- Download evaluation reports

Students can:

- Log in using their registration number
- View assigned assignments
- Download question papers
- Upload answer PDFs
- Track submission status
- View evaluation results
- View marks, percentage, and feedback

Each assignment maintains its own submission and evaluation records. This prevents the results of one assignment from overwriting the results of another assignment.

---

## ✨ Features

### 👨‍🏫 Teacher Portal

- Teacher login using Teacher ID
- Teacher dashboard
- Create assignments
- Assign one assignment to multiple sections
- Supported sections:
  - C
  - F
  - H
- Upload question paper PDF
- Define custom marking rubric
- View all assignments created by the teacher
- Assignment-specific submission tracking
- Section-wise student lists
- View submitted student PDFs
- Evaluate student submissions
- Manually adjust final marks
- View student evaluation reports
- View class statistics
- View submission statistics
- View evaluation statistics
- View average score
- View highest and lowest scores
- Track submitted, evaluated, pending, and not-submitted students

---

### 👨‍🎓 Student Portal

- Student login using Registration Number
- Student dashboard
- View assigned assignments
- View assignment status
- Download question papers
- Upload answer PDF
- View submission status
- View evaluation status
- View marks and percentage
- View teacher/evaluation feedback
- View strengths
- View weak topics
- View improvement suggestions
- Download evaluation reports

---

## 🧠 Evaluation System

EvalAI currently uses a **Demo Evaluation Engine** for development and demonstration.

The current evaluator works locally using Python and does not require an external AI API.

The evaluator:

1. Reads the uploaded question paper PDF.
2. Reads the uploaded student answer PDF.
3. Uses the teacher's custom rubric.
4. Generates a question-wise evaluation.
5. Calculates marks.
6. Calculates the final percentage.
7. Generates strengths.
8. Identifies weak areas.
9. Provides improvement suggestions.
10. Generates an overall feedback summary.

---

## 📋 Custom Marking Rubric

Teachers can define marks for different evaluation criteria.

Example:

```text
Definition      → 2 marks
Explanation     → 4 marks
Example         → 2 marks
Diagram         → 2 marks
---------------------------
Total           → 10 marks