/** PlanPage — Shows active plan with live step progress, chat, approval flow. */

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import {
  Button,
  Card,
  Title2,
  Title3,
  Body1,
  Body2,
  Caption1,
  Badge,
  Spinner,
  Textarea,
  ProgressBar,
  Divider,
  Switch,
  makeStyles,
  tokens,
  mergeClasses,
} from "@fluentui/react-components";
import {
  Checkmark24Regular,
  Dismiss24Regular,
  Send24Regular,
  ArrowLeft24Regular,
  CheckmarkCircle24Filled,
  DismissCircle24Filled,
  ArrowCircleRight24Filled,
  Clock24Regular,
  ChevronDown24Regular,
  ChevronUp24Regular,
  ArrowSync24Regular,
  History24Regular,
  DismissCircle24Regular,
  FastForward24Filled,
} from "@fluentui/react-icons";
import { useNavigate, useParams } from "react-router-dom";
import type { Plan, PlanStep, AgentMessage } from "../models";
import { PlanStatus, StepStatus, WSMessageType } from "../models";
import {
  getPlan,
  getPlans,
  approvePlan,
  approveStep,
  cancelPlan,
  sendSubtaskResponse,
  sendClarification,
  sendUserMessage,
  getAgentMessages,
} from "../api/apiService";
import { WebSocketService } from "../services/WebSocketService";
import FormattedContent from "../components/FormattedContent";

const useStyles = makeStyles({
  container: {
    display: "flex",
    flexDirection: "column",
    height: "100vh",
    backgroundColor: tokens.colorNeutralBackground2,
  },
  header: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    padding: "16px 24px",
    borderBottom: `1px solid ${tokens.colorNeutralStroke1}`,
    backgroundColor: tokens.colorNeutralBackground1,
  },
  headerInfo: {
    flexGrow: 1,
  },
  content: {
    display: "flex",
    flexGrow: 1,
    overflow: "hidden",
  },

  /* ── Sidebar ── */
  sidebar: {
    width: "420px",
    minWidth: "380px",
    borderRight: `1px solid ${tokens.colorNeutralStroke1}`,
    overflowY: "auto",
    padding: "16px",
    display: "flex",
    flexDirection: "column",
    gap: "4px",
    backgroundColor: tokens.colorNeutralBackground1,
  },
  sidebarHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "8px",
  },
  progressSection: {
    marginBottom: "12px",
    display: "flex",
    flexDirection: "column",
    gap: "6px",
  },
  progressLabel: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },

  /* ── Step cards ── */
  stepCard: {
    cursor: "pointer",
    transitionProperty: "box-shadow, border-color",
    transitionDuration: "0.15s",
    transitionTimingFunction: "ease",
    ":hover": {
      boxShadow: tokens.shadow4,
    },
  },
  stepDone: {
    borderLeft: `4px solid ${tokens.colorPaletteGreenBorder1}`,
  },
  stepRunning: {
    borderLeft: `4px solid ${tokens.colorBrandBackground}`,
    boxShadow: tokens.shadow4,
  },
  stepPending: {
    borderLeft: `4px solid ${tokens.colorNeutralStroke1}`,
    opacity: 0.7,
  },
  stepFailed: {
    borderLeft: `4px solid ${tokens.colorPaletteRedBorder1}`,
  },
  stepSkipped: {
    borderLeft: `4px solid ${tokens.colorNeutralStroke2}`,
    opacity: 0.5,
  },
  stepHeaderRow: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    width: "100%",
  },
  stepNumber: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    width: "28px",
    height: "28px",
    borderRadius: "50%",
    fontWeight: "bold",
    fontSize: tokens.fontSizeBase200,
    flexShrink: 0,
  },
  stepNumPending: {
    backgroundColor: tokens.colorNeutralBackground4,
    color: tokens.colorNeutralForeground3,
  },
  stepNumRunning: {
    backgroundColor: tokens.colorBrandBackground,
    color: tokens.colorNeutralForegroundOnBrand,
  },
  stepNumDone: {
    backgroundColor: tokens.colorPaletteGreenBackground3,
    color: tokens.colorNeutralForegroundOnBrand,
  },
  stepNumFailed: {
    backgroundColor: tokens.colorPaletteRedBackground3,
    color: tokens.colorNeutralForegroundOnBrand,
  },
  stepInfo: {
    flexGrow: 1,
    minWidth: 0,
  },
  stepAgent: {
    fontWeight: 600,
    fontSize: tokens.fontSizeBase300,
  },
  stepTask: {
    fontSize: tokens.fontSizeBase200,
    color: tokens.colorNeutralForeground3,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  stepMeta: {
    display: "flex",
    alignItems: "center",
    gap: "6px",
    flexShrink: 0,
  },
  stepDuration: {
    fontSize: tokens.fontSizeBase100,
    color: tokens.colorNeutralForeground3,
    display: "flex",
    alignItems: "center",
    gap: "2px",
  },
  expandToggle: {
    flexShrink: 0,
    minWidth: "24px",
  },

  /* ── Expanded output ── */
  stepOutput: {
    padding: "8px 12px",
    marginTop: "4px",
    backgroundColor: tokens.colorNeutralBackground3,
    borderRadius: "4px",
    fontSize: tokens.fontSizeBase200,
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
    maxHeight: "300px",
    overflowY: "auto",
    lineHeight: "1.5",
  },
  stepError: {
    padding: "8px 12px",
    marginTop: "4px",
    backgroundColor: tokens.colorPaletteRedBackground1,
    borderRadius: "4px",
    fontSize: tokens.fontSizeBase200,
    color: tokens.colorPaletteRedForeground1,
  },
  runningIndicator: {
    display: "flex",
    alignItems: "center",
    gap: "6px",
    padding: "4px 0",
  },
  simulatedBanner: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    padding: "8px 16px",
    backgroundColor: tokens.colorPaletteYellowBackground1,
    borderRadius: "4px",
    marginBottom: "8px",
    fontSize: tokens.fontSizeBase200,
    color: tokens.colorPaletteYellowForeground2,
  },

  /* ── Chat area ── */
  chatArea: {
    flexGrow: 1,
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
  },
  messages: {
    flexGrow: 1,
    overflowY: "auto",
    padding: "16px 24px",
    display: "flex",
    flexDirection: "column",
    gap: "12px",
  },
  inputBar: {
    display: "flex",
    gap: "8px",
    padding: "12px 24px",
    borderTop: `1px solid ${tokens.colorNeutralStroke1}`,
    alignItems: "flex-end",
  },
  inputField: {
    flexGrow: 1,
  },
  agentMsg: {
    padding: "12px",
    borderRadius: "8px",
    backgroundColor: tokens.colorNeutralBackground3,
    maxWidth: "80%",
    alignSelf: "flex-start",
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
  },
  userMsg: {
    padding: "12px",
    borderRadius: "8px",
    backgroundColor: tokens.colorBrandBackground2,
    maxWidth: "80%",
    alignSelf: "flex-end",
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
  },
  systemMsg: {
    padding: "8px 12px",
    borderRadius: "8px",
    backgroundColor: tokens.colorNeutralBackground4,
    alignSelf: "center",
    textAlign: "center" as const,
    fontSize: tokens.fontSizeBase200,
  },
  approvalBar: {
    display: "flex",
    gap: "8px",
    padding: "12px 24px",
    borderTop: `1px solid ${tokens.colorNeutralStroke1}`,
    justifyContent: "center",
    backgroundColor: tokens.colorNeutralBackground4,
  },
  clarificationBanner: {
    display: "flex",
    flexDirection: "column",
    gap: "8px",
    padding: "16px 24px",
    borderTop: `2px solid ${tokens.colorBrandStroke1}`,
    backgroundColor: tokens.colorBrandBackground2,
  },
  clarificationQuestion: {
    fontSize: tokens.fontSizeBase300,
    fontWeight: 600,
    color: tokens.colorNeutralForeground1,
  },
  clarificationLabel: {
    fontSize: tokens.fontSizeBase200,
    color: tokens.colorNeutralForeground3,
    fontWeight: 600,
    textTransform: "uppercase" as const,
    letterSpacing: "0.5px",
  },
  processingIndicator: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    padding: "12px 16px",
    borderRadius: "8px",
    backgroundColor: tokens.colorBrandBackground2,
    alignSelf: "flex-start",
    maxWidth: "80%",
    animation: "pulse 1.5s ease-in-out infinite",
  },
});

const USER_ID = "default-user";

/* ── Helpers ─────────────────────────────────────────────────────── */

function stepStatusStyle(status: StepStatus, styles: ReturnType<typeof useStyles>) {
  switch (status) {
    case StepStatus.COMPLETED:
      return styles.stepDone;
    case StepStatus.IN_PROGRESS:
      return styles.stepRunning;
    case StepStatus.FAILED:
      return styles.stepFailed;
    case StepStatus.SKIPPED:
      return styles.stepSkipped;
    default:
      return styles.stepPending;
  }
}

function stepNumStyle(status: StepStatus, styles: ReturnType<typeof useStyles>) {
  switch (status) {
    case StepStatus.COMPLETED:
      return styles.stepNumDone;
    case StepStatus.IN_PROGRESS:
      return styles.stepNumRunning;
    case StepStatus.FAILED:
      return styles.stepNumFailed;
    default:
      return styles.stepNumPending;
  }
}

function stepStatusIcon(status: StepStatus) {
  switch (status) {
    case StepStatus.COMPLETED:
      return <CheckmarkCircle24Filled primaryFill={tokens.colorPaletteGreenForeground1} />;
    case StepStatus.IN_PROGRESS:
      return <Spinner size="tiny" />;
    case StepStatus.FAILED:
      return <DismissCircle24Filled primaryFill={tokens.colorPaletteRedForeground1} />;
    case StepStatus.SKIPPED:
      return <ArrowCircleRight24Filled primaryFill={tokens.colorNeutralForeground3} />;
    default:
      return <Clock24Regular />;
  }
}

function planStatusBadge(status: PlanStatus) {
  const map: Record<PlanStatus, "informative" | "important" | "success" | "danger" | "warning"> = {
    [PlanStatus.CREATED]: "informative",
    [PlanStatus.PLANNING]: "informative",
    [PlanStatus.CLARIFYING]: "warning",
    [PlanStatus.AWAITING_APPROVAL]: "warning",
    [PlanStatus.APPROVED]: "success",
    [PlanStatus.REJECTED]: "danger",
    [PlanStatus.EXECUTING]: "important",
    [PlanStatus.COMPLETED]: "success",
    [PlanStatus.FAILED]: "danger",
    [PlanStatus.CANCELLED]: "danger",
  };
  return <Badge color={map[status] ?? "informative"} size="large">{status.replace(/_/g, " ")}</Badge>;
}

/** A single tool call with live status. */
interface ToolCallInfo {
  name: string;
  status: "calling" | "completed" | "error";
  detail?: string;
}

/** A sub-task generated for an agent before execution. */
interface SubTaskInfo {
  id: string;
  label: string;
  status: "pending" | "in_progress" | "completed" | "failed";
  promptTokens?: number;
  completionTokens?: number;
  totalTokens?: number;
}

/** Info about a sub-task awaiting user input before the next one runs. */
interface SubtaskInputRequest {
  subtaskId: string;
  subtaskLabel: string;
  subtaskIndex: number;
  totalSubtasks: number;
  nextSubtask: string;
  resultPreview: string;
  isLastSubtask: boolean;
}

/** Per-step status data received via STEP_STATUS WebSocket events. */
interface StepLiveInfo {
  status: string;
  message: string;
  duration?: string;
  output?: string;
  error?: string;
  toolCalls?: ToolCallInfo[];
  subtasks?: SubTaskInfo[];
  awaitingApproval?: boolean;
  awaitingSubtaskInput?: SubtaskInputRequest;
  promptTokens?: number;
  completionTokens?: number;
  totalTokens?: number;
  llmCalls?: number;
}

/* ── Component ───────────────────────────────────────────────────── */

export default function PlanPage() {
  const styles = useStyles();
  const navigate = useNavigate();
  const { planId } = useParams<{ planId?: string }>();

  const [plan, setPlan] = useState<Plan | null>(null);
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [approving, setApproving] = useState(false);
  const [approvalError, setApprovalError] = useState<string | null>(null);
  const [waitingClarification, setWaitingClarification] = useState(false);
  const [chatInput, setChatInput] = useState("");
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set());
  const [stepLiveInfo, setStepLiveInfo] = useState<Map<number, StepLiveInfo>>(new Map());
  const [subtaskAnswerText, setSubtaskAnswerText] = useState<Map<number, string>>(new Map());
  const [cancelling, setCancelling] = useState(false);
  const [autoApproveSteps, setAutoApproveSteps] = useState<Set<number>>(new Set());
  const autoApproveRef = useRef<Set<number>>(new Set());
  const messagesEnd = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocketService | null>(null);

  // Keep ref in sync with state so WS handler reads latest value
  useEffect(() => {
    autoApproveRef.current = autoApproveSteps;
  }, [autoApproveSteps]);

  // Toggle auto-approve for a step's sub-tasks
  const toggleAutoApprove = useCallback((stepNum: number) => {
    setAutoApproveSteps((prev) => {
      const next = new Set(prev);
      if (next.has(stepNum)) {
        next.delete(stepNum);
      } else {
        next.add(stepNum);
      }
      return next;
    });
  }, []);

  // ── Retroactive auto-approve effect ──
  // When auto-approve is toggled ON for a step that is already awaiting
  // approval or subtask input, immediately fire the approval so the user
  // doesn't have to wait for a future WS message.
  useEffect(() => {
    if (!plan || autoApproveSteps.size === 0) return;

    for (const stepNum of autoApproveSteps) {
      const info = stepLiveInfo.get(stepNum);
      if (!info) continue;

      // Retroactively approve the step if it's awaiting step-level approval
      if (info.awaitingApproval) {
        console.log(`[auto-approve] Retroactively approving step ${stepNum}`);
        approveStep(plan.plan_id, USER_ID, stepNum, true, "")
          .then(() => {
            // Clear the awaiting flag
            setStepLiveInfo((prev) => {
              const next = new Map(prev);
              const existing = next.get(stepNum);
              if (existing) {
                next.set(stepNum, { ...existing, awaitingApproval: false });
              }
              return next;
            });
            setMessages((prev) => [
              ...prev,
              {
                id: crypto.randomUUID(),
                plan_id: plan.plan_id,
                step_id: "",
                agent: "system",
                content: `Auto-approved Step ${stepNum} — execution will begin.`,
                timestamp: new Date().toISOString(),
              },
            ]);
          })
          .catch((err) => console.error("Retroactive auto-approve step failed:", err));
        // Only fire once per step — the flag will be cleared by .then()
        continue;
      }

      // Retroactively continue the subtask if it's awaiting subtask input
      if (info.awaitingSubtaskInput) {
        const subtaskId = info.awaitingSubtaskInput.subtaskId;
        const label = info.awaitingSubtaskInput.subtaskLabel;
        const idx = info.awaitingSubtaskInput.subtaskIndex + 1;
        const total = info.awaitingSubtaskInput.totalSubtasks;
        console.log(`[auto-approve] Retroactively continuing subtask ${subtaskId} for step ${stepNum}`);
        sendSubtaskResponse(plan.plan_id, USER_ID, stepNum, subtaskId, "continue", "")
          .then(() => {
            // Clear the awaiting flag
            setStepLiveInfo((prev) => {
              const next = new Map(prev);
              const existing = next.get(stepNum);
              if (existing) {
                next.set(stepNum, { ...existing, awaitingSubtaskInput: undefined });
              }
              return next;
            });
            setMessages((prev) => [
              ...prev,
              {
                id: crypto.randomUUID(),
                plan_id: plan.plan_id,
                step_id: "",
                agent: "system",
                content: `Auto-approved sub-task ${idx}/${total}: "${label}" — continuing.`,
                timestamp: new Date().toISOString(),
              },
            ]);
          })
          .catch((err) => console.error("Retroactive auto-approve subtask failed:", err));
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoApproveSteps, stepLiveInfo, plan?.plan_id]);

  // Toggle a step card expansion
  const toggleStep = useCallback((stepNum: number) => {
    setExpandedSteps((prev) => {
      const next = new Set(prev);
      if (next.has(stepNum)) {
        next.delete(stepNum);
      } else {
        next.add(stepNum);
      }
      return next;
    });
  }, []);

  // Auto-expand running step
  useEffect(() => {
    if (plan?.m_plan?.steps) {
      const running = plan.m_plan.steps.find((s) => s.status === StepStatus.IN_PROGRESS);
      if (running) {
        setExpandedSteps((prev) => {
          const next = new Set(prev);
          next.add(running.step_number);
          return next;
        });
      }
    }
  }, [plan?.m_plan?.steps]);

  // Progress computation
  const progress = useMemo(() => {
    if (!plan?.m_plan?.steps?.length) return { completed: 0, total: 0, pct: 0 };
    const total = plan.m_plan.steps.length;
    const completed = plan.m_plan.steps.filter(
      (s) => s.status === StepStatus.COMPLETED || s.status === StepStatus.SKIPPED
    ).length;
    return { completed, total, pct: total > 0 ? completed / total : 0 };
  }, [plan?.m_plan?.steps]);

  // Detect simulated mode — any step output starts with [SIMULATED]
  const isSimulated = useMemo(() => {
    if (!plan?.m_plan?.steps) return false;
    return plan.m_plan.steps.some(
      (s) => s.output?.startsWith("[SIMULATED]") === true
    ) || Array.from(stepLiveInfo.values()).some(
      (info) => info.output?.startsWith("[SIMULATED]") === true
    );
  }, [plan?.m_plan?.steps, stepLiveInfo]);

  // Scroll chat to bottom on new messages
  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Polling fallback — periodically refresh plan + messages while active
  useEffect(() => {
    if (
      !plan ||
      plan.overall_status === PlanStatus.COMPLETED ||
      plan.overall_status === PlanStatus.FAILED ||
      plan.overall_status === PlanStatus.CANCELLED ||
      plan.overall_status === PlanStatus.REJECTED ||
      plan.overall_status === PlanStatus.CREATED
    ) {
      return;
    }
    const interval = setInterval(async () => {
      try {
        const pid = plan.plan_id || plan.id;
        const refreshed = await getPlan(pid, USER_ID);
        setPlan(refreshed);
        hydrateSubtasks(refreshed);
        const msgs = await getAgentMessages(pid);
        if (msgs.length > messages.length) {
          setMessages(msgs);
        }
      } catch {
        // ignore — WS may deliver updates instead
      }
    }, 3000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [plan?.overall_status, plan?.plan_id]);

  // Hydrate stepLiveInfo from persisted subtask data on a loaded plan.
  // Preserves token usage from both the persisted plan data and any
  // existing WebSocket-derived state so that polling doesn't wipe tokens.
  const hydrateSubtasks = useCallback((p: Plan) => {
    if (!p.m_plan?.steps) return;
    setStepLiveInfo((prev) => {
      const next = new Map(prev);
      for (const s of p.m_plan!.steps) {
        if (s.subtasks && s.subtasks.length > 0) {
          const existing = next.get(s.step_number);
          // Merge subtask token data: prefer existing WS state, fall back to persisted
          const existingSubtaskMap = new Map(
            (existing?.subtasks ?? []).map((st) => [st.id, st])
          );
          next.set(s.step_number, {
            status: existing?.status ?? s.status ?? "",
            message: existing?.message ?? "",
            duration: existing?.duration ?? "",
            output: existing?.output ?? s.output ?? "",
            error: existing?.error ?? s.error ?? "",
            subtasks: s.subtasks.map((st) => {
              const ws = existingSubtaskMap.get(st.id);
              return {
                id: st.id,
                label: st.label,
                status: st.status as "pending" | "in_progress" | "completed" | "failed",
                promptTokens: ws?.promptTokens || st.prompt_tokens || 0,
                completionTokens: ws?.completionTokens || st.completion_tokens || 0,
                totalTokens: ws?.totalTokens || st.total_tokens || 0,
              };
            }),
            toolCalls: existing?.toolCalls,
            awaitingApproval: existing?.awaitingApproval,
            awaitingSubtaskInput: existing?.awaitingSubtaskInput,
            // Preserve step-level tokens: prefer WS state, fall back to persisted
            promptTokens: existing?.promptTokens || s.prompt_tokens || 0,
            completionTokens: existing?.completionTokens || s.completion_tokens || 0,
            totalTokens: existing?.totalTokens || s.total_tokens || 0,
            llmCalls: existing?.llmCalls || s.llm_calls || 0,
          });
        }
      }
      return next;
    });
  }, []);

  // Load plan
  useEffect(() => {
    const fetchPlan = async () => {
      try {
        if (planId) {
          const p = await getPlan(planId, USER_ID);
          setPlan(p);
          hydrateSubtasks(p);
          const msgs = await getAgentMessages(planId);
          setMessages(msgs);
        } else {
          // Get most recent plan
          const plans = await getPlans(USER_ID);
          if (plans.length > 0) {
            const latest = plans[plans.length - 1];
            setPlan(latest);
            hydrateSubtasks(latest);
            const msgs = await getAgentMessages(latest.id);
            setMessages(msgs);
          }
        }
      } catch (err) {
        console.error("Failed to load plan:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchPlan();
  }, [planId, hydrateSubtasks]);

  // WebSocket connection
  useEffect(() => {
    const ws = new WebSocketService(USER_ID);
    wsRef.current = ws;

    ws.subscribe((type: WSMessageType, data: Record<string, unknown>) => {
      switch (type) {
        case WSMessageType.PLAN_UPDATE: {
          if (data.plan_id || data.plan) {
            const planData = (data.plan ?? data) as Plan;
            setPlan(planData);
            if (planData.overall_status === PlanStatus.CLARIFYING) {
              setWaitingClarification(true);
            }
            if (
              planData.overall_status === PlanStatus.PLANNING ||
              planData.overall_status === PlanStatus.AWAITING_APPROVAL
            ) {
              setWaitingClarification(false);
            }
          }
          break;
        }
        case WSMessageType.STEP_STATUS: {
          // Granular step-level update
          const stepNum = data.step_number as number;
          if (stepNum != null) {
            setStepLiveInfo((prev) => {
              const next = new Map(prev);
              const existing = next.get(stepNum);
              // Preserve subtasks, toolCalls, and awaitingSubtaskInput when updating step status
              next.set(stepNum, {
                status: data.status as string,
                message: (data.message as string) ?? "",
                duration: (data.duration as string) ?? "",
                output: (data.output as string) ?? "",
                error: (data.error as string) ?? "",
                subtasks: existing?.subtasks,
                toolCalls: existing?.toolCalls,
                awaitingApproval: existing?.awaitingApproval,
                awaitingSubtaskInput: existing?.awaitingSubtaskInput,
                promptTokens: (data.prompt_tokens as number) || existing?.promptTokens || 0,
                completionTokens: (data.completion_tokens as number) || existing?.completionTokens || 0,
                totalTokens: (data.total_tokens as number) || existing?.totalTokens || 0,
                llmCalls: (data.llm_calls as number) || existing?.llmCalls || 0,
              });
              return next;
            });
            // Auto-expand the step that just started
            if (data.status === StepStatus.IN_PROGRESS) {
              setExpandedSteps((prev) => {
                const next = new Set(prev);
                next.add(stepNum);
                return next;
              });
            }
            // Add chat message with output when step completes
            if (data.status === StepStatus.COMPLETED && data.output) {
              const stepAgent = plan?.m_plan?.steps.find(s => s.step_number === stepNum)?.agent || "Agent";
              const stepTask = plan?.m_plan?.steps.find(s => s.step_number === stepNum)?.task || "";
              const outputStr = data.output as string;
              // Show full output in chat (FormattedContent will handle rendering)
              const chatContent = `**Step ${stepNum} completed:** ${stepTask}\n\n${outputStr}`;
              setMessages((prev) => [
                ...prev,
                {
                  id: crypto.randomUUID(),
                  plan_id: (data.plan_id as string) ?? plan?.plan_id ?? "",
                  step_id: "",
                  agent: stepAgent,
                  content: chatContent,
                  timestamp: new Date().toISOString(),
                },
              ]);
            }
          }
          break;
        }
        case WSMessageType.TOOL_PROGRESS: {
          // Live tool-call progress per step
          const tpStep = data.step_number as number;
          const toolName = (data.tool_name as string) ?? "";
          const toolStatus = (data.status as string) ?? "calling";
          const toolDetail = (data.detail as string) ?? "";
          if (tpStep != null && toolName) {
            setStepLiveInfo((prev) => {
              const next = new Map(prev);
              const existing = next.get(tpStep) || { status: "in_progress", message: "" };
              const toolCalls = [...(existing.toolCalls || [])];
              // Find existing entry for this tool
              const idx = toolCalls.findIndex((t) => t.name === toolName && t.status === "calling");
              if (toolStatus === "completed" && idx >= 0) {
                toolCalls[idx] = { name: toolName, status: "completed", detail: toolDetail };
              } else if (toolStatus === "calling") {
                toolCalls.push({ name: toolName, status: "calling", detail: toolDetail });
              } else {
                toolCalls.push({ name: toolName, status: toolStatus as ToolCallInfo["status"], detail: toolDetail });
              }
              next.set(tpStep, {
                ...existing,
                toolCalls,
                message: `${data.agent}: ${toolDetail}`,
              });
              return next;
            });
            // Auto-expand step with active tool calls
            setExpandedSteps((prev) => {
              const next = new Set(prev);
              next.add(tpStep);
              return next;
            });
          }
          break;
        }
        case WSMessageType.AGENT_SUBTASKS: {
          // Receive the list of sub-tasks for an agent step
          const stStep = data.step_number as number;
          const rawSubtasks = data.subtasks as Array<{ id: string; label: string }>;
          if (stStep != null && rawSubtasks) {
            setStepLiveInfo((prev) => {
              const next = new Map(prev);
              const existing = next.get(stStep) || { status: "in_progress", message: "" };
              const subtasks: SubTaskInfo[] = rawSubtasks.map((st) => ({
                id: st.id,
                label: st.label,
                status: "pending" as const,
              }));
              next.set(stStep, { ...existing, subtasks });
              return next;
            });
            // Auto-expand
            setExpandedSteps((prev) => {
              const next = new Set(prev);
              next.add(stStep);
              return next;
            });
          }
          break;
        }
        case WSMessageType.SUBTASK_UPDATE: {
          // Update a single sub-task's status
          const suStep = data.step_number as number;
          const subtaskId = data.subtask_id as string;
          const subtaskStatus = data.status as SubTaskInfo["status"];
          if (suStep != null && subtaskId) {
            setStepLiveInfo((prev) => {
              const next = new Map(prev);
              const existing = next.get(suStep);
              if (!existing?.subtasks) return prev;
              const subtasks = existing.subtasks.map((st) =>
                st.id === subtaskId
                  ? {
                      ...st,
                      status: subtaskStatus,
                      promptTokens: (data.prompt_tokens as number) || 0,
                      completionTokens: (data.completion_tokens as number) || 0,
                      totalTokens: (data.total_tokens as number) || 0,
                    }
                  : st
              );
              // Update step-level running totals from the backend
              const stepPrompt = (data.step_prompt_tokens as number) || existing.promptTokens || 0;
              const stepCompletion = (data.step_completion_tokens as number) || existing.completionTokens || 0;
              const stepTotal = (data.step_total_tokens as number) || existing.totalTokens || 0;
              next.set(suStep, {
                ...existing,
                subtasks,
                promptTokens: stepPrompt,
                completionTokens: stepCompletion,
                totalTokens: stepTotal,
              });
              return next;
            });
          }
          break;
        }
        case WSMessageType.SUBTASK_INPUT_REQUEST: {
          // A sub-task completed — system is waiting for user input before proceeding
          const siStep = data.step_number as number;
          if (siStep != null) {
            // Check if auto-approve is enabled for this step
            const isAutoApproved = autoApproveRef.current.has(siStep);

            if (isAutoApproved) {
              // Auto-approve: immediately send "continue" without showing the input gate
              const siPlanId = (data.plan_id as string) ?? "";
              const siSubtaskId = data.subtask_id as string;
              sendSubtaskResponse(
                siPlanId,
                USER_ID,
                siStep,
                siSubtaskId,
                "continue",
                "",
              ).catch((err) => {
                console.error("Auto-approve subtask failed:", err);
              });

              // Still show the chat message but mark it as auto-approved
              const stIdx = (data.subtask_index as number) + 1;
              const stTotal = data.total_subtasks as number;
              const isLast = (data.is_last_subtask as boolean) || false;
              const resultPreview = (data.result_preview as string) || "";

              let chatMsg = `**Sub-task ${stIdx}/${stTotal} auto-approved:** "${data.subtask_label}"`;
              if (resultPreview) {
                chatMsg += `\n\n**Result:**\n${resultPreview}`;
                if (resultPreview.length >= 300) {
                  chatMsg += "\n\n*...output truncated. See step details for full output.*";
                }
              }
              if (isLast) {
                chatMsg += "\n\n*All sub-tasks auto-approved and completed.*";
              }

              setMessages((prev) => [
                ...prev,
                {
                  id: crypto.randomUUID(),
                  plan_id: siPlanId,
                  step_id: "",
                  agent: "system",
                  content: chatMsg,
                  timestamp: new Date().toISOString(),
                },
              ]);
              break;
            }

            setStepLiveInfo((prev) => {
              const next = new Map(prev);
              const existing = next.get(siStep) || { status: "in_progress", message: "" };
              next.set(siStep, {
                ...existing,
                awaitingSubtaskInput: {
                  subtaskId: data.subtask_id as string,
                  subtaskLabel: data.subtask_label as string,
                  subtaskIndex: data.subtask_index as number,
                  totalSubtasks: data.total_subtasks as number,
                  nextSubtask: (data.next_subtask as string) || "",
                  resultPreview: data.result_preview as string,
                  isLastSubtask: (data.is_last_subtask as boolean) || false,
                },
              });
              return next;
            });
            // Auto-expand
            setExpandedSteps((prev) => {
              const next = new Set(prev);
              next.add(siStep);
              return next;
            });
            // System message — conversational prompt with result preview
            const stIdx = (data.subtask_index as number) + 1;
            const stTotal = data.total_subtasks as number;
            const isLast = (data.is_last_subtask as boolean) || false;
            const resultPreview = (data.result_preview as string) || "";
            const stepAgent = plan?.m_plan?.steps.find(s => s.step_number === siStep)?.agent || "Agent";
            
            // Build chat message with result preview
            let chatMsg = isLast
              ? `**Sub-task ${stIdx}/${stTotal} completed:** "${data.subtask_label}"\n\nAll sub-tasks done — provide any final input or confirm to finish.`
              : `**Sub-task ${stIdx}/${stTotal} completed:** "${data.subtask_label}"`;
            
            // Append result preview if available
            if (resultPreview) {
              chatMsg += `\n\n**Result:**\n${resultPreview}`;
              if (resultPreview.length >= 300) {
                chatMsg += "\n\n*...output truncated. See step details for full output.*";
              }
            }
            
            if (!isLast && data.next_subtask) {
              chatMsg += `\n\n**Next:** ${data.next_subtask}`;
            }
            
            setMessages((prev) => [
              ...prev,
              {
                id: crypto.randomUUID(),
                plan_id: (data.plan_id as string) ?? "",
                step_id: "",
                agent: stepAgent,
                content: chatMsg,
                timestamp: new Date().toISOString(),
              },
            ]);
          }
          break;
        }
        case WSMessageType.STEP_APPROVAL_REQUEST: {
          // Agent sub-tasks generated — waiting for user to approve/reject this step
          const saStep = data.step_number as number;
          if (saStep != null) {
            const isStepAutoApproved = autoApproveRef.current.has(saStep);

            if (isStepAutoApproved) {
              // Auto-approve step immediately and log to chat
              const saPlanId = (data.plan_id as string) ?? plan?.plan_id ?? "";
              approveStep(saPlanId, USER_ID, saStep, true, "").catch((err) => {
                console.error("Auto-approve step failed:", err);
              });
              setMessages((prev) => [
                ...prev,
                {
                  id: crypto.randomUUID(),
                  plan_id: saPlanId,
                  step_id: "",
                  agent: "system",
                  content: `Auto-approved agent "${data.agent}" (Step ${saStep}) — execution will begin.`,
                  timestamp: new Date().toISOString(),
                },
              ]);
              break;
            }

            setStepLiveInfo((prev) => {
              const next = new Map(prev);
              const existing = next.get(saStep) || { status: "in_progress", message: "" };
              next.set(saStep, { ...existing, awaitingApproval: true });
              return next;
            });
            // Auto-expand the step awaiting approval
            setExpandedSteps((prev) => {
              const next = new Set(prev);
              next.add(saStep);
              return next;
            });
            // Add system message
            setMessages((prev) => [
              ...prev,
              {
                id: crypto.randomUUID(),
                plan_id: (data.plan_id as string) ?? "",
                step_id: "",
                agent: "system",
                content: `Review sub-tasks for agent "${data.agent}" (Step ${saStep}) and approve or reject in the sidebar.`,
                timestamp: new Date().toISOString(),
              },
            ]);
          }
          break;
        }
        case WSMessageType.AGENT_RESPONSE: {
          if (data.message) {
            setMessages((prev) => [...prev, data.message as AgentMessage]);
          } else if (data.content) {
            setMessages((prev) => [
              ...prev,
              {
                id: crypto.randomUUID(),
                plan_id: (data.plan_id as string) ?? "",
                step_id: (data.step_id as string) ?? "",
                agent: (data.agent as string) ?? "agent",
                content: data.content as string,
                timestamp: new Date().toISOString(),
              },
            ]);
          }
          break;
        }
        case WSMessageType.HUMAN_CLARIFICATION_REQUEST: {
          setWaitingClarification(true);
          if (data.message) {
            setMessages((prev) => [...prev, data.message as AgentMessage]);
          } else if (data.question) {
            setMessages((prev) => [
              ...prev,
              {
                id: crypto.randomUUID(),
                plan_id: (data.plan_id as string) ?? "",
                step_id: "",
                agent: "system",
                content: data.question as string,
                timestamp: new Date().toISOString(),
              },
            ]);
          }
          break;
        }
        case WSMessageType.PLAN_APPROVAL: {
          if (data.plan) {
            setPlan(data.plan as Plan);
          } else {
            setPlan((prev) =>
              prev ? { ...prev, overall_status: PlanStatus.AWAITING_APPROVAL } : prev
            );
          }
          break;
        }
        case WSMessageType.PLAN_COMPLETE: {
          setPlan((prev) =>
            prev ? { ...prev, overall_status: PlanStatus.COMPLETED } : prev
          );
          setMessages((prev) => [
            ...prev,
            {
              id: crypto.randomUUID(),
              plan_id: (data.plan_id as string) ?? "",
              step_id: "",
              agent: "system",
              content: (data.summary as string) || "Plan execution completed.",
              timestamp: new Date().toISOString(),
            },
          ]);
          break;
        }
        case WSMessageType.ERROR: {
          setMessages((prev) => [
            ...prev,
            {
              id: crypto.randomUUID(),
              plan_id: plan?.id ?? "",
              step_id: "",
              agent: "system",
              content: (data.error as string) ?? (data.message as string) ?? "An error occurred",
              timestamp: new Date().toISOString(),
            },
          ]);
          break;
        }
      }
    });

    ws.connect();
    return () => ws.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleApproval = useCallback(
    async (approved: boolean) => {
      if (!plan) return;
      setApproving(true);
      setApprovalError(null);
      try {
        await approvePlan(plan.plan_id, USER_ID, approved, approved ? "" : "User rejected plan");
        setPlan((prev) =>
          prev
            ? { ...prev, overall_status: approved ? PlanStatus.APPROVED : PlanStatus.CANCELLED }
            : prev
        );
        // Add a system message so user sees feedback in chat
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            plan_id: plan.plan_id,
            step_id: "",
            agent: "system",
            content: approved
              ? "Plan approved! Execution will begin shortly."
              : "Plan rejected. You can submit a new request.",
            timestamp: new Date().toISOString(),
          },
        ]);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to submit approval";
        console.error("Approval failed:", message);
        setApprovalError(message);
        // Also show the error in chat so user sees something
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            plan_id: plan.plan_id,
            step_id: "",
            agent: "system",
            content: `Approval failed: ${message}`,
            timestamp: new Date().toISOString(),
          },
        ]);
      } finally {
        setApproving(false);
      }
    },
    [plan]
  );

  // Cancel a running plan
  const handleCancel = useCallback(async () => {
    if (!plan) return;
    if (!window.confirm("Are you sure you want to cancel this execution?")) return;
    setCancelling(true);
    try {
      await cancelPlan(plan.plan_id, USER_ID, "Cancelled by user");
      setPlan((prev) =>
        prev ? { ...prev, overall_status: PlanStatus.CANCELLED } : prev
      );
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          plan_id: plan.plan_id,
          step_id: "",
          agent: "system",
          content: "Execution cancelled by user.",
          timestamp: new Date().toISOString(),
        },
      ]);
    } catch (err) {
      console.error("Cancel failed:", err);
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          plan_id: plan.plan_id,
          step_id: "",
          agent: "system",
          content: `Cancel failed: ${err instanceof Error ? err.message : "Unknown error"}`,
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
      setCancelling(false);
    }
  }, [plan]);

  // Send a general user message during execution
  const handleSendMessage = useCallback(async () => {
    if (!plan || !chatInput.trim()) return;
    const text = chatInput.trim();
    // Optimistically add the message to the local chat
    setMessages((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        plan_id: plan.plan_id,
        step_id: "user-message",
        agent: "user",
        content: text,
        timestamp: new Date().toISOString(),
      } as AgentMessage,
    ]);
    setChatInput("");

    // If there's a pending clarification, also resolve it
    if (waitingClarification) {
      await sendClarification(plan.plan_id, USER_ID, text);
      setWaitingClarification(false);
    } else {
      await sendUserMessage(plan.plan_id, USER_ID, text);
    }
  }, [plan, chatInput, waitingClarification]);

  // Handle per-step (per-agent) approval after sub-task review
  const handleStepApproval = useCallback(
    async (stepNumber: number, approved: boolean, autoApproveAll: boolean = false) => {
      if (!plan) return;
      try {
        await approveStep(
          plan.plan_id,
          USER_ID,
          stepNumber,
          approved,
          autoApproveAll ? "__auto_approve_all__" : (approved ? "" : "User rejected step")
        );
        // Clear the awaiting flag immediately
        setStepLiveInfo((prev) => {
          const next = new Map(prev);
          const existing = next.get(stepNumber);
          if (existing) {
            next.set(stepNumber, { ...existing, awaitingApproval: false });
          }
          return next;
        });
        // Add a system message
        const stepAgent = plan.m_plan?.steps.find((s) => s.step_number === stepNumber)?.agent ?? `Step ${stepNumber}`;
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            plan_id: plan.plan_id,
            step_id: "",
            agent: "user",
            content: autoApproveAll
              ? `Auto-approved all sub-tasks for ${stepAgent} (Step ${stepNumber}) — executing without pauses.`
              : approved
                ? `Approved ${stepAgent} (Step ${stepNumber}) — execution will begin.`
                : `Rejected ${stepAgent} (Step ${stepNumber}) — step will be skipped.`,
            timestamp: new Date().toISOString(),
          },
        ]);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to submit step approval";
        console.error("Step approval failed:", message);
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            plan_id: plan.plan_id,
            step_id: "",
            agent: "system",
            content: `Step approval failed: ${message}`,
            timestamp: new Date().toISOString(),
          },
        ]);
      }
    },
    [plan]
  );

  // Handle per-subtask response (continue / skip / answer / auto_approve_all)
  const handleSubtaskResponse = useCallback(
    async (stepNumber: number, subtaskId: string, action: "continue" | "skip" | "answer" | "auto_approve_all") => {
      if (!plan) return;
      const answerText = (subtaskAnswerText.get(stepNumber) || "").trim();
      // For auto_approve_all, send as-is (don't override with "answer")
      const effectiveAction = action === "auto_approve_all"
        ? "auto_approve_all"
        : (answerText ? "answer" : action);
      try {
        await sendSubtaskResponse(
          plan.plan_id,
          USER_ID,
          stepNumber,
          subtaskId,
          effectiveAction,
          answerText,
        );
        // Clear the awaiting flag
        setStepLiveInfo((prev) => {
          const next = new Map(prev);
          const existing = next.get(stepNumber);
          if (existing) {
            next.set(stepNumber, { ...existing, awaitingSubtaskInput: undefined });
          }
          return next;
        });
        // Clear the answer text
        setSubtaskAnswerText((prev) => {
          const next = new Map(prev);
          next.delete(stepNumber);
          return next;
        });
        // User message in chat
        const label = effectiveAction === "answer" ? `Provided input: "${answerText}"` :
          effectiveAction === "auto_approve_all" ? "Auto-approving all remaining sub-tasks" :
          action === "skip" ? "Skipping remaining sub-tasks" : "Continue to next sub-task";
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            plan_id: plan.plan_id,
            step_id: "",
            agent: "user",
            content: label,
            timestamp: new Date().toISOString(),
          },
        ]);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to send sub-task response";
        console.error("Sub-task response failed:", message);
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            plan_id: plan.plan_id,
            step_id: "",
            agent: "system",
            content: `Sub-task response failed: ${message}`,
            timestamp: new Date().toISOString(),
          },
        ]);
      }
    },
    [plan, subtaskAnswerText]
  );

  // Derive the latest unanswered clarification question from messages.
  // Works during both CLARIFYING (pre-plan) and EXECUTING (in-plan agent questions).
  const latestClarificationQuestion = useMemo(() => {
    if (!waitingClarification && plan?.overall_status !== PlanStatus.CLARIFYING) return null;
    // System messages are questions, user messages are answers.
    // Find the last system message that doesn't have a user answer after it.
    const systemMsgs = messages.filter((m) => m.agent === "system");
    const userMsgs = messages.filter((m) => m.agent === "user");
    if (systemMsgs.length > userMsgs.length) {
      return {
        question: systemMsgs[systemMsgs.length - 1].content,
        questionNumber: systemMsgs.length,
      };
    }
    return null;
  }, [messages, plan?.overall_status, waitingClarification]);

  /* ── Render helpers ────────────────────────────────────────────── */

  function renderStepCard(step: PlanStep, idx: number) {
    const isExpanded = expandedSteps.has(step.step_number);
    const liveInfo = stepLiveInfo.get(step.step_number);
    // Prefer live info output, fall back to step.output from plan state
    const rawOutput = liveInfo?.output || step.output || "";
    // Strip [SIMULATED] prefix for display
    const output = rawOutput.startsWith("[SIMULATED] ") ? rawOutput.slice(12) : rawOutput;
    const error = liveInfo?.error || step.error || "";
    const duration = liveInfo?.duration || "";
    const isRunning = step.status === StepStatus.IN_PROGRESS;
    const isDone = step.status === StepStatus.COMPLETED;
    const isFailed = step.status === StepStatus.FAILED;

    return (
      <Card
        key={step.id || idx}
        className={mergeClasses(styles.stepCard, stepStatusStyle(step.status, styles))}
        size="small"
        onClick={() => toggleStep(step.step_number)}
      >
        <div style={{ padding: "8px 12px" }}>
          <div className={styles.stepHeaderRow}>
            {/* Step number circle */}
            <div className={mergeClasses(styles.stepNumber, stepNumStyle(step.status, styles))}>
              {isDone ? "\u2713" : isFailed ? "!" : idx + 1}
            </div>

            {/* Agent name + task */}
            <div className={styles.stepInfo}>
              <div className={styles.stepAgent}>{step.agent}</div>
              <div className={styles.stepTask} title={step.task}>
                {step.task}
              </div>
            </div>

            {/* Status icon + duration + tokens + expand toggle */}
            <div className={styles.stepMeta}>
              {(liveInfo?.totalTokens ?? 0) > 0 && (
                <span
                  className={styles.stepDuration}
                  title={`Prompt: ${(liveInfo?.promptTokens ?? 0).toLocaleString()} · Completion: ${(liveInfo?.completionTokens ?? 0).toLocaleString()}`}
                  style={{ color: tokens.colorNeutralForeground3 }}
                >
                  🪙 {(liveInfo?.totalTokens ?? 0).toLocaleString()}
                </span>
              )}
              {duration && (
                <span className={styles.stepDuration}>
                  <Clock24Regular style={{ width: 14, height: 14 }} />
                  {duration}
                </span>
              )}
              {stepStatusIcon(step.status)}
              <Button
                appearance="subtle"
                size="small"
                icon={isExpanded ? <ChevronUp24Regular /> : <ChevronDown24Regular />}
                className={styles.expandToggle}
                onClick={(e) => {
                  e.stopPropagation();
                  toggleStep(step.step_number);
                }}
              />
            </div>
          </div>

          {/* Auto-approve toggle — shown for pending/running steps */}
          {(step.status === StepStatus.PENDING || isRunning) && (
            <div
              style={{ paddingLeft: "36px", marginTop: "4px" }}
              onClick={(e) => e.stopPropagation()}
            >
              <Switch
                checked={autoApproveSteps.has(step.step_number)}
                onChange={() => toggleAutoApprove(step.step_number)}
                label="Auto-approve all sub-tasks"
                style={{ fontSize: tokens.fontSizeBase200 }}
              />
            </div>
          )}

          {/* Running indicator */}
          {isRunning && !liveInfo?.subtasks?.length && !liveInfo?.awaitingApproval && (
            <div className={styles.runningIndicator}>
              <Spinner size="extra-tiny" />
              <Caption1 style={{ color: tokens.colorBrandForeground1 }}>
                {liveInfo?.message || `${step.agent} is working...`}
              </Caption1>
            </div>
          )}

          {/* Awaiting approval indicator */}
          {isRunning && liveInfo?.awaitingApproval && (
            <div className={styles.runningIndicator}>
              <Clock24Regular style={{ width: 16, height: 16, color: tokens.colorPaletteMarigoldForeground1 }} />
              <Caption1 style={{ color: tokens.colorPaletteMarigoldForeground1, fontWeight: 600 }}>
                Awaiting your approval — review sub-tasks below
              </Caption1>
            </div>
          )}

          {/* ── Sub-tasks — shown when expanded and sub-tasks exist ── */}
          {isExpanded && liveInfo?.subtasks && liveInfo.subtasks.length > 0 && (
            <div style={{ marginTop: "8px", paddingLeft: "36px", display: "flex", flexDirection: "column", gap: "2px" }}>
              {liveInfo.subtasks.map((st) => {
                const stColor =
                  st.status === "completed"
                    ? tokens.colorPaletteGreenForeground1
                    : st.status === "failed"
                      ? tokens.colorPaletteRedForeground1
                      : st.status === "in_progress"
                        ? tokens.colorBrandForeground1
                        : tokens.colorNeutralForeground3;
                return (
                  <div
                    key={st.id}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                      padding: "4px 0",
                      fontSize: tokens.fontSizeBase200,
                      color: stColor,
                    }}
                  >
                    {st.status === "pending" && (
                      <div style={{
                        width: 16, height: 16, borderRadius: "50%",
                        border: `2px solid ${tokens.colorNeutralStroke2}`,
                        flexShrink: 0,
                      }} />
                    )}
                    {st.status === "in_progress" && <Spinner size="extra-tiny" />}
                    {st.status === "completed" && (
                      <CheckmarkCircle24Filled
                        primaryFill={tokens.colorPaletteGreenForeground1}
                        style={{ width: 16, height: 16, flexShrink: 0 }}
                      />
                    )}
                    {st.status === "failed" && (
                      <DismissCircle24Filled
                        primaryFill={tokens.colorPaletteRedForeground1}
                        style={{ width: 16, height: 16, flexShrink: 0 }}
                      />
                    )}
                    <span style={{
                      fontWeight: st.status === "in_progress" ? 600 : 400,
                      textDecoration: st.status === "completed" ? "none" : "none",
                      flex: 1,
                    }}>
                      {st.label}
                    </span>
                    {st.status === "completed" && (st.totalTokens ?? 0) > 0 && (
                      <span
                        style={{
                          fontSize: tokens.fontSizeBase100,
                          color: tokens.colorNeutralForeground4,
                          whiteSpace: "nowrap",
                        }}
                        title={`Prompt: ${(st.promptTokens ?? 0).toLocaleString()} · Completion: ${(st.completionTokens ?? 0).toLocaleString()}`}
                      >
                        🪙 {(st.totalTokens ?? 0).toLocaleString()}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* ── Per-agent approval buttons — shown when awaiting approval ── */}
          {isExpanded && liveInfo?.awaitingApproval && (
            <div
              style={{
                marginTop: "10px",
                display: "flex",
                flexDirection: "column",
                gap: "10px",
                padding: "14px 16px 14px 36px",
                backgroundColor: tokens.colorNeutralBackground4,
                borderRadius: tokens.borderRadiusMedium,
                border: `1px solid ${tokens.colorBrandStroke1}`,
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <Body2 style={{ fontWeight: 600, color: tokens.colorBrandForeground1 }}>
                Review sub-tasks above and choose how to proceed:
              </Body2>
              <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end", flexWrap: "wrap" }}>
                <Button
                  appearance="primary"
                  size="small"
                  icon={<FastForward24Filled />}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleStepApproval(step.step_number, true, true);
                  }}
                  title="Approve and run all sub-tasks without pausing for input"
                >
                  Auto-approve All
                </Button>
                <Button
                  appearance="primary"
                  size="small"
                  icon={<ArrowCircleRight24Filled />}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleStepApproval(step.step_number, true);
                  }}
                  title="Approve and pause after each sub-task for review"
                >
                  Continue
                </Button>
                <Button
                  appearance="secondary"
                  size="small"
                  icon={<Dismiss24Regular />}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleStepApproval(step.step_number, false);
                  }}
                  title="Skip this agent step entirely"
                >
                  Skip
                </Button>
              </div>
            </div>
          )}

          {/* ── Sub-task input request — one-at-a-time question gate ── */}
          {isExpanded && liveInfo?.awaitingSubtaskInput && (
            <div
              style={{
                marginTop: "10px",
                display: "flex",
                flexDirection: "column",
                gap: "10px",
                padding: "14px 16px 14px 36px",
                backgroundColor: tokens.colorNeutralBackground4,
                borderRadius: tokens.borderRadiusMedium,
                border: `1px solid ${tokens.colorBrandStroke1}`,
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <Body2 style={{ fontWeight: 600, color: tokens.colorBrandForeground1 }}>
                Sub-task {liveInfo.awaitingSubtaskInput.subtaskIndex + 1}/{liveInfo.awaitingSubtaskInput.totalSubtasks} completed: "{liveInfo.awaitingSubtaskInput.subtaskLabel}"
              </Body2>
              {!liveInfo.awaitingSubtaskInput.isLastSubtask && liveInfo.awaitingSubtaskInput.nextSubtask && (
                <Caption1 style={{ color: tokens.colorNeutralForeground3 }}>
                  Next: {liveInfo.awaitingSubtaskInput.nextSubtask}
                </Caption1>
              )}
              {liveInfo.awaitingSubtaskInput.isLastSubtask && (
                <Caption1 style={{ color: tokens.colorNeutralForeground3 }}>
                  This is the last sub-task. Provide any final input or confirm to finish.
                </Caption1>
              )}
              <Textarea
                placeholder={liveInfo.awaitingSubtaskInput.isLastSubtask
                  ? "Provide any final comments or corrections (optional)..."
                  : "Answer the question or provide instructions for the next sub-task (optional)..."
                }
                value={subtaskAnswerText.get(step.step_number) || ""}
                onChange={(_e, data) => {
                  setSubtaskAnswerText((prev) => {
                    const next = new Map(prev);
                    next.set(step.step_number, data.value);
                    return next;
                  });
                }}
                style={{ minHeight: "56px", fontSize: tokens.fontSizeBase200 }}
                resize="vertical"
              />
              <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end", flexWrap: "wrap" }}>
                {(subtaskAnswerText.get(step.step_number) || "").trim() && (
                  <Button
                    appearance="primary"
                    size="small"
                    icon={<Send24Regular />}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleSubtaskResponse(
                        step.step_number,
                        liveInfo!.awaitingSubtaskInput!.subtaskId,
                        "answer"
                      );
                    }}
                  >
                    Send & Continue
                  </Button>
                )}
                {!liveInfo.awaitingSubtaskInput.isLastSubtask && (
                  <Button
                    appearance="primary"
                    size="small"
                    icon={<FastForward24Filled />}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleSubtaskResponse(
                        step.step_number,
                        liveInfo!.awaitingSubtaskInput!.subtaskId,
                        "auto_approve_all"
                      );
                    }}
                    title="Run all remaining sub-tasks without stopping"
                  >
                    Auto-approve All
                  </Button>
                )}
                <Button
                  appearance="primary"
                  size="small"
                  icon={<ArrowCircleRight24Filled />}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleSubtaskResponse(
                      step.step_number,
                      liveInfo!.awaitingSubtaskInput!.subtaskId,
                      "continue"
                    );
                  }}
                >
                  {liveInfo.awaitingSubtaskInput.isLastSubtask ? "Finish" : "Continue"}
                </Button>
                {!liveInfo.awaitingSubtaskInput.isLastSubtask && (
                  <Button
                    appearance="secondary"
                    size="small"
                    icon={<Dismiss24Regular />}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleSubtaskResponse(
                        step.step_number,
                        liveInfo!.awaitingSubtaskInput!.subtaskId,
                        "skip"
                      );
                    }}
                  >
                    Skip
                  </Button>
                )}
              </div>
            </div>
          )}

          {/* ── Live tool calls — shown under active sub-task when running ── */}
          {isExpanded && isRunning && liveInfo?.toolCalls && liveInfo.toolCalls.length > 0 && (
            <div style={{
              marginTop: "4px",
              paddingLeft: liveInfo?.subtasks?.length ? "52px" : "36px",
              borderLeft: liveInfo?.subtasks?.length ? `2px solid ${tokens.colorNeutralStroke2}` : "none",
              marginLeft: liveInfo?.subtasks?.length ? "43px" : "0",
            }}>
              <Caption1 style={{ color: tokens.colorNeutralForeground3, marginBottom: "2px", display: "block" }}>
                Tool calls:
              </Caption1>
              {liveInfo.toolCalls.slice(-6).map((tc, i) => (
                <div
                  key={`${tc.name}-${i}`}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                    padding: "2px 0",
                    fontSize: tokens.fontSizeBase100,
                    color:
                      tc.status === "completed"
                        ? tokens.colorPaletteGreenForeground1
                        : tc.status === "error"
                          ? tokens.colorPaletteRedForeground1
                          : tokens.colorBrandForeground1,
                  }}
                >
                  {tc.status === "calling" && <Spinner size="extra-tiny" />}
                  {tc.status === "completed" && (
                    <CheckmarkCircle24Filled
                      primaryFill={tokens.colorPaletteGreenForeground1}
                      style={{ width: 14, height: 14 }}
                    />
                  )}
                  {tc.status === "error" && (
                    <DismissCircle24Filled
                      primaryFill={tokens.colorPaletteRedForeground1}
                      style={{ width: 14, height: 14 }}
                    />
                  )}
                  <span style={{ fontFamily: "monospace", fontSize: tokens.fontSizeBase100 }}>
                    {tc.name}
                  </span>
                </div>
              ))}
              {liveInfo.toolCalls.length > 6 && (
                <Caption1 style={{ color: tokens.colorNeutralForeground3, fontStyle: "italic" }}>
                  ...and {liveInfo.toolCalls.length - 6} earlier calls
                </Caption1>
              )}
            </div>
          )}

          {/* Completed sub-tasks summary — shown when step is done */}
          {isExpanded && isDone && liveInfo?.subtasks && liveInfo.subtasks.length > 0 && (
            <div style={{ marginTop: "4px", paddingLeft: "36px", display: "flex", flexDirection: "column", gap: "1px" }}>
              {liveInfo.subtasks.map((st) => (
                <div
                  key={st.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    padding: "2px 0",
                    fontSize: tokens.fontSizeBase200,
                    color: tokens.colorPaletteGreenForeground1,
                  }}
                >
                  <CheckmarkCircle24Filled
                    primaryFill={tokens.colorPaletteGreenForeground1}
                    style={{ width: 16, height: 16, flexShrink: 0 }}
                  />
                  <span>{st.label}</span>
                </div>
              ))}
              {liveInfo.toolCalls && liveInfo.toolCalls.length > 0 && (
                <Caption1 style={{ color: tokens.colorNeutralForeground3, marginTop: "2px", paddingLeft: "24px" }}>
                  {liveInfo.toolCalls.length} tool call{liveInfo.toolCalls.length > 1 ? "s" : ""} executed
                </Caption1>
              )}
            </div>
          )}

          {/* Completed step with tool calls but no sub-tasks */}
          {isExpanded && isDone && !liveInfo?.subtasks?.length && liveInfo?.toolCalls && liveInfo.toolCalls.length > 0 && (
            <div style={{ marginTop: "4px", paddingLeft: "36px", marginBottom: "4px" }}>
              <Caption1 style={{ color: tokens.colorNeutralForeground3 }}>
                Tools used: {liveInfo.toolCalls.map((tc) => tc.name).join(", ")}
              </Caption1>
            </div>
          )}

          {/* Expanded output section */}
          {isExpanded && (isDone || isFailed || output || error) && (
            <>
              <Divider style={{ margin: "8px 0" }} />
              {error && <div className={styles.stepError}>{error}</div>}
              {output && <div className={styles.stepOutput}><FormattedContent content={output} compact /></div>}
              {!output && !error && isDone && (
                <Caption1 style={{ color: tokens.colorNeutralForeground3 }}>
                  Completed — no output captured
                </Caption1>
              )}
            </>
          )}
        </div>
      </Card>
    );
  }

  /* ── Loading / empty states ────────────────────────────────────── */

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", padding: 64 }}>
        <Spinner label="Loading plan..." />
      </div>
    );
  }

  if (!plan) {
    return (
      <div style={{ padding: 32 }}>
        <Body1>No active plan found.</Body1>
        <Button icon={<ArrowLeft24Regular />} onClick={() => navigate("/")}>
          Back to Home
        </Button>
      </div>
    );
  }

  /* ── Main render ───────────────────────────────────────────────── */

  const isExecuting = plan.overall_status === PlanStatus.EXECUTING;
  const isFinished =
    plan.overall_status === PlanStatus.COMPLETED || plan.overall_status === PlanStatus.FAILED;
  const isCancellable =
    plan.overall_status === PlanStatus.PLANNING ||
    plan.overall_status === PlanStatus.AWAITING_APPROVAL ||
    plan.overall_status === PlanStatus.EXECUTING;

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.header}>
        <Button
          appearance="subtle"
          icon={<ArrowLeft24Regular />}
          onClick={() => navigate("/")}
        />
        <div className={styles.headerInfo} style={{ flex: 1 }}>
          <Title2>Migration Plan</Title2>
          <Body2>
            {plan.initial_goal ? plan.initial_goal.substring(0, 120) : "Migration Plan"}
          </Body2>
        </div>
        {planStatusBadge(plan.overall_status)}
        {isCancellable && (
          <Button
            icon={<DismissCircle24Regular />}
            appearance="subtle"
            onClick={handleCancel}
            disabled={cancelling}
            title="Cancel Execution"
            style={{ color: tokens.colorPaletteRedForeground1 }}
          >
            {cancelling ? "Cancelling..." : "Cancel"}
          </Button>
        )}
        <Button
          icon={<History24Regular />}
          appearance="subtle"
          onClick={() => navigate("/history")}
          title="Execution History"
        />
      </div>

      <div className={styles.content}>
        {/* ── Sidebar — Step Timeline ── */}
        <div className={styles.sidebar}>
          <div className={styles.sidebarHeader}>
            <Title3>Execution Steps</Title3>
            {plan.m_plan?.steps && (
              <Caption1>
                {progress.completed}/{progress.total} done
              </Caption1>
            )}
          </div>

          {/* Progress bar — visible during and after execution */}
          {(isExecuting || isFinished || plan.overall_status === PlanStatus.CANCELLED) && plan.m_plan?.steps && (
            <div className={styles.progressSection}>
              <ProgressBar
                value={progress.pct}
                thickness="large"
                color={
                  plan.overall_status === PlanStatus.FAILED || plan.overall_status === PlanStatus.CANCELLED
                    ? "error"
                    : "brand"
                }
              />
              <div className={styles.progressLabel}>
                <Caption1>
                  {isExecuting && (
                    <>
                      <ArrowSync24Regular style={{ width: 14, height: 14, marginRight: 4 }} />
                      Executing...
                    </>
                  )}
                  {plan.overall_status === PlanStatus.COMPLETED && "All steps completed"}
                  {plan.overall_status === PlanStatus.FAILED && "Execution finished with errors"}
                  {plan.overall_status === PlanStatus.CANCELLED && "Execution cancelled"}
                </Caption1>
                <Caption1>{Math.round(progress.pct * 100)}%</Caption1>
              </div>
            </div>
          )}

          {/* Simulated mode banner */}
          {isSimulated && (
            <div className={styles.simulatedBanner}>
              <Badge color="warning" size="small">SIMULATED</Badge>
              <span>Running in local dev mode — no Azure AI Foundry client configured. Outputs are simulated.</span>
            </div>
          )}

          <Divider />

          {/* Step cards */}
          <div style={{ display: "flex", flexDirection: "column", gap: "6px", marginTop: "8px" }}>
            {plan.m_plan?.steps.map((step, idx) => renderStepCard(step, idx))}
          </div>

          {(!plan.m_plan || plan.m_plan.steps.length === 0) && (
            <Body2 style={{ padding: "16px 0", textAlign: "center" as const }}>
              Plan steps will appear here once created.
            </Body2>
          )}
        </div>

        {/* ── Chat Area ── */}
        <div className={styles.chatArea}>
          <div className={styles.messages}>
            {messages.length === 0 && (
              <div className={styles.systemMsg}>Waiting for agent activity...</div>
            )}
            {messages.map((msg) => {
              const isUser = msg.agent === "user";
              const isSystem = msg.agent === "system";
              return (
                <div
                  key={msg.id}
                  className={
                    isSystem ? styles.systemMsg : isUser ? styles.userMsg : styles.agentMsg
                  }
                >
                  {!isUser && !isSystem && (
                    <Body2>
                      <strong>{msg.agent}</strong>
                    </Body2>
                  )}
                  <FormattedContent content={msg.content} />
                </div>
              );
            })}
            {/* Processing indicator when subtasks are executing */}
            {(() => {
              // Find currently executing step with in-progress subtasks
              const activeStep = Array.from(stepLiveInfo.entries()).find(
                ([, info]) => info.status === "in_progress" && info.subtasks?.some(st => st.status === "in_progress")
              );
              if (!activeStep) return null;
              const [stepNum, info] = activeStep;
              const activeSubtask = info.subtasks?.find(st => st.status === "in_progress");
              const stepAgent = plan?.m_plan?.steps.find(s => s.step_number === stepNum)?.agent || "Agent";
              return (
                <div className={styles.processingIndicator}>
                  <Spinner size="small" />
                  <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                    <Body2 style={{ fontWeight: 600, color: tokens.colorBrandForeground1 }}>
                      {stepAgent} is working...
                    </Body2>
                    {activeSubtask && (
                      <Caption1 style={{ color: tokens.colorNeutralForeground2 }}>
                        {activeSubtask.label}
                      </Caption1>
                    )}
                  </div>
                </div>
              );
            })()}
            <div ref={messagesEnd} />
          </div>

          {/* Approval Bar */}
          {plan.overall_status === PlanStatus.AWAITING_APPROVAL && (
            <div className={styles.approvalBar}>
              <Body1 style={{ marginRight: 12 }}>
                Review the plan steps on the left. Approve to start execution?
              </Body1>
              {approvalError && (
                <Body2 style={{ color: tokens.colorPaletteRedForeground1, marginRight: 8 }}>
                  {approvalError}
                </Body2>
              )}
              <Button
                appearance="primary"
                icon={approving ? <Spinner size="tiny" /> : <Checkmark24Regular />}
                onClick={() => handleApproval(true)}
                disabled={approving}
              >
                {approving ? "Approving\u2026" : "Approve"}
              </Button>
              <Button
                appearance="secondary"
                icon={approving ? <Spinner size="tiny" /> : <Dismiss24Regular />}
                onClick={() => handleApproval(false)}
                disabled={approving}
              >
                {approving ? "Rejecting\u2026" : "Reject"}
              </Button>
            </div>
          )}

          {/* Clarification Banner — highlighted question when an agent needs input */}
          {(waitingClarification || plan.overall_status === PlanStatus.CLARIFYING) &&
            latestClarificationQuestion && (
            <div className={styles.clarificationBanner}>
              <div className={styles.clarificationLabel}>
                {plan.overall_status === PlanStatus.EXECUTING
                  ? `Agent needs your input — Question ${latestClarificationQuestion.questionNumber}`
                  : `Clarification needed — Question ${latestClarificationQuestion.questionNumber}`}
              </div>
              <div className={styles.clarificationQuestion}>
                {latestClarificationQuestion.question}
              </div>
            </div>
          )}

          {/* Persistent Chat Input — always visible during active states */}
          {plan.overall_status !== PlanStatus.COMPLETED &&
            plan.overall_status !== PlanStatus.FAILED &&
            plan.overall_status !== PlanStatus.CANCELLED &&
            plan.overall_status !== PlanStatus.REJECTED &&
            plan.overall_status !== PlanStatus.CREATED &&
            plan.overall_status !== PlanStatus.AWAITING_APPROVAL && (
            <div className={styles.inputBar}>
              <Textarea
                className={styles.inputField}
                placeholder={
                  waitingClarification
                    ? "Type your answer to the question above..."
                    : "Send a message to the agents..."
                }
                value={chatInput}
                onChange={(_e, data) => setChatInput(data.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
                resize="vertical"
              />
              <Button
                appearance="primary"
                icon={<Send24Regular />}
                onClick={handleSendMessage}
                disabled={!chatInput.trim()}
              >
                Send
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
