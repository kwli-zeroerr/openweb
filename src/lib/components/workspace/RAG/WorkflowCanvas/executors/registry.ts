import type { Executor } from "./Executor";
import { NativeExecutor } from "./NativeExecutor";
import { LangGraphExecutor } from "./LangGraphExecutor";

export type ExecutorName = "native" | "langgraph";

export function createExecutor(name: ExecutorName): Executor {
  switch (name) {
    case "langgraph":
      return new LangGraphExecutor();
    case "native":
    default:
      return new NativeExecutor();
  }
}


