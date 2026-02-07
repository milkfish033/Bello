export interface Message {
  role: "user" | "assistant";
  content: string;
  status?: "loading" | "error";
  quote_md?: string | null;
  current_intent?: string | null;
}
