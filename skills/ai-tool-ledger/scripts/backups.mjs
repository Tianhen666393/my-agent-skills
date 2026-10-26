import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';

const day = timestamp => new Intl.DateTimeFormat('sv-SE', {timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(timestamp));
const identity = filename => crypto.createHash('sha256').update(process.platform==='win32'?filename.toLowerCase():filename).digest('hex').slice(0,16);

export function backupLocations(filename){
 const absolute=path.resolve(filename),volume=path.parse(absolute).root;
 if(process.platform!=='win32'||!/^\w:\\$/.test(volume))throw Error('集中备份需要本地 Windows 盘符；当前路径不支持，请先明确该卷的备份与回收站位置');
 return {backups:path.join(volume,'.agent_backups'),trash:path.join(volume,'.agent_trash')};
}

export async function createBackup(filename,agent,reason,locations=backupLocations(filename),now=Date.now()){
 const original=await fs.realpath(filename);
 if(path.parse(original).root.toLowerCase()!==path.parse(locations.backups).root.toLowerCase())throw Error('禁止跨盘备份');
 const task='AI工具台账-'+identity(original);
 const parent=path.join(locations.backups,day(now),task);
 await fs.mkdir(parent,{recursive:true});
 const directory=await fs.mkdtemp(path.join(parent,'备份-'+now+'-'));
 const backupName=path.basename(original);
 const metadata={type:'ai-tool-ledger-backup',original,createdAt:new Date(now).toISOString(),agent,reason,backupName};
 await fs.copyFile(original,path.join(directory,backupName),fs.constants.COPYFILE_EXCL);
 await fs.writeFile(path.join(directory,'备份说明.md'),[
  '# AI 工具台账备份说明','',
  '- 原文件完整路径：'+original,
  '- 备份文件：'+backupName,
  '- 备份时间：'+metadata.createdAt+'（UTC；日期目录按北京时间）',
  '- 执行 Agent：'+agent,
  '- 备份原因：'+reason,
  '- 恢复方法：关闭占用台账的程序，先备份当前文件，经用户确认后将本目录中的备份文件复制回原路径。',
  '- 保留规则：下次成功登记后，备份时间超过 30 天的本台账备份连同说明移入同盘当天回收站；不物理删除。',''
 ].join('\n'),{encoding:'utf8',flag:'wx'});
 await fs.writeFile(path.join(directory,'backup.json'),JSON.stringify(metadata,null,2)+'\n',{encoding:'utf8',flag:'wx'});
 console.log('备份及说明：'+directory);
 return directory;
}

export async function archiveExpiredBackups(filename,locations=backupLocations(filename),now=Date.now()){
 const original=await fs.realpath(filename),task='AI工具台账-'+identity(original),moved=[];
 if(path.parse(original).root.toLowerCase()!==path.parse(locations.trash).root.toLowerCase())throw Error('禁止跨盘归档');
 const dates=await fs.readdir(locations.backups,{withFileTypes:true}).catch(error=>{if(error.code==='ENOENT')return [];throw error;});
 for(const dateEntry of dates){
  if(!dateEntry.isDirectory()||!/^\d{4}-\d{2}-\d{2}$/.test(dateEntry.name))continue;
  const parent=path.join(locations.backups,dateEntry.name,task);
  const parentInfo=await fs.lstat(parent).catch(error=>{if(error.code==='ENOENT')return null;throw error;});
  if(!parentInfo?.isDirectory()||parentInfo.isSymbolicLink())continue;
  for(const entry of await fs.readdir(parent,{withFileTypes:true})){
   if(!entry.isDirectory()||!entry.name.startsWith('备份-'))continue;
   const directory=path.join(parent,entry.name);
   let metadata;
   try{metadata=JSON.parse(await fs.readFile(path.join(directory,'backup.json'),'utf8'));}catch{continue;}
   const created=Date.parse(metadata.createdAt);
   if(metadata.type!=='ai-tool-ledger-backup'||metadata.original!==original||!Number.isFinite(created)||now-created<=30*86400000)continue;
   const contents=await fs.readdir(directory,{withFileTypes:true});
   const expected=[path.basename(original),'备份说明.md','backup.json'];
   if(metadata.backupName!==path.basename(original)||contents.length!==expected.length||contents.some(item=>!item.isFile()||!expected.includes(item.name)))continue;
   const trashParent=path.join(locations.trash,day(now),task);
   await fs.mkdir(trashParent,{recursive:true});
   const container=await fs.mkdtemp(path.join(trashParent,'过期备份-'));
   const target=path.join(container,entry.name);
   await fs.rename(directory,target);
   moved.push(target);
   console.log('超过 30 天的台账备份已移入回收站：'+target);
  }
 }
 return moved;
}
