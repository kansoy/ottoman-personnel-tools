"""Bind sparse model readings to exact native text and source pages."""
from __future__ import annotations
import copy,re
from . import contract as BASE

def ground(raw,unit,packet):
    lines=packet['lines'];index={str(x['id']):i for i,x in enumerate(lines)}
    money={str(x['id']):x for x in packet['money_anchors']}
    issues=[];used=[];evidence=[]
    def citation(ids,where):
        if not ids:issues.append(where+':missing_source_lines');return '',[]
        ids=[str(x) for x in ids];bad=[x for x in ids if x not in index]
        if bad:issues.append(where+':invalid_source_line');return '',[]
        lo,hi=min(index[x] for x in ids),max(index[x] for x in ids)
        ls=lines[lo:hi+1];return '\n'.join(x['text'] for x in ls),sorted({x['pdf_page'] for x in ls})
    candidate=copy.deepcopy(raw)
    for n,f in enumerate(candidate.get('facts',[])):
        f['quote'],f['pdf_pages']=citation(f.get('source_lines'),f'fact:{n}')
    # Keep the revised whole-biography decisions through schema normalization,
    # with the same immutable source-line/page binding as events and facts.
    birth=candidate.get('birth_resolution',{})
    if birth and (birth.get('year') is not None or birth.get('source_lines')):
        birth['quote'],birth['pdf_pages']=citation(birth.get('source_lines'),'birth_resolution')
        for lid in birth.get('supersedes_source_lines',[]):
            if str(lid) not in index:issues.append('birth_resolution:invalid_superseded_source_line')
    for field in ('internship_spells','service_spells'):
        for n,spell in enumerate(candidate.get(field,[])):
            spell['quote'],spell['pdf_pages']=citation(spell.get('source_lines'),f'{field}:{n}')
    for n,gap in enumerate(candidate.get('completeness_check',{}).get('unexplained_gaps',[])):
        gap['quote'],gap['pdf_pages']=citation(gap.get('source_lines'),f'unexplained_gap:{n}')
    for e in candidate.get('events',[]):
        no=e.get('event_no');tag=f'event:{no}'
        e['source_quote'],e['pdf_pages']=citation(e.get('source_lines'),tag)
        if e.get('context_lines'):e['context_quote']=citation(e['context_lines'],tag+':office_context')[0]
        for d in e.get('dates',[])+e.get('end_dates',[]):
            d['date_quote']=citation(d.get('source_lines'),tag+':date')[0]
            if d.get('context_lines'):d['context_quote']=citation(d['context_lines'],tag+':date_context')[0]
        for p in e.get('payments',[]):
            aid=p.get('pay_anchor_id')
            if aid:
                aid=str(aid);anchor=money.get(aid)
                if not anchor:issues.append(tag+':invalid_money_anchor');continue
                used.append(aid)
                for key in ('amount_literal','amount','currency_raw','subunit_amount_literal','subunit_amount','subunit_currency_raw'):
                    p[key]=anchor.get(key)
                p['reading_flags']=anchor.get('flags',[])
                p['basis']='direct' if anchor.get('amount') is not None else 'unclear'
                ids=p.get('source_lines') or anchor['line_ids']
                p['quote']=citation(ids,tag+':pay')[0]
                # Always include its actual amount line, even if model only
                # selected a continuation line describing the pay component.
                if not BASE.supported(anchor.get('amount_literal',''),p['quote']):
                    p['quote']=citation(list(dict.fromkeys(ids+anchor['line_ids'])),tag+':pay_anchor')[0]
            else:p['quote']=citation(p.get('source_lines'),tag+':pay')[0]
    excluded=[]
    for x in candidate.get('excluded_money',[]):
        aid=str(x.get('pay_anchor_id',''))
        if aid not in money:issues.append('invalid_excluded_money_anchor');continue
        used.append(aid)
        x['source_lines']=x.get('source_lines') or money[aid]['line_ids']
        q,pages=citation(x['source_lines'],'excluded:'+aid)
        x['quote']=q;x['pdf_pages']=pages
        excluded.append({'anchor_id':aid,'reason':x.get('reason',''),'quote':q,'pdf_pages':pages,'anchor':money[aid]})
    missing=sorted(set(money)-set(used));duplicates=sorted({x for x in used if used.count(x)>1})
    for aid in duplicates:
        literal=BASE.LITERAL.fold(money[aid].get('amount_literal',''))
        distributive=bool(re.search(r'birer|ikiser|ucer|dorder|beser|altisar|yediser|sekizer|dokuzar|onar|yirmiser|otuzar|kirkar|elliser',literal))
        if distributive:
            for e in candidate.get('events',[]):
                for p in e.get('payments',[]):
                    if p.get('pay_anchor_id')==aid:p['reuse_reason']='Source distributive amount applies separately to stated intervals; interval wording requires review.'
        else:issues.append('duplicated_money_requires_review:'+aid)
    issues.extend('unassigned_money:'+x for x in missing)
    parsed=BASE.normalize(candidate,BASE.SCHEMA)
    for e in parsed['events']:
        if not e['status']:e['status']='recorded'
        if not e['office_basis']:e['office_basis']='explicit' if e['office_raw'] else 'not_recorded'
        for d in e['dates']+e['end_dates']:
            # Keep abbreviated source labels out of full calendar-year fields.
            # The original sparse response and exact native lines remain intact;
            # no century is supplied even when a nearby year looks plausible.
            year=d['year']
            if (d['calendar'] in ('hijri','rumi') and isinstance(year,int)
                    and not isinstance(year,bool) and 0<=year<1000):
                d['year_abbreviated']=year;d['year']=None;d['year_basis']='unresolved'
            if not d['year_basis']:d['year_basis']='literal' if d['year'] is not None else 'unresolved'
        if not e['date_raw']:e['date_raw']=' | '.join(d['date_quote'] for d in e['dates'])
        for p in e['payments']:
            if not p['basis']:p['basis']='direct' if p['amount'] is not None else 'unclear'
    BASE.schema_check(parsed,BASE.SCHEMA)
    issues+=BASE.validate(parsed,unit)
    return parsed,sorted(set(issues)),{'money_anchor_count':len(money),'assigned_anchor_count':len(set(used)),'missing_money':missing,'duplicated_money':duplicates,'excluded_money':excluded,'source_lines':lines}

