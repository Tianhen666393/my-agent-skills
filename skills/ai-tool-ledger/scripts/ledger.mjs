import fs from 'node:fs/promises';
import { existsSync } from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
import os from 'node:os';
import {execFileSync} from 'node:child_process';
import {createBackup,archiveExpiredBackups} from './backups.mjs';

const args=process.argv.slice(2), command=args.shift();
const opt=k=>{const i=args.indexOf('--'+k);return i<0?undefined:args[i+1];};
const agent=opt('agent');
if(!agent||/[\\/:*?\[\]]/.test(agent)||agent.length>29||!['inspect','check','init','upsert','remove','migrate','redesign','consolidate'].includes(command)) {
  throw Error('命令：inspect/check/init/upsert/remove/migrate/redesign/consolidate --agent 当前应用（有效 Excel 工作表名）');
}

function documentsDirectory(){
 if(process.platform==='win32'){
  const documents=execFileSync('powershell.exe',['-NoProfile','-NonInteractive','-Command',"[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; [Environment]::GetFolderPath('MyDocuments')"],{encoding:'utf8',windowsHide:true}).trim();
  if(!documents)throw Error('无法解析当前用户文档目录，请传 --workbook');
  return documents;
 }
 if(process.platform==='linux'){
  try{const documents=execFileSync('xdg-user-dir',['DOCUMENTS'],{encoding:'utf8'}).trim();if(path.isAbsolute(documents))return documents;}catch{}
 }
 return path.join(os.homedir(),'Documents');
}

function agentSkillRuntimeDir(agentName){
 const h=os.homedir();
 if(agentName==='Antigravity') return path.join(h,'.gemini','config','skills');
 if(agentName==='Codex') return path.join(h,'.codex','skills');
 if(agentName==='Claude') return path.join(h,'.claude','skills');
 if(agentName==='DeepSeekHarness') return path.join(h,'.deepseek','skills');
 return null;
}

function mergeApps(existingApps, agentName, statusTag){
 const parts = String(existingApps || '')
  .split(/[；;]/)
  .map(s => s.trim())
  .filter(Boolean)
  .filter(s => !s.includes('其他应用未核实') && !s.includes('其他应用未检查'));
 const newPart = `${agentName} (${statusTag})`;
 const otherParts = parts.filter(p => !p.startsWith(agentName));
 return [...otherParts, newPart].join('；');
}

function defaultWorkbookPath(){
 const docs = documentsDirectory();
 const preferred = path.join(docs, 'my-pc-ledger', 'AI工具安装清单.xlsx');
 const legacy = path.join(docs, 'AI工具台账', 'AI工具安装清单.xlsx');
 return existsSync(preferred) ? preferred : (existsSync(legacy) ? legacy : preferred);
}

const file=path.resolve(opt('workbook')||defaultWorkbookPath());
const root=opt('dependency-root')||process.env.AI_TOOL_LEDGER_DEPENDENCY_ROOT;
const require=root?createRequire(path.join(path.resolve(root),'__ledger__.cjs')):createRequire(import.meta.url);
let Workbook,SpreadsheetFile,FileBlob;
try{({Workbook,SpreadsheetFile,FileBlob}=require('@oai/artifact-tool'));}catch{throw Error('缺少 @oai/artifact-tool；请使用当前应用已有依赖，通过 --dependency-root 或 AI_TOOL_LEDGER_DEPENDENCY_ROOT 指向 node_modules。不会自动安装或扫描其他应用。');}

const legacyFields=['kind','name','purpose','version','status','path','source','check','checkedAt','notes'];
const legacyHeaders=['类别','名称','用途说明','版本','当前状态','绝对地址','来源 / 范围','路径核实','核实日期','安装备注'];
const fields=['name','purpose','apps','status','kind','version','path','source','check','checkedAt','notes'];
const headers=['名称','用途说明','适用应用 / 核实范围','当前状态','类别','版本','绝对地址','来源 / 范围','路径核实','核实日期','安装备注'];
const defaults=['共用Skill与插件','Codex自带','Claude自带','DeepSeekHarness自带','共用工具'];

const isSharedSheet = s => s === '共用Skill与插件' || s === '共用工具';
const isOwnSheet = s => s === agent + '自带';
const allowed = s => isOwnSheet(s) || isSharedSheet(s);
const own = e => allowed(e.sheet);
const norm = p => path.resolve(p).toLowerCase();
const date = () => new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
const exists = async p => !!(await fs.stat(p).catch(()=>null));

let lock;
if(args.includes('--apply')){
 await fs.mkdir(path.dirname(file),{recursive:true});
 lock=await fs.open(file+'.lock','wx').catch(error=>{throw Error(error.code==='EEXIST'?'台账正在写入或留有锁文件，请核实写入进程后处理：'+file+'.lock':error.message);});
}

async function run(){
try{
async function verify(e, strict=false){
 if(!path.isAbsolute(e.path||'')) throw Error('必须提供绝对路径：'+e.name);
 if(!await exists(e.path)){if(strict)throw Error('路径不存在：'+e.path);return '路径不存在，保留历史记录';}
 if(e.kind==='Skill'){
  const p=path.extname(e.path).toLowerCase()==='.md'?e.path:path.join(e.path,'SKILL.md');
  const text=await fs.readFile(p,'utf8').catch(()=>null);
  if(!text){if(strict)throw Error('缺少 SKILL.md：'+e.name);return '目录存在，缺少技能入口';}
  const m=text.match(/^name:\s*["']?([^\r\n"']+)/m);
  if(!m||m[1].trim().toLowerCase()!==e.name.toLowerCase())throw Error('skill 身份冲突：'+e.name+' / '+m?.[1]);
  if(e.sheet==='共用Skill与插件'){
   const runtimeBase=agentSkillRuntimeDir(agent);
   if(runtimeBase){
    const runtimePath=path.join(runtimeBase,e.name,'SKILL.md');
    const runtimeExists=await exists(runtimePath);
    return runtimeExists
     ? `已核实源码；当前应用(${agent})已同步生效`
     : `已核实源码；当前应用(${agent})未同步`;
   }
  }
  return '已核实 SKILL.md 身份；未执行技能';
 }
 if(e.kind==='插件'){
  for(const rel of ['.codex-plugin/plugin.json','.claude-plugin/plugin.json','plugin.json']){
   const p=path.join(e.path,rel);if(!await exists(p))continue;
   const data=JSON.parse(await fs.readFile(p,'utf8'));
   if(data.name!==e.name)throw Error('插件身份冲突：'+e.name);
   return '已核实插件清单身份；未测试功能';
  }
  if(strict)throw Error('插件缺少可核实清单：'+e.name);
  return '目录存在，未核实插件身份';
 }
 const packageFile=path.join(e.path,'package.json');
 if(await exists(packageFile)){
  const data=JSON.parse(await fs.readFile(packageFile,'utf8'));
  const expected=e.name.toLowerCase(),actual=(data.name||'').toLowerCase();
  if(actual!==expected&&!actual.endsWith('/'+expected))throw Error('工具包身份冲突：'+e.name+' / '+data.name);
  return '已核实 package.json：'+data.name+'；未测试功能';
 }
 const venvPackages={ReportLab:'reportlab','Agent Reach':'agent_reach','CLIP 图像识别环境（网盘整理专用）':'open_clip'};
 if(venvPackages[e.name]){
  const location=path.join(e.path,'Lib/site-packages'), dirs=await fs.readdir(location).catch(()=>[]);
  const packageName=venvPackages[e.name];
  const candidate=dirs.find(n=>n.toLowerCase().startsWith(packageName.toLowerCase()+'-')&&n.endsWith('.dist-info'));
  if(candidate){const metadata=await fs.readFile(path.join(location,candidate,'METADATA'),'utf8');const match=metadata.match(/^Name:\s*(.+)$/m);if(match)return '已核实包元数据：'+match[1].trim()+'；未测试功能';}
  if(strict)throw Error('环境存在但缺少目标包：'+e.name);
  return '环境目录存在，目标包未核实';
 }
 return (await fs.stat(e.path)).isFile()?'文件存在；未测试功能':'目录存在；具体包和功能需单独核实';
}

let records=[], names=[...defaults], wb;
if(await exists(file)){
 if(command==='init'){console.log('台账已存在，保留原文件：'+file);return;}
 wb=await SpreadsheetFile.importXlsx(await FileBlob.load(file));
 const info=await wb.inspect({kind:'sheet',include:'id,name',maxChars:20000});
 const sheets=info.ndjson.split('\n').filter(Boolean).map(x=>JSON.parse(x)).filter(x=>x.name);
 names=sheets.map(meta=>meta.name);
 if(command==='inspect'){
  console.log(info.ndjson);
  if(opt('preview-dir')){await fs.mkdir(opt('preview-dir'),{recursive:true});for(const meta of sheets){const s=wb.worksheets.getItem(meta.name),n=Math.min(7,s.getUsedRange().values.length);const blob=await wb.render({sheetName:meta.name,range:'A1:K'+n,scale:1,format:'png'});await fs.writeFile(path.join(opt('preview-dir'),meta.name+'.png'),new Uint8Array(await blob.arrayBuffer()));}}
  return;
 }
 for(const meta of sheets){
  const s=wb.worksheets.getItem(meta.name), values=s.getUsedRange().values;
  if(command==='migrate')continue;
  const legacy=JSON.stringify(values[2]?.slice(0,10))===JSON.stringify(legacyHeaders);
  if(!defaults.includes(meta.name)&&!meta.name.endsWith('自带')&&!(command==='redesign'&&/^(Codex|Claude|DeepSeekHarness)自行安装$/.test(meta.name)))throw Error('额外工作表，需要先审查：'+meta.name);
  if(legacy&&command!=='redesign')throw Error('旧版字段，需要经授权运行 redesign');
  const readFields=legacy?legacyFields:fields;
  if(!legacy&&JSON.stringify(values[2]?.slice(0,11))!==JSON.stringify(headers))throw Error('字段不符，停止以免丢失数据');
  if(values.some(r=>r.length>readFields.length&&r.slice(readFields.length).some(Boolean)))throw Error('存在额外字段');
  if(s.getUsedRange().formulas.some(r=>r.some(v=>v)))throw Error('存在公式，停止以免丢失');
  for(const row of values.slice(3)){
   if(!row[legacy?1:0])continue;
   const e={sheet:meta.name,...Object.fromEntries(readFields.map((k,i)=>[k,row[i]??'']))};
   if(legacy){
    const owner=meta.name.replace(/自带$|自行安装$/,'');
    e.apps=(meta.name==='共用工具'?agent:owner)+'；入口已登记，功能未测试';
    if(meta.name.endsWith('自行安装')){
     if(owner!==agent)throw Error('不得代其他 Agent 迁移自行安装记录：'+meta.name);
     e.sheet=['Skill','插件'].includes(e.kind)?'共用Skill与插件':'共用工具';
     e.apps=owner+'；其他应用未核实';
    }
   }
   records.push(e);
  }
 }
}

if(!await exists(file)&&['inspect','check','remove','redesign','migrate','consolidate'].includes(command))throw Error('台账不存在，请经授权使用 init --apply 或 upsert --apply 创建：'+file);

if(command==='check'){
 for(const e of records.filter(own))console.log(JSON.stringify({sheet:e.sheet,name:e.name,path:e.path,result:await verify(e)},null,0));
 return;
}

if(command==='consolidate'){
 const shared = records.filter(r => r.sheet === '共用Skill与插件');
 const otherRecords = records.filter(r => r.sheet !== '共用Skill与插件');
 const groups = new Map();
 for(const r of shared){
  const key = (r.name||'').trim().toLowerCase();
  if(!groups.has(key)) groups.set(key, []);
  groups.get(key).push(r);
 }
 const consolidated = [];
 const docsDir = documentsDirectory();
 const mySkillsBase = path.join(docsDir, 'my-agent-skills', 'skills');
 const ccSkillsBase = path.join(os.homedir(), '.cc-switch', 'skills');

 for(const [key, rows] of groups){
  const primary = rows[0];
  const name = primary.name;
  let canonicalPath = primary.path;
  const personalCandidate = path.join(mySkillsBase, name);
  const ccCandidate = path.join(ccSkillsBase, name);
  if(await exists(path.join(personalCandidate, 'SKILL.md'))){
   canonicalPath = personalCandidate;
  } else if(await exists(path.join(ccCandidate, 'SKILL.md'))){
   canonicalPath = ccCandidate;
  }

  const appStatuses = [];
  for(const candidateAgent of ['Codex', 'Antigravity', 'Claude', 'DeepSeekHarness']){
   const rBase = agentSkillRuntimeDir(candidateAgent);
   if(rBase && await exists(path.join(rBase, name, 'SKILL.md'))){
    appStatuses.push(`${candidateAgent} (已同步生效)`);
   } else if(rows.some(r => String(r.apps||'').includes(candidateAgent))){
    const matchRow = rows.find(r => String(r.apps||'').includes(candidateAgent));
    if(matchRow && String(matchRow.apps).includes('未核实')){
     appStatuses.push(`${candidateAgent} (仅核验共用源，分发未核实)`);
    }
   }
  }
  if(appStatuses.length === 0){
   appStatuses.push(agent + ' (已同步生效)');
  }
  const mergedAppsStr = appStatuses.join('；');
  const mergedNotes = rows.map(r => r.notes).filter(Boolean).filter((v,i,a)=>a.indexOf(v)===i).join('\n');
  const isPersonal = canonicalPath.toLowerCase().includes('my-agent-skills');
  const source = isPersonal ? '个人技能仓库 (Tianhen666393/my-agent-skills)' : '共用';

  const entry = {
   ...primary,
   path: canonicalPath,
   apps: mergedAppsStr,
   source,
   status: '已核实源码；多应用已分发同步',
   notes: mergedNotes,
   checkedAt: date()
  };
  entry.check = await verify(entry);
  consolidated.push(entry);
 }
 records = [...consolidated, ...otherRecords];
 console.log(JSON.stringify({command,apply:args.includes('--apply'),originalShared:shared.length,consolidatedShared:consolidated.length,total:records.length}));
 if(!args.includes('--apply')) return;
} else {
 const request=['redesign','init'].includes(command)?{entries:[]}:JSON.parse((await fs.readFile(opt('request'),'utf8')).replace(/^\uFEFF/,''));
 if(!Array.isArray(request.entries))throw Error('请求需要 entries 数组');
 if(command==='migrate'&&!(args.includes('--allow-migration')))throw Error('迁移需要 --allow-migration 及用户授权');
 for(const input of request.entries){
  const e={...input};
  if(!e.name||!e.kind||!e.purpose?.trim())throw Error('名称、类别和用途说明不能为空');
  if(!names.includes(e.sheet))names.push(e.sheet);
  
  if(e.sheet==='共用Skill与插件'){
   const index=records.findIndex(r=>r.sheet===e.sheet&&r.kind===e.kind&&r.name.toLowerCase()===e.name.toLowerCase());
   e.apps = index>=0 ? mergeApps(records[index].apps, agent, '已同步生效') : (e.apps || `${agent} (已同步生效)`);
   e.check = await verify(e, !e.historical);
   e.checkedAt = date();
   e.version ||= '未提供';
   if(command==='remove'){
    if(index<0)throw Error('找不到精确记录：'+e.name);
    if(await exists(e.path))throw Error('组件路径仍存在，不能视为卸载成功');
    records.splice(index,1);continue;
   }
   if(index>=0){
    const old=records[index];
    e.notes=[old.notes,e.notes,e.previousPath?'历史地址：'+e.previousPath:''].filter(Boolean).filter((v,i,a)=>a.indexOf(v)===i).join('\n');
    records[index]={...old,...e};
   } else {
    records.push(e);
   }
  } else {
   e.apps ||= agent+'；其他应用未核实';
   if(!own(e))throw Error('拒绝跨 Agent 登记：'+e.sheet);
   const keyPath=e.previousPath||e.path;
   const index=records.findIndex(r=>r.sheet===e.sheet&&r.kind===e.kind&&r.name.toLowerCase()===e.name.toLowerCase()&&norm(r.path)===norm(keyPath));
   if(index>=0&&records[index].sheet===agent+'自带'&&!isOwnSheet(records[index].sheet))throw Error('拒绝修改其他 Agent 的自带记录：'+e.name);
   if(command==='remove'){
    if(index<0)throw Error('找不到精确记录：'+e.name);
    if(await exists(e.path))throw Error('组件路径仍存在，不能视为卸载成功');
    records.splice(index,1);continue;
   }
   e.check=await verify(e,!e.historical);e.checkedAt=date();e.version ||= '未提供';
   if(index>=0){const old=records[index];e.notes=[old.notes,e.notes,e.previousPath?'历史地址：'+e.previousPath:''].filter(Boolean).filter((v,i,a)=>a.indexOf(v)===i).join('\n');records[index]={...old,...e};}
   else records.push(e);
  }
 }
 console.log(JSON.stringify({command,apply:args.includes('--apply'),total:records.length,sheets:Object.fromEntries(names.map(n=>[n,records.filter(r=>r.sheet===n).length]))}));
 if(!args.includes('--apply'))return;
}

wb=Workbook.create();
for(const [i,name] of names.entries()){
 const s=wb.worksheets.add(name),rows=records.filter(e=>e.sheet===name),end=Math.max(4,rows.length+3);
 s.showGridLines=false;
 s.getRange('A1:D1').merge();s.getRange('A1').values=[[name+'组件清单']];
 s.getRange('A2:D2').merge();s.getRange('A2').values=[['截至 '+date()+'；'+(rows.length?rows.length+' 条；共用表示单一真理源资产，各应用同步状态由对应 Agent 联合核验':'等待对应 agent 自检登记')]];
 s.getRange('A3:K3').values=[headers];
 if(rows.length)s.getRange('A4:K'+end).values=rows.map(e=>fields.map(k=>e[k]||''));
 const all=s.getRange('A1:K'+end);all.format.font={name:'Microsoft YaHei',size:11};all.format.verticalAlignment='center';all.format.wrapText=true;all.format.horizontalAlignment='left';
 s.getRange('A1:K1').format.rowHeight=32;s.getRange('A1').format.font={size:16,bold:true,color:'#17365D'};
 s.getRange('A2:K2').format.rowHeight=28;
 s.getRange('A3:K3').format.rowHeight=30;s.getRange('A3:K3').format.fill='#17365D';s.getRange('A3:K3').format.font={bold:true,color:'#FFFFFF'};s.getRange('A3:K3').format.horizontalAlignment='center';
 s.getRange('A4:K'+end).format.rowHeight=42;
 const widths=[30,64,36,34,12,20,80,30,48,16,90];
 widths.forEach((w,c)=>s.getRange(String.fromCharCode(65+c)+'1:'+String.fromCharCode(65+c)+end).format.columnWidth=w);
 const table=s.tables.add('A3:K'+end,true,'Ledger'+i);table.style='TableStyleLight9';table.showFilterButton=true;
 s.freezePanes.freezeRows(3);
 s.getRange('I4:I'+end).conditionalFormats.add('containsText',{text:'不存在',format:{fill:'#FCE4D6',font:{color:'#9C0006'}}});
}
wb.recalculate();
await fs.mkdir(path.dirname(file),{recursive:true});
if(await exists(file)){
 await createBackup(file,agent,'执行 '+command+' 前保存原台账，供本次修改回退');
}
const staging=path.join(path.dirname(file),'.ledger-'+crypto.randomBytes(5).toString('hex')+'.xlsx');
await (await SpreadsheetFile.exportXlsx(wb)).save(staging);
const reopened=await SpreadsheetFile.importXlsx(await FileBlob.load(staging));
let count=0;for(const name of names){const v=reopened.worksheets.getItem(name).getUsedRange().values;const rows=v.slice(3).filter(r=>r[0]);count+=rows.length;const expected=records.filter(e=>e.sheet===name).map(e=>fields.map(k=>e[k]||''));if(JSON.stringify(rows.map(row=>fields.map((_,index)=>row[index]||'')))!==JSON.stringify(expected))throw Error('回读字段不一致，原台账未覆盖：'+name);}
if(count!==records.length)throw Error('回读记录数不一致，原台账未覆盖');
await fs.rename(staging,file);
console.log('保存并回读验证成功：'+file);
if(['upsert','remove','migrate','redesign','consolidate'].includes(command)){
 try{await archiveExpiredBackups(file);}catch(error){console.error('台账已保存，但过期备份归档未完成：'+error.message);}
}
const inspectSidecar=staging+'.inspect.ndjson';
if(await exists(inspectSidecar)){
 const scratch=opt('preview-dir')||path.join(process.cwd(),'work');await fs.mkdir(scratch,{recursive:true});
 await fs.rename(inspectSidecar,path.join(scratch,path.basename(inspectSidecar)));
}
if(opt('preview-dir')){
 await fs.mkdir(opt('preview-dir'),{recursive:true});
 for(const name of names){const n=Math.min(7,Math.max(4,records.filter(r=>r.sheet===name).length+3));const blob=await wb.render({sheetName:name,range:'A1:D'+n,scale:1,format:'png'});await fs.writeFile(path.join(opt('preview-dir'),name+'.png'),new Uint8Array(await blob.arrayBuffer()));}
}
}finally{
 if(lock){await lock.close();await fs.unlink(file+'.lock');}
}
}
await run();
