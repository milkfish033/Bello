export interface Message {
  role: "user" | "assistant";
  content: string;
  status?: "loading" | "error";
  quote_md?: string | null;
  current_intent?: string | null;
  /** 思考过程步骤（类似 Cursor），仅 assistant 消息可能有 */
  thinking_steps?: string[];
}
