export class ApiError extends Error {constructor(public status:number,message:string){super(message)}}
export async function api<T>(path:string,body?:unknown):Promise<T>{
 const response=await fetch('/api/v1'+path,{method:body===undefined?'GET':'POST',headers:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(10000)});
 const data=await response.json();
 if(!response.ok)throw new ApiError(response.status,typeof data.detail==='string'?data.detail:'Invalid request. Check input ranges.');
 return data as T;
}
