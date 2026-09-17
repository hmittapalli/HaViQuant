import test from 'node:test';
import assert from 'node:assert/strict';
import { assess, uniqueApplication, calendarFile } from '../src/recruiting.ts';
const person={id:'p',name:'Test Candidate',headline:'Developer',location:'',stage:'New',skills:['JavaScript','Lightning Web Components','C#']};
const role={id:'j',title:'Developer',company:'Test',location:'',work_mode:'',status:'Open',required_skills:['Java','LWC','C++'],preferred_skills:[],requirements_reviewed:true};
test('aliases match but substrings and distinct languages do not',()=>{const r=assess(person,role);assert.equal(r.score,33);assert.deepEqual(r.gaps,['Java','C++']);});
test('empty, unreviewed and prose requirements never get a score',()=>{assert.equal(assess(person,{...role,required_skills:[]}).score,null);assert.equal(assess(person,{...role,requirements_reviewed:false}).score,null);assert.equal(assess(person,{...role,required_skills:['Responsible for leading the delivery of many enterprise applications and other responsibilities']}).score,null);});
test('mapping identity is the candidate-job pair',()=>{const items=[{id:'a',candidate_id:'p',job_id:'j',stage:'New'}];assert.equal(uniqueApplication(items,'p','j').id,'a');assert.equal(uniqueApplication(items,'p','other'),undefined);});
test('calendar exports correct UTC duration and escapes user text',()=>{const text=calendarFile({id:'m',starts_at:'2026-09-15T19:00:00Z',duration:60,interviewer:'Alex',location:'Room, 1; desk'},person,role);assert.ok(text.includes('DTSTART:20260915T190000Z'));assert.ok(text.includes('DTEND:20260915T200000Z'));assert.ok(text.includes('LOCATION:Room\\, 1\\; desk'));assert.ok(!text.includes('ATTENDEE'));});
