/** The backend's response shapes that the screens use (see docs/03-api-contracts.md). */

export type Role = "parent" | "student";
export type UIMode = "playful" | "friendly" | "standard" | "dense";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  preferred_language: string;
}

export interface StudentProfile {
  class_level: string;
  board: string;
  board_name: string | null;
  medium: string;
  primary_language: string;
  stream: string | null;
  goal: string;
  subjects: string[];
  class_label: string;
}

export interface Student {
  id: string;
  name: string;
  age: number | null;
  has_own_login: boolean;
  profile: StudentProfile | null;
}

export interface Me {
  user: User;
  active_role: Role;
  active_student: Student | null;
  onboarding_complete: boolean;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
}

export interface AuthResponse {
  user: User;
  tokens: TokenPair;
}

export interface ChildSession {
  access_token: string;
}

export interface Option {
  code: string;
  label: string;
}

export interface LanguageOption extends Option {
  native_label: string;
}

export interface ClassOption {
  class_level: string;
  label: string;
  band: string;
  requires_stream: boolean;
  available_goals: string[];
  default_goal: string;
  suggested_subjects: string[];
  suggested_subjects_by_stream: Record<string, string[]> | null;
}

export interface OnboardingOptions {
  classes: ClassOption[];
  material_types: Option[];
  upload: { accepted_extensions: string[]; max_file_mb: number };
  boards: Option[];
  streams: Option[];
  goals: Option[];
  languages: LanguageOption[];
  mediums: LanguageOption[];
}

export type ClassFeatures = Record<
  | "exam_style_practice"
  | "practice_tests"
  | "chapter_tests"
  | "adaptive_difficulty"
  | "weak_topic_detection"
  | "timed_tests"
  | "full_mock_tests"
  | "previous_year_questions"
  | "board_exam_preparation"
  | "competitive_exam_modes"
  | "misconception_detection",
  boolean
>;

export interface ClassProfile {
  class_level: string;
  label: string;
  ui_mode: UIMode;
  features: ClassFeatures;
  question_formats: string[];
  default_session_questions: number;
  max_session_questions: number;
}

// ---- My Books (docs/03 §3.3)

export interface Source {
  book_id: string;
  book_title: string;
  chapter: string | null;
  exercise: string | null;
  page: number | null;
}

export type DocumentStatus = "queued" | "processing" | "ready" | "failed";

export interface BookDocument {
  id: string;
  original_filename: string;
  status: DocumentStatus;
  progress: { step: string; state: "pending" | "active" | "done" | "failed" }[];
  error: { code: string; message: string } | null;
  summary: { chapters: number | null; exercises: number | null; questions: number | null };
}

export interface Book {
  id: string;
  title: string;
  subject: string;
  material_type: string;
  class_level: string;
  class_label: string;
  student_id: string | null;
  status: string;
  chapter_count: number;
  documents: BookDocument[];
}

export interface Chapter {
  id: string;
  book_id: string;
  label: string;
  page_start: number | null;
  page_end: number | null;
  topic_count: number;
  exercise_count: number;
  question_count: number;
}

export interface Exercise {
  id: string;
  label: string;
  title: string;
  page_start: number | null;
  question_count: number;
}

export interface ChapterDetail extends Chapter {
  topics: { id: string; number: string | null; title: string }[];
  exercises: Exercise[];
}

export interface ExerciseDetail extends Exercise {
  questions: {
    id: string;
    number: string | null;
    text: string;
    instructions: string | null;
    page_start: number | null;
  }[];
}

// ---- Practice and progress (docs/03 §3.5)

export interface Question {
  id: string;
  number: number;
  format: string;
  difficulty: string;
  case: string | null;
  text: string;
  options: string[];
  match_left: string[];
  match_right: string[];
  unit: string | null;
  source: Source;
}

export interface PracticeItem {
  question: Question;
  attempts: number;
  correct: boolean | null;
  hints_shown: number;
  hints_total: number;
  steps_shown: boolean;
  answer_shown: boolean;
}

export interface PracticeSession {
  id: string;
  student_id: string;
  status: "preparing" | "ready" | "completed" | "failed";
  error: { code: string; message: string } | null;
  question_count: number;
  items: PracticeItem[];
  answered: number;
  correct: number;
}

export interface AnswerResult {
  correct: boolean;
  try_again: boolean;
  feedback: string | null;
  correct_answer: string | null;
  session_completed: boolean;
}

export interface Help {
  hint: string | null;
  hints_left: number;
  concept: string | null;
  steps: string[];
  final_answer: string | null;
}

export interface Explanation {
  explanation: string;
  steps: string[];
  sources: Source[];
}

export interface Progress {
  questions_answered: number;
  correct_first_time: number;
  accuracy: number | null;
  time_spent_ms: number;
  hints_used: number;
  sessions_completed: number;
  by_chapter: { id: string; name: string; attempted: number; accuracy: number }[];
  by_topic: { id: string; name: string; attempted: number; accuracy: number }[];
  recent_sessions: {
    id: string;
    status: PracticeSession["status"];
    questions: number;
    answered: number;
    correct: number;
    created_at: string;
  }[];
}

/**
 * A request the backend has already filled in (a recommendation, a task of the study plan): sent back
 * as it is to POST /practice/sessions or /mock-tests.
 */
export type RequestBody = Record<string, string | number | null>;

/** The "Explain this" request of a learn task or a recommendation (POST /learn/explain). */
export interface ReviseRequest {
  question: string;
  chapter_id: string | null;
}

// ---- Mock tests (docs/03 §3.7)

/** previous_year: a test like a book's previous-year papers, started from their analysis. */
export type TestKind = "practice" | "chapter" | "full_mock" | "previous_year";

/** JEE / NEET / CUET mode: the competitive exam whose pattern a Class 11–12 learner's tests follow. */
export type Exam = "jee" | "neet" | "cuet";

/** An answer as the API takes and gives it back: the field that fits the question. */
export interface Answer {
  option?: number | null;
  value?: number | null;
  text?: string | null;
  pairs?: number[] | null;
}

export interface PaperSection {
  code: string;
  title: string;
  marks: number;
  /** Marks lost for a wrong answer; 0: no negative marking. */
  negative: number;
  questions: Question[];
}

export interface MockTest {
  id: string;
  student_id: string;
  kind: TestKind;
  exam: Exam | null;
  status: "preparing" | "ready" | "failed";
  book_title: string | null;
  chapter: string | null;
  topic: string | null;
  exercise: string | null;
  question_count: number;
  total_marks: number;
  duration_minutes: number | null;
  difficulty: string;
  attempts: { id: string; started_at: string; submitted_at: string | null; score: number | null }[];
}

export interface MockTestDetail extends MockTest {
  error: { code: string; message: string } | null;
  sections: PaperSection[];
}

export interface TestAttempt {
  id: string;
  mock_test_id: string;
  status: "in_progress" | "submitted";
  seconds_left: number | null;
  sections: PaperSection[];
  responses: Record<string, Answer>;
}

export interface TestReport {
  score: number;
  total_marks: number;
  percentage: number;
  time_taken_ms: number;
  correct: number;
  wrong: number;
  unanswered: number;
  sections: { code: string; title: string; score: number; total_marks: number }[];
  areas: (Area & { questions: number; accuracy: number })[];
  questions: {
    question: Question;
    marks: number;
    marks_awarded: number | null;
    correct: boolean | null;
    response: Answer | null;
    feedback: string | null;
    solution: { concept: string; steps: string[]; final_answer: string };
  }[];
}

// ---- Study plans (docs/03 §3.7)

export interface PlanItem {
  id: string;
  kind: "learn" | "practice" | "test";
  status: "pending" | "done" | "skipped" | "missed";
  minutes: number;
  reason: string;
  book_title: string;
  chapter: string | null;
  topic: string | null;
  practice: RequestBody | null;
  revise: ReviseRequest | null;
  test: RequestBody | null;
}

export interface StudyPlan {
  id: string;
  exam_date: string;
  daily_minutes: number;
  status: "active" | "finished";
  days_left: number;
  /** Today (India time): the plan is planned again on the first visit of each day. */
  planned_on: string;
  unscheduled: number;
  done: number;
  missed: number;
  total: number;
  days: { day: string; minutes: number; items: PlanItem[] }[];
}

// ---- Adaptive learning and the dashboard (docs/03 §3.6, §3.8)

/** A topic of a chapter, or the chapter itself. */
export interface Area {
  chapter_id: string;
  chapter: string;
  topic: string | null;
}

export interface AreaMastery extends Area {
  mastery: number;
  attempts: number;
}

export interface Recommendation extends Area {
  id: string;
  status: "active" | "done";
  reason: string;
  practice: RequestBody;
  revise: ReviseRequest | null;
}

export interface Dashboard {
  week: { day: string; answered: number; correct: number; minutes: number }[];
  strong: AreaMastery[];
  needs_attention: AreaMastery[];
  recommendations: Recommendation[];
  tests: {
    attempt_id: string;
    mock_test_id: string;
    kind: TestKind;
    place: string | null;
    score: number;
    total_marks: number;
    percentage: number;
    submitted_at: string;
  }[];
  plan: { days_left: number; done: number; total: number; today: PlanItem[] } | null;
  /** Up to 3 active misconceptions. */
  misconceptions: Misconception[];
}

/** A wrong idea the learner keeps showing in an area (docs/03 §3.9). */
export interface Misconception extends Area {
  id: string;
  status: "active" | "resolved";
  pattern: string;
  fix: string;
  answers: number;
  practice: RequestBody;
  revise: ReviseRequest;
}

// ---- Previous-year paper analysis (docs/03 §3.9)

export interface PaperAnalysis {
  status: "none" | "preparing" | "ready" | "failed";
  papers: {
    document_id: string;
    title: string;
    status: "new" | "preparing" | "ready" | "failed";
    error: { code: string; message: string } | null;
    year: number | null;
    questions: number;
    total_marks: number;
  }[];
  chapters: (Area & {
    marks_per_paper: number;
    share: number;
    papers: number;
    trend: "rising" | "falling" | "steady" | null;
    practice: RequestBody;
  })[];
  unmatched: { questions: number };
  topics: (Area & { questions: number; papers: number })[];
  formats: { format: string; share: number }[];
  layout: { title: string; questions: number; marks: number }[];
  layout_year: number | null;
  test: RequestBody | null;
}

// ---- The Parent AI Assistant and the Student AI Tutor (docs/03 §3.8)

export type ChatKind = "assistant" | "tutor";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources: Source[];
  /** Tutor replies: how much help this was, on the hint ladder. */
  rung: "hint_1" | "hint_2" | "concept" | "steps" | "answer" | null;
}

export interface ChatSummary {
  id: string;
  student_id: string;
  title: string;
}

export interface Chat extends ChatSummary {
  messages: ChatMessage[];
}

export interface ApiErrorBody {
  code: string;
  message: string;
  details: { field: string; message: string }[] | null;
}
