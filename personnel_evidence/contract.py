"""Sparse-output schema and mechanical source checks. These are not historical adjudication."""
from __future__ import annotations
import json,re,unicodedata
from pathlib import Path
from . import literals as LITERAL
SCHEMA=json.loads(Path(__file__).with_name("schema.json").read_text())

def normalize(value,schema):
    typ=schema['type'];types=typ if isinstance(typ,list) else [typ]
    if value is None:
        if 'null' in types:return None
        if 'object' in types:value={}
        elif 'array' in types:return []
        elif 'string' in types:return ''
    if isinstance(value,dict) and 'object' in types:
        return {k:normalize(value.get(k),s) for k,s in schema['properties'].items()}
    if isinstance(value,list) and 'array' in types:return [normalize(x,schema['items']) for x in value]
    return value

def schema_check(value,schema):
    types=schema['type'];types=types if isinstance(types,list) else [types]
    actual=('null' if value is None else 'boolean' if isinstance(value,bool) else 'integer' if isinstance(value,int) else 'number' if isinstance(value,float) else 'string' if isinstance(value,str) else 'array' if isinstance(value,list) else 'object' if isinstance(value,dict) else 'unknown')
    if actual not in types and not(actual=='integer' and 'number' in types):raise ValueError('schema_type_mismatch')
    if 'enum' in schema and value not in schema['enum']:raise ValueError('schema_enum_mismatch')
    if actual=='object':
        if set(value)!=set(schema['required']):raise ValueError('schema_keys_mismatch')
        for k,v in value.items():schema_check(v,schema['properties'][k])
    if actual=='array':
        for v in value:schema_check(v,schema['items'])

def canonical(s):
    return re.sub(r'\s+',' ',unicodedata.normalize('NFC',str(s))).strip()
def source_text(unit):return '\n'.join(x['text_raw'] for x in unit['body_segments'])
def supported(q,text):return bool(q) and canonical(q) in canonical(text)

def explicit_calendar_years(text):
    """Only adjacent, explicit native calendar labels bind a year here.

    Month names, chronology, plausible centuries and different paired year
    numbers do not establish a mismatch. Return evidence, never corrected dates.
    """
    text=LITERAL.fold(re.sub(r'\[(\d{1,2})\](\d{2,3})',r' \1\2 ',text))
    result={}
    labels={
        'hijri':(r'(?:\bhicri\w*|\bh\.)\s*[:(]?\s*$',
                 r'^[\s,()]*sene[\s-]*i\s+hicri\w*'),
        'rumi':(r'(?:\bsene[\s-]*i\s+mali(?:ye\w*)?\b|\brumi|\br\.)\s*[:(]?\s*$',
                r'^[\s,()]*sene[\s-]*i\s+mali(?:ye\w*)?\b'),
        'gregorian':(r'\bmiladi\w*\s*[:(]?\s*$',
                     r'^[\s,()]*sene[\s-]*i\s+miladi\w*')}
    for value,start,end,_ in LITERAL.number_runs(text):
        if not isinstance(value,int) or not 1000<=value<=2100:continue
        prefix=text[max(0,start-45):start];suffix=text[end:end+45]
        for calendar,(before,after) in labels.items():
            if re.search(before,prefix) or re.search(after,suffix):
                result.setdefault(value,set()).add(calendar)
    return result
def money_number(literal):
    text=LITERAL.fold(literal)
    text=re.sub(r'\s*(?:gurus|kurus|lira|para|santim)\s*$','',text)
    distributives={'birer':'bir','ikiser':'iki','ucer':'uc','dorder':'dort','beser':'bes','altisar':'alti','yediser':'yedi','sekizer':'sekiz','dokuzar':'dokuz','onar':'on','yirmiser':'yirmi','otuzar':'otuz','kirkar':'kirk','elliser':'elli','altmisar':'altmis','yetmiser':'yetmis','seksener':'seksen','doksanar':'doksan','yuzer':'yuz','biner':'bin'}
    for word,value in distributives.items():text=re.sub(r'\b'+word+r'\b',value,text)
    text=re.sub(r'\bbine\s*$','bin',text)
    return LITERAL.numeric_literal(text)
def atomic(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');tmp.replace(path)

def cited_quote(q,claimed_pages,unit):
    """A quotation must occur on the claimed page(s), including continuations."""
    if not q or not claimed_pages:return False
    bits=[];spans=[];offset=0
    for segment in unit['body_segments']:
        bit=canonical(segment['text_raw']);bits.append(bit)
        spans.append((offset,offset+len(bit),segment['pdf_page']));offset+=len(bit)+1
    text=' '.join(bits);q=canonical(q);start=0
    while True:
        found=text.find(q,start)
        if found<0:return False
        pages={p for lo,hi,p in spans if lo<found+len(q) and hi>found}
        if pages<=set(claimed_pages):return True
        start=found+1

def validate(parsed,unit):
    errors=[];text=source_text(unit)
    pages={s['pdf_page'] for s in unit['body_segments']}
    if parsed.get('person_key')!=unit['person_key']:errors.append('wrong_person_key')
    facts=parsed.get('facts',[]);events=parsed.get('events',[])
    if not events:errors.append('no_events')
    seen=set();earlier={}
    for n,f in enumerate(facts):
        if not cited_quote(f.get('quote'),f.get('pdf_pages'),unit):errors.append(f'fact:{n}:quote_page_mismatch')
        if not set(f.get('pdf_pages',[]))<=pages:errors.append(f'fact:{n}:wrong_page')
    for e in events:
        n=e.get('event_no');tag=f'event:{n}'
        if n in seen:errors.append(tag+':duplicate_number')
        if not cited_quote(e.get('source_quote'),e.get('pdf_pages'),unit):errors.append(tag+':quote_page_mismatch')
        if e.get('context_quote') and not supported(e['context_quote'],text):errors.append(tag+':context_not_in_entry')
        if not set(e.get('pdf_pages',[]))<=pages:errors.append(tag+':wrong_page')
        if e.get('office_basis')=='continued_narrative':
            ref=e.get('office_reference_event_no')
            if not e.get('context_quote'):errors.append(tag+':missing_office_context')
            if ref is not None and (ref not in earlier or ref>=n):errors.append(tag+':invalid_office_reference')
        for d in e.get('dates',[])+e.get('end_dates',[]):
            if not supported(d.get('date_quote'),text):errors.append(tag+':date_quote_not_in_entry')
            if d.get('month') is not None and not 1<=d['month']<=12:errors.append(tag+':invalid_month')
            if d.get('day') is not None and not 1<=d['day']<=31:errors.append(tag+':invalid_day')
            if d.get('context_quote') and not supported(d['context_quote'],text):errors.append(tag+':invalid_date_context')
            nums=[x[0] for x in LITERAL.number_runs(re.sub(r'\[(\d{1,2})\](\d{2,3})',r' \1\2 ',d.get('date_quote','')))]
            y=d.get('year');basis=d.get('year_basis')
            if d.get('calendar') in ('hijri','rumi'):
                if isinstance(y,int) and not isinstance(y,bool) and 0<=y<1000:
                    errors.append(tag+':abbreviated_year_requires_context')
                elif y is None and d.get('year_abbreviated') is not None:
                    errors.append(tag+':abbreviated_year_requires_context')
            bound=explicit_calendar_years(d.get('date_quote',''))
            if y in bound and d.get('calendar')!='unspecified' and d.get('calendar') not in bound[y]:
                errors.append(tag+':date_year_explicit_calendar_mismatch')
            if y is not None and basis in ('literal','editorial_expansion') and y not in nums:errors.append(tag+':date_year_not_literal')
            if y is not None and basis=='contextual':
                contextual_nums=nums+[x[0] for x in LITERAL.number_runs(re.sub(r'\[(\d{1,2})\](\d{2,3})',r' \1\2 ',d.get('context_quote','')))]
                if not any(x in contextual_nums for x in (y,y%1000,y%100)):errors.append(tag+':date_contextual_year_not_supported')
            if y is not None and basis=='relative':
                ref=d.get('reference_event_no')
                if not d.get('context_quote') or ref not in earlier or ref>=n:errors.append(tag+':missing_relative_date_basis')
            if y is not None and basis in ('malformed','unresolved'):errors.append(tag+':unresolved_year_given_numeric')
        for p in e.get('payments',[]):
            if not supported(p.get('quote'),text):errors.append(tag+':payment_quote_not_in_entry')
            if p.get('basis')=='direct' and not supported(p.get('amount_literal'),p.get('quote','')):errors.append(tag+':amount_literal_not_in_quote')
            if p.get('basis')=='direct' and p.get('amount') is not None and money_number(p.get('amount_literal',''))!=p['amount']:errors.append(tag+':amount_numeric_mismatch')
            if p.get('subunit_amount') is not None and money_number(p.get('subunit_amount_literal',''))!=p['subunit_amount']:errors.append(tag+':subunit_numeric_mismatch')
            if p.get('basis')=='explicit_reference':
                ref=p.get('reference_event_no');prior=earlier.get(ref)
                if not prior or ref>=n:errors.append(tag+':invalid_pay_reference')
                elif p.get('amount') is not None and not any(x.get('component')==p.get('component') and x.get('amount')==p['amount'] for x in prior.get('payments',[])):errors.append(tag+':referenced_component_amount_mismatch')
        seen.add(n);earlier[n]=e
    for n,x in enumerate(parsed.get('excluded_money',[])):
        if not cited_quote(x.get('quote'),x.get('pdf_pages'),unit):errors.append(f'excluded:{n}:quote_page_mismatch')
        if not set(x.get('pdf_pages',[]))<=pages:errors.append(f'excluded:{n}:wrong_page')
    # These are source-linked model decisions, not historical certification.
    birth=parsed.get('birth_resolution') or {}
    if birth.get('year') is not None and not cited_quote(birth.get('quote'),birth.get('pdf_pages'),unit):
        errors.append('birth_resolution:quote_page_mismatch')
    for field in ('internship_spells','service_spells'):
        for n,spell in enumerate(parsed.get(field,[])):
            tag=f'{field}:{n}'
            if not cited_quote(spell.get('quote'),spell.get('pdf_pages'),unit):
                errors.append(tag+':quote_page_mismatch')
            refs=[spell.get(k) for k in ('start_event_no','end_event_no','office_reference_event_no')]
            refs+=spell.get('pay_reference_event_nos',[])+spell.get('interruption_event_nos',[])
            if any(ref is not None and ref not in seen for ref in refs):
                errors.append(tag+':invalid_event_reference')
            duration=spell.get('duration_years')
            if duration is not None and duration<0:errors.append(tag+':negative_duration')
    # Coverage review is separate from exact quote support: a complete quotation
    # is not proof that every monetary fact/date was extracted correctly.
    return sorted(set(errors))

