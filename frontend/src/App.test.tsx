import {render,screen,fireEvent} from '@testing-library/react';
import {describe,it,expect,vi} from 'vitest';
import {LockNotice,endpointLabel,mergeChartData} from './App';
import {api,ApiError} from './api';
import type {Forecast,Packet} from './types';
describe('consent lock',()=>{it('clearly blocks data and offers explicit restoration',()=>{const restore=vi.fn();render(<LockNotice restore={restore}/>);expect(screen.getByText('Demo access locked')).toBeInTheDocument();fireEvent.click(screen.getByRole('button',{name:'Restore demo access'}));expect(restore).toHaveBeenCalledOnce()})});
describe('API errors',()=>{it('preserves consent denial status',async()=>{vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,status:403,json:async()=>({detail:'Consent revoked'})}));await expect(api('/patients/a')).rejects.toEqual(new ApiError(403,'Consent revoked'));vi.unstubAllGlobals()})});
describe('showcase evidence helpers',()=>{
 const forecast=(flags:Forecast['event_flags']):Forecast=>({points:[],origin:'2026-10-01T00:00:00+05:30',state_version:1,unit:'mg/dL',model_version:'0.2.0-hybrid-gbr',data_age_minutes:0,event_flags:flags,event_probability:null,above_180_probability:null,below_70_probability:null,explanations:[],uncertainty:{status:'unavailable'}});
 it('states the selected primary endpoint without implying diagnosis',()=>{
  expect(endpointLabel(forecast({above_180:true,below_70:false}),60)).toBe('Hyperglycemia flag within 60 min');
  expect(endpointLabel(forecast({above_180:false,below_70:true}),60)).toBe('Hypoglycemia flag within 60 min');
  expect(endpointLabel(forecast({above_180:false,below_70:false}),60)).toBe('No threshold crossing within 60 min');
 });
 it('merges observed and forecast timestamps for a stable responsive chart',()=>{
  const history=[{timestamp:'2026-10-01T00:00:00+05:30',glucose:150,hr:70,hrv:40,eda:1,temperature:33,activity:1,carbs:0,index:0}] as Packet[];
  const points=[{timestamp:'2026-10-01T00:05:00+05:30',glucose:155,minute:5}];
  expect(mergeChartData(history,points)).toEqual([{timestamp:history[0].timestamp,observed:150},{timestamp:points[0].timestamp,predicted:155}]);
 });
});
