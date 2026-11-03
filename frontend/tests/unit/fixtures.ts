import type { OnboardingOptions } from "@/lib/types";

/** A small part of GET /meta/options: one class from three bands. */
export const options: OnboardingOptions = {
  classes: [
    {
      class_level: "ukg",
      label: "UKG",
      band: "foundational",
      requires_stream: false,
      available_goals: ["strong_basics", "other"],
      default_goal: "strong_basics",
      suggested_subjects: ["English", "Hindi", "Maths"],
      suggested_subjects_by_stream: null,
    },
    {
      class_level: "class_7",
      label: "Class 7",
      band: "middle",
      requires_stream: false,
      available_goals: ["school_exam", "strong_basics", "other"],
      default_goal: "school_exam",
      suggested_subjects: ["Mathematics", "Science", "Social Science"],
      suggested_subjects_by_stream: null,
    },
    {
      class_level: "class_11",
      label: "Class 11",
      band: "senior_secondary",
      requires_stream: true,
      available_goals: ["school_exam", "board_exam", "jee", "neet", "cuet", "other"],
      default_goal: "school_exam",
      suggested_subjects: ["English"],
      suggested_subjects_by_stream: {
        science: ["Physics", "Chemistry", "Mathematics"],
        commerce: ["Accountancy", "Economics"],
        arts: ["History", "Political Science"],
      },
    },
  ],
  boards: [
    { code: "cbse", label: "CBSE" },
    { code: "state", label: "State Board" },
  ],
  streams: [
    { code: "science", label: "Science" },
    { code: "commerce", label: "Commerce" },
    { code: "arts", label: "Arts / Humanities" },
  ],
  goals: [
    { code: "school_exam", label: "School exams" },
    { code: "board_exam", label: "Board exams" },
    { code: "jee", label: "JEE" },
    { code: "neet", label: "NEET" },
    { code: "cuet", label: "CUET" },
    { code: "strong_basics", label: "Build strong basics" },
    { code: "other", label: "Other" },
  ],
  languages: [
    { code: "en", label: "English", native_label: "English" },
    { code: "hi", label: "Hindi", native_label: "हिन्दी" },
    { code: "hinglish", label: "Hinglish", native_label: "Hinglish" },
  ],
  mediums: [
    { code: "en", label: "English", native_label: "English" },
    { code: "hi", label: "Hindi", native_label: "हिन्दी" },
  ],
};
