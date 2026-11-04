import type { Reason } from "@/lib/types";

/**
 * Every word shown on screen in English. hi.ts and hinglish.ts have the same shape (the `Copy` type
 * makes sure none is missing); lib/copy/index.ts lists the languages. Parent screens use parent words
 * (docs/04 §4.5).
 */
/** "1 chapter", "3 chapters". */
function counted(count: number, word: string): string {
  return `${count} ${word}${count === 1 ? "" : "s"}`;
}

const percent = (share: number | null) => `${Math.round((share ?? 0) * 100)}%`;
const level: Record<string, string> = { easy: "easy", medium: "medium", hard: "hard" };
const rightLately = (reason: Reason) =>
  `${percent(reason.accuracy)} right in the last ${reason.answers} answers`;

export const en = {
  /** The language itself: its code, its name in the picker, `lang` of the page, how dates are written. */
  language: { code: "en", name: "English", htmlLang: "en", locale: "en-IN" },
  /** The language picker's label (for screen readers; the picker shows each language's own name). */
  languagePicker: "Language",
  signOut: "Sign out",
  cancel: "Cancel",
  start: "Start",
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
    myClassDetails: "My class details",
    switchLearner: "Grown-ups",
    recent: "Your recent practice",
    continue: "Continue",
    recommended: "Recommended for You",
    todaysPlan: "Today's plan",
    openPlan: "Open my plan",
    revise: "Revise the idea first",
  },

  switcher: {
    label: "Showing",
  },

  dashboard: {
    title: (name: string) => `${name} at a glance`,
    uploadBook: "Upload Book",
    createPractice: "Create Practice",
    books: (count: number) => counted(count, "book"),
    week: "This week",
    weekTotal: (answered: number, minutes: number) =>
      `${counted(answered, "question")} answered · ${minutes} min`,
    dayLine: (day: string, answered: number, correct: number) =>
      `${day}: ${answered} answered, ${correct} right the first time`,
    right: "Right the first time",
    notRight: "Not right the first time",
    strong: "Strong areas",
    needsAttention: "Needs attention",
    noAreas: "This fills in after a few practices.",
    recommended: "Recommended",
    startRecommended: "Start Recommended Practice",
    recommendationDone: "Done today ✓",
    recentTests: "Recent tests",
    allTests: "All tests",
    plan: "Today's plan",
    planLine: (daysLeft: number, done: number, total: number) =>
      `${counted(daysLeft, "day")} to the exam · ${done} of ${total} tasks done`,
    seePlan: "See the plan",
  },

  library: {
    title: "My Learning Library",
    subtitle: "Books, notes and question papers for your family.",
    upload: "Upload Book",
    empty: "No books yet. Upload a textbook, notes or a question paper to get started.",
    forChild: (name: string) => `For ${name}`,
    forFamily: "For the whole family",
    chapters: (count: number) => counted(count, "chapter"),
    status: {
      empty: "No files yet",
      processing: "Reading…",
      ready: "Ready",
      failed: "Needs attention",
    } as Record<string, string>,
    files: "Files",
    addFile: "Add another file",
    retry: "Try again",
    removeFile: "Remove",
    deleteBook: "Delete this book",
    deleteBookText: "This removes the book, its files, and the practice questions made from it.",
    deleteConfirm: "Yes, delete",
    chaptersTitle: "Chapters",
    papersTitle: "Papers",
    noChapters: "Chapters appear here once the book has been read.",
    found: (chapters: number, exercises: number, questions: number) =>
      `Found ${counted(chapters, "chapter")}, ${counted(exercises, "exercise")} and ${counted(questions, "question")}.`,
  },

  upload: {
    title: "Upload Book",
    subtitle: "Add a textbook, school notes, a question bank or old question papers.",
    bookTitle: "Book name",
    bookTitlePlaceholder: "For example, Class 7 Mathematics",
    subject: "Subject",
    subjectPlaceholder: "For example, Mathematics",
    materialType: "What is it?",
    forWhom: "Who is it for?",
    family: "The whole family",
    file: "File",
    fileHint: (extensions: string, mb: number) => `${extensions} · up to ${mb} MB`,
    submit: "Upload",
    sending: (percent: number) => `Uploading… ${percent}%`,
    failed: "The upload did not finish. Please try again.",
    tooBig: (mb: number) =>
      `This file is bigger than ${mb} MB. Try splitting it, for example one chapter per file.`,
    // docs/04 §4.5: the parent never reads the technical stage names.
    steps: {
      extract_text: "Reading your book",
      detect_chapters: "Finding the chapters",
      detect_exercises: "Finding exercises and questions",
      detect_topics: "Understanding the topics",
      make_chunks: "Getting practice ready",
      embed_chunks: "Getting practice ready",
    } as Record<string, string>,
  },

  chapter: {
    learn: "Learn",
    practice: "Practice",
    exerciseQuestions: "Exercise Questions",
    generate: "Generate Questions",
    takeTest: "Take Test",
    topics: "Topics",
    exercises: "Exercises",
    sections: "Sections",
    questions: (count: number) => counted(count, "question"),
    page: (page: number) => `page ${page}`,
    fromBook: "As printed in the book",
    noExercises: "No exercises were found in this chapter.",
  },

  practiceForm: {
    title: "Create Practice",
    subtitle: (name: string) => `Questions made for ${name}'s class, from your books.`,
    source: "Practise from",
    allBooks: "All books",
    wholeBook: "The whole book",
    wholeChapter: "The whole chapter",
    book: "Book",
    chapter: "Chapter",
    exercise: "Exercise",
    count: "Number of questions",
    countHint: (max: number) => `Up to ${max}`,
    difficulty: "Difficulty",
    type: "Question type",
    language: "Language",
    submit: "Create Practice",
    playfulTitle: "Let's play!",
    playfulAll: "Everything",
    noBooks: "There are no books for this class yet. A grown-up can upload one in My Books.",
  },

  difficulties: { easy: "Easy", medium: "Medium", hard: "Hard", mixed: "Mixed" } as Record<string, string>,

  testKinds: {
    practice: "Practice test",
    chapter: "Chapter test",
    full_mock: "Full mock test",
    previous_year: "Previous-year pattern test",
  } as Record<string, string>,

  exams: { jee: "JEE Main pattern", neet: "NEET pattern", cuet: "CUET pattern" } as Record<string, string>,

  tests: {
    title: "Mock Tests",
    myTitle: "Tests",
    subtitle: (name: string) => `Tests made for ${name}'s class, from your books, marked like an exam.`,
    create: "Create Test",
    none: "No tests yet.",
    notForClass: "Tests start from Class 3.",
    kind: "Kind of test",
    chooseChapter: "Choose a chapter for a chapter test.",
    countHint: (max: number) => `Up to ${max}. Leave empty for the usual length.`,
    timeLimit: "Time limit in minutes",
    noTimeLimitHint: "Leave empty for no time limit.",
    fullMockTimeHint: "Leave empty for about 2 minutes a mark.",
    allBooks: "All books",
    summary: (questions: number, marks: number, minutes: number | null) =>
      [
        counted(questions, "question"),
        counted(marks, "mark"),
        minutes ? `${minutes} min` : "No time limit",
      ].join(" · "),
    preparingTitle: "Getting the test ready…",
    failedTitle: "This test could not be made",
    start: "Start test",
    continue: "Continue",
    retake: "Take again",
    result: "See result",
    inProgress: "In progress",
    sittings: "Sittings",
    seeQuestions: "See the questions",
    sectionTitle: (code: string, title: string, marks: number, negative: number) =>
      `Section ${code} · ${title} · ${counted(marks, "mark")} each` +
      (negative ? `, −${negative} for a wrong answer` : ""),
    examMode: (exam: string) =>
      `Tests follow the ${exam}: a wrong answer loses marks, as in the exam. A question left out costs nothing.`,
    previous: "Previous",
    next: "Next",
    answered: (count: number, total: number) => `${count} of ${total} answered`,
    grid: "Go to a question",
    timeLeft: "Time left",
    submit: "Submit test",
    submitCheck: (left: number) =>
      left ? `${counted(left, "question")} not answered yet. Submit anyway?` : "Submit the test now?",
    submitYes: "Yes, submit",
    marking: "Marking your answers…",
    // The report
    reportTitle: "Result",
    score: "Score",
    timeTaken: "Time taken",
    correct: "Correct",
    wrong: "Wrong",
    notAnswered: "Not answered",
    bySection: "By section",
    byArea: "By chapter and topic",
    questions: "Every question",
    marks: (awarded: number | null, marks: number) => `${awarded ?? 0} / ${marks}`,
    yourAnswer: "Your answer:",
    solution: "Solution",
    allTests: "All tests",
  },

  papers: {
    title: "Previous-year papers",
    intro: "See which chapters carry the most marks, then practise them or take a test like the papers.",
    analyse: "Analyse the papers",
    analyseAgain: "Analyse again",
    analyseAgainHint: "Added a paper or a textbook? Analyse again.",
    preparing: "Reading the papers… This takes a minute or two.",
    failed: "We couldn't analyse these papers. Please try again.",
    paperLine: (year: number | null, questions: number, marks: number) =>
      [year ?? "Year not shown", counted(questions, "question"), counted(marks, "mark")].join(" · "),
    notYet: "Not analysed yet",
    whereMarks: "Where the marks go",
    marksLine: (marks: number, papers: number, total: number) =>
      `${counted(marks, "mark")} a paper · in ${papers} of ${counted(total, "paper")}`,
    trend: { rising: "↑ More each year", falling: "↓ Less each year", steady: "Steady" } as Record<
      string,
      string
    >,
    unmatched: (questions: number) => `${counted(questions, "question")} not from your textbooks.`,
    noTextbook: "Upload this class's textbook too, so the questions can be matched to its chapters.",
    topics: "Topics asked most",
    topicLine: (questions: number, papers: number) =>
      `${counted(questions, "question")} · in ${counted(papers, "paper")}`,
    kinds: "Kinds of questions",
    layout: (year: number | null) => (year ? `The ${year} paper` : "The latest paper"),
    layoutLine: (questions: number, marks: number) =>
      `${counted(questions, "question")} · ${counted(marks, "mark")} each`,
    practise: "Practise",
    makeTest: "Make a test like these papers",
    otherClass: (label: string) =>
      `These papers are for ${label}. Choose a child in ${label} to practise them.`,
  },

  mistakes: {
    title: "Understand Mistakes",
    myTitle: "Mistakes to fix",
    remember: "Remember:",
    seen: (answers: number) => `Seen in ${counted(answers, "answer")}`,
    fixed: "Put right ✓",
    practise: "Practise this",
  },

  plans: {
    title: "Study Plans",
    myTitle: "Study Plan",
    none: (name: string) =>
      `${name} has no study plan yet. A plan spreads the chapters over the days until the exam.`,
    noneInChildMode: "No study plan yet. A grown-up can make one in the parent area.",
    noneSolo:
      "No study plan yet. Tell us when your exam is, and the chapters are spread over the days until then.",
    make: "Make a plan",
    makeNew: "Make a new plan",
    remove: "Remove this plan",
    removeConfirm: "Yes, remove",
    newTitle: "Make a study plan",
    newSubtitle: "The tasks come from what the learner already knows, and change as they practise.",
    replaces: "This replaces the current plan.",
    examDate: "Exam date",
    dailyMinutes: "Minutes a day",
    dailyMinutesHint: "Between 10 and 300",
    target: "Target score (%)",
    targetHint: "Chapters below it get more practice.",
    chapters: "Chapters in the exam",
    chaptersHint: "Choose none to include every chapter.",
    submit: "Make plan",
    daysLeft: (days: number) => `${counted(days, "day")} to the exam`,
    examOn: (date: string) => `Exam on ${date}`,
    progress: (done: number, total: number) => `${done} of ${total} tasks done`,
    missed: (count: number) => `${count} missed`,
    perDay: (minutes: number) => `${minutes} min a day`,
    unscheduled: "Not everything fits: add minutes a day or choose fewer chapters.",
    finished: "The exam day has come. Make a new plan for the next exam.",
    today: "Today",
    comingUp: "Coming up",
    nothingToday: "Nothing planned for today. 🎉",
    minutes: (minutes: number) => `${minutes} min`,
    kinds: { learn: "Learn", practice: "Practice", test: "Test" } as Record<string, string>,
    status: { pending: "To do", done: "Done", skipped: "Skipped", missed: "Missed" } as Record<
      string,
      string
    >,
    wholeBook: (title: string) => `${title} (whole book)`,
    markDone: "✓ Done",
    undo: "Undo",
  },

  formats: {
    mixed: "Mixed",
    mcq: "MCQ",
    visual_choice: "Picture choice",
    matching: "Matching",
    counting: "Counting",
    fill_blank: "Fill in the blanks",
    true_false: "True / False",
    short_answer: "Short answer",
    long_answer: "Long answer",
    numerical: "Numerical",
    assertion_reason: "Assertion / Reason",
    case_based: "Case-based",
  } as Record<string, string>,

  practice: {
    preparingTitle: "Getting your questions ready…",
    preparingText: "Writing and checking new questions takes a minute or two. This page updates by itself.",
    failedTitle: "This practice could not be made",
    readyFor: (name: string) => `Ready for ${name}`,
    startNow: (name: string) => `Start now with ${name}`,
    questionOf: (number: number, total: number) => `Question ${number} of ${total}`,
    check: "Check",
    next: "Next question",
    finish: "See results",
    correct: "Correct! Well done 🎉",
    playfulCorrect: "Yay! Well done! ⭐",
    tryAgain: "Let's try again! 🌟",
    wrong: "Not quite.",
    correctAnswer: (answer: string) => `The answer is: ${answer}`,
    yourAnswer: "Your answer",
    numberPlaceholder: "Type a number",
    textPlaceholder: "Type your answer",
    matchPrompt: (item: string) => `${item} goes with…`,
    hint: "Hint",
    hintsLeft: (left: number) => `${counted(left, "hint")} left`,
    showSteps: "Show Steps",
    showAnswer: "Show Answer",
    concept: "Concept",
    finalAnswer: "Final answer",
    explainTitle: "Explain this question",
    explainStyles: {
      simple: "Explain Simply",
      like_10: "Explain Like I'm 10",
      hindi: "Explain in Hindi",
      hinglish: "Explain in Hinglish",
    } as Record<string, string>,
    generatedFrom: "Generated from concepts in:",
    doneTitle: "Practice complete!",
    playfulDoneTitle: "You did it! 🎉",
    score: (correct: number, total: number) => `${correct} of ${total} correct the first time`,
    stars: (count: number) => `You earned ${counted(count, "star")}!`,
    again: "Practice more",
    home: "Back home",
    busy: "One moment…",
  },

  concepts: {
    title: "Learn a Concept",
    subtitle: "Pick a chapter and ask anything about it.",
    ask: "What would you like to understand?",
    askPlaceholder: "For example: How do I solve 2x + 4 = 10?",
    explain: "Explain",
    styles: {
      normal: "Normal",
      simple: "Explain Simply",
      like_10: "Explain Like I'm 10",
      hindi: "In Hindi",
      hinglish: "In Hinglish",
    } as Record<string, string>,
    basedOn: "Based on:",
    noBooks: "There are no chapters for this class yet.",
  },

  progress: {
    title: "Progress",
    myTitle: "My progress",
    starsTitle: "My Stars",
    answered: "Questions answered",
    accuracy: "Correct the first time",
    time: "Time practising",
    hints: "Hints used",
    byChapter: "By chapter",
    byTopic: "By topic",
    recent: "Recent practice",
    none: "No practice yet. Results appear here after the first practice.",
    minutes: (minutes: number) =>
      minutes < 60 ? `${minutes} min` : `${Math.floor(minutes / 60)}h ${minutes % 60}m`,
    sessionLine: (answered: number, total: number, correct: number) =>
      `${answered} of ${total} answered · ${correct} correct`,
    status: {
      preparing: "Being prepared",
      ready: "Not finished",
      completed: "Finished",
      failed: "Could not be made",
    } as Record<string, string>,
    keepGoing: "Every right answer gives you a star. Keep going!",
  },

  /** Streaks, XP and badges (the youngest see the streak, today's goal and stickers, no XP). */
  rewards: {
    title: "Streak and badges",
    streak: (days: number) => (days ? `🔥 ${counted(days, "day")} in a row` : "🔥 No streak yet"),
    streakHint: "Answer a question every day to keep the streak going.",
    level: (level: number) => `Level ${level}`,
    xp: (inside: number, size: number) => `${inside} / ${size} XP`,
    today: (answered: number, goal: number) => `Today: ${answered} of ${goal} questions`,
    goalDone: "Today's goal done! 🎉",
    gained: (xp: number) => `+${xp} XP`,
    newBadge: (name: string) => `New badge: ${name}`,
    newSticker: (name: string) => `New sticker: ${name}`,
    badgesTitle: "Badges",
    stickersTitle: "My stickers",
    earnedOn: (date: string) => `Earned ${date}`,
    badges: {
      first_practice: { name: "First practice", how: "Finish a practice." },
      perfect_practice: {
        name: "Perfect practice",
        how: "Get every question of a practice right the first time.",
      },
      right_10: { name: "10 right answers", how: "Get 10 questions right the first time." },
      right_100: { name: "100 right answers", how: "Get 100 questions right the first time." },
      streak_3: { name: "3 days in a row", how: "Practise 3 days in a row." },
      streak_7: { name: "A week in a row", how: "Practise 7 days in a row." },
      streak_30: { name: "A month in a row", how: "Practise 30 days in a row." },
      first_test: { name: "First test", how: "Submit a test." },
      topic_mastered: { name: "Topic mastered", how: "Make a topic strong." },
      mistake_fixed: { name: "Mistake put right", how: "Put right a mistake you kept making." },
      level_5: { name: "Level 5", how: "Reach level 5." },
    } as Record<string, { name: string; how: string }>,
  },

  /** Progress over time: the charts of Progress ("Track Progress", never "analytics": docs/04 §4.5). */
  trends: {
    title: "Progress over time",
    weeks: "The last 12 weeks",
    weekOf: (date: string) => `Week of ${date}`,
    tests: "Test scores",
    subjects: "By subject",
    formats: "By kind of question",
    difficulties: "By difficulty",
    table: "Show the numbers",
    week: "Week",
    test: "Test",
    date: "Date",
    score: "Score",
    answered: "Answered",
    minutes: "Minutes",
    byYear: (years: string) => `Marks by year: ${years}`,
  },

  chat: {
    assistant: {
      title: "AI Assistant",
      intro: "Ask about your child's learning: progress, weak topics, what to practise next.",
      placeholder: "Ask a question…",
      // Without the child's name: it is never sent to the AI.
      suggestions: [
        "How is my child doing this week?",
        "Which topics need attention?",
        "What should we practise next?",
        "How did the last test go?",
      ],
      aiOff: "The assistant needs the AI, which is not switched on yet.",
    },
    tutor: {
      title: "AI Tutor",
      intro: "Stuck on a problem? You get a hint first, and more help when you ask for it.",
      placeholder: "Type your question or problem…",
      suggestions: [] as string[],
      aiOff: "The tutor needs the AI, which is not switched on yet.",
    },
    send: "Send",
    thinking: "Thinking…",
    conversations: "Conversations",
    newConversation: "New conversation",
    rungs: { hint_1: "Hint 1", hint_2: "Hint 2", concept: "Concept", steps: "Steps", answer: "Answer" },
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

  /**
   * Labels the backend sends in English (classes, boards, goals…), by code. English shows the
   * backend's own label, so these are empty here; another language fills in what it says differently.
   */
  options: {
    classes: {} as Record<string, string>,
    boards: {} as Record<string, string>,
    streams: {} as Record<string, string>,
    goals: {} as Record<string, string>,
    material_types: {} as Record<string, string>,
  },

  /** Why a recommendation or a plan task was chosen (the backend sends a code and its numbers). */
  reasons: {
    weak: (r) => `${rightLately(r)}. Revise the idea, then practise ${level[r.difficulty ?? ""]} questions.`,
    again: () => "Let's practise this again, with easy questions.",
    next_level: (r) => `${rightLately(r)}. Next: ${level[r.difficulty ?? ""]} questions.`,
    keep_going: (r) => `${rightLately(r)}. A little more practice makes it strong.`,
    review: (r) => `Last practised ${r.days} days ago. A short practice keeps it fresh.`,
    new_chapter: () => "Not practised yet. Start with a short practice.",
    revise: (r) => `${rightLately(r)}. Revise the idea.`,
    strengthen: (r) => `Then strengthen it with ${level[r.difficulty ?? ""]} questions.`,
    final_review: (r) => `${percent(r.mastery)} mastered. A quick review before the exam.`,
    learn_first: () => "Not practised yet. Learn the idea first.",
    first_practice: () => "A first practice of this chapter.",
    towards_aim: (r) => `${percent(r.mastery)} mastered; the aim is ${percent(r.aim)}.`,
    more_practice: (r) => `More practice: the aim is ${percent(r.aim)}.`,
    full_mock_test: () => "A full mock test, timed like the exam.",
    practice_test: () => "A practice test on the whole book.",
    planned: () => "Planned for you.",
  } as Record<string, (reason: Reason) => string>,

  /**
   * Error messages by code. English shows the backend's own message for the rest (written to be safe
   * for parents); another language translates every code it can.
   */
  errors: {
    unreachable: "We can't reach EduGuide right now. Please try again in a minute.",
    internal_error: "Something went wrong on our side. Please try again.",
    // Said more helpfully than the API can, by where it happened: what the parent can do about it.
    questions_ai_not_configured:
      "There are not enough saved questions for this choice, and writing new ones needs the AI, which is not switched on yet. Try another chapter, fewer questions or a different type.",
    explain_ai_not_configured: "Explanations need the AI, which is not switched on yet.",
    marking_ai_not_configured: "Written answers are marked by the AI, which is not switched on yet.",
    analysis_ai_not_configured: "Analysing papers needs the AI, which is not switched on yet.",
  } as Record<string, string>,
};

export type Copy = typeof en;
