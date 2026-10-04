import fitz


def extract_text_from_pdf(pdf_path):
    """
    Extract text from a PDF file.
    """

    document = fitz.open(pdf_path)

    text = ""

    for page in document:
        text += page.get_text()

    document.close()

    return text


def evaluate_assignment(question_paper, student_answers, rubric):
    """
    Demo evaluator used until the OpenAI API is connected.

    The evaluator currently uses a fixed demo performance of 90%.
    The important part is that the TOTAL MARKS always comes from
    the teacher's custom rubric.
    """

    # --------------------------------------------------------
    # READ PDF CONTENT
    # --------------------------------------------------------

    question_text = extract_text_from_pdf(
        question_paper
    )

    answer_text = extract_text_from_pdf(
        student_answers
    )

    # --------------------------------------------------------
    # READ RUBRIC
    # --------------------------------------------------------

    try:
        definition = int(
            rubric.get("definition", 2)
        )
    except (TypeError, ValueError):
        definition = 2

    try:
        explanation = int(
            rubric.get("explanation", 4)
        )
    except (TypeError, ValueError):
        explanation = 4

    try:
        example = int(
            rubric.get("example", 2)
        )
    except (TypeError, ValueError):
        example = 2

    try:
        diagram = int(
            rubric.get("diagram", 2)
        )
    except (TypeError, ValueError):
        diagram = 2

    # Prevent negative rubric values.
    definition = max(0, definition)
    explanation = max(0, explanation)
    example = max(0, example)
    diagram = max(0, diagram)

    total_marks = (
        definition
        + explanation
        + example
        + diagram
    )

    if total_marks <= 0:
        total_marks = 10

    # --------------------------------------------------------
    # DEMO EVALUATION
    # --------------------------------------------------------
    #
    # Until OpenAI API credits are available, we simulate
    # a strong student performance of approximately 90%.
    #
    # This keeps the score proportional to ANY rubric total.
    # --------------------------------------------------------

    demo_score = round(
        total_marks * 0.90,
        1
    )

    # --------------------------------------------------------
    # QUESTION-WISE DEMO BREAKDOWN
    # --------------------------------------------------------
    #
    # For the current sample question paper:
    #
    # Q1 = 5 marks
    # Q2 = 5 marks
    #
    # We keep the familiar 4/5 and 5/5 demonstration when
    # the rubric total is 10.
    #
    # For other totals, the result is scaled proportionally.
    # --------------------------------------------------------

    if total_marks == 10:
        q1_possible = 5
        q2_possible = 5

        q1_score = 4
        q2_score = 5

    else:
        # Split the total approximately equally.
        q1_possible = round(
            total_marks / 2,
            1
        )

        q2_possible = round(
            total_marks - q1_possible,
            1
        )

        # Give Q1 around 80%.
        q1_score = round(
            q1_possible * 0.80,
            1
        )

        # Give Q2 around 100%.
        q2_score = round(
            q2_possible,
            1
        )

        # Safety correction so the question scores equal
        # the intended overall demo score.
        current_score = q1_score + q2_score

        difference = round(
            demo_score - current_score,
            1
        )

        q2_score = round(
            q2_score + difference,
            1
        )

        q2_score = max(
            0,
            min(q2_score, q2_possible)
        )

    # --------------------------------------------------------
    # PERCENTAGE
    # --------------------------------------------------------

    percentage = round(
        (demo_score / total_marks) * 100,
        1
    )

    # --------------------------------------------------------
    # REPORT
    # --------------------------------------------------------

    result = f"""
EVALAI - ASSIGNMENT EVALUATION
================================

CUSTOM RUBRIC
-------------

Definition: {definition} marks
Explanation: {explanation} marks
Example: {example} marks
Diagram: {diagram} marks

Total Possible Marks: {total_marks:g}


QUESTION-WISE EVALUATION
------------------------

Question 1
Marks: {q1_score:g} / {q1_possible:g}

Feedback:
The student demonstrated a good understanding of the
concept and provided a mostly correct explanation.
The answer could be improved with additional detail.


Question 2
Marks: {q2_score:g} / {q2_possible:g}

Feedback:
The answer demonstrates a clear understanding of the
concept and provides a relevant example.


================================
TOTAL MARKS: {demo_score:g} / {total_marks:g}
PERCENTAGE: {percentage:g}%


STRENGTHS
---------

- Good understanding of the core concepts
- Relevant explanations
- Appropriate real-world examples
- Clear overall understanding


WEAK TOPICS
-----------

- Some explanations could contain more detail
- Supporting examples can be expanded
- Important points should be explained more systematically


SUGGESTIONS
-----------

- Give more detailed explanations.
- Include relevant examples wherever possible.
- Use diagrams when they improve the explanation.
- Review the areas where marks were lost.


OVERALL FEEDBACK
----------------

Good performance. The student demonstrates a clear
understanding of the concepts covered in the assignment.

The evaluation is currently running in DEMO MODE.
The OpenAI-powered evaluator can be connected later
without changing the assignment workflow.
"""

    return result