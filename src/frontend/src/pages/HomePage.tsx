/** HomePage — Team selection and task submission. */

import { useState, useEffect, useCallback } from "react";
import {
  Card,
  CardHeader,
  CardPreview,
  Button,
  Input,
  Title1,
  Title3,
  Body1,
  Body2,
  Spinner,
  Badge,
  Dropdown,
  Option,
  Label,
  makeStyles,
  tokens,
} from "@fluentui/react-components";
import {
  DatabaseArrowRight24Regular,
  PeopleTeam24Regular,
  Send24Regular,
  Play24Regular,
  BrainCircuit24Regular,
  History24Regular,
} from "@fluentui/react-icons";
import { useNavigate } from "react-router-dom";
import type { TeamConfiguration, StartingTask } from "../models";
import {
  getTeamConfigs,
  selectTeam,
  processRequest,
  getLlmProvider,
  setLlmProvider,
  type LlmProviderInfo,
} from "../api/apiService";

const useStyles = makeStyles({
  container: {
    display: "flex",
    flexDirection: "column",
    gap: "24px",
    padding: "32px",
    maxWidth: "1200px",
    margin: "0 auto",
  },
  header: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    marginBottom: "8px",
  },
  teamsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))",
    gap: "16px",
  },
  teamCard: {
    cursor: "pointer",
    transition: "box-shadow 0.2s",
    ":hover": {
      boxShadow: tokens.shadow8,
    },
  },
  selectedCard: {
    border: `2px solid ${tokens.colorBrandBackground}`,
  },
  taskInput: {
    display: "flex",
    gap: "8px",
    marginTop: "16px",
  },
  taskInputField: {
    flexGrow: 1,
  },
  startingTasks: {
    display: "flex",
    flexWrap: "wrap",
    gap: "8px",
    marginTop: "12px",
  },
  agentBadges: {
    display: "flex",
    flexWrap: "wrap",
    gap: "4px",
    marginTop: "8px",
  },
  providerRow: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    padding: "12px 16px",
    backgroundColor: tokens.colorNeutralBackground2,
    borderRadius: tokens.borderRadiusMedium,
  },
  providerDropdown: {
    minWidth: "180px",
  },
});

const USER_ID = "default-user"; // TODO: Replace with auth

export default function HomePage() {
  const styles = useStyles();
  const navigate = useNavigate();

  const [teams, setTeams] = useState<TeamConfiguration[]>([]);
  const [selectedTeam, setSelectedTeam] = useState<TeamConfiguration | null>(null);
  const [taskInput, setTaskInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [providerInfo, setProviderInfo] = useState<LlmProviderInfo | null>(null);

  useEffect(() => {
    getTeamConfigs(USER_ID)
      .then(setTeams)
      .catch(console.error)
      .finally(() => setLoading(false));
    getLlmProvider()
      .then(setProviderInfo)
      .catch(console.error);
  }, []);

  const handleProviderChange = useCallback(
    async (_e: unknown, data: { optionValue?: string }) => {
      const provider = data.optionValue;
      if (!provider) return;
      try {
        const result = await setLlmProvider(provider);
        setProviderInfo((prev) =>
          prev ? { ...prev, active: result.active } : prev
        );
      } catch (err) {
        console.error("Failed to switch LLM provider:", err);
      }
    },
    []
  );

  const handleSelectTeam = useCallback(
    async (team: TeamConfiguration) => {
      setSelectedTeam(team);
      await selectTeam(USER_ID, team.id);
    },
    []
  );

  const handleSubmit = useCallback(async () => {
    if (!selectedTeam || !taskInput.trim()) return;
    setSubmitting(true);
    try {
      await processRequest(USER_ID, taskInput.trim(), selectedTeam.id);
      navigate("/plan");
    } catch (err) {
      console.error("Submit failed:", err);
    } finally {
      setSubmitting(false);
    }
  }, [selectedTeam, taskInput, navigate]);

  const handleStartingTask = useCallback(
    async (task: StartingTask) => {
      if (!selectedTeam) return;
      setSubmitting(true);
      try {
        await processRequest(USER_ID, task.prompt, selectedTeam.id);
        navigate("/plan");
      } catch (err) {
        console.error("Starting task failed:", err);
      } finally {
        setSubmitting(false);
      }
    },
    [selectedTeam, navigate]
  );

  if (loading) {
    return (
      <div className={styles.container}>
        <Spinner label="Loading teams..." />
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <DatabaseArrowRight24Regular />
        <Title1 style={{ flex: 1 }}>DA-MACAÉ</Title1>
        <Button
          icon={<History24Regular />}
          appearance="subtle"
          onClick={() => navigate("/history")}
        >
          Execution History
        </Button>
      </div>
      <Body1>
        Multi-Agent Custom Automation Engine for Data Migration. Select a team
        and describe your migration task.
      </Body1>

      {/* LLM Provider Toggle */}
      {providerInfo && providerInfo.available.length > 1 && (
        <div className={styles.providerRow}>
          <BrainCircuit24Regular />
          <Label weight="semibold">LLM Provider</Label>
          <Dropdown
            className={styles.providerDropdown}
            value={providerInfo.active === "claude" ? "Claude (Anthropic)" : providerInfo.active === "openai" ? "Azure OpenAI" : "Simulated"}
            selectedOptions={[providerInfo.active]}
            onOptionSelect={handleProviderChange}
          >
            {providerInfo.available.map((p) => (
              <Option key={p} value={p}>
                {p === "claude" ? "Claude (Anthropic)" : p === "openai" ? "Azure OpenAI" : "Simulated"}
              </Option>
            ))}
          </Dropdown>
          <Badge
            appearance="filled"
            color={providerInfo.active === "claude" ? "important" : providerInfo.active === "openai" ? "brand" : "informative"}
          >
            {providerInfo.active}
          </Badge>
        </div>
      )}

      {/* Team Selection */}
      <div>
        <div className={styles.header}>
          <PeopleTeam24Regular />
          <Title3>Select a Team</Title3>
        </div>
        <div className={styles.teamsGrid}>
          {teams.map((team) => (
            <Card
              key={team.id}
              className={`${styles.teamCard} ${
                selectedTeam?.id === team.id ? styles.selectedCard : ""
              }`}
              onClick={() => handleSelectTeam(team)}
            >
              <CardHeader
                header={<Title3>{team.name}</Title3>}
                description={<Body2>{team.description}</Body2>}
              />
              <CardPreview>
                <div className={styles.agentBadges}>
                  {team.agents.map((agent) => (
                    <Badge key={agent.id} appearance="outline" size="small">
                      {agent.name}
                    </Badge>
                  ))}
                </div>
              </CardPreview>
            </Card>
          ))}
          {teams.length === 0 && (
            <Body1>No teams configured. Add team JSON files to data/agent_teams/.</Body1>
          )}
        </div>
      </div>

      {/* Task Input */}
      {selectedTeam && (
        <div>
          <Title3>Describe Your Migration Task</Title3>
          <div className={styles.taskInput}>
            <Input
              className={styles.taskInputField}
              placeholder="e.g., Migrate AdventureWorks database from SQL Server to PostgreSQL on Azure..."
              value={taskInput}
              onChange={(_e, data) => setTaskInput(data.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
              disabled={submitting}
            />
            <Button
              appearance="primary"
              icon={<Send24Regular />}
              onClick={handleSubmit}
              disabled={submitting || !taskInput.trim()}
            >
              {submitting ? "Submitting..." : "Submit"}
            </Button>
          </div>

          {/* Starting Tasks */}
          {selectedTeam.starting_tasks.length > 0 && (
            <div>
              <Body2 style={{ marginTop: "16px" }}>Or choose a pre-built task:</Body2>
              <div className={styles.startingTasks}>
                {selectedTeam.starting_tasks.map((task, i) => (
                  <Button
                    key={i}
                    appearance="outline"
                    icon={<Play24Regular />}
                    onClick={() => handleStartingTask(task)}
                    disabled={submitting}
                  >
                    {task.title}
                  </Button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
