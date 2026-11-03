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
  | "competitive_exam_modes",
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

export interface ApiErrorBody {
  code: string;
  message: string;
  details: { field: string; message: string }[] | null;
}
