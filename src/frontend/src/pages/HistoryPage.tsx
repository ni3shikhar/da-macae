/** HistoryPage — Shows past migration team execution history. */

import { useState, useEffect, useMemo } from "react";
import {
  Card,
  Button,
  Title3,
  Body1,
  Body2,
  Caption1,
  Badge,
  Spinner,
  Input,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import {
  ArrowLeft24Regular,
  History24Regular,
  Search24Regular,
  CheckmarkCircle24Filled,
  DismissCircle24Filled,
  ArrowCircleRight24Filled,
  Clock24Regular,
  ArrowSync24Regular,
  Play24Regular,
} from "@fluentui/react-icons";
import { useNavigate } from "react-router-dom";
import type { Plan } from "../models";
import { PlanStatus } from "../models";
import { getPlans } from "../api/apiService";

const USER_ID = "default-user";

/* ── Styles ──────────────────────────────────────────────────────── */

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
    backgroundColor: tokens.colorNeutralBackground1,
    borderBottom: `1px solid ${tokens.colorNeutralStroke1}`,
  },
  headerTitle: {
    flex: 1,
    display: "flex",
    alignItems: "center",
    gap: "10px",
  },
  content: {
    flex: 1,
    overflow: "auto",
    padding: "24px",
  },
  toolbar: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    marginBottom: "20px",
    flexWrap: "wrap",
  },
  searchBox: {
    minWidth: "280px",
    flexGrow: 1,
    maxWidth: "500px",
  },
  filterGroup: {
    display: "flex",
    gap: "6px",
    flexWrap: "wrap",
  },
  filterBtn: {
    minWidth: "auto",
  },
  statsRow: {
    display: "flex",
    gap: "16px",
    marginBottom: "20px",
    flexWrap: "wrap",
  },
  statCard: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
    padding: "12px 20px",
    borderRadius: tokens.borderRadiusMedium,
    backgroundColor: tokens.colorNeutralBackground1,
    border: `1px solid ${tokens.colorNeutralStroke1}`,
    minWidth: "140px",
  },
  statNumber: {
    fontSize: tokens.fontSizeHero700,
    fontWeight: 700,
    lineHeight: 1,
  },
  statLabel: {
    fontSize: tokens.fontSizeBase200,
    color: tokens.colorNeutralForeground3,
  },
  planList: {
    display: "flex",
    flexDirection: "column",
    gap: "12px",
  },
  planCard: {
    cursor: "pointer",
    transition: "box-shadow 0.15s, border-color 0.15s",
    padding: "16px 20px",
    ":hover": {
      boxShadow: tokens.shadow8,
    },
  },
  planRow: {
    display: "flex",
    alignItems: "flex-start",
    gap: "16px",
  },
  planIcon: {
    flexShrink: 0,
    marginTop: "2px",
  },
  planBody: {
    flex: 1,
    minWidth: 0,
  },
  planGoal: {
    fontSize: tokens.fontSizeBase400,
    fontWeight: 600,
    color: tokens.colorNeutralForeground1,
    marginBottom: "4px",
    overflow: "hidden",
    textOverflow: "ellipsis",
    display: "-webkit-box",
    WebkitLineClamp: 2,
    WebkitBoxOrient: "vertical" as const,
  },
  planMeta: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    flexWrap: "wrap",
    marginTop: "6px",
  },
  metaItem: {
    display: "flex",
    alignItems: "center",
    gap: "4px",
    fontSize: tokens.fontSizeBase200,
    color: tokens.colorNeutralForeground3,
  },
  planRight: {
    display: "flex",
    flexDirection: "column",
    alignItems: "flex-end",
    gap: "6px",
    flexShrink: 0,
  },
  stepsBar: {
    display: "flex",
    gap: "3px",
    marginTop: "4px",
  },
  stepDot: {
    width: "8px",
    height: "8px",
    borderRadius: "2px",
  },
  empty: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    padding: "64px 24px",
    gap: "12px",
    color: tokens.colorNeutralForeground3,
  },
});

/* ── Helpers ─────────────────────────────────────────────────────── */

type StatusFilter = "all" | "completed" | "failed" | "executing" | "other";

function statusBadge(status: PlanStatus) {
  switch (status) {
    case PlanStatus.COMPLETED:
      return { color: "success" as const, icon: <CheckmarkCircle24Filled />, label: "Completed" };
    case PlanStatus.FAILED:
      return { color: "danger" as const, icon: <DismissCircle24Filled />, label: "Failed" };
    case PlanStatus.EXECUTING:
      return { color: "warning" as const, icon: <ArrowSync24Regular />, label: "Executing" };
    case PlanStatus.APPROVED:
      return { color: "brand" as const, icon: <ArrowCircleRight24Filled />, label: "Approved" };
    case PlanStatus.AWAITING_APPROVAL:
      return { color: "informative" as const, icon: <Clock24Regular />, label: "Awaiting Approval" };
    case PlanStatus.PLANNING:
      return { color: "informative" as const, icon: <ArrowSync24Regular />, label: "Planning" };
    case PlanStatus.CANCELLED:
      return { color: "subtle" as const, icon: <DismissCircle24Filled />, label: "Cancelled" };
    case PlanStatus.REJECTED:
      return { color: "danger" as const, icon: <DismissCircle24Filled />, label: "Rejected" };
    default:
      return { color: "informative" as const, icon: <Clock24Regular />, label: status };
  }
}

function stepDotColor(status: string): string {
  switch (status) {
    case "completed":
      return tokens.colorPaletteGreenBackground3;
    case "failed":
      return tokens.colorPaletteRedBackground3;
    case "in_progress":
      return tokens.colorPaletteYellowBackground3;
    case "skipped":
      return tokens.colorNeutralBackground5;
    default:
      return tokens.colorNeutralStroke1;
  }
}

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function relativeDuration(start: string, end: string): string {
  try {
    const ms = new Date(end).getTime() - new Date(start).getTime();
    if (ms < 0) return "—";
    const sec = Math.floor(ms / 1000);
    if (sec < 60) return `${sec}s`;
    const min = Math.floor(sec / 60);
    const remSec = sec % 60;
    if (min < 60) return `${min}m ${remSec}s`;
    const hr = Math.floor(min / 60);
    const remMin = min % 60;
    return `${hr}h ${remMin}m`;
  } catch {
    return "—";
  }
}

function matchesFilter(plan: Plan, filter: StatusFilter): boolean {
  if (filter === "all") return true;
  if (filter === "completed") return plan.overall_status === PlanStatus.COMPLETED;
  if (filter === "failed") return plan.overall_status === PlanStatus.FAILED;
  if (filter === "executing")
    return [PlanStatus.EXECUTING, PlanStatus.PLANNING, PlanStatus.APPROVED, PlanStatus.AWAITING_APPROVAL].includes(plan.overall_status);
  // "other" = cancelled, rejected, created, clarifying
  return ![PlanStatus.COMPLETED, PlanStatus.FAILED, PlanStatus.EXECUTING, PlanStatus.PLANNING, PlanStatus.APPROVED, PlanStatus.AWAITING_APPROVAL].includes(plan.overall_status);
}

/* ── Component ───────────────────────────────────────────────────── */

export default function HistoryPage() {
  const styles = useStyles();
  const navigate = useNavigate();

  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<StatusFilter>("all");

  useEffect(() => {
    getPlans(USER_ID)
      .then((data) => {
        // Sort by most recent first
        data.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
        setPlans(data);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    return plans.filter((p) => {
      if (!matchesFilter(p, filter)) return false;
      if (search.trim()) {
        const q = search.toLowerCase();
        return (
          p.initial_goal?.toLowerCase().includes(q) ||
          p.plan_id?.toLowerCase().includes(q) ||
          p.team_id?.toLowerCase().includes(q) ||
          p.overall_status?.toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [plans, filter, search]);

  const stats = useMemo(() => {
    const total = plans.length;
    const completed = plans.filter((p) => p.overall_status === PlanStatus.COMPLETED).length;
    const failed = plans.filter((p) => p.overall_status === PlanStatus.FAILED).length;
    const active = plans.filter((p) =>
      [PlanStatus.EXECUTING, PlanStatus.PLANNING, PlanStatus.APPROVED, PlanStatus.AWAITING_APPROVAL].includes(p.overall_status)
    ).length;
    return { total, completed, failed, active };
  }, [plans]);

  if (loading) {
    return (
      <div className={styles.container}>
        <Spinner label="Loading execution history..." style={{ margin: "auto" }} />
      </div>
    );
  }

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.header}>
        <Button
          icon={<ArrowLeft24Regular />}
          appearance="subtle"
          onClick={() => navigate("/")}
        />
        <div className={styles.headerTitle}>
          <History24Regular />
          <Title3>Execution History</Title3>
        </div>
      </div>

      <div className={styles.content}>
        {/* Stats summary */}
        <div className={styles.statsRow}>
          <div className={styles.statCard}>
            <div>
              <div className={styles.statNumber}>{stats.total}</div>
              <div className={styles.statLabel}>Total</div>
            </div>
          </div>
          <div className={styles.statCard}>
            <CheckmarkCircle24Filled style={{ color: tokens.colorPaletteGreenForeground1 }} />
            <div>
              <div className={styles.statNumber} style={{ color: tokens.colorPaletteGreenForeground1 }}>{stats.completed}</div>
              <div className={styles.statLabel}>Completed</div>
            </div>
          </div>
          <div className={styles.statCard}>
            <DismissCircle24Filled style={{ color: tokens.colorPaletteRedForeground1 }} />
            <div>
              <div className={styles.statNumber} style={{ color: tokens.colorPaletteRedForeground1 }}>{stats.failed}</div>
              <div className={styles.statLabel}>Failed</div>
            </div>
          </div>
          <div className={styles.statCard}>
            <ArrowSync24Regular style={{ color: tokens.colorPaletteYellowForeground2 }} />
            <div>
              <div className={styles.statNumber} style={{ color: tokens.colorPaletteYellowForeground2 }}>{stats.active}</div>
              <div className={styles.statLabel}>Active</div>
            </div>
          </div>
        </div>

        {/* Search + Filters */}
        <div className={styles.toolbar}>
          <Input
            className={styles.searchBox}
            placeholder="Search by goal, plan ID, team..."
            contentBefore={<Search24Regular />}
            value={search}
            onChange={(_e, d) => setSearch(d.value)}
          />
          <div className={styles.filterGroup}>
            {(["all", "completed", "failed", "executing", "other"] as StatusFilter[]).map((f) => (
              <Button
                key={f}
                className={styles.filterBtn}
                appearance={filter === f ? "primary" : "subtle"}
                size="small"
                onClick={() => setFilter(f)}
              >
                {f === "all" ? "All" : f === "executing" ? "Active" : f.charAt(0).toUpperCase() + f.slice(1)}
              </Button>
            ))}
          </div>
        </div>

        {/* Plan List */}
        {filtered.length === 0 ? (
          <div className={styles.empty}>
            <History24Regular style={{ fontSize: 48 }} />
            <Title3>{plans.length === 0 ? "No executions yet" : "No matching executions"}</Title3>
            <Body1>
              {plans.length === 0
                ? "Start a migration task from the home page to see execution history here."
                : "Try adjusting your search or filter."}
            </Body1>
            {plans.length === 0 && (
              <Button appearance="primary" icon={<Play24Regular />} onClick={() => navigate("/")}>
                Start New Task
              </Button>
            )}
          </div>
        ) : (
          <div className={styles.planList}>
            {filtered.map((plan) => {
              const badge = statusBadge(plan.overall_status);
              const steps = plan.m_plan?.steps ?? [];
              const completedSteps = steps.filter((s) => s.status === "completed").length;

              return (
                <Card
                  key={plan.plan_id}
                  className={styles.planCard}
                  onClick={() => navigate(`/plan/${plan.plan_id}`)}
                >
                  <div className={styles.planRow}>
                    <div className={styles.planIcon}>{badge.icon}</div>

                    <div className={styles.planBody}>
                      <div className={styles.planGoal}>
                        {plan.initial_goal || "Untitled task"}
                      </div>
                      <div className={styles.planMeta}>
                        <Caption1 className={styles.metaItem}>
                          <Clock24Regular style={{ fontSize: 14 }} />
                          {formatDate(plan.created_at)}
                        </Caption1>
                        {plan.team_id && (
                          <Badge appearance="outline" size="small">
                            {plan.team_id}
                          </Badge>
                        )}
                        {steps.length > 0 && (
                          <Caption1 className={styles.metaItem}>
                            {completedSteps}/{steps.length} steps
                          </Caption1>
                        )}
                        {plan.created_at && plan.updated_at && plan.overall_status === PlanStatus.COMPLETED && (
                          <Caption1 className={styles.metaItem}>
                            Duration: {relativeDuration(plan.created_at, plan.updated_at)}
                          </Caption1>
                        )}
                      </div>

                      {/* Step progress dots */}
                      {steps.length > 0 && (
                        <div className={styles.stepsBar}>
                          {steps.map((s, i) => (
                            <div
                              key={i}
                              className={styles.stepDot}
                              style={{ backgroundColor: stepDotColor(s.status) }}
                              title={`Step ${s.step_number}: ${s.agent} — ${s.status}`}
                            />
                          ))}
                        </div>
                      )}
                    </div>

                    <div className={styles.planRight}>
                      <Badge
                        appearance="filled"
                        color={badge.color}
                        size="medium"
                      >
                        {badge.label}
                      </Badge>
                      {plan.m_plan?.summary && (
                        <Body2
                          style={{
                            maxWidth: 250,
                            textAlign: "right",
                            color: tokens.colorNeutralForeground3,
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {plan.m_plan.summary}
                        </Body2>
                      )}
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
