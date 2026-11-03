/**
 * Every word shown on screen, in one place. English only for now; Step 11 adds Hindi and
 * Hinglish with the same shape. Parent screens use parent words (docs/04 §4.5).
 */
export const copy = {
  appName: "EduGuide AI",
  soon: "Soon",
  signOut: "Sign out",
  loading: "Loading…",

  landing: {
    signIn: "Sign in",
    title: "Turn Your Child's Books Into a Personalized AI Tutor",
    subtitle:
      "Upload textbooks, notes and question papers. EduGuide AI creates personalized practice, explains difficult concepts, tracks progress and helps parents understand exactly what their child needs to improve.",
    getStarted: "Get Started",
    seeHow: "See How It Works",
    howTitle: "How it works",
    steps: [
      {
        emoji: "📘",
        title: "Upload",
        text: "Add your child's textbooks, school notes and old question papers.",
      },
      {
        emoji: "🔍",
        title: "Understand",
        text: "EduGuide reads every book and finds the chapters, exercises and questions.",
      },
      {
        emoji: "✏️",
        title: "Practice",
        text: "Your child gets practice made for their class, with hints before answers.",
      },
      {
        emoji: "📈",
        title: "Improve",
        text: "See what your child knows, where they struggle, and what to do next.",
      },
    ],
    classesTitle: "Made for every class, Nursery to Class 12",
    classesText: "The screens and the questions change as your child grows.",
    groups: [
      {
        emoji: "🧸",
        title: "Nursery – Class 2",
        text: "Pictures, big buttons, counting and matching. No marks, no timers.",
      },
      { emoji: "🌱", title: "Class 3 – 5", text: "Chapter practice with small, step-by-step explanations." },
      { emoji: "🔭", title: "Class 6 – 8", text: "Concepts, real-life questions and chapter tests." },
      {
        emoji: "🎯",
        title: "Class 9 – 12",
        text: "Board-style practice, timed tests, and JEE, NEET and CUET goals.",
      },
    ],
    trust: "Your books stay private to your family. Every answer shows where it came from.",
    preview: {
      question: "Which one is an apple?",
      choices: [
        { emoji: "🍎", label: "Apple", correct: true },
        { emoji: "🐱", label: "Cat", correct: false },
        { emoji: "🚗", label: "Car", correct: false },
      ],
      praise: "Yay! Well done! ⭐",
    },
  },

  login: {
    title: "Welcome back",
    subtitle: "Sign in to continue learning.",
    email: "Email",
    password: "Password",
    submit: "Sign in",
    noAccount: "New to EduGuide?",
    createAccount: "Create an account",
  },

  register: {
    title: "Welcome to EduGuide AI 👋",
    whoAreYou: "Who are you?",
    parent: "Parent",
    parentHint: "I want to help my child learn",
    student: "Student",
    studentHint: "I want to study on my own",
    fullName: "Your name",
    email: "Email",
    password: "Password",
    passwordHint: "At least 8 characters",
    submit: "Create account",
    haveAccount: "Already have an account?",
    signIn: "Sign in",
  },

  profileForm: {
    classTitle: "Which class?",
    classHint: "Everything else depends on the class, so it comes first.",
    bands: {
      foundational: "Early years",
      preparatory: "Primary",
      middle: "Middle school",
      secondary: "Secondary",
      senior_secondary: "Senior secondary",
    } as Record<string, string>,
    childName: "Child's name",
    age: "Age",
    ageHint: "Optional",
    board: "Board",
    boardName: "Name of the board",
    boardNamePlaceholder: "For example, MP Board",
    medium: "Medium of instruction at school",
    language: "Language for explanations",
    stream: "Stream",
    goal: "Learning goal",
    subjects: "Subjects",
    subjectsHint: "Tap to choose, or add your own.",
    addSubject: "Add a subject",
    add: "Add",
  },

  onboarding: {
    childTitle: "Add Child",
    childSubtitle: "Tell us about your child. You can add more children later.",
    childSubmit: "Add child",
    profileTitle: "Your class details",
    profileSubtitle: "We use these to choose the right questions and explanations for you.",
    profileSubmit: "Save and start",
  },

  whoIsLearning: {
    title: "Who is learning today?",
    subtitle: "Tap a name to hand the device to your child.",
    addChild: "Add a child",
    parentArea: "Parent area",
  },

  parent: {
    nav: "Parent menu",
    childrenTitle: "Children",
    childrenSubtitle: "Add, change or remove your children's profiles.",
    addChild: "Add child",
    startLearning: "Start learning",
    edit: "Edit",
    goal: "Goal",
    noProfile: "Class details missing",
    newChildTitle: "Add Child",
    editTitle: "Edit profile",
    save: "Save changes",
    removeTitle: "Remove this child",
    removeText: (name: string) =>
      `This deletes ${name}'s practice and progress for good. Books added for ${name} stay in your library.`,
    remove: (name: string) => `Remove ${name}`,
    removeConfirm: "Yes, remove",
    cancel: "Cancel",
    settingsTitle: "Settings",
    account: "Account",
    name: "Name",
    email: "Email",
    language: "Language",
  },

  learn: {
    hello: (name: string) => `Hi ${name} 👋`,
    nav: "Learning menu",
    playfulIntro: "What shall we do today?",
    intro: "What would you like to do today?",
    comingSoon: "Your practice will appear here very soon.",
    myClassDetails: "My class details",
    switchLearner: "Grown-ups",
  },

  exitChildMode: {
    title: "For grown-ups",
    text: "Enter the parent's password to leave this learner's screen.",
    password: "Parent's password",
    submit: "Continue",
    back: "Back to learning",
  },

  nav: {
    dashboard: "Dashboard",
    children: "Children",
    books: "My Books",
    practice: "Practice",
    tests: "Mock Tests",
    plans: "Study Plans",
    progress: "Progress",
    assistant: "AI Assistant",
    settings: "Settings",
    home: "Home",
    learn: "Learn",
    studentTests: "Tests",
    studyPlan: "Study Plan",
    tutor: "AI Tutor",
    playAndLearn: "Play & Learn",
    myStars: "My Stars",
  },

  notFound: {
    title: "We couldn't find that page",
    back: "Go to the home page",
  },

  // Other errors show the backend's message, which is written to be safe for parents.
  errors: {
    unreachable: "We can't reach EduGuide right now. Please try again in a minute.",
    unexpected: "Something went wrong on our side. Please try again.",
  },
};
