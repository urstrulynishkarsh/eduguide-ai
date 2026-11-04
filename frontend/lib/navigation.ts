import {
  BarChart3,
  BookOpen,
  Bot,
  CalendarCheck,
  ClipboardCheck,
  Home,
  LayoutDashboard,
  Lightbulb,
  PencilLine,
  Settings,
  Users,
  type LucideIcon,
} from "lucide-react";

import type { copy } from "@/lib/copy";
import type { ClassFeatures, ReviseRequest, UIMode } from "@/lib/types";

export interface NavItem {
  label: keyof typeof copy.nav;
  href: string;
  icon: LucideIcon;
  /** Shown instead of the icon in the two younger layouts. */
  emoji?: string;
  /** Hidden unless the learner's class has this feature. */
  feature?: keyof ClassFeatures;
}

const home: NavItem = { label: "home", href: "/learn", icon: Home, emoji: "🏠" };
const practice: NavItem = {
  label: "practice",
  href: "/learn/practice",
  icon: PencilLine,
  emoji: "✏️",
};
const learn: NavItem = { label: "learn", href: "/learn/concepts", icon: Lightbulb, emoji: "💡" };
const progress: NavItem = {
  label: "progress",
  href: "/learn/progress",
  icon: BarChart3,
  emoji: "📈",
};

/** All seven items of spec §38. */
const fullMenu: NavItem[] = [
  home,
  practice,
  learn,
  {
    label: "studentTests",
    href: "/learn/tests",
    icon: ClipboardCheck,
    emoji: "📝",
    feature: "practice_tests",
  },
  progress,
  { label: "studyPlan", href: "/learn/plan", icon: CalendarCheck, emoji: "🗓️" },
  { label: "tutor", href: "/learn/tutor", icon: Bot, emoji: "🤖" },
];

/** Smaller menus for the younger classes (docs/04 §4.4): no tests, few words. */
const STUDENT_NAV: Record<UIMode, NavItem[]> = {
  playful: [
    home,
    { label: "playAndLearn", href: "/learn/practice", icon: PencilLine, emoji: "🎈" },
    { label: "myStars", href: "/learn/progress", icon: BarChart3, emoji: "⭐" },
  ],
  friendly: [home, practice, learn, progress],
  standard: fullMenu,
  dense: fullMenu,
};

export const PARENT_NAV: NavItem[] = [
  { label: "dashboard", href: "/parent/dashboard", icon: LayoutDashboard },
  { label: "children", href: "/parent/children", icon: Users },
  { label: "books", href: "/parent/books", icon: BookOpen },
  { label: "practice", href: "/parent/practice", icon: PencilLine },
  { label: "tests", href: "/parent/tests", icon: ClipboardCheck },
  { label: "plans", href: "/parent/plans", icon: CalendarCheck },
  { label: "progress", href: "/parent/progress", icon: BarChart3 },
  { label: "assistant", href: "/parent/assistant", icon: Bot },
  { label: "settings", href: "/parent/settings", icon: Settings },
];

/** The learner's menu: the layout's items, minus features the class does not have. */
export function studentNav(uiMode: UIMode, features: ClassFeatures): NavItem[] {
  return STUDENT_NAV[uiMode].filter((item) => !item.feature || features[item.feature]);
}

/** Learn a Concept with an "Explain this" request filled in (a recommendation, a plan task, a mistake). */
export function conceptHref(revise: ReviseRequest, task?: string): string {
  const query = `q=${encodeURIComponent(revise.question)}${task ? `&task=${task}` : ""}`;
  return `/learn/concepts/${revise.chapter_id}?${query}`;
}
