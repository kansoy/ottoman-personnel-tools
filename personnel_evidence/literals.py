"""Literal numeric parsing for the independent personnel edition.

No astronomical date conversion, century completion, annual wage filling or
currency conversion occurs here. Every result retains a rule and status.
"""
from __future__ import annotations

import re
import unicodedata


def fold(text):
    text = str(text or '').replace('Ģ', 'ş').replace('ġ', 'ş').replace('Ġ', 'i')
    text = text.replace('ı', 'i').replace('İ', 'i').lower()
    text = ''.join(c for c in unicodedata.normalize('NFKD', text) if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', text).strip()


UNITS = {'sifir': 0, 'bir': 1, 'iki': 2, 'uc': 3, 'dort': 4, 'bes': 5,
         'alti': 6, 'yedi': 7, 'sekiz': 8, 'dokuz': 9, 'on': 10, 'yirmi': 20,
         'yigirmi': 20, 'otuz': 30, 'kirk': 40, 'elli': 50, 'altmis': 60,
         'yetmis': 70, 'seksen': 80, 'doksan': 90}
NUMBER_WORDS = set(UNITS) | {'yuz', 'bin', 'milyon'}
TOKEN_NUMBER = '|'.join(sorted(NUMBER_WORDS, key=len, reverse=True))


def word_number(text):
    """Parse complete Turkish cardinal phrases, including glued OCR tokens."""
    raw = fold(text)
    half = bool(re.search(r'\bbu[cç]uk\b', raw))
    raw = re.sub(r'\bbu[cç]uk\b', '', raw)
    raw = re.sub(r"[’'`\-]", '', raw)
    raw = re.sub(r'\s+', '', raw)
    if not raw:
        return None
    tokens = re.findall(TOKEN_NUMBER, raw)
    if ''.join(tokens) != raw:
        return None
    total = group = 0
    for token in tokens:
        if token in UNITS:
            group += UNITS[token]
        elif token == 'yuz':
            group = max(group, 1) * 100
        elif token == 'bin':
            total += max(group, 1) * 1000
            group = 0
        elif token == 'milyon':
            total = (total + max(group, 1)) * 1000000
            group = 0
    return total + group + (0.5 if half else 0)


def numeric_literal(text):
    raw = re.sub(r'\s*([.,])\s*',r'\1',fold(text).strip())
    if re.fullmatch(r'\d+(?:[.,]\d+)?\s+bucuk',raw):
        base=numeric_literal(re.sub(r'\s+bucuk$','',raw))
        return base+0.5 if base is not None else None
    if re.fullmatch(r'\d+', raw):
        return int(raw)
    # Ottoman/Turkish printed thousands grouping; a single decimal separator is
    # accepted only when it does not also look like a thousands group.
    if re.fullmatch(r'\d{1,3}(?:[.,\s]\d{3})+', raw):
        return int(re.sub(r'[.,\s]', '', raw))
    if re.fullmatch(r'\d+[.,]\d{1,2}', raw):
        return float(raw.replace(',', '.'))
    return word_number(raw)


def number_runs(text):
    """Return complete digit and Turkish cardinal runs with source offsets."""
    normalized = fold(text)
    pattern = rf'(?<!\w)(?:\d{{1,3}}(?:\s+\d{{3}})+|\d+(?:\s*[.,]\s*\d+)*|(?:{TOKEN_NUMBER})(?:\s*(?:{TOKEN_NUMBER}))*)(?:\s+bucuk)?(?!\w)'
    result = []
    for match in re.finditer(pattern, normalized):
        value = numeric_literal(match.group())
        if value is not None:
            result.append((value, match.start(), match.end(), match.group()))
    return result


DATE_FIELDS = ('year_ah', 'year_ah_end', 'month_ah', 'day_ah', 'year_rumi',
               'year_rumi_end', 'month_rumi', 'day_rumi', 'year_gregorian',
               'year_gregorian_end', 'month_gregorian', 'day_gregorian',
               'year_unspecified', 'year_unspecified_end', 'month_unspecified',
               'day_unspecified', 'year_abbreviated', 'date_precision',
               'date_parse_status', 'date_parse_basis') + tuple(f'{unit}_{family}_end' for family in ('ah','rumi','gregorian','unspecified') for unit in ('month','day'))

SOLAR_MONTHS = {
    'ocak': 1, 'kanunisani': 1, 'kanunusani': 1, 'kanunisani': 1,
    'subat': 2, 'mart': 3, 'nisan': 4, 'mayis': 5, 'haziran': 6,
    'temmuz': 7, 'agustos': 8, 'eylul': 9, 'ekim': 10,
    'tesrinievvel': 10, 'tesrinievvel': 10, 'kasim': 11,
    'tesrinisani': 11, 'aralik': 12, 'kanunievvel': 12,
    'kanunuevvel': 12,
}
LUNAR_MONTHS = {
    'muharrem': 1, 'muharremulharam': 1, 'safer': 2,
    'rebiulevvel': 3, 'rebiulevveli': 3, 'rabiulevvel': 3,
    'rebiulahir': 4, 'rebiulahiri': 4, 'rebiulahar': 4,
    'rabiulahir': 4, 'rabiulahar': 4, 'rebiyulahir': 4,
    'cemaziyelevvel': 5, 'cumadelula': 5, 'cemaziyelula': 5,
    'cemaziyelevveli': 5, 'cemaziyelahir': 6, 'cemaziyelahire': 6,
    'cumadelahire': 6, 'cumadelahiri': 6, 'receb': 7, 'recep': 7,
    'saban': 8, 'sabanulmuazzam': 8, 'ramazan': 9, 'sevval': 10,
    'zilkade': 11, 'zilka': 11, 'zilkaade': 11, 'zilkade': 11,
    'zilhicce': 12, 'zilhic': 12,
}


def month_hits(text):
    # Ignore punctuation in conventional Ottoman month spellings, retaining
    # offsets in a companion compact string so the nearest day/year can be read.
    compact_chars = []
    offsets = []
    for i, char in enumerate(text):
        if 'a' <= char <= 'z':
            compact_chars.append(char)
            offsets.append(i)
        elif char.isdigit():
            compact_chars.append('|')
            offsets.append(i)
    compact = ''.join(compact_chars)
    hits = []
    for family, lookup in (('ah', LUNAR_MONTHS), ('solar', SOLAR_MONTHS)):
        for spelling in sorted(lookup, key=len, reverse=True):
            for match in re.finditer(re.escape(spelling), compact):
                begin, end = offsets[match.start()], offsets[match.end()-1]+1
                if any(begin >= x[1] and end <= x[2] for x in hits):
                    continue
                hits.append((family, begin, end, lookup[spelling], spelling))
    return sorted(hits, key=lambda x: x[1])


def parse_date(raw, calendar_hint=''):
    result = {key: '' for key in DATE_FIELDS}
    text = fold(raw)
    editorial_digits=bool(re.search(r'\[\d\]\d{3}',text))
    text=re.sub(r'\[(\d)\](\d{3})',r'\1\2',text)
    result['date_parse_status'] = 'not_recorded' if not text else 'unresolved_literal'
    if not text:
        return result
    numbers = number_runs(text)
    # Explicit compact calendar notation may touch digits (H.15N1299). Only
    # dates use this lexical rule; the monetary parser never splits such tokens.
    known_spans={(n[1],n[2]) for n in numbers}
    for match in re.finditer(r'(?<!\d)\d{4}(?!\d)',text):
        if (match.start(),match.end()) not in known_spans:
            numbers.append((int(match.group()),match.start(),match.end(),match.group()))
    numbers.sort(key=lambda n:n[1])
    months = month_hits(text)
    years = [n for n in numbers if isinstance(n[0], int) and 1000 <= n[0] <= 2100]
    labels=list(re.finditer(r'(?<![a-z])([hrm])\s*\.\s*',text))
    dates = []
    for value, begin, end, token in years:
        prefix = text[max(0, begin-22):begin]
        suffix = text[end:end+30]
        preceding=[label for label in labels if label.end()<=begin]
        label=preceding[-1] if preceding else None
        next_label=next((label for label in labels if label.start()>begin),None)
        segment_begin=label.end() if label else 0
        segment_end=next_label.start() if next_label else len(text)
        local_months=[m for m in months if segment_begin<=m[1]<segment_end]
        nearest = min(local_months, key=lambda m: min(abs(begin-m[1]), abs(end-m[2])), default=None)
        distance = min(abs(begin-nearest[1]), abs(end-nearest[2])) if nearest else 1000
        if label and label.group(1)=='h':
            family,basis='ah','explicit_hijri_segment_label'
        elif label and label.group(1)=='r':
            family,basis='rumi','explicit_rumi_segment_label'
        elif label and label.group(1)=='m' and value>=1600:
            family,basis='gregorian','explicit_gregorian_segment_label'
        elif re.search(r'(?:h\.|h\s|hicri|hicriyye|hicriye|hicr[iî])\s*$', prefix) or 'hicri' in suffix:
            family, basis = 'ah', 'explicit_hijri_label'
        elif re.search(r'(?:r\.|r\s|rumi|maliye|mali)\s*$', prefix):
            family, basis = 'rumi', 'explicit_rumi_or_financial_label'
        elif value >= 1600:
            family, basis = 'gregorian', 'source_reported_modern_year_convention_no_conversion'
        elif nearest and nearest[0] == 'ah' and distance < 80:
            family, basis = 'ah', 'named_lunar_month'
        elif fold(calendar_hint) == 'ah' and len(years) == 1:
            family, basis = 'ah', 'accepted_explicit_calendar_hint'
        elif fold(calendar_hint) == 'rumi' and len(years) == 1:
            family, basis = 'rumi', 'accepted_explicit_calendar_hint'
        else:
            family, basis = 'unspecified', 'literal_year_calendar_unresolved'
        month = ''
        day = ''
        if nearest and distance < 50 and ((family == 'ah' and nearest[0] == 'ah') or (family in ('gregorian', 'rumi', 'unspecified') and nearest[0] == 'solar')):
            month = nearest[3]
            before = [n for n in numbers if n[2] <= nearest[1] and nearest[1]-n[2] < 12 and 1 <= n[0] <= 31]
            if before:
                day = before[-1][0]
            else:
                tail = text[nearest[2]:nearest[2]+65]
                ordinal = re.search(rf'((?:{TOKEN_NUMBER})(?:\s+(?:{TOKEN_NUMBER}))*)(?:inde|inda|unde|unda|sinde|sinda|isinde|isinda)(?:\W|$)', tail)
                if ordinal:
                    phrase = ordinal.group(1)
                    day = word_number(phrase) or ''
                    if day and not 1 <= day <= 31:
                        day = ''
                if 'gurre' in tail[:30]:
                    day = 1
        if family=='ah' and not month:
            compact=text[segment_begin:segment_end]
            code=re.search(r'(?<!\d)(\d{1,2})\s*(ra|za|ca|[msrcbsnlz])\s*(\d{3,4})(?!\d)',compact)
            if code:
                month={'m':1,'s':2,'ra':3,'r':4,'ca':5,'c':6,'b':7,'n':9,'l':10,'za':11,'z':12}.get(code.group(2),'')
                day=int(code.group(1))
        dates.append((family, value, month, day, begin, end, basis))
    # In an explicitly paired AH/Gregorian date, each family gets its own values.
    for family in ('ah', 'rumi', 'gregorian', 'unspecified'):
        selected = [d for d in dates if d[0] == family]
        if not selected:
            continue
        first = selected[0]
        result['year_' + family] = first[1]
        result['month_' + family] = first[2]
        result['day_' + family] = first[3]
        if len(selected) > 1 and selected[-1][1] != first[1]:
            result['year_' + family + '_end'] = selected[-1][1]
        elif len(selected) > 1:
            # Multiple same-year dates cannot be represented as one point date.
            result['day_' + family] = ''
            result['month_' + family] = ''
    abbreviated = [n for n in numbers if 100 <= n[0] < 1000 or (31<n[0]<100 and re.search(r'sene|yil|hicri',text[n[2]:n[2]+28]))]
    if abbreviated:
        result['year_abbreviated'] = abbreviated[0][0]
    if dates:
        is_interval = any(result.get('year_' + f + '_end') for f in ('ah','rumi','gregorian','unspecified')) or bool(re.search(r'arasi|arasinda|tarihleri|\d\s*[-–]\s*\d|\d{4}\s*/\s*\d{1,2}(?!\d)', text))
        if len(months)>1 and all(m[0]=='solar' for m in months) and len(years)==1 and re.search(r'[-–]',text[months[0][2]:months[-1][1]]):
            is_interval=True
            family=dates[0][0]
            result['month_'+family]=months[0][3]
            result['month_'+family+'_end']=months[-1][3]
            result['day_'+family]=''
        result['date_precision'] = 'interval' if is_interval else ('day' if any(result['day_'+f] for f in ('ah','rumi','gregorian','unspecified')) else ('month' if any(result['month_'+f] for f in ('ah','rumi','gregorian','unspecified')) else 'year'))
        result['date_parse_status'] = 'partial_literal_calendar_unresolved' if any(d[0] == 'unspecified' for d in dates) else 'parsed_literal'
        result['date_parse_basis'] = '; '.join(dict.fromkeys(d[6] for d in dates))
        if editorial_digits:
            result['date_parse_basis']+='; source_visible_editorial_leading_digit'
    elif abbreviated:
        result['date_parse_status'] = 'abbreviated_year_century_unresolved'
        result['date_parse_basis'] = 'literal_abbreviated_year_retained_no_completion'
    elif re.search(r'merkume|mezkur|ayni|o sene|sene\s*i\s*merk', text):
        result['date_parse_status'] = 'relative_date_unresolved'
    return result


MONEY_FIELDS = ('salary_level', 'salary_increment', 'salary_reduction', 'allowance_amount',
                'acting_allowance_amount', 'pension_amount', 'family_pension_amount',
                'dismissal_pay_amount', 'fee_amount', 'liability_amount', 'other_compensation_amount', 'other_amount',
                'amount_numeric', 'currency', 'pay_frequency', 'pay_component',
                'amount_parse_status', 'amount_parse_basis')


def parse_money(raw, context='', component_hint='', frequency_hint='', kind_hint='', currency_hint=''):
    result = {key: '' for key in MONEY_FIELDS}
    text = fold(raw)
    context = fold(context)
    explicit_measure=fold(kind_hint) or fold(component_hint)
    if explicit_measure in ('salary_level','salary','salary_increment','salary_reduction','acting_allowance','allowance','pension','dismissal_pay','travel_allowance','liability','family_pension','other_compensation'):
        result['pay_component']='salary' if explicit_measure=='salary_level' else explicit_measure
    result['amount_parse_status'] = 'not_recorded' if not text else 'unresolved_literal'
    if not text:
        if result['pay_component']:
            result['amount_parse_status']='unquantified_explicit_component'
        return result
    if re.search(r'(?:kadarinin|ust\s*taraf|fazlasinin|yarisinin|nispetinde|nisbetinde)',text) or (re.search(r'kadarinin|ust\s*taraf',context) and len(number_runs(text))!=1):
        result['amount_parse_status']='payment_formula_not_realized_amount'
        result['pay_component']='payment_formula'
        return result
    if len(number_runs(text))==1 and re.search(re.escape(number_runs(text)[0][3])+r'\s*(?:kurus|gurus)?\s*kadarinin',context):
        result['amount_parse_status']='payment_formula_threshold_not_amount'
        result['pay_component']='payment_formula'
        return result
    currency_text=fold(currency_hint) or text
    if not currency_hint and not re.search(r'kur\s*us|gur[uû]?s|lira|alt[ui]n|altun',text):
        # A unit immediately after this literal amount is explicit. Do not take
        # a different component's currency from the whole evidence sentence.
        hit=context.find(text)
        currency_text=context[hit+len(text):hit+len(text)+22] if hit>=0 else ''
    if re.search(r'kur\s*us|gur[uû]?s|guru\s*s', currency_text):
        result['currency'] = 'kuruş'
    elif re.search(r'\blira', currency_text):
        result['currency'] = 'lira'
    elif re.search(r'\balt[ui]n|altun', currency_text):
        result['currency'] = 'gold_literal_unit'
    frequency = fold(frequency_hint)
    # Only period words explicitly present in the quoted clause are used.
    if re.search(r'aylik|sehri|mahiyye|mahiyye', frequency+' '+context):
        result['pay_frequency'] = 'monthly'
    elif re.search(r'yevmi|gunluk', frequency+' '+context):
        result['pay_frequency'] = 'daily'
    elif re.search(r'senevi|yillik', frequency+' '+context):
        result['pay_frequency'] = 'annual'
    elif re.search(r'saatde|saatlik', frequency+' '+context):
        result['pay_frequency'] = 'hourly'
    if re.search(r'ayni\s+(?:maas|miktar)|o\s+miktar|aynen\s+veril|maas\s*inin\s*aynen', text):
        result['amount_parse_status'] = 'inherited_amount_unresolved'
        return result
    nums = number_runs(text)
    # Numbers in dates or percentages are not standalone monetary amounts.
    if '%' in text or re.search(r'yuzde', text):
        result['amount_parse_status'] = 'percentage_not_amount'
        return result
    if not nums:
        return result
    monetary_context = text if any(w in text for w in ('maas','kurus','gurus','zam','tenzil','harcirah','tazmin','zimmet','tekaud')) else context
    component = fold(component_hint)
    kind = fold(kind_hint)
    final_level=bool(re.search(r'(?:kurus|gurus)[ae]\b',text) and re.search(r'tenzil|iblag|yuksel|cikar',context))
    if kind=='salary_level':
        slot,label='salary_level','salary'
    elif kind=='salary_increment':
        slot,label='salary_increment','salary_increment'
    elif kind=='salary_reduction':
        slot,label='salary_reduction','salary_reduction'
    elif kind=='family_pension' or component=='family_pension':
        slot,label='family_pension_amount','family_pension'
    elif kind=='pension' or component=='pension':
        slot,label='pension_amount','pension'
    elif kind=='acting_allowance' or component=='acting_allowance':
        slot,label='acting_allowance_amount','acting_allowance'
    elif kind=='dismissal_pay' or component=='dismissal_pay':
        slot,label='dismissal_pay_amount','dismissal_pay'
    elif kind in ('allowance','travel_allowance'):
        slot,label='allowance_amount',kind
    elif kind=='liability':
        slot,label='liability_amount','liability'
    elif kind=='other_compensation':
        slot,label='other_compensation_amount','other_compensation'
    elif re.search(r'varidat|hasilat|gelir|r[uü]sum',context) and not re.search(r'maas|ucret|aylik|tahsisat',context):
        slot,label='other_amount','institutional_revenue_not_personal_pay'
    elif re.search(r'mazuliyet|mazuliyyet|kadro[ -]*haric|mazul maas',context) and kind not in ('salary_increment','salary_reduction'):
        slot,label='dismissal_pay_amount','dismissal_pay'
    elif final_level:
        slot,label='salary_level','salary'
    elif kind=='family_pension' or component=='family_pension':
        slot, label = 'family_pension_amount', 'family_pension'
    elif kind=='pension' or component=='pension':
        slot, label = 'pension_amount', 'pension'
    elif kind=='acting_allowance' or component=='acting_allowance':
        slot, label = 'acting_allowance_amount', 'acting_allowance'
    elif kind=='dismissal_pay' or component=='dismissal_pay':
        slot, label = 'dismissal_pay_amount', 'dismissal_pay'
    elif kind=='other_compensation' or component=='other_compensation':
        slot, label = 'other_compensation_amount', 'other_compensation'
    elif re.search(r'zimmet|borc|tazmin\s+et|geri\s+ode|tahsil\s+edil', monetary_context) or component in ('liability','debt','fine') or kind in ('liability','debt','fine'):
        slot, label = 'liability_amount', 'liability'
    elif re.search(r'harcirah|harc-i\s*rah|yolluk|tahsisat|tazminat|masraf|bedel', monetary_context) or component in ('allowance','travel_allowance','allowance/travel'):
        slot, label = 'allowance_amount', 'allowance'
    elif re.search(r'tekaud|emekl|pension', monetary_context) or component == 'pension':
        slot, label = 'pension_amount', 'pension'
    elif component == 'fee' or kind == 'fee':
        slot, label = 'fee_amount', 'fee'
    elif re.search(r'\bzamm?[iy]|zam\s|ilave', text) or kind in ('salary_increment','increment','increase_amount'):
        slot, label = 'salary_increment', 'salary_increment'
    elif re.search(r'tenzil\s+mik|indirim\s+mik|eksilt|tenzil(?:i|en)\b', text) or kind in ('salary_reduction','reduction','decrease_amount'):
        slot, label = 'salary_reduction', 'salary_reduction'
    elif component in ('salary','salary_level') or re.search(r'maas|aylik|sehri', monetary_context) or kind == 'salary_level':
        slot, label = 'salary_level', 'salary'
    else:
        slot, label = 'other_amount', 'unclassified_amount'
    if len(nums) == 1:
        value = nums[0][0]
        # A source sentence stating a change BY x is an increment/reduction even
        # if an earlier model called it salary. A level TO x remains a level.
        around = context
        token = re.escape(nums[0][3])
        if slot == 'salary_level' and not kind and re.search(token + r'\s*(?:kurus|gurus)?\s*(?:zam|ilave|artiril|arttir|artir)', around):
            slot, label = 'salary_increment', 'salary_increment'
        if slot == 'salary_level' and not kind and re.search(token + r'\s*(?:kurus|gurus)?\s*(?:dusur|eksilt|tenzil)', around):
            slot,label='salary_reduction','salary_reduction'
        result[slot] = result['amount_numeric'] = value
        result['pay_component'] = label
        result['amount_parse_status'] = 'parsed_literal'
        result['amount_parse_basis'] = 'complete_digit_or_turkish_cardinal_literal; source_clause_component'
        return result
    # Explicit "x zam ... y ... iblağ" retains change and resulting level.
    if len(nums) == 2 and re.search(r'zam|ilave', text) and re.search(r'iblag|cikar|yuksel|altmis|olmus', text):
        result['salary_increment'], result['salary_level'] = nums[0][0], nums[1][0]
        result['pay_component'] = 'salary_change_and_resulting_level'
        result['amount_parse_status'] = 'parsed_explicit_change_and_result'
        result['amount_parse_basis'] = 'two_literal_amounts_with_explicit_increment_and_result_clause'
    else:
        result['amount_parse_status'] = 'multiple_amounts_unresolved'
        result['pay_component'] = label
    return result
