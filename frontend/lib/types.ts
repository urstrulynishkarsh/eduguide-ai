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
}

export interface ApiErrorBody {
  code: string;
  message: string;
  details: { field: string; message: string }[] | null;
}
