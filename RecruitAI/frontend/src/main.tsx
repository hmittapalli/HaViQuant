import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  BriefcaseBusiness,
  CalendarDays,
  CheckCircle2,
  ChevronDown,
  Command,
  Database,
  Eye,
  FilePlus2,
  FileSearch,
  Gauge,
  Layers3,
  Menu,
  MessageSquareText,
  Moon,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  Sun,
  UploadCloud,
  UserPlus,
  Users,
} from "lucide-react";
import "./styles.css";
import Workspace from './Workspace';

type Kpi = { label: string; value: number | string; detail: string };
type PriorityAction = { priority: "P0" | "P1" | "P2" | "P3"; title: string; reason: string; owner: string; action: string };
type Interview = { id: string; candidate_id: string; job_id: string; interviewer: string; scheduled_at: string; status: string };
type Overview = {
  demo_mode: boolean;
  greeting: string;
  kpis: Kpi[];
  priority_actions: PriorityAction[];
  funnel: Record<string, number>;
  upcoming_interviews: Interview[];
  ai_recommendations: string[];
};
type Job = {
  id: string;
  title: string;
  company: string;
  location: string;
  work_mode: string;
  employment_type: string;
  owner: string;
  status: string;
  required_skills: string[];
  preferred_skills: string[];
};
type Candidate = {
  id: string;
  name: string;
  headline: string;
  location: string;
  stage: string;
  owner: string;
  skills: string[];
  years_experience: number;
  availability_days: number;
  resume_quality: number;
};
type MatchEvidence = {
  candidate_id: string;
  job_id: string;
  overall: number;
  eligibility: string;
  mandatory: number;
  preferred: number;
  confidence: string;
  evidence: string[];
  gaps: string[];
};
type CopilotResponse = { answer: string; actions: string[]; evidence: string[]; confidence: string };

import { API } from './api-config';

const emptyOverview: Overview = {
  demo_mode: false,
  greeting: "Workspace is ready",
  kpis: [
    { label: "Open Roles", value: 0, detail: "No jobs imported yet" },
    { label: "Active Candidates", value: 0, detail: "No candidates uploaded yet" },
    { label: "Interviews", value: 0, detail: "No interviews scheduled yet" },
    { label: "High Match Candidates", value: 0, detail: "Run AI match after importing data" },
    { label: "Offers", value: 0, detail: "No offers created yet" },
  ],
  priority_actions: [],
  funnel: { New: 0, Screening: 0, Interview: 0, Offer: 0, Hired: 0 },
  upcoming_interviews: [],
  ai_recommendations: ["Import jobs and candidates to generate recommendations."],
};

const roleGroups = {
  Home: ["Overview"],
  Recruiting: ["Jobs", "Candidates", "AI Match", "Job Discovery", "Talent Search"],
  Engagement: ["Messages", "Interviews", "Calendar"],
  Operations: ["Pipeline", "Submissions", "Offers"],
  Staffing: ["Clients", "Vendors", "Talent Pools"],
  HR: ["Employees", "Onboarding", "HR Operations"],
  Intelligence: ["Analytics", "Reports", "AI Copilot"],
  Admin: ["Integrations", "Compliance", "Users & Permissions", "Security", "Settings"],
};

function useApi<T>(path: string, fallback: T) {
  const [data, setData] = useState<T>(fallback);
  const [status, setStatus] = useState<"loading" | "ready" | "fallback">("loading");

  useEffect(() => {
    let cancelled = false;
    fetch(`${API}${path}`)
      .then((res) => {
        if (!res.ok) throw new Error("API unavailable");
        return res.json();
      })
      .then((json) => {
        if (!cancelled) {
          setData(json);
          setStatus("ready");
        }
      })
      .catch(() => {
        if (!cancelled) {
          setData(fallback);
          setStatus("fallback");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [path]);

  return { data, status };
}

function Shell() {
  const [dark, setDark] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [useDemoData, setUseDemoData] = useState(false);
  const [activeView, setActiveView] = useState("Overview");
  const [query, setQuery] = useState("Find Salesforce Leads in Dallas with 90%+ match");
  const [copilot, setCopilot] = useState<CopilotResponse | null>(null);
  const [selectedJobId, setSelectedJobId] = useState("JOB-1001");
  const [selectedCandidateId, setSelectedCandidateId] = useState("CAN-501");
  const [localJobs, setLocalJobs] = useState<Job[]>(() => readStored<Job[]>("recruitai.jobs", []));
  const [localCandidates, setLocalCandidates] = useState<Candidate[]>(() => readStored<Candidate[]>("recruitai.candidates", []));
  const [activity, setActivity] = useState<string[]>(() => readStored<string[]>("recruitai.activity", ["HaViHire workspace opened with no uploaded records."]));

  useEffect(() => { writeStored("recruitai.jobs", localJobs); }, [localJobs]);
  useEffect(() => { writeStored("recruitai.candidates", localCandidates); }, [localCandidates]);
  useEffect(() => { writeStored("recruitai.activity", activity); }, [activity]);

  const { data: apiOverview, status } = useApi<Overview>("/api/overview", emptyOverview);
  const { data: apiJobs } = useApi<Job[]>("/api/jobs", []);
  const { data: apiCandidates } = useApi<Candidate[]>("/api/candidates", []);
  const { data: apiMatches } = useApi<MatchEvidence[]>(`/api/matches?job_id=${selectedJobId}`, []);

  const jobs = useDemoData ? [...localJobs, ...apiJobs] : localJobs;
  const candidates = useDemoData ? [...localCandidates, ...apiCandidates] : localCandidates;
  const matches = useDemoData ? apiMatches : localMatches(jobs, candidates, selectedJobId);
  const hasWorkspaceData = jobs.length > 0 || candidates.length > 0;
  const localOverview = useMemo<Overview>(() => ({
    ...emptyOverview,
    kpis: [
      { label: "Open Roles", value: jobs.length, detail: jobs.length ? "Created in this browser session" : "No jobs imported yet" },
      { label: "Active Candidates", value: candidates.length, detail: candidates.length ? "Created in this browser session" : "No candidates uploaded yet" },
      { label: "Interviews", value: 0, detail: "No interviews scheduled yet" },
      { label: "High Match Candidates", value: matches.filter((match) => match.overall >= 85).length, detail: "Run AI match after importing data" },
      { label: "Offers", value: 0, detail: "No offers created yet" },
    ],
    funnel: {
      New: candidates.filter((candidate) => candidate.stage === "New").length,
      Screening: candidates.filter((candidate) => candidate.stage === "Screening").length,
      Interview: candidates.filter((candidate) => candidate.stage === "Interview").length,
      Offer: candidates.filter((candidate) => candidate.stage === "Offer").length,
      Hired: candidates.filter((candidate) => candidate.stage === "Hired").length,
    },
    ai_recommendations: hasWorkspaceData ? ["Local records are ready for review. Connect persistence to keep them after refresh."] : emptyOverview.ai_recommendations,
  }), [candidates, hasWorkspaceData, jobs, matches]);
  const overview = useDemoData ? apiOverview : localOverview;
  const selectedJob = jobs.find((job) => job.id === selectedJobId);
  const selectedCandidate = candidates.find((candidate) => candidate.id === selectedCandidateId);
  const selectedMatch = matches.find((match) => match.candidate_id === selectedCandidateId) ?? matches[0];
  const maxFunnel = useMemo(() => Math.max(...Object.values(overview.funnel), 1), [overview]);

  function pushActivity(message: string) {
    setActivity((items) => [message, ...items].slice(0, 8));
  }

  function openView(view: string) {
    setActiveView(view);
    pushActivity(`Opened ${view} workspace.`);
  }

  function loadDemoData() {
    setUseDemoData((enabled) => {
      const next = !enabled;
      pushActivity(next ? "Loaded demo records for local testing." : "Cleared demo records. Workspace is empty again.");
      return next;
    });
  }

  function runAction(action: PriorityAction) {
    const targetView = action.action.includes("Compare") ? "AI Match" : action.action.includes("feedback") ? "Interviews" : "Candidates";
    setActiveView(targetView);
    setQuery(action.reason);
    pushActivity(`${action.action}: ${action.title} assigned to ${action.owner}.`);
  }

  function createJob() {
    setActiveView("Create Job");
    pushActivity("Create Job form opened.");
  }

  function addCandidate() {
    setActiveView("Upload Resume");
    pushActivity("Upload Resume intake opened.");
  }

  function saveJob(job: Job) {
    setLocalJobs((items) => [job, ...items.filter((item) => item.id !== job.id)]);
    setSelectedJobId(job.id);
    setActiveView("Jobs");
    pushActivity(`Created local job ${job.id}: ${job.title}.`);
  }

  function saveCandidate(candidate: Candidate) {
    setLocalCandidates((items) => [candidate, ...items.filter((item) => item.id !== candidate.id)]);
    setSelectedCandidateId(candidate.id);
    setActiveView("Candidates");
    pushActivity(`Created local candidate ${candidate.id}: ${candidate.name}.`);
  }

  async function askCopilot(event?: React.FormEvent) {
    event?.preventDefault();
    pushActivity(`Copilot request submitted: ${query}`);
    if (!useDemoData) {
      setCopilot({
        answer: "No uploaded jobs or candidates are available yet. Upload/import data or load demo data to run AI analysis.",
        actions: ["Upload Resume", "Create Job", "Load Demo Data"],
        evidence: ["Workspace has zero candidate records", "Workspace has zero job records"],
        confidence: "High",
      });
      setActiveView("AI Copilot");
      return;
    }
    try {
      const response = await fetch(`${API}/api/copilot`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: query, role: "Recruiter" }),
      });
      if (!response.ok) throw new Error("Copilot unavailable");
      const json: CopilotResponse = await response.json();
      setCopilot(json);
      setActiveView("AI Copilot");
      pushActivity(`Copilot returned ${json.confidence.toLowerCase()} confidence guidance.`);
    } catch {
      setCopilot({
        answer: "Backend copilot is unavailable. Start the FastAPI service to use calculated responses.",
        actions: ["Check API", "Use Demo Dashboard"],
        evidence: ["Fallback generated by frontend"],
        confidence: "Low",
      });
      setActiveView("AI Copilot");
    }
  }

  const context = {
    activeView,
    overview,
    jobs,
    candidates,
    matches,
    selectedJob,
    selectedCandidate,
    selectedMatch,
    maxFunnel,
    copilot,
    activity,
    useDemoData,
    hasWorkspaceData,
    setSelectedJobId,
    setSelectedCandidateId,
    setActiveView,
    pushActivity,
    runAction,
    askCopilot,
    loadDemoData,
    createJob,
    addCandidate,
    saveJob,
    saveCandidate,
  };

  return (
    <div className={dark ? "app dark" : "app"}>
      <aside className={collapsed ? "sidebar collapsed" : "sidebar"}>
        <div className="brand">
          <div className="brandMark">R</div>
          {!collapsed && (
            <div>
              <strong>RecruitAI</strong>
              <span>Operating System</span>
            </div>
          )}
        </div>
        <button className="ghost iconRow" onClick={() => setCollapsed(!collapsed)}>
          <Menu size={18} />
          {!collapsed && <span>Collapse</span>}
        </button>
        <nav>
          {Object.entries(roleGroups).map(([group, items]) => (
            <section key={group}>
              {!collapsed && <p>{group}</p>}
              {items.slice(0, collapsed ? 1 : items.length).map((item) => (
                <button className={item === activeView ? "active" : ""} key={item} onClick={() => openView(item)}>
                  <span className="dot" />
                  {!collapsed && item}
                </button>
              ))}
            </section>
          ))}
        </nav>
      </aside>

      <main>
        <header className="topbar">
          <form className="searchBox" onSubmit={askCopilot}>
            <Search size={18} />
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Ask RecruitAI anything..." />
            <button type="submit" aria-label="Ask RecruitAI"><Send size={16} /></button>
          </form>
          <button className="ghost" onClick={loadDemoData}><Database size={16} /> {useDemoData ? "Clear Demo" : "Load Demo"}</button>
          <button className="ghost" onClick={createJob}><FilePlus2 size={16} /> Create Job</button>
          <button className="primary" onClick={addCandidate}><UserPlus size={16} /> Add Candidate</button>
          <button className="theme" onClick={() => setDark(!dark)} aria-label="Toggle theme">
            {dark ? <Sun size={18} /> : <Moon size={18} />}
          </button>
        </header>

        <section className="hero compactHero">
          <div>
            <span className="demo">{useDemoData ? "Demo records loaded" : hasWorkspaceData ? "Saved locally · persists on refresh" : "No uploaded data"}</span>
            <h1>{activeView}</h1>
            <p>{viewSubtitle(activeView, selectedJob, selectedCandidate, hasWorkspaceData)}</p>
          </div>
          <div className="health">
            <CheckCircle2 size={18} />
            <span>{status === "ready" ? "API connected" : "API fallback"}</span>
          </div>
        </section>

        <ViewSurface {...context} />
      </main>
    </div>
  );
}

type SurfaceContext = {
  activeView: string;
  overview: Overview;
  jobs: Job[];
  candidates: Candidate[];
  matches: MatchEvidence[];
  selectedJob?: Job;
  selectedCandidate?: Candidate;
  selectedMatch?: MatchEvidence;
  maxFunnel: number;
  copilot: CopilotResponse | null;
  activity: string[];
  useDemoData: boolean;
  hasWorkspaceData: boolean;
  setSelectedJobId: (id: string) => void;
  setSelectedCandidateId: (id: string) => void;
  setActiveView: (view: string) => void;
  pushActivity: (message: string) => void;
  runAction: (action: PriorityAction) => void;
  askCopilot: () => void;
  loadDemoData: () => void;
  createJob: () => void;
  addCandidate: () => void;
  saveJob: (job: Job) => void;
  saveCandidate: (candidate: Candidate) => void;
};

function ViewSurface(props: SurfaceContext) {
  const { activeView, overview, jobs, candidates, matches, maxFunnel, activity, hasWorkspaceData } = props;

  if (activeView === "Create Job") {
    return (
      <section className="singleWorkspace">
        <CreateJobForm onSave={props.saveJob} />
        <ActivityPanel activity={activity} />
      </section>
    );
  }

  if (activeView === "Upload Resume" || activeView === "Add Candidate") {
    return (
      <section className="singleWorkspace">
        <UploadResumePanel onSave={props.saveCandidate} />
        <ActivityPanel activity={activity} />
      </section>
    );
  }

  if (["Job Discovery", "Talent Search", "Messages", "Pipeline", "Submissions", "Offers", "Clients", "Vendors", "Talent Pools", "Employees", "Onboarding", "HR Operations", "Analytics", "Reports", "Integrations", "Settings"].includes(activeView)) {
    return <ModuleWorkspace {...props} />;
  }

  if (["Compliance", "Users & Permissions", "Security"].includes(activeView)) {
    return (
      <section className="singleWorkspace">
        <CompliancePanel />
        <ActivityPanel activity={activity} />
      </section>
    );
  }

  if (["Interviews", "Calendar"].includes(activeView)) {
    return (
      <section className="singleWorkspace">
        <InterviewPanel interviews={overview.upcoming_interviews} candidates={candidates} onAction={props.pushActivity} />
        <ActivityPanel activity={activity} />
      </section>
    );
  }

  if (activeView === "AI Copilot") {
    return (
      <section className="singleWorkspace">
        <CopilotPanel response={props.copilot} onRun={props.askCopilot} />
        <ActivityPanel activity={activity} />
      </section>
    );
  }

  if (activeView === "Jobs") {
    return (
      <section className="singleWorkspace">
        <JobsPanel jobs={jobs} selectedJobId={props.selectedJob?.id ?? ""} onLoadDemo={props.loadDemoData} onSelect={(job) => {
          props.setSelectedJobId(job.id);
          props.setActiveView("AI Match");
          props.pushActivity(`Selected ${job.id} for match analysis.`);
        }} />
        <ActivityPanel activity={activity} />
      </section>
    );
  }

  if (activeView === "Candidates" || activeView === "Candidate 360") {
    return (
      <section className="singleWorkspace">
        <CandidatePanel candidates={candidates} selectedCandidateId={props.selectedCandidate?.id ?? ""} onAddCandidate={props.addCandidate} onSelect={(candidate) => {
          props.setSelectedCandidateId(candidate.id);
          props.setActiveView("Candidate 360");
          props.pushActivity(`Selected ${candidate.name} for Candidate 360.`);
        }} />
        <Candidate360 candidate={props.selectedCandidate} match={props.selectedMatch} job={props.selectedJob} onAction={props.pushActivity} />
        <ActivityPanel activity={activity} />
      </section>
    );
  }

  if (activeView === "AI Match") {
    return (
      <section className="singleWorkspace">
        <MatchPanel matches={matches} candidates={candidates} selectedCandidateId={props.selectedCandidate?.id ?? ""} onSelect={(candidateId) => {
          props.setSelectedCandidateId(candidateId);
          props.pushActivity(`Opened match evidence for ${candidateId}.`);
        }} />
        <SolutionPanel candidate={props.selectedCandidate} job={props.selectedJob} onAction={props.pushActivity} hasData={hasWorkspaceData} />
      </section>
    );
  }

  return (
    <>
      <section className="kpis">
        {overview.kpis.map((kpi) => (
          <button key={kpi.label} className="kpi" onClick={() => props.setActiveView(kpi.label.includes("Candidate") ? "Candidates" : kpi.label.includes("Interview") ? "Interviews" : "Jobs")}>
            <span>{kpi.label}</span>
            <strong>{kpi.value}</strong>
            <small>{kpi.detail}</small>
          </button>
        ))}
      </section>

      {!hasWorkspaceData && activeView === "Overview" ? (
        <EmptyStart onLoadDemo={props.loadDemoData} onCreateJob={props.createJob} onAddCandidate={props.addCandidate} />
      ) : (
        <section className="workspace">
          <div className="leftPane">
            {activeView === "Candidates" || activeView === "Candidate 360" ? (
              <CandidatePanel candidates={candidates} selectedCandidateId={props.selectedCandidate?.id ?? ""} onAddCandidate={props.addCandidate} onSelect={(candidate) => {
                props.setSelectedCandidateId(candidate.id);
                props.setActiveView("Candidate 360");
                props.pushActivity(`Selected ${candidate.name} for Candidate 360.`);
              }} />
            ) : (
              <>
                <RecruiterBrief overview={overview} jobs={jobs} candidates={candidates} onRun={props.runAction} onOpen={props.setActiveView} />
                <JobsPanel jobs={jobs} selectedJobId={props.selectedJob?.id ?? ""} onLoadDemo={props.loadDemoData} onSelect={(job) => {
                  props.setSelectedJobId(job.id);
                  props.setActiveView("AI Match");
                  props.pushActivity(`Selected ${job.id} for match analysis.`);
                }} />
              </>
            )}
          </div>
          <div className="rightPane">
            <MatchPanel matches={matches} candidates={candidates} selectedCandidateId={props.selectedCandidate?.id ?? ""} onSelect={(candidateId) => {
              props.setSelectedCandidateId(candidateId);
              props.pushActivity(`Opened match evidence for ${candidateId}.`);
            }} />
            <FunnelPanel funnel={overview.funnel} maxFunnel={maxFunnel} onStage={(stage) => {
              props.setActiveView("Candidates");
              props.pushActivity(`Opened ${stage} candidate pipeline.`);
            }} />
          </div>
        </section>
      )}

      <section className="bottomGrid">
        <Candidate360 candidate={props.selectedCandidate} match={props.selectedMatch} job={props.selectedJob} onAction={props.pushActivity} />
        <ActivityPanel activity={activity} />
        <SolutionPanel candidate={props.selectedCandidate} job={props.selectedJob} onAction={props.pushActivity} hasData={hasWorkspaceData} />
      </section>
    </>
  );
}

function ModuleWorkspace(props: SurfaceContext) {
  if (props.activeView === "Job Discovery") return <JobDiscoveryPanel {...props} />;
  const config = moduleConfig(props.activeView);
  return (
    <section className="moduleGrid">
      <Panel title={config.title} icon={config.icon}>
        <div className="moduleHero">
          <span className="sectionLabel">{config.status}</span>
          <strong>{config.headline}</strong>
          <p>{config.description}</p>
          <div className="actionButtons">
            {config.actions.map((action) => (
              <button key={action} onClick={() => runModuleAction(action, props)}>{action}</button>
            ))}
          </div>
        </div>
      </Panel>
      <Panel title="Workspace data" icon={<Database size={18} />}>
        {props.hasWorkspaceData ? (
          <ul className="clean">
            <li>Jobs available: {props.jobs.length}</li>
            <li>Candidates available: {props.candidates.length}</li>
            <li>AI match records available: {props.matches.length}</li>
          </ul>
        ) : (
          <EmptyMini view={props.activeView} onLoadDemo={props.loadDemoData} />
        )}
      </Panel>
      <ActivityPanel activity={props.activity} />
    </section>
  );
}

function JobDiscoveryPanel(props: SurfaceContext) {
  const candidate = props.selectedCandidate ?? props.candidates[0];
  const discovered = [
    { source: "LinkedIn", title: "Salesforce Technical Architect", company: "Enterprise Systems Co.", location: "Dallas, TX", skills: ["Salesforce", "Apex", "LWC", "Architecture", "Data Cloud"] },
    { source: "Indeed", title: "Lead DocuSign Developer", company: "Lennar", location: "Irving, TX", skills: ["DocuSign", "API", "IAM", "Salesforce", "SSO"] },
    { source: "Dice", title: "Salesforce Integration Architect", company: "Northstar Digital", location: "Remote", skills: ["Salesforce", "MuleSoft", "REST APIs", "AWS", "Architecture"] },
    { source: "Company career site", title: "Enterprise CRM Architect", company: "Fortune 500 Partner", location: "Remote", skills: ["Salesforce", "Integration", "Leadership", "Data Cloud"] },
  ];
  return <section className="discoveryGrid">
    <Panel title="Best jobs for this candidate" icon={<BriefcaseBusiness size={18} />}>
      <div className="discoveryHeader"><div><span className="sectionLabel">{candidate ? `Personalized for ${candidate.name}` : "Add a candidate first"}</span><strong>Ranked by resume evidence and job requirements</strong></div><button className="primary" onClick={() => props.pushActivity("Job discovery refresh queued for connected providers.")}>Refresh sources</button></div>
      <div className="sourceNotice"><span className="pill">Preview providers</span> Results below are clearly labeled examples until job-board connections are authorized in Integrations.</div>
      <div className="jobResults">{candidate ? discovered.map(job => { const match = localMatch(candidate, { id: "DISCOVERY", title: job.title, company: job.company, location: job.location, work_mode: job.location === "Remote" ? "Remote" : "Hybrid", employment_type: "Full-Time", owner: "RecruitAI", status: "Open", required_skills: job.skills, preferred_skills: [] }); return <article className="jobResult" key={job.title}><div className="jobResultTop"><div><span className="sourceTag">{job.source}</span><h3>{job.title}</h3><p>{job.company} · {job.location}</p></div><div className="matchScore"><b>{match.overall}%</b><span>match</span></div></div><div className="chips">{job.skills.map(skill => <span className={match.gaps.includes(skill) ? "missingSkill" : ""} key={skill}>{match.gaps.includes(skill) ? "Needs: " : "✓ "}{skill}</span>)}</div><div className="jobResultFooter"><span>{match.gaps.length ? `${match.gaps.length} skill${match.gaps.length === 1 ? "" : "s"} to strengthen` : "Strong fit"}</span><button onClick={() => { props.setActiveView("AI Match"); props.pushActivity(`Opened evidence for ${job.title}.`); }}>View match plan</button></div></article>; }) : <EmptyMini view="job matches" onLoadDemo={props.loadDemoData} />}</div>
    </Panel>
    <Panel title="Recruiter next steps" icon={<Gauge size={18} />}><div className="discoverySteps"><div><b>1</b><span>Review the top match and missing skills.</span></div><div><b>2</b><span>Update the resume only with truthful experience.</span></div><div><b>3</b><span>Apply or send a recruiter-ready profile.</span></div><div><b>4</b><span>Connect job boards to refresh live postings.</span></div></div></Panel>
  </section>;
}

function runModuleAction(action: string, props: SurfaceContext) {
  if (action.includes("JD") || action.includes("Job")) {
    props.createJob();
    return;
  }
  if (action.includes("Resume") || action.includes("Candidate")) {
    props.addCandidate();
    return;
  }
  if (action === "Load Demo") {
    props.loadDemoData();
    return;
  }
  props.pushActivity(`${props.activeView}: ${action} clicked.`);
}

function moduleConfig(view: string) {
  const defaults = {
    title: view,
    status: "Ready for setup",
    headline: `${view} workspace is ready`,
    description: "No uploaded records are available yet. Connect an integration, upload a document, or load demo data to exercise this module.",
    actions: ["Upload Data", "Connect Source", "Load Demo"],
    icon: <FileSearch size={18} />,
  };
  const map: Record<string, typeof defaults> = {
    "Job Discovery": { ...defaults, title: "Job Discovery", headline: "Find and normalize jobs from connected sources", actions: ["Upload JD", "Connect Job Board", "Create Search"] },
    "Talent Search": { ...defaults, title: "Talent Search", headline: "Search candidates by skills, location, freshness, and eligibility", actions: ["Upload Resume", "Import Candidates", "Run Search"] },
    Messages: { ...defaults, title: "Messages", headline: "Draft outreach and follow-up messages", actions: ["Draft Message", "Use Template", "Review Queue"], icon: <MessageSquareText size={18} /> },
    Pipeline: { ...defaults, title: "Pipeline", headline: "Track candidates through recruiting stages", actions: ["Create Pipeline", "Filter Stage", "Export View"], icon: <Layers3 size={18} /> },
    Submissions: { ...defaults, title: "Submissions", headline: "Prepare client-ready candidate submissions", actions: ["Create Submission", "Attach Evidence", "Send for Review"] },
    Offers: { ...defaults, title: "Offers", headline: "Manage offer approvals and compensation checks", actions: ["Create Offer", "Approval Route", "Generate Letter"] },
    Integrations: { ...defaults, title: "Integrations", headline: "Connect ATS, email, calendar, job boards, and storage", actions: ["Connect ATS", "Connect Calendar", "Test Sync"], icon: <Database size={18} /> },
    Analytics: { ...defaults, title: "Analytics", headline: "Measure funnel health, source quality, and recruiter workload", actions: ["Build Report", "Filter Date", "Export CSV"], icon: <Gauge size={18} /> },
    Reports: { ...defaults, title: "Reports", headline: "Create executive and client reporting packs", actions: ["Create Report", "Schedule Report", "Export PDF"], icon: <FileSearch size={18} /> },
  };
  return map[view] ?? defaults;
}

function EmptyStart({ onLoadDemo, onCreateJob, onAddCandidate }: { onLoadDemo: () => void; onCreateJob: () => void; onAddCandidate: () => void }) {
  return (
    <section className="emptyStart">
      <Panel title="Start with your data" icon={<UploadCloud size={18} />}>
        <div className="moduleHero">
          <span className="sectionLabel">Empty workspace</span>
          <strong>No jobs, candidates, interviews, or names have been uploaded.</strong>
          <p>Use the buttons below to start building real records. Demo data is only for local testing and will not show unless you load it.</p>
          <div className="actionButtons">
            <button onClick={onCreateJob}>Create Job</button>
            <button onClick={onAddCandidate}>Add Candidate</button>
            <button onClick={onLoadDemo}>Load Demo Data</button>
          </div>
        </div>
      </Panel>
    </section>
  );
}

type ParsedDocument = { name: string; headline: string; location: string; skills: string[]; company: string; text: string };

export function DocumentIntake({ kind, onParsed, onBusy }: { kind: "resume" | "job description"; onParsed: (data: ParsedDocument) => void; onBusy: (busy: boolean) => void }) {
  const [state, setState] = useState<"idle" | "reading" | "ready" | "error">("idle");
  const [filename, setFilename] = useState("");
  const [error, setError] = useState("");
  async function read(file?: File) {
    if (!file) return;
    setFilename(file.name); setError("");
    if (file.size > 8 * 1024 * 1024) { setState("error"); setError("Choose a file smaller than 8 MB."); return; }
    setState("reading"); onBusy(true);
    try {
      const response = await fetch(`${API}/api/intake/parse?filename=${encodeURIComponent(file.name)}&kind=${kind === "job description" ? "job" : "resume"}`, { method: "POST", headers: { "Content-Type": "application/octet-stream" }, body: file });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Unable to read this document.");
      onParsed(data); setState("ready");
    } catch (error) { setState("error"); setError(error instanceof Error ? error.message : "Unable to read this document. Please try again."); }
    finally { onBusy(false); }
  }
  return <div className="intakeIntro">
    <div className="intakeSteps"><span className="current">01 Upload</span><span>02 Review details</span><span>03 Save {kind === "resume" ? "candidate" : "role"}</span></div>
    <label className={`documentDrop ${state}`}>
      <UploadCloud size={32} />
      <strong>{state === "reading" ? "Reading your document…" : filename || `Choose a ${kind}`}</strong>
      <span>{state === "ready" ? "Details extracted. Review and edit the fields below." : "PDF, DOCX or TXT · Up to 8 MB · Processed locally"}</span>
      <input aria-label={`Upload ${kind}`} type="file" accept=".pdf,.docx,.txt" disabled={state === "reading"} onChange={event => { void read(event.target.files?.[0]); event.target.value = ""; }} />
    </label>
    <p className={state === "error" ? "intakeError" : "intakeHint"} role={state === "error" ? "alert" : "status"}>{error || (state === "ready" ? "Autofill is a first pass. Missing details stay blank; confirm everything before saving." : "Start with a document, or enter the details below yourself.")}</p>
  </div>;
}

function CreateJobForm({ onSave }: { onSave: (job: Job) => void }) {
  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("");
  const [location, setLocation] = useState("");
  const [skills, setSkills] = useState("");
  const [workMode, setWorkMode] = useState("Hybrid");
  const [busy, setBusy] = useState(false);

  function submit(event: React.FormEvent) {
    event.preventDefault();
    const id = `JOB-${crypto.randomUUID()}`;
    onSave({
      id,
      title: title || "Untitled Role",
      company: company || "New Client",
      location: location || "Location pending",
      work_mode: workMode,
      employment_type: "Full-Time",
      owner: "Hari Mittapalli",
      status: "Draft",
      required_skills: splitSkills(skills),
      preferred_skills: [],
    });
    setTitle("");
    setCompany("");
    setLocation("");
    setSkills("");
  }

  return (
    <Panel title="Create a role" icon={<FilePlus2 size={18} />}>
      <DocumentIntake kind="job description" onBusy={setBusy} onParsed={data => { setTitle(data.headline); setCompany(data.company); setLocation(data.location); setSkills(data.skills.join(", ")); }} />
      <form className="formGrid" onSubmit={submit}>
        <label>
          Job title
          <input required value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Salesforce Technical Lead" />
        </label>
        <label>
          Client / company
          <input value={company} onChange={(event) => setCompany(event.target.value)} placeholder="Client name" />
        </label>
        <label>
          Location
          <input value={location} onChange={(event) => setLocation(event.target.value)} placeholder="Dallas, TX" />
        </label>
        <label>
          Work mode
          <select value={workMode} onChange={(event) => setWorkMode(event.target.value)}>
            <option>Remote</option>
            <option>Hybrid</option>
            <option>On-site</option>
          </select>
        </label>
        <label className="wide">
          Required skills
          <textarea value={skills} onChange={(event) => setSkills(event.target.value)} placeholder="Apex, LWC, Integration, Leadership" />
        </label>
        <div className="formActions">
          <button type="submit" className="primary" disabled={busy}>Save Job</button>
        </div>
      </form>
    </Panel>
  );
}

function UploadResumePanel({ onSave }: { onSave: (candidate: Candidate) => void }) {
  const [name, setName] = useState("");
  const [headline, setHeadline] = useState("");
  const [location, setLocation] = useState("");
  const [skills, setSkills] = useState("");
  const [busy, setBusy] = useState(false);

  function submit(event: React.FormEvent) {
    event.preventDefault();
    const id = `CAN-${crypto.randomUUID()}`;
    onSave({
      id,
      name: name || "New Candidate",
      headline: headline || "Headline not provided",
      location: location || "Location pending",
      stage: "New",
      owner: "Hari Mittapalli",
      skills: splitSkills(skills),
      years_experience: 0,
      availability_days: 0,
      resume_quality: 0,
    });
    setName("");
    setHeadline("");
    setLocation("");
    setSkills("");

  }

  return (
    <Panel title="Add your next great hire" icon={<UploadCloud size={18} />}>
      <DocumentIntake kind="resume" onBusy={setBusy} onParsed={data => { setName(data.name); setLocation(data.location); setHeadline(data.headline); setSkills(data.skills.join(", ")); }} />
      <form className="formGrid" onSubmit={submit}>
        <label>
          Candidate name
          <input required value={name} onChange={(event) => setName(event.target.value)} placeholder="Candidate name" />
        </label>
        <label>
          Location
          <input value={location} onChange={(event) => setLocation(event.target.value)} placeholder="City, State" />
        </label>
        <label className="wide">
          Headline
          <input value={headline} onChange={(event) => setHeadline(event.target.value)} placeholder="Short profile summary" />
        </label>
        <label className="wide">
          Skills ({splitSkills(skills).length} extracted / entered)
          <textarea value={skills} onChange={(event) => setSkills(event.target.value)} placeholder="Salesforce, Apex, LWC" />
        </label>
        <div className="formActions">
          <button type="submit" className="primary" disabled={busy}>Save Candidate</button>
        </div>
      </form>
    </Panel>
  );
}

function EmptyMini({ view, onLoadDemo }: { view: string; onLoadDemo: () => void }) {
  return (
    <div className="emptyMini">
      <strong>No {view.toLowerCase()} records yet.</strong>
      <p>Import real data to populate this view, or load demo data to test the flow.</p>
      <button onClick={onLoadDemo}>Load Demo Data</button>
    </div>
  );
}

function PriorityPanel({ actions, onRun }: { actions: PriorityAction[]; onRun: (action: PriorityAction) => void }) {
  return (
    <Panel title="Priority actions" icon={<Gauge size={18} />}>
      <div className="actionList">
        {actions.length ? actions.map((action) => (
          <button className="action" key={action.title} onClick={() => onRun(action)}>
            <span className={`badge ${action.priority.toLowerCase()}`}>{action.priority}</span>
            <div>
              <strong>{action.title}</strong>
              <p>{action.reason}</p>
              <small>{action.owner} · {action.action}</small>
            </div>
            <Eye size={17} />
          </button>
        )) : <p className="muted">No priority actions yet.</p>}
      </div>
    </Panel>
  );
}

function RecruiterBrief({ overview, jobs, candidates, onRun, onOpen }: { overview: Overview; jobs: Job[]; candidates: Candidate[]; onRun: (action: PriorityAction) => void; onOpen: (view: string) => void }) {
  const top = overview.priority_actions[0];
  return <Panel title="Recruiter command center" icon={<Gauge size={18} />}>
    <div className="briefIntro"><div><span className="sectionLabel">TODAY'S FOCUS</span><strong>{top?.title ?? (jobs.length ? "Review your open roles" : "Start by creating a job")}</strong><p>{top?.reason ?? "RecruitAI will keep the next action visible here."}</p></div><button className="primary" onClick={() => top ? onRun(top) : onOpen(jobs.length ? "Jobs" : "Create Job")}>{top?.action ?? (jobs.length ? "Open Jobs" : "Create Job")}</button></div>
    <div className="briefStats"><button onClick={() => onOpen("Jobs")}><b>{jobs.length}</b><span>roles to work</span></button><button onClick={() => onOpen("Candidates")}><b>{candidates.length}</b><span>candidates in workspace</span></button><button onClick={() => onOpen("Job Discovery")}><b>Find</b><span>best jobs for a candidate</span></button></div>
    {overview.priority_actions.length > 1 && <div className="briefQueue"><span className="sectionLabel">UP NEXT</span>{overview.priority_actions.slice(1, 4).map(action => <button key={action.title} onClick={() => onRun(action)}><span className={`badge ${action.priority.toLowerCase()}`}>{action.priority}</span><span>{action.title}</span><small>{action.action} →</small></button>)}</div>}
  </Panel>;
}

function JobsPanel({ jobs, selectedJobId, onLoadDemo, onSelect }: { jobs: Job[]; selectedJobId: string; onLoadDemo: () => void; onSelect: (job: Job) => void }) {
  return (
    <Panel title="Jobs" icon={<BriefcaseBusiness size={18} />}>
      <div className="table">
        {jobs.length ? jobs.map((job) => (
          <button className={job.id === selectedJobId ? "row selected" : "row"} key={job.id} onClick={() => onSelect(job)}>
            <div>
              <strong>{job.title}</strong>
              <small>{job.company} · {job.location}</small><div className="chips recordSkills">{job.required_skills.slice(0, 6).map(skill => <span key={skill}>{skill}</span>)}</div>
            </div>
            <span>{job.work_mode}</span>
            <span className="pill">{job.status}</span>
          </button>
        )) : <EmptyMini view="jobs" onLoadDemo={onLoadDemo} />}
      </div>
    </Panel>
  );
}

function CandidatePanel({ candidates, selectedCandidateId, onAddCandidate, onSelect }: { candidates: Candidate[]; selectedCandidateId: string; onAddCandidate: () => void; onSelect: (candidate: Candidate) => void }) {
  return (
    <Panel title="Candidates" icon={<Users size={18} />}>
      <div className="table">
        {candidates.length ? candidates.map((candidate) => (
          <button className={candidate.id === selectedCandidateId ? "candidate selected" : "candidate"} key={candidate.id} onClick={() => onSelect(candidate)}>
            <div className="avatar">{initials(candidate.name)}</div>
            <div>
              <strong>{candidate.name}</strong>
              <p>{candidate.headline}</p>
              <small>{candidate.location}{candidate.years_experience ? ` · ${candidate.years_experience} years` : ""}</small><div className="chips recordSkills">{candidate.skills.slice(0, 6).map(skill => <span key={skill}>{skill}</span>)}{candidate.skills.length > 6 && <span>+{candidate.skills.length - 6} more · Open profile</span>}</div>
            </div>
            <span className="pill">{candidate.stage}</span>
          </button>
        )) : (
          <div className="emptyMini">
            <strong>No uploaded candidates yet.</strong>
            <p>Add a candidate manually or load demo data to test Candidate 360.</p>
            <button onClick={onAddCandidate}>Add Candidate</button>
          </div>
        )}
      </div>
    </Panel>
  );
}

function MatchPanel({ matches, candidates, selectedCandidateId, onSelect }: { matches: MatchEvidence[]; candidates: Candidate[]; selectedCandidateId: string; onSelect: (candidateId: string) => void }) {
  return (
    <Panel title="AI match evidence" icon={<Sparkles size={18} />}>
      {matches.length ? matches.slice(0, 3).map((match) => {
        const candidate = candidates.find((item) => item.id === match.candidate_id);
        return (
          <button className={match.candidate_id === selectedCandidateId ? "match selected" : "match"} key={`${match.candidate_id}-${match.job_id}`} onClick={() => onSelect(match.candidate_id)}>
            <div className="score">{match.overall}%</div>
            <div>
              <strong>{candidate?.name ?? match.candidate_id}</strong>
              <p>{candidate?.headline}</p>
              <div className="chips">
                <span>Eligibility {match.eligibility}</span>
                <span>Mandatory {match.mandatory}%</span>
                <span>Confidence {match.confidence}</span>
              </div>
            </div>
          </button>
        );
      }) : <p className="muted">No match evidence yet. Add one job and one candidate to run AI match.</p>}
    </Panel>
  );
}

function FunnelPanel({ funnel, maxFunnel, onStage }: { funnel: Record<string, number>; maxFunnel: number; onStage: (stage: string) => void }) {
  return (
    <Panel title="Hiring funnel" icon={<Layers3 size={18} />}>
      <div className="funnel">
        {Object.entries(funnel).slice(0, 5).map(([stage, value]) => (
          <button key={stage} className="funnelItem" onClick={() => onStage(stage)}>
            <div className="funnelLabel">
              <span>{stage}</span>
              <strong>{value}</strong>
            </div>
            <div className="bar">
              <span style={{ width: `${Math.max(8, (value / maxFunnel) * 100)}%` }} />
            </div>
          </button>
        ))}
      </div>
    </Panel>
  );
}

function CopilotPanel({ response, onRun }: { response: CopilotResponse | null; onRun: () => void }) {
  return (
    <Panel title="AI Copilot" icon={<Command size={18} />}>
      <div className="copilot">
        <p>{response?.answer ?? "Ask RecruitAI to find candidates, explain match scores, draft outreach, or identify follow-up work."}</p>
        <div className="chips">
          {(response?.evidence ?? ["Workspace readiness checked", "No instruction is executed from uploaded documents", "User action required for data import"]).map((item) => <span key={item}>{item}</span>)}
        </div>
        <div className="actionButtons">
          {(response?.actions ?? ["Upload Resume", "Create Job", "Load Demo Data"]).map((action) => (
            <button key={action} onClick={onRun}>{action}</button>
          ))}
        </div>
      </div>
    </Panel>
  );
}

function InterviewPanel({ interviews, candidates, onAction }: { interviews: Interview[]; candidates: Candidate[]; onAction: (message: string) => void }) {
  return (
    <Panel title="Interview operations" icon={<CalendarDays size={18} />}>
      {interviews.length ? interviews.map((interview) => {
        const candidate = candidates.find((item) => item.id === interview.candidate_id);
        return (
          <div className="interview" key={interview.id}>
            <div>
              <strong>{candidate?.name ?? interview.candidate_id} with {interview.interviewer}</strong>
              <p>{new Date(interview.scheduled_at).toLocaleString()} · {interview.status}</p>
            </div>
            <button onClick={() => onAction(`Requested feedback from ${interview.interviewer} for ${candidate?.name ?? interview.candidate_id}.`)}>Request Feedback</button>
          </div>
        );
      }) : <p className="muted">No interviews scheduled yet.</p>}
    </Panel>
  );
}

function CompliancePanel() {
  return (
    <Panel title="Compliance and access" icon={<ShieldCheck size={18} />}>
      <ul className="clean">
        <li>Role based access controls are modeled at the API boundary.</li>
        <li>Sensitive fields require field level visibility policy.</li>
        <li>Uploaded documents are treated as data, not executable instructions.</li>
        <li>Every sensitive read/write is designed to be audit logged.</li>
      </ul>
    </Panel>
  );
}

function SkillList({ skills }: { skills: string[] }) {
  const [expanded, setExpanded] = useState(false);
  return <div><p className="muted">{skills.length} extracted skills · Review for accuracy</p><div className="chips">{(expanded ? skills : skills.slice(0, 12)).map(skill => <span key={skill}>{skill}</span>)}</div>{skills.length > 12 && <button className="ghost" type="button" aria-expanded={expanded} onClick={() => setExpanded(!expanded)}>{expanded ? "Show fewer skills" : `View all ${skills.length} skills`}</button>}</div>;
}

function Candidate360({ candidate, match, job, onAction }: { candidate?: Candidate; match?: MatchEvidence; job?: Job; onAction?: (message: string) => void }) {
  return (
    <Panel title="Candidate 360" icon={<Users size={18} />}>
      {candidate ? (
        <div className="profileCard">
          <div className="avatar large">{initials(candidate.name)}</div>
          <strong>{candidate.name}</strong>
          <p>{candidate.headline}</p>
          <div className="chips">
            <span>{candidate.location}</span>
            <span className="pill">{candidate.stage}</span>

          </div>
          <div className="candidateMapping"><span className="sectionLabel">CURRENT JOB MAPPING</span><strong>{job?.title ?? "No job selected"}</strong><small>{job ? `${job.company} · ${job.location}` : "Select a job to see match details."}</small>{match && <b className="mappingScore">{match.overall}% match</b>}</div>
          <div className="stageTracker">{["New", "Screening", "Interview", "Offer", "Hired"].map(stage => <span className={stage === candidate.stage ? "current" : ""} key={stage}><i />{stage}</span>)}</div>
          <SkillList key={candidate.id} skills={candidate.skills} />
          {match && (
            <ul className="clean compact">
              <li>Overall match: {match.overall}%</li>
              <li>Eligibility: {match.eligibility}</li>
              <li>Gaps: {match.gaps.length ? match.gaps.join(", ") : "None"}</li>
            </ul>
          )}
          <div className="profileActions"><button className="primary" onClick={() => onAction?.(`Interview scheduling opened for ${candidate.name}${job ? ` on ${job.title}` : ""}.`)}>Schedule interview</button><button onClick={() => onAction?.(`Status update opened for ${candidate.name}.`)}>Update status</button></div>
        </div>
      ) : <p className="muted">No candidate selected because no candidate has been uploaded.</p>}
    </Panel>
  );
}

function ActivityPanel({ activity }: { activity: string[] }) {
  return (
    <Panel title="Work activity" icon={<MessageSquareText size={18} />}>
      <div className="activityList">
        {activity.map((item) => <p key={item}>{item}</p>)}
      </div>
    </Panel>
  );
}

function SolutionPanel({ candidate, job, onAction, hasData }: { candidate?: Candidate; job?: Job; onAction: (message: string) => void; hasData: boolean }) {
  const match = hasData && candidate && job ? localMatch(candidate, job) : undefined;
  return (
    <Panel title="Proposed solution" icon={<FileSearch size={18} />}>
      <div className="solutionStack">
        <span className="sectionLabel">{hasData ? "Recommended move" : "Setup required"}</span>
        <strong>{hasData ? `${candidate?.name ?? "Top candidate"} for ${job?.id ?? "selected job"}` : "Import real data before recommendations"}</strong>
        <p>{hasData ? `Resume match ${match?.overall ?? 0}% · ${match?.mandatory ?? 0}% required skills. Resolve the gaps below, then update the resume or submit.` : "RecruitAI will not show invented people. Add jobs/candidates or load demo records to test the flow."}</p>
        {match && <div className="matchExplainer"><strong>What to improve</strong>{match.gaps.length ? <ul className="clean">{match.gaps.map(gap => <li key={gap}>Add evidence for <b>{gap}</b> if the candidate truly has it.</li>)}</ul> : <p className="muted">All required skills are present in the resume.</p>}</div>}
        <div className="actionButtons">
          <button onClick={() => onAction(hasData ? "Drafted client submission summary with evidence and risk notes." : "Opened upload/import checklist.")}>{hasData ? "Draft Summary" : "Upload Checklist"}</button>
          <button onClick={() => onAction(hasData ? "Created follow-up task for candidate freshness and compensation check." : "Opened integration setup checklist.")}>{hasData ? "Create Task" : "Connect Source"}</button>
        </div>
      </div>
    </Panel>
  );
}

function Panel({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="panel">
      <div className="panelTitle">
        <span>{icon}</span>
        <h2>{title}</h2>
        <ChevronDown size={16} />
      </div>
      {children}
    </section>
  );
}

function initials(name: string) {
  return name.split(" ").map((part) => part[0]).join("");
}

function splitSkills(value: string) {
  return value.split(",").map((skill) => skill.trim()).filter(Boolean);
}

function readStored<T>(key: string, fallback: T): T {
  try { const raw = window.localStorage.getItem(key); return raw ? JSON.parse(raw) as T : fallback; } catch { return fallback; }
}

function writeStored<T>(key: string, value: T) {
  try { window.localStorage.setItem(key, JSON.stringify(value)); } catch { /* private browsing or quota limits: keep session state */ }
}

function localMatch(candidate: Candidate, job: Job): MatchEvidence {
  const canon = (value: string) => value.toLowerCase().replace(/[^a-z0-9]/g, "");
  const candidateSkills = candidate.skills.map(canon);
  const hit = (skill: string) => { const wanted = canon(skill); return candidateSkills.some(s => s === wanted || s.includes(wanted) || wanted.includes(s)); };
  const hits = job.required_skills.filter(hit); const preferred = job.preferred_skills.filter(hit);
  const mandatory = Math.round(hits.length / Math.max(job.required_skills.length, 1) * 100);
  const preferredScore = Math.round(preferred.length / Math.max(job.preferred_skills.length, 1) * 100);
  const overall = Math.round(mandatory * .55 + preferredScore * .15 + (candidate.years_experience >= 5 ? 100 : 60) * .15 + 70 * .15);
  return { candidate_id: candidate.id, job_id: job.id, overall, eligibility: mandatory >= 80 ? "PASS" : "PARTIAL", mandatory, preferred: preferredScore, confidence: mandatory >= 80 ? "High" : "Medium", evidence: [`${hits.length}/${job.required_skills.length} required skills found in resume`, `${preferred.length}/${job.preferred_skills.length} preferred skills found`], gaps: job.required_skills.filter(s => !hit(s)) };
}

function localMatches(jobs: Job[], candidates: Candidate[], jobId: string): MatchEvidence[] {
  const job = jobs.find(j => j.id === jobId); return job ? candidates.map(c => localMatch(c, job)).sort((a, b) => b.overall - a.overall) : [];
}

function viewSubtitle(view: string, job?: Job, candidate?: Candidate, hasWorkspaceData = false) {
  if (!hasWorkspaceData) return "No records have been uploaded yet. This view is ready for real data.";
  if (view === "AI Match") return `Analyzing candidates for ${job?.title ?? "selected job"}.`;
  if (view === "Candidates" || view === "Candidate 360") return `Reviewing ${candidate?.name ?? "candidate"} profile, freshness, and evidence.`;
  if (view === "AI Copilot") return "Use natural language to drive recruiting work.";
  if (view === "Interviews" || view === "Calendar") return "Schedule, request feedback, and manage interview operations.";
  return "Here is what needs your attention today.";
}

createRoot(document.getElementById("root")!).render(<Workspace />);
