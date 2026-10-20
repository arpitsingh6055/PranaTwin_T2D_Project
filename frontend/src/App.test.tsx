import {render,screen,fireEvent} from '@testing-library/react';
import {describe,it,expect,vi} from 'vitest';
import {LockNotice} from './App';
import {api,ApiError} from './api';
describe('consent lock',()=>{it('clearly blocks data and offers explicit restoration',()=>{const restore=vi.fn();render(<LockNotice restore={restore}/>);expect(screen.getByText('Demo access locked')).toBeInTheDocument();fireEvent.click(screen.getByRole('button',{name:'Restore demo access'}));expect(restore).toHaveBeenCalledOnce()})});
describe('API errors',()=>{it('preserves consent denial status',async()=>{vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,status:403,json:async()=>({detail:'Consent revoked'})}));await expect(api('/patients/a')).rejects.toEqual(new ApiError(403,'Consent revoked'));vi.unstubAllGlobals()})});
