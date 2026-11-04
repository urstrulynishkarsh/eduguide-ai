# 7. Class-aware learning rules

A Nursery child and a Class 12 student must not get the same kind of question, explanation or
screen. This document describes the rules that make the difference.

## 7.1 Where the rules live

| What | Where |
|---|---|
| The rules themselves | `backend/app/class_profiles/registry.py` — six groups of classes, expanded into 15 profiles |
| The shape of a profile | `backend/app/class_profiles/models.py` (`ClassProfile`) |
| Checks for the child form | `backend/app/class_profiles/rules.py` |
| For the frontend | `GET /api/v1/meta/options` (summary of every class) and `GET /api/v1/meta/classes/{class_level}` (full profile) |
| Tests that protect them | `backend/tests/unit/test_class_profiles.py` |

**Every table below was printed from the code**, so it shows what the backend really does. If you
change `registry.py`, update this page.

The profile for Class 5, as the API returns it (shortened):

```json
{
  "class_level": "class_5",
  "label": "Class 5",
  "band": "preparatory",
  "age_range": "9-11",
  "language_complexity": "simple",
  "question_complexity": "medium",
  "explanation_style": "child_friendly",
  "max_concept_depth": "intermediate",
  "ui_mode": "friendly"
}
```

These are the values the product spec gives for Class 5 (§4); the Class 12 profile matches the
spec's second example in the same way. Codes use underscores (`child_friendly`), and the class is
written `class_5` rather than the number `5` so that Nursery, LKG and UKG fit the same pattern.

## 7.2 The five bands

| Band | Classes | Spec section | The experience in one line |
|---|---|---|---|
| `foundational` | Nursery, LKG, UKG, Class 1, Class 2 | §5 | A friendly early-learning tutor: pictures, matching, counting — **not** an exam interface |
| `preparatory` | Class 3 – 5 | §6 | Chapter and exercise practice with simple, step-by-step explanations |
| `middle` | Class 6 – 8 | §7 | Concepts and application, adaptive difficulty, weak-topic detection |
| `secondary` | Class 9 – 10 | §8 | Board-oriented preparation: board-style questions, timed and full mock tests |
| `senior_secondary` | Class 11 – 12 | §9 | Stream and goal (School / Board / JEE / NEET / CUET) shape everything |

## 7.3 Profile of every class

| Class | Band | Typical age | Language | Question complexity | Explanation style | Concept depth | Layout |
|---|---|---|---|---|---|---|---|
| Nursery | `foundational` | 3–4 | `very_simple` | `very_easy` | `playful` | `introductory` | `playful` |
| LKG | `foundational` | 4–5 | `very_simple` | `very_easy` | `playful` | `introductory` | `playful` |
| UKG | `foundational` | 5–6 | `very_simple` | `very_easy` | `playful` | `introductory` | `playful` |
| Class 1 | `foundational` | 5–7 | `simple` | `easy` | `playful` | `basic` | `playful` |
| Class 2 | `foundational` | 6–8 | `simple` | `easy` | `playful` | `basic` | `playful` |
| Class 3 | `preparatory` | 7–9 | `simple` | `medium` | `child_friendly` | `intermediate` | `friendly` |
| Class 4 | `preparatory` | 8–10 | `simple` | `medium` | `child_friendly` | `intermediate` | `friendly` |
| Class 5 | `preparatory` | 9–11 | `simple` | `medium` | `child_friendly` | `intermediate` | `friendly` |
| Class 6 | `middle` | 10–12 | `moderate` | `upper_medium` | `conceptual` | `upper_intermediate` | `standard` |
| Class 7 | `middle` | 11–13 | `moderate` | `upper_medium` | `conceptual` | `upper_intermediate` | `standard` |
| Class 8 | `middle` | 12–14 | `moderate` | `upper_medium` | `conceptual` | `upper_intermediate` | `standard` |
| Class 9 | `secondary` | 13–15 | `standard` | `challenging` | `exam_oriented` | `proficient` | `dense` |
| Class 10 | `secondary` | 14–16 | `standard` | `challenging` | `exam_oriented` | `proficient` | `dense` |
| Class 11 | `senior_secondary` | 15–17 | `advanced` | `advanced` | `academic` | `advanced` | `dense` |
| Class 12 | `senior_secondary` | 16–18 | `advanced` | `advanced` | `academic` | `advanced` | `dense` |

Age is only a typical range. The **class**, not the age, decides the experience; a child's real age
never blocks anything.

## 7.4 Limits a program can check

Words like "simple" are useful in a prompt, but a validator needs numbers.

| Classes | Words per sentence (about) | Steps in a solution (max) | MCQ options | Questions per session (default / max) |
|---|---|---|---|---|
| Nursery – UKG | 8 | 1 | 3 | 5 / 10 |
| Class 1 – 2 | 10 | 2 | 3 | 5 / 10 |
| Class 3 – 5 | 15 | 4 | 4 | 8 / 20 |
| Class 6 – 8 | 20 | 6 | 4 | 10 / 30 |
| Class 9 – 10 | 25 | 8 | 4 | 10 / 50 |
| Class 11 – 12 | 30 | 12 | 4 | 10 / 50 |

These numbers are **sensible starting values, not research findings**. Tune them after watching
real children use the product.

## 7.5 Which questions may be generated

A question has a **format** (how it is shown and answered) and a **style** (what kind of thinking
it asks for). Any style can use any allowed format — a HOTS question can be an MCQ or a long answer.

| Classes | Formats | Styles |
|---|---|---|
| Nursery – UKG | `visual_choice`, `matching`, `counting`, `mcq` | `recall` |
| Class 1 – 2 | `visual_choice`, `matching`, `counting`, `mcq` | `recall` |
| Class 3 – 5 | `mcq`, `fill_blank`, `true_false`, `short_answer` | `recall`, `conceptual`, `word_problem`, `hots` |
| Class 6 – 8 | `mcq`, `short_answer`, `long_answer`, `case_based`, `assertion_reason` | `recall`, `conceptual`, `word_problem`, `application`, `hots` |
| Class 9 – 10 | `mcq`, `short_answer`, `long_answer`, `numerical`, `assertion_reason`, `case_based` | `recall`, `conceptual`, `application`, `hots`, `competency_based`, `board_style` |
| Class 11 – 12 | `mcq`, `short_answer`, `long_answer`, `numerical`, `assertion_reason`, `case_based` | `recall`, `conceptual`, `application`, `hots`, `competency_based`, `board_style`, `competitive_exam` |

How the names in spec §17 map to these codes:

| Spec says | Here |
|---|---|
| Identification ("Which one is an apple? 🍎 🐱 🚗") | format `visual_choice` |
| Simple MCQ | format `mcq` with 3 options |
| Fill blanks, True/False, Short answer, Long answer, Numerical, Matching, Counting | formats of the same name |
| Assertion/Reason, Case-based | formats `assertion_reason`, `case_based` |
| Word problems, Application, HOTS, Competency-based | styles `word_problem`, `application`, `hots`, `competency_based` |
| Board-style, Competitive-exam style | styles `board_style`, `competitive_exam` |

## 7.6 Which features exist

The frontend hides whatever is switched off, and each backend feature checks its switch when it
is built (tests in Step 8, adaptive difficulty in Step 7, and so on). A test the class does not
have, or a time limit below Class 9, is refused with `422 test_not_for_class`.

| Feature | Nursery – UKG | Class 1 – 2 | Class 3 – 5 | Class 6 – 8 | Class 9 – 10 | Class 11 – 12 |
|---|---|---|---|---|---|---|
| `exam_style_practice` | – | – | ✓ | ✓ | ✓ | ✓ |
| `practice_tests` | – | – | ✓ | ✓ | ✓ | ✓ |
| `chapter_tests` | – | – | – | ✓ | ✓ | ✓ |
| `adaptive_difficulty` | – | – | – | ✓ | ✓ | ✓ |
| `weak_topic_detection` | – | – | – | ✓ | ✓ | ✓ |
| `timed_tests` | – | – | – | – | ✓ | ✓ |
| `full_mock_tests` | – | – | – | – | ✓ | ✓ |
| `previous_year_questions` | – | – | – | – | ✓ | ✓ |
| `board_exam_preparation` | – | – | – | – | ✓ | ✓ |
| `competitive_exam_modes` | – | – | – | – | – | ✓ |
| `misconception_detection` | – | – | ✓ | ✓ | ✓ | ✓ |

Each switch follows the class where the spec first introduces the feature (§6 practice tests,
§7 adaptive difficulty and weak topics, §8 timed and mock tests, §9 competitive goals;
misconceptions from Class 3, where wrong ideas in arithmetic first show). If you
would rather give adaptive difficulty to Class 3–5 as well, it is one word in `registry.py`.

## 7.7 Rules for the child form

**Class is chosen first**, because it decides what the rest of the form offers.

| Class | Goals that can be chosen | Default |
|---|---|---|
| Nursery – UKG | Build strong basics, Other | Build strong basics |
| Class 1 – 2 | Build strong basics, School exams, Other | Build strong basics |
| Class 3 – 8 | School exams, Build strong basics, Other | School exams |
| Class 9 | School exams, Board exams, Build strong basics, Other | School exams |
| Class 10 | School exams, Board exams, Build strong basics, Other | Board exams |
| Class 11 | School exams, Board exams, JEE, NEET, CUET, Other | School exams |
| Class 12 | School exams, Board exams, JEE, NEET, CUET, Other | Board exams |

- **Stream** (Science / Commerce / Arts) is required for Class 11–12 and refused for every other class.
- **JEE and NEET** need the Science stream. CUET is open to all streams.
- **Subjects** are free text with suggestions per class (and per stream for Class 11–12), because
  boards name and split subjects differently.
- **Language the AI uses:** English, Hindi or Hinglish today. Marathi, Gujarati, Bengali, Tamil,
  Telugu, Kannada, Malayalam and Punjabi are already registered in `app/core/languages.py`; each
  can be picked as the school **medium** now and switched on for AI content later with one flag.

## 7.8 How the AI is told to behave

These lines are stored in each profile (`ai_guidelines`) and placed in every prompt for that class.

**Nursery – UKG**

- Talk like a warm, patient pre-school teacher.
- Use very short sentences and words a small child hears at home.
- Ask about one thing at a time: a colour, a shape, a letter, a number or an everyday object.
- Prefer pictures or emoji, counting, matching and 'which one is...' questions.
- Always encourage. Never say 'wrong' or 'incorrect'; invite the child to try again.
- No marks, no timers and no exam words.

**Class 1 – 2**

- Talk like a friendly primary-school teacher.
- Use short sentences and simple everyday words.
- One idea per question: simple reading, basic vocabulary or basic arithmetic.
- Use familiar things in examples: fruits, toys, animals, family, school.
- Always encourage. Never say 'wrong'; invite the child to try again.
- No exam-style language.

**Class 3 – 5**

- Explain with simple examples from daily life: money, sweets, cricket, school, family.
- Break every explanation into small numbered steps.
- When you use a new word, say what it means in plain language.
- Keep word problems to one or two operations.
- Keep thinking (HOTS) questions gentle: one small twist on what the chapter teaches.
- Be encouraging and praise effort.
- Stay inside the chapter and the class syllabus. Do not bring in ideas from higher classes.

**Class 6 – 8**

- Explain why a rule works, not only how to apply it.
- Use the correct subject terms and define each one the first time it appears.
- Connect ideas to real situations; include application and thinking (HOTS) questions.
- Use assertion-reason and case-based questions only where they fit the chapter.
- Point out the common mistake for a concept when it helps.
- Stay inside the chapter and the class syllabus. Do not bring in ideas from higher classes.

**Class 9 – 10**

- Follow the question style and marking pattern of the learner's board.
- Use textbook terminology exactly and show the working a board examiner expects.
- Include competency-based, case-study and assertion-reason questions where they fit the chapter.
- Mention common exam mistakes and where marks are usually lost.
- Stay inside the chapter and the class syllabus. Do not bring in ideas from higher classes.

**Class 11 – 12**

- Be rigorous: precise definitions, standard notation, SI units and justified steps.
- Match the question style to the learner's goal: school exam, board exam, JEE, NEET or CUET.
- For a JEE goal prefer conceptual, numerical and multi-concept problems at higher difficulty.
- For a NEET goal stay close to the NCERT text: conceptual, assertion-reason, application MCQs.
- Derive or justify results wherever the syllabus expects it.
- Stay inside the Class 11-12 syllabus unless the learner asks to go further.

## 7.9 Two kinds of "difficulty" — do not mix them

| | What it is | Who sets it |
|---|---|---|
| **Complexity of the class** | How hard things may be *at all* for this class (the tables above) | The class profile. Fixed |
| **Difficulty of a question** | Easy / Medium / Hard / Mixed **within that class** (spec §18) | The parent's choice, later the adaptive engine |

A "hard" Class 3 question is still a Class 3 question. The adaptive engine (Step 7) only moves the
second one, using the rule from spec §23 on the child's recent history for that topic — never at random:

| Recent accuracy on the topic | What happens |
|---|---|
| above 85% | difficulty goes up |
| 60% – 85% | difficulty stays |
| below 60% | difficulty goes down, a concept revision is offered, foundation questions are generated |

How it is built (Step 7, `backend/app/adaptive_learning/`):

- **Per area.** An area is a topic of a chapter, or the chapter itself for questions without a
  topic. Its numbers are worked out again after every answer, from the last 10 *first* answers to
  each question in each practice (as basic progress counts them, so trying again never inflates them).
- **The level** of each area starts at medium and moves only on **at least 5 answers given since it
  last moved**, so it never jumps twice on the same answers. Below 60 % the area also *needs
  attention*, and today's recommendations offer a concept revision (Explain) and practice at the
  lowered level: the foundation questions.
- **Mastery** (0–1) is the average credit of those answers: 1 for right without help, a quarter less
  per hint, a quarter if the steps or the answer were opened first, 0 for wrong. Recent answers count
  more (each one 0.85 of the next), and harder ones more (easy 1, medium 1.5, hard 2). **Confidence** is
  answers ÷ 10, up to 1. An area is **strong** at mastery 0.85 or more over at least 5 answers.
- **Nursery – Class 5** (`adaptive_difficulty` and `weak_topic_detection` off): no levels and no
  "needs attention" label. Their recommendations repeat what was often wrong, gently ("Let's
  practise this again"), with easy questions.

All these numbers are constants at the top of `mastery.py` (and `recommendations.py`): starting
values like those in 7.4, to tune after watching real children.

## 7.10 How each later step uses the profile

| Step | Use |
|---|---|
| 4 Question generation | Formats, styles, option count and guidelines go into the prompt; the limits in 7.4 are checked on the output; a question using a format the class does not allow is rejected. Built: `question_generation/` |
| 4 Practice sessions | Default and maximum questions per session (7.4); a `question_type` the class does not use is refused |
| 4 Solutions and hints | Explanation style and the maximum number of steps; 1–2 hints per question. Nursery–Class 2: a wrong answer is an invitation to try again, with the answer kept back |
| 4 Goal strategy (Class 11–12) | The goal changes the mix, as in spec §9: **JEE** → conceptual, numerical, application, higher difficulty, multi-concept. **NEET** → NCERT-focused, conceptual MCQs, assertion-reason, application MCQs. **Board exam** → board pattern and marking. Implemented as a small strategy table next to the question generator (`question_generation/strategy.py`) |
| 5–6 Frontend | `ui_mode` picks the layout; `features` hides screens; goals and stream come from `/meta/options` |
| 7 Adaptive learning | Levels only where `adaptive_difficulty` is on, the "needs attention" label only where `weak_topic_detection` is on; younger classes get gentle repetition instead (7.9). Built: `adaptive_learning/` |
| 8 Tests and plans | Practice tests from Class 3, chapter tests from Class 6, full mock tests and time limits from Class 9 (`practice_tests`, `chapter_tests`, `full_mock_tests`, `timed_tests`); a paper's sections are the formats the class uses (Class 3–5: objective and short answers; Class 6–8 add long answers; Class 9–12 add numerical problems); a test's size is capped like a practice (7.4). The study plan's final test is the biggest the class has; Nursery–Class 2 plans have none. Built: `question_generation/paper.py`, `services/mock_test_service.py`, `adaptive_learning/planner.py` |
| 10 Papers, misconceptions, exam modes | Previous-year papers are analysed from Class 9 (`previous_year_questions`) and a test like them is timed at the paper's pace; misconceptions are looked for from Class 3 (`misconception_detection`); a Class 11–12 learner (`competitive_exam_modes`) whose goal is JEE, NEET or CUET takes every test in that exam's pattern — sections, +4 / −1 (CUET +5 / −1), pace — and their study plan's final test is timed the same way. Built: `question_generation/paper.py` (`EXAMS`), `analytics/papers.py`, `adaptive_learning/misconceptions.py` |

## 7.11 Changing a rule

1. Edit the group in `backend/app/class_profiles/registry.py`.
2. Run `pytest tests/unit/test_class_profiles.py`. The tests insist that: all 15 classes have a
   profile; the Class 5 and Class 12 profiles still match the spec's examples; complexity never
   goes *down* as the class goes up; Nursery–Class 2 stays free of exam features; stream and
   competitive goals stay limited to Class 11–12.
3. Update the tables on this page.

No database migration is needed — profiles are configuration, not data.
