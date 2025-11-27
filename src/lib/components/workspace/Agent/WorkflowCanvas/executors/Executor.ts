import type { WorkflowNode, WorkflowConnection, Message } from "../types";
import type { RagFlowRetrievalResponse } from "$lib/apis/agent";

export interface ExecutionInput {
  question: string;
  nodes: WorkflowNode[];
  connections: WorkflowConnection[];
}

export interface ExecutionOutput extends Partial<RagFlowRetrievalResponse> {
  question: string;
  retrieved_context: string | null;
  llm_output: string | null;
  timings?: Record<string, number>; // 毫秒
  messages?: Record<string, Record<string, Message>>; // nodeId -> { portKey: Message }
}

export interface Executor {
  execute(input: ExecutionInput): Promise<ExecutionOutput>;
}


