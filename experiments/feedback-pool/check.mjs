// DOM behavior checks; visual layout and native focus still need browser review.
import fs from 'node:fs';
import vm from 'node:vm';
import { pathToFileURL } from 'node:url';
const {parseHTML}=await import(pathToFileURL(process.argv[2]));
const html=fs.readFileSync(process.argv[3],'utf8');
const fixture=process.argv[4] || 'core';
function setup(){
 const {window,document}=parseHTML(html);
 Object.defineProperty(window.HTMLSelectElement.prototype,'value',{configurable:true,get(){return this.getAttribute('data-qa-value')||this.querySelector('option[selected]')?.getAttribute('value')||this.querySelector('option')?.getAttribute('value')||''},set(v){this.setAttribute('data-qa-value',v)}});
 let focused=null;window.HTMLElement.prototype.focus=function(){focused=this};
 Object.defineProperty(document,'activeElement',{configurable:true,get:()=>focused});
 const context=vm.createContext({window,document,console,setTimeout,clearTimeout,queueMicrotask});window.innerWidth=1200;
 for(const s of document.querySelectorAll('script'))new vm.Script(s.textContent).runInContext(context,{timeout:2000});
 const q=s=>document.querySelector(s);
 const fire=(el,type,props={})=>{if(!el)throw Error(`Missing element for ${type}`);const e=new window.Event(type,{bubbles:true,cancelable:true});Object.assign(e,props);el.dispatchEvent(e)};
 const click=s=>fire(typeof s==='string'?q(s):s,'click');
 const stages=stage=>{const e=new window.Event('openai:set_globals');e.detail={globals:{widgetState:{privateContent:{workspace:{stage,selected:0}}}}};window.dispatchEvent(e)};
 return {q,click,fire,document,stages};
}
const assert=(ok,msg)=>{if(!ok)throw Error(msg)};
function core(){const {q,click}=setup();assert(q('#sumi-tasks').querySelectorAll('[data-task]').length===3,'three initial tasks');click('[data-action="accept"]');assert(q('#sumi-detail').textContent.includes('Main has not changed'),'acceptance must not integrate');assert(q('[data-action="integrate"]'),'separate integration action');click('[data-action="integrate"]');assert(q('#sumi-tasks').textContent.includes('Blocked'),'dependent task remains blocked');click('[data-task="1"]');click('[data-action="answer"]');assert(q('[data-action="complete"]'),'decision resumes worker');}
function check(id){
 const {q,click,fire,document,stages}=setup();
 if(id==='F1'){const input=q('input[type="search"]')||q('input[type="text"]')||q('input:not([type])');assert(input,'search input');input.value='BROWSER';fire(input,'input');assert(q('#sumi-tasks').querySelectorAll('[data-task]').length===1,'case insensitive filter');assert(q('#sumi-detail h2').textContent.includes('Revision-bound'),'filter preserves selection');input.value='xyz-no-match';fire(input,'input');assert(!q('#sumi-tasks [data-task]'),'empty filter');assert(q('#sumi-tasks').textContent.trim()||[...document.querySelectorAll('.left *')].some(e=>!e.hidden&&/no tasks|no matches/i.test(e.textContent)),'empty feedback');input.value='';fire(input,'input');assert(q('#sumi-tasks').querySelectorAll('[data-task]').length===3,'clear filter');}
 if(id==='F2'){const tab=q('[data-tab="summary"]');tab.focus();fire(tab,'keydown',{key:'ArrowRight'});assert(q('[data-tab="diff"]').getAttribute('aria-pressed')==='true','right activates diff');assert(document.activeElement===q('[data-tab="diff"]'),'restores focus');fire(q('[data-tab="diff"]'),'keydown',{key:'ArrowLeft'});fire(q('[data-tab="summary"]'),'keydown',{key:'ArrowLeft'});assert(q('[data-tab="history"]').getAttribute('aria-pressed')==='true','wrap left to history');}
 if(id==='F3'){click('[data-tab="diff"]');const box=q('#sumi-detail input[type="checkbox"]');assert(box,'wrap checkbox');assert(box.checked||box.hasAttribute('checked'),'wrap defaults on');box.checked=false;box.removeAttribute('checked');fire(box,'change');click('[data-tab="summary"]');click('[data-tab="diff"]');const next=q('#sumi-detail input[type="checkbox"]');assert(!next.checked&&!next.hasAttribute('checked'),'wrap choice persists');}
 if(id==='F4'){click('[data-action="feedback"]');q('#sumi-feedback').value='  ';fire(q('#sumi-feedback'),'input');click('[data-action="revise"]');assert(q('#sumi-feedback'),'empty feedback not submitted');assert(q('[role="alert"]')||q('[aria-invalid="true"]'),'feedback accessible error');q('#sumi-feedback').value='Please improve this';fire(q('#sumi-feedback'),'input');click('[data-action="revise"]');assert(q('[data-action="complete"]'),'valid feedback resumes');click('[data-task="1"]');q('#sumi-answer').value=' ';fire(q('#sumi-answer'),'input');click('[data-action="answer"]');assert(q('#sumi-answer'),'empty answer not submitted');assert(q('[role="alert"]')||q('[aria-invalid="true"]'),'answer accessible error');}
 if(id==='F5'){let d=q('details.facts');assert(d&&!d.hasAttribute('open'),'starts closed');d.open=true;d.setAttribute('open','');fire(d,'toggle');click('[data-tab="diff"]');d=q('details.facts');assert(d.open||d.hasAttribute('open'),'details stay open');assert(!q('details.session-details').hasAttribute('open'),'session independent');}
 if(id==='F6'){stages(['running','running','blocked']);assert(/working/i.test(q('#sumi-attention').textContent),'working message');stages(['integrated','integrated','integrated']);assert(/all tasks integrated/i.test(q('#sumi-attention').textContent),'completed message');stages(['queued','queued','blocked']);assert(/no decisions waiting/i.test(q('#sumi-attention').textContent),'neutral message');}
}
const results=[];
for(const name of ['core',...(fixture==='all'?['F1','F2','F3','F4','F5','F6']:fixture==='core'?[]:[fixture])]){try{name==='core'?core():check(name);results.push({name,pass:true})}catch(e){results.push({name,pass:false,error:e.message})}}
console.log(JSON.stringify(results));process.exitCode=results.some(x=>!x.pass)?1:0;
