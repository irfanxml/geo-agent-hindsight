import {demoHistory,demoRecommendations,demoScans} from '../data/demoData';
import type {ApiHealth,BrandDashboard,HindsightRecord,PipelineResult,Recommendation,ScanResult} from '../types';
// Demo selectors use staged milestones; the main scan button calls the local Python API.
export async function getScanResult(n=1):Promise<ScanResult>{await new Promise(r=>window.setTimeout(r,320));return demoScans[Math.max(0,Math.min(9,n-1))];}
export async function getHistory():Promise<HindsightRecord>{return demoHistory;}
export async function getRecommendation(n=1):Promise<Recommendation>{return demoRecommendations[Math.max(0,Math.min(9,n-1))];}

export async function runVisibilityScan(brand:string,category:string):Promise<PipelineResult>{
 const response=await fetch('/api/scan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({brand,category,num_queries:10})});
 if(!response.ok){let message=`Scan failed (${response.status}).`;try{const body=await response.json();message=body.detail??message;}catch{/* Keep the status message. */}throw new Error(message);}
 return response.json() as Promise<PipelineResult>;
}

export async function saveAction(brand:string,action:string,outcome_summary:string,visibility_delta:number):Promise<HindsightRecord>{
 const response=await fetch('/api/action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({brand,action,outcome_summary,visibility_delta})});
 if(!response.ok){let message=`Could not save action (${response.status}).`;try{const body=await response.json();message=body.detail??message;}catch{/* Keep the status message. */}throw new Error(message);}
 const result=await response.json() as {history:HindsightRecord};
 return result.history;
}

export async function getBrandDashboard(brand:string):Promise<BrandDashboard>{
 const response=await fetch(`/api/dashboard/${encodeURIComponent(brand)}`);
 if(!response.ok)throw new Error(`Could not load saved dashboard (${response.status}).`);
 return response.json() as Promise<BrandDashboard>;
}

export async function getApiHealth():Promise<ApiHealth>{
 const response=await fetch('/api/health');
 if(!response.ok)throw new Error(`API health check failed (${response.status}).`);
 return response.json() as Promise<ApiHealth>;
}
