export type ScanResult = { brand:string; timestamp:string; queries_tested:string[]; mentions:number; total_queries:number; competitors_mentioned:Record<string,number>; raw_snippets:string[] };
export type ActionRecord = { action:string; date:string; outcome_summary:string; visibility_delta:number };
export type HindsightRecord = { brand:string; scan_history:ScanResult[]; actions_log:ActionRecord[] };
export type Recommendation = { brand:string; recommendation:string; based_on_past_action:string|null; confidence_note:string; scan_number:number };
export type PipelineResult = { scan:ScanResult; recommendation:Recommendation; memory:HindsightRecord; memory_write:{ok:boolean;scan_number:number;storage?:string} };
export type BrandDashboard = { history:HindsightRecord; scan:ScanResult|null; recommendation:Recommendation|null };
export type ApiHealth = { status:'ok'; mode:'mock'|'live'; ready:boolean; missing_keys:string[] };
