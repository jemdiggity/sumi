import fs from 'node:fs';
import vm from 'node:vm';
import {pathToFileURL} from 'node:url';
const {parseHTML}=await import(pathToFileURL(process.argv[2]));
const text=fs.readFileSync(process.argv[3],'utf8');
function assert(ok,message){if(!ok)throw Error(message)}
assert(!/^<<<<<<<|^>>>>>>>|^%%%%%%%/m.test(text),'Unresolved merge markers');
assert(/<body[\s>]/i.test(text)&&/<\/body>/i.test(text),'Complete body required');
const {window,document}=parseHTML(text);window.HTMLElement.prototype.focus=function(){};
const context=vm.createContext({window,document,console,URLSearchParams,location:{search:''},setTimeout,clearTimeout,requestAnimationFrame:f=>f()});
for(const script of document.querySelectorAll('script')){assert(!script.src&&!script.hasAttribute('src'),'App must remain self-contained');new vm.Script(script.textContent).runInContext(context,{timeout:2500})}
assert(document.querySelectorAll('[data-character]').length>=6,'Character roster missing');
assert(window.BebopScene?.get&&window.BebopScene?.set,'Scene capture/restore missing');
window.BebopScene.set({search:'zz-no-match',filter:'all',selectedCharacter:null});
assert([...document.querySelectorAll('[data-character]')].every(c=>c.hidden),'Search empty state broken');
window.BebopScene.set({search:'',filter:'all',selectedCharacter:'spike'});
assert(window.BebopScene.get().selectedCharacter==='spike','Character details cannot open');
assert(/spike/i.test(document.querySelector('#character-detail').textContent),'Detail content missing');
window.BebopScene.set({search:'',filter:'crew',selectedCharacter:null});
assert(document.querySelector('[data-character="vicious"]').hidden,'Crew filter broken');
window.BebopScene.set({search:'',filter:'all',selectedCharacter:null});
console.log('PASS: JavaScript initialization, roster, search, details, crew filter, scene restoration, no conflict markers');
