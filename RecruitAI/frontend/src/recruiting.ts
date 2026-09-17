export type Person = { id: string; name: string; headline: string; location: string; skills: string[]; stage: string; resume_text?: string; [key: string]: unknown };
export type Role = { id: string; title: string; company: string; location: string; work_mode: string; status: string; required_skills: string[]; preferred_skills: string[]; description?: string; source?: string; source_url?: string; requirements_reviewed?: boolean; [key: string]: unknown };
export const stages = ['New', 'Screening', 'Interview', 'Offer', 'Hired', 'Rejected', 'Withdrawn'];
export type Application = { id: string; candidate_id: string; job_id: string; stage: string; updated_at: string; notes: string };
export type Meeting = { id: string; application_id: string; interviewer: string; starts_at: string; duration: number; location: string; status: string };
const aliases: Record<string, string> = { lightningwebcomponents: 'lwc', salesforcedx: 'sfdx', fieldservicelightning: 'fsl', javascript: 'javascript', amazonwebservices: 'aws', identityandaccessmanagement: 'iam', singlesignon: 'sso' };
export function canonical(value: string) { const key = value.toLowerCase().replace(/[^a-z0-9+#.]/g, ''); return aliases[key] || key; }
export function assess(person: Person, role: Role) {
  const requirements = [...new Set(role.required_skills.map(s => s.trim()).filter(Boolean))];
  const rows = requirements.map(skill => {
    const matched = person.skills.find(s => canonical(s) === canonical(skill));
    const terms = [skill, ...Object.keys(aliases).filter(k => aliases[k] === canonical(skill))];
    const excerpt = (person.resume_text || '').split(/\n|(?<=[.!?])\s/).find(line => terms.some(term => line.toLowerCase().includes(term.toLowerCase())));
    return { skill, matched: Boolean(matched), evidence: matched ? (excerpt || `Profile lists “${matched}”. Original resume evidence has not been verified.`) : 'Not evidenced in the saved profile. Confirm with the candidate.' };
  });
  const invalid = requirements.some(s => s.length > 60 || s.split(/\s+/).length > 7);
  const review = !requirements.length || invalid || role.requirements_reviewed === false;
  // Keep preliminary technology coverage separate from reviewed mandatory skills.
  const vocabulary = ['Salesforce','Apex','LWC','Lightning Web Components','Aura','SOQL','SOSL','REST','SOAP','MuleSoft','Service Cloud','Sales Cloud','Experience Cloud','DocuSign','JavaScript','TypeScript','Java','Python','SQL','C#','C++','AWS','Azure','Git','Copado','CI/CD','Agile','Scrum','OmniStudio','Salesforce Flow'];
  const text = [role.description || '', ...requirements].join(' ');
  const detected = vocabulary.filter(skill => new RegExp('(^|[^a-z0-9])' + skill.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '(?=$|[^a-z0-9])','i').test(text));
  const preliminarySkills = detected.filter((skill,index)=>detected.findIndex(s=>canonical(s)===canonical(skill))===index);
  const preliminaryMatched = preliminarySkills.filter(skill=>person.skills.some(s=>canonical(s)===canonical(skill)));
  const preliminaryScore = preliminarySkills.length ? Math.round(preliminaryMatched.length / preliminarySkills.length * 100) : null;
  return { rows, review, preliminaryScore, preliminarySkills, score: review ? null : Math.round(rows.filter(r => r.matched).length / rows.length * 100), gaps: rows.filter(r => !r.matched).map(r => r.skill) };
}
export function uniqueApplication(items: Application[], candidate: string, job: string) { return items.find(a => a.candidate_id === candidate && a.job_id === job); }
export function calendarFile(meeting: Meeting, person: Person, role: Role) {
  const stamp = (s: string) => new Date(s).toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '');
  const esc = (s: string) => s.replace(/\\/g, '\\\\').replace(/\r?\n/g, '\\n').replace(/[,;]/g, c => '\\' + c);
  return ['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//RecruitAI//Interviews//EN','BEGIN:VEVENT',`UID:${meeting.id}@recruitai.local`,`DTSTAMP:${stamp(new Date().toISOString())}`,`DTSTART:${stamp(meeting.starts_at)}`,`DTEND:${stamp(new Date(new Date(meeting.starts_at).getTime()+meeting.duration*60000).toISOString())}`,`SUMMARY:${esc(person.name + ' — ' + role.title)}`,`LOCATION:${esc(meeting.location)}`,`DESCRIPTION:${esc('Interviewer: ' + meeting.interviewer + '. Calendar draft only; invite participants in your calendar.')}`,'END:VEVENT','END:VCALENDAR'].join('\r\n');
}
