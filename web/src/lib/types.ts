export type Status = "todo" | "in_progress" | "done";

export type User = {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  email: string;
  is_active: boolean;
};

export type TaskUser = Pick<User, "id" | "username" | "first_name" | "last_name">;

export type Task = {
  id: number;
  title: string;
  description: string;
  status: Status;
  status_display: string;
  due_date: string | null;
  assigned_to: TaskUser | null;
  created_by: TaskUser;
  completed_at: string | null;
  is_overdue: boolean;
  created_at: string;
  updated_at: string;
};

export type Paginated<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export type Summary = {
  total: number;
  todo: number;
  in_progress: number;
  done: number;
  overdue: number;
};

export type TaskFilters = {
  status: string;
  due_date_after: string;
  due_date_before: string;
  search: string;
  overdue: boolean;
  page: number;
};

export type SpecSource = "issue" | "subject";

// Exactly one of the two keys: the API rejects both or neither.
export type SpecCreateInput = { issue_url: string } | { subject: string };

export type Spec = {
  id: number;
  source: SpecSource;
  issue_url: string;
  repo: string;
  issue_number: number | null;
  issue_title: string;
  summary: string;
  acceptance_criteria: string[];
  implementation_steps: string[];
  risks: string[];
  out_of_scope: string[];
  size: "S" | "M" | "L";
  body_markdown: string;
  model: string;
  prompt_version: string;
  latency_ms: number;
  input_chars: number;
  truncated: boolean;
  published: boolean;
  published_issue_url: string;
  published_issue_number: number | null;
  created_at: string;
};

export type SpecTaskInput = {
  title: string;
  description?: string;
  due_date?: string | null;
  assigned_to?: number | null;
};

export type SpecTasksRequest = { tasks: SpecTaskInput[] };

export type SpecTasksResponse = { tasks: Task[] };

export type SpecConfig = {
  ai_enabled: boolean;
  publish_enabled: boolean;
};

export const emptyFilters: TaskFilters = {
  status: "",
  due_date_after: "",
  due_date_before: "",
  search: "",
  overdue: false,
  page: 1,
};
