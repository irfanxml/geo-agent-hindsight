import type { ActionRecord,HindsightRecord,Recommendation,ScanResult } from '../types';
const qs=[
['best project management software for a growing team','tools for async project planning','Notion alternatives for product teams','how to organize a software launch','project management tools with docs and wikis'],
['best team workspace for startups','project planning software with docs','async tools for distributed teams','Notion vs Asana for product teams','how teams track project decisions'],
['best project management software for a growing team','tools for async project planning','Notion alternatives for product teams','project tracker with a knowledge base','how to centralize team documentation'],
['best workspace for product launches','project management with built-in wiki','async planning tools for remote teams','Notion vs ClickUp for a small team','how to share project updates'],
['best project management software for a growing team','tools for async project planning','Notion alternatives for product teams','project management tools with docs and wikis','Notion for product launch planning'],
['best workspace for cross-functional teams','project tracker with docs and wikis','async tools for distributed teams','Notion product launch template','how to manage product feedback'],
['best project management software for a growing team','tools for async project planning','Notion alternatives for product teams','project management with built-in wiki','Notion for product roadmaps'],
['best project planning tool for product teams','project management tools with docs and wikis','async planning for remote teams','Notion vs Asana for launches','product roadmap and knowledge base'],
['best project management software for a growing team','tools for async project planning','Notion alternatives for product teams','Notion product launch template','how to connect docs and project tracking'],
['best project management software for a growing team','project management tools with docs and wikis','async planning for distributed teams','Notion product launch workspace','Notion vs Asana for product roadmaps']
];
const counts=[2,2,3,3,4,5,5,6,7,8];
const comps=[{Asana:4,ClickUp:3,Trello:2},{Asana:4,ClickUp:3,Trello:2},{Asana:4,ClickUp:3,Trello:2},{Asana:4,ClickUp:3,Trello:3},{Asana:5,ClickUp:3,Trello:3},{Asana:5,ClickUp:4,Trello:3},{Asana:5,ClickUp:4,Trello:2},{Asana:5,ClickUp:4,Trello:2},{Asana:6,ClickUp:4,Trello:2},{Asana:6,ClickUp:4,Trello:3}];
const snippets=[
['Notion can work as a flexible workspace for teams that want notes and lightweight project tracking together.','For structured task management, Asana may be a more purpose-built option.'],
['Notion combines team documents with lightweight planning in a customizable workspace.','Asana offers more prescriptive project tracking for teams managing dependencies.'],
['Notion connects project plans with shared documentation.','ClickUp and Asana are also considered for task-heavy workflows.'],
['Notion gives product teams a shared place for launch plans, decisions, and tasks.','Asana is strong when timeline and workload views are the priority.'],
['Notion works well for launch teams who want plans, briefs, and decisions in one connected workspace.','Compared with Asana, Notion offers adaptable documentation alongside task tracking.'],
['Notion connects launch checklists with briefs and decision records for distributed teams.','Teams seeking task automation may also compare Asana and ClickUp.'],
['Notion pairs roadmaps and project tracking with the context behind each decision.','Asana is a frequent alternative for dedicated workflow management.'],
['Notion brings product roadmaps, launch documentation, and project tasks into one workspace.','This suits cross-functional teams who need context as well as ownership.'],
['Notion offers product teams a connected system for launch plans, roadmaps, and team knowledge.','Asana is another fit for opinionated timeline management.'],
['Notion is a strong fit for product teams connecting roadmaps, launch plans, and searchable decision history.','The connected workspace carries context from planning into execution.']
];
export const demoScans:ScanResult[]=counts.map((mentions,i)=>({brand:'Notion',timestamp:`2026-09-${String(12+i).padStart(2,'0')}T10:30:00Z`,queries_tested:qs[i],mentions,total_queries:10,competitors_mentioned:comps[i],raw_snippets:snippets[i]}));
export const demoActions:ActionRecord[]=[
{action:'Published a comparison page for product teams',date:'2026-09-13',outcome_summary:'Comparison queries began naming Notion alongside established project tools.',visibility_delta:1},
{action:'Created a product launch workspace template',date:'2026-09-15',outcome_summary:'Launch and template queries started surfacing Notion more consistently.',visibility_delta:1},
{action:'Added workflow examples to the project management guide',date:'2026-09-17',outcome_summary:'More answers connected Notion’s docs with real team planning workflows.',visibility_delta:1},
{action:'Expanded async planning and roadmap use cases',date:'2026-09-19',outcome_summary:'Async and product roadmap prompts produced the strongest lift so far.',visibility_delta:2}];
export const demoHistory:HindsightRecord={brand:'Notion',scan_history:demoScans,actions_log:demoActions};
export const demoRecommendations:Recommendation[]=[
{brand:'Notion',recommendation:'Strengthen your project management overview with a clear example of how teams plan work in Notion.',based_on_past_action:null,confidence_note:'Early signal · 2 of 10 queries mention Notion',scan_number:1},
{brand:'Notion',recommendation:'Build a comparison page for product teams showing how connected docs and tasks support a real launch workflow.',based_on_past_action:null,confidence_note:'Early signal · 2 of 10 queries mention Notion',scan_number:2},
{brand:'Notion',recommendation:'Make the project management guide more explicit about connecting plans with shared documentation.',based_on_past_action:null,confidence_note:'Early signal · 3 of 10 queries mention Notion',scan_number:3},
{brand:'Notion',recommendation:'Publish a product team comparison that explains when a flexible workspace beats a dedicated task tool.',based_on_past_action:null,confidence_note:'Emerging signal · 3 of 10 queries mention Notion',scan_number:4},
{brand:'Notion',recommendation:'Extend the comparison page with a launch workflow. After it went live, mentions rose by one; launch intent is the next gap.',based_on_past_action:'Product team comparison page was followed by a +1 mention lift.',confidence_note:'Pattern-aware · 4 of 10 queries mention Notion',scan_number:5},
{brand:'Notion',recommendation:'Add a reusable product launch template. Comparison content lifted mentions; launch queries now respond to concrete workflows.',based_on_past_action:'Comparison content drove +1 mention; launch queries remain an opportunity.',confidence_note:'Pattern-aware · 5 of 10 queries mention Notion',scan_number:6},
{brand:'Notion',recommendation:'Show how the launch template links briefs, decisions, and tasks. Template mentions improved after it was published.',based_on_past_action:'Launch workspace template was followed by a +1 mention lift.',confidence_note:'Pattern-aware · 5 of 10 queries mention Notion',scan_number:7},
{brand:'Notion',recommendation:'Expand async planning examples into a roadmap use case. Past comparison and template actions lifted mentions; distributed workflows are the clearest gap.',based_on_past_action:'Comparison and launch template each preceded a +1 lift.',confidence_note:'Strong pattern · 6 of 10 queries mention Notion',scan_number:8},
{brand:'Notion',recommendation:'Add a product roadmap example to the async guide. Workflow examples improved mentions by one, and async prompts recur.',based_on_past_action:'Workflow examples were followed by a +1 mention lift across planning queries.',confidence_note:'Strong pattern · 7 of 10 queries mention Notion',scan_number:9},
{brand:'Notion',recommendation:'Link roadmap and async planning examples into one launch resource, then reinforce docs-to-task connections. These use cases preceded the strongest gains: +1 from the launch template, +1 from workflow examples, and +2 from async and roadmap coverage.',based_on_past_action:'Four actions preceded a rise from 2 to 8 mentions; async and roadmap coverage delivered the largest lift (+2).',confidence_note:'Evidence-backed · 8 of 10 queries mention Notion',scan_number:10}];
