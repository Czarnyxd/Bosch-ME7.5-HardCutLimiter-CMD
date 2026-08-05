#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, shutil, sys
from pathlib import Path

RPM_VALUES=[6400,6500,6600,6700,6800,6900,7000,7100,7200]
ECU_INDEX=5
ECU_NAME='BOSCH VAG ME7.5 1.8T 20V'

def hx(s: str) -> bytes:
    """Parse hex exactly like the original VB code.

    The source splits textbox contents into tokens and evaluates each token
    using Conversion.Val("&H" + token). Therefore a token such as "0"
    is a valid single byte 0x00, even though bytes.fromhex("0") rejects it.
    """
    text = str(s).strip()
    if not text:
        return b""
    tokens = text.replace(",", " " ).split()
    if len(tokens) > 1:
        try:
            return bytes(int(token, 16) & 0xFF for token in tokens)
        except ValueError as exc:
            raise ValueError(f"invalid hex token in {s!r}") from exc
    token = tokens[0]
    if len(token) <= 2:
        try:
            return bytes([int(token, 16) & 0xFF])
        except ValueError as exc:
            raise ValueError(f"invalid hex byte {s!r}") from exc
    if len(token) % 2:
        raise ValueError(f"odd-length packed hex string {s!r}")
    try:
        return bytes.fromhex(token)
    except ValueError as exc:
        raise ValueError(f"invalid packed hex string {s!r}") from exc


def _ascii_strings(data: bytes, min_len: int = 4):
    """Return printable ASCII strings with their file offsets."""
    import re
    pattern = rb"[\x20-\x7E]{%d,}" % min_len
    return [(m.start(), m.group().decode("ascii", errors="ignore").strip())
            for m in re.finditer(pattern, data)]


def read_ecu_info(data: bytes) -> dict[str, str]:
    """Extract common Bosch/VAG ME7.5 identification fields from the BIN.

    The routine uses only data present in the firmware and does not require
    ME7Info.exe. It is deliberately conservative: unknown fields remain
    ``Not found`` rather than being guessed.
    """
    import re

    strings = _ascii_strings(data)
    joined = "\n".join(text for _, text in strings)
    upper = joined.upper()

    info = {
        "VAG part number": "Not found",
        "VAG software": "Not found",
        "Bosch hardware": "Not found",
        "Bosch software": "Not found",
        "Engine ID": "Not found",
        "Bootrom": "Not found",
        "EPK": "Not found",
    }

    # Typical VAG numbers: 06A906032DR, 8N0906018BR, 8E0909518AN.
    vag = re.search(r"\b(?:0?[0-9A-Z]{2,3}[0-9A-Z]{6,9})\b", upper)
    preferred = re.findall(r"\b(?:06A|8N0|8E0|4B0|8L0)[0-9A-Z]{7,9}\b", upper)
    if preferred:
        info["VAG part number"] = preferred[0]
    elif vag and any(x in vag.group(0) for x in ("906", "907", "909")):
        info["VAG part number"] = vag.group(0)

    # Bosch HW/SW identifiers are normally stored as 10-digit ASCII strings.
    bosch_hw = re.search(r"\b0261[0-9]{6}\b", joined)
    bosch_sw = re.search(r"\b1037[0-9]{6}\b", joined)
    if bosch_hw:
        info["Bosch hardware"] = bosch_hw.group(0)
    if bosch_sw:
        info["Bosch software"] = bosch_sw.group(0)

    # EPK usually starts with a calibration/version prefix and contains ME7.5.
    for _, text in strings:
        if "ME7.5" in text.upper() and ("/" in text or len(text) > 18):
            info["EPK"] = text[:120]
            break

    # Engine strings commonly look like: 1.8L R4/5VT, 1.8T, 20VT.
    engine_patterns = [
        r"\b[0-9]\.[0-9]L\s+R[0-9]/[0-9A-Z]+\b",
        r"\b1\.8T(?:\s*20V?T?)?\b",
        r"\b[0-9]\.[0-9]L\s+[A-Z0-9/ -]{2,20}\b",
    ]
    for pattern in engine_patterns:
        m = re.search(pattern, joined, re.IGNORECASE)
        if m:
            info["Engine ID"] = m.group(0).strip()
            break

    # Bootrom formats seen in ME7 files include 05.12 and similar values.
    boot = re.search(r"\b0[0-9]\.[0-9]{2}\b", joined)
    if boot:
        info["Bootrom"] = boot.group(0)

    # VAG software version is usually a four-digit ASCII value near the PN.
    if info["VAG part number"] != "Not found":
        pn = info["VAG part number"]
        for _, text in strings:
            pos = text.upper().find(pn)
            if pos >= 0:
                neighborhood = text[max(0, pos - 20):pos + len(pn) + 40]
                versions = re.findall(r"(?<![0-9])[0-9]{4}(?![0-9])", neighborhood)
                if versions:
                    info["VAG software"] = versions[-1]
                    break

    return info

def find_all(data:bytes, pat:bytes):
 p=0; out=[]
 while True:
  p=data.find(pat,p)
  if p<0:return out
  out.append(p);p+=1

def _first_rule(rules: dict, ecu: int, hex_value: str):
    for d in rules['detections']:
        if d['ecu'] == ecu and d['hex'].upper() == hex_value.upper():
            return d
    return None


def _use_detection(data: bytes, rule: dict | None):
    if not rule:
        return None
    hits = find_all(data, hx(rule['hex']))
    if not hits:
        return None
    addr = hits[0] + int(rule['adjust'])
    if addr < 0 or addr >= len(data):
        return None
    return addr, hits


def detect_me75(data: bytes, rules: dict):
    """Mirror the original ME7.5 if/else-if detection order.

    The original application does not collect every matching signature. It
    stops at the first successful signature in each fallback chain and keeps
    Label8 and Label26 as two independent type flags.
    """
    labels = {f'Label{i}': 0 for i in range(1, 40)}
    state = {'Label8': '', 'Label26': '', 'TextBox2': ''}
    found = []

    # ECU protocol marker: used only to validate ME7.5, not as the limiter base.
    proto = _use_detection(data, _first_rule(rules, 5, '4D45372E35'))
    if not proto:
        return labels, state, found
    found.append(('Protocol', proto[0], '4D45372E35', len(proto[1]), None))

    # Label6 / limiter base fallback chain.
    chain6 = [
        ('B004FFFF0700', 'Label26', 'type7'),
        ('AB1A01000400', 'Label8', 'type3'),
        ('C012FFFF', 'Label8', 'type2'),
        ('B004FFFF', 'Label8', 'type1'),
        ('C012ABFFFFFF', 'Label8', 'type5'),
    ]
    for sig, state_key, state_value in chain6:
        rule = _first_rule(rules, 5, sig)
        result = _use_detection(data, rule)
        if result:
            addr, hits = result
            labels['Label6'] = addr
            state[state_key] = state_value
            found.append(('Label6', addr, sig, len(hits), state_value))
            break

    # Label7 direct signature.
    result = _use_detection(data, _first_rule(rules, 5, '08085572'))
    if result:
        addr, hits = result
        labels['Label7'] = addr
        found.append(('Label7', addr, '08085572', len(hits), None))

    # Label9 fallback chain. Type assignments match the original source.
    chain9 = [
        ('ABFF0096', None, None),
        ('ABFFFFFF0500', 'Label26', 'type3'),
        ('004058025802', 'Label26', 'type6'),
        ('00100400070046', 'Label8', 'type4'),
        ('0400070046', None, None),  # HexSearch10 branch
        # The second identical signature uses a different search helper in the
        # original. The extracted rule set cannot distinguish helper semantics;
        # only use this as a fallback if the first rule did not resolve.
        ('ABFF007D05', None, None),
        ('ABFFFFFFFFFF0000', None, None),
        ('05000600FFFF', None, None),
    ]
    for sig, state_key, state_value in chain9:
        rule = _first_rule(rules, 5, sig)
        result = _use_detection(data, rule)
        if result:
            addr, hits = result
            labels['Label9'] = addr
            if state_key:
                state[state_key] = state_value
            found.append(('Label9', addr, sig, len(hits), state_value))
            break

    # Label13: first signature wins; C0... is only a fallback.
    for sig in ('A0A0A08080', 'C0C0C08080'):
        result = _use_detection(data, _first_rule(rules, 5, sig))
        if result:
            addr, hits = result
            labels['Label13'] = addr
            found.append(('Label13', addr, sig, len(hits), None))
            break

    # Label14 exists only for Label8 type1.
    if state['Label8'] == 'type1':
        result = _use_detection(data, _first_rule(rules, 5, 'FA009F24'))
        if result:
            addr, hits = result
            labels['Label14'] = addr
            found.append(('Label14', addr, 'FA009F24', len(hits), None))

    return labels, state, found


def detect(data: bytes, rules: dict):
    return detect_me75(data, rules)


def _normalize_ecu_name(value: str) -> str:
    """Normalize Label4 text from the decompiled application.

    The source contains small spelling/spacing differences, for example two
    spaces before ``Detected`` in the R32 branch. Exact string matching made
    unrelated ECU branches appear unconditional.
    """
    import re
    value = re.sub(r"\s+", " ", value.strip()).upper()
    value = value.replace(" 20 VT", " 20V")
    value = value.replace(" / R32 DETECTED", " / R32 DETECTED")
    return value


def applies(p, ecu_name, rpm_idx, state):
    import re

    conditions = p.get('conditions') or []
    c = ' '.join(conditions)

    # Reproduce Label4 ECU guards. Any patch that explicitly names one or more
    # Label4 values belongs only to those ECU families. This also handles OR
    # branches and harmless spacing differences present in the decompiled code.
    label4_values = re.findall(r'Label4\.Text,\s*"([^"]*)"', c)
    if label4_values:
        selected = _normalize_ecu_name(ecu_name + ' Detected')
        allowed = {_normalize_ecu_name(value) for value in label4_values}
        if selected not in allowed:
            return False

    # Label16 is used by the original app for the RS3-specific secondary path.
    # It must never be treated as an unconditional operation for ME7.5.
    label16_values = re.findall(r'Label16\.Text,\s*"([^"]*)"', c)
    if label16_values:
        selected_label16 = ''
        results = [selected_label16 == value for value in label16_values]
        if '||' in c:
            if not any(results):
                return False
        elif not all(results):
            return False

    if p.get('rpm_index') is not None and p['rpm_index'] != rpm_idx:
        return False

    comparisons = []
    for key in ('Label8', 'Label26', 'TextBox2'):
        for value in re.findall(rf'{key}\.Text,\s*"([^"]*)"', c):
            comparisons.append((key, value))
    if comparisons:
        results = [state.get(key, '') == value for key, value in comparisons]
        if '||' in c:
            if not any(results):
                return False
        elif not all(results):
            return False
    return True

def build_ops(data,rules,rpm_idx,labels,state):
 name=ECU_NAME; ops=[]; skipped=[]
 for n,p in enumerate(rules['patches'],1):
  if not applies(p,name,rpm_idx,state):continue
  base=labels.get(p['label'],0)
  if not base:
   skipped.append((n,p,'missing '+p['label']));continue
  off=base+int(p['offset']); new=hx(p['data'])
  if off<0 or off+len(new)>len(data):
   skipped.append((n,p,'outside file'));continue
  ops.append((off,new,n,p))
 # Keep exact source order. Overlapping writes are intentional in the original code.
 return ops,skipped

def _display_variant(state: dict) -> str:
    for key in ('Label26', 'Label8', 'TextBox2'):
        value = state.get(key, '')
        if value:
            if value.lower().startswith('type'):
                return 'Type ' + value[4:]
            return value
    return 'Standard'


def _signature_display_name(label: str) -> str:
    return {
        'Protocol': 'ECU protocol',
        'Label6': 'RPM tables',
        'Label7': 'HardCut data',
        'Label9': 'Limiter block',
        'Label13': 'Control data',
        'Label14': 'Secondary limit',
    }.get(label, label)


def main():
 ap=argparse.ArgumentParser(description='Bosch ME7.5 1.8T HardCut limiter CMD')
 ap.add_argument('bin',type=Path)
 ap.add_argument('--rpm',type=int,choices=RPM_VALUES)
 ap.add_argument('--detect',action='store_true')
 ap.add_argument('--output',type=Path)
 ap.add_argument('--force',action='store_true',help='allow ambiguous signature matches')
 a=ap.parse_args()
 if not a.bin.is_file():sys.exit('ERROR: input file not found')
 rules=json.loads((Path(__file__).with_name('rules.json')).read_text())
 data=a.bin.read_bytes()
 print('='*68);print('             BOSCH ME7.5 HARD CUT LIMITER CMD');print('='*68)
 print(f'Version          : 1.5 ME7.5 ONLY')
 print(f'Input file       : {a.bin.name}\nFile size        : {len(data)} bytes')

 ecu_info = read_ecu_info(data)
 print('\n' + '-'*60)
 print('ECU INFORMATION')
 print('-'*60)
 for key, value in ecu_info.items():
  print(f'{key:<17}: {value}')
 print('-'*60)

 labels,state,found=detect(data,rules)
 if not found:sys.exit('ERROR: ECU/HardCut signatures not found. Use an original supported BIN.')
 variant_raw = ', '.join(f'{k}={v}' for k,v in state.items() if v) or 'standard'
 variant_display = _display_variant(state)

 print('\n' + '-'*60)
 print('ECU DETECTION')
 print('-'*60)
 print(f'ECU protocol     : {ECU_NAME}')
 print(f'HardCut variant  : {variant_display}')
 print(f'Detection status : Supported')
 print(f'Patterns found   : {len(found)}')
 print('\nDetected locations:')
 for lab,addr,sig,count,t in found:
  extra=f' ({count} matches)' if count>1 else ''
  print(f'  {_signature_display_name(lab):<18}: 0x{addr:06X}{extra}')
 print('-'*60)

 if any(count>1 for _,_,_,count,_ in found) and not a.force:
  print('\nWARNING: at least one signature is ambiguous; original program uses first match.')
  print('Use --force only after checking displayed addresses.')
  if not a.detect:sys.exit(2)
 if a.detect:return
 rpm=a.rpm
 if rpm is None:
  print('\nSelect HardCut RPM:')
  for i,v in enumerate(RPM_VALUES,1):print(f'  {i}. {v} RPM')
  try:rpm=RPM_VALUES[int(input('Selection: ').strip())-1]
  except:sys.exit('ERROR: invalid RPM selection')
 idx=RPM_VALUES.index(rpm)
 ops,skipped=build_ops(data,rules,idx,labels,state)
 if not ops:sys.exit('ERROR: no applicable patch operations found for this ECU/RPM.')
 out=a.output or a.bin.with_name(f'{a.bin.stem}_HARDCUT_{rpm}{a.bin.suffix or ".bin"}')
 if out.resolve()==a.bin.resolve():sys.exit('ERROR: output may not overwrite original file')
 mod=bytearray(data); log=[]
 for off,new,n,p in ops:
  old=bytes(mod[off:off+len(new)])
  mod[off:off+len(new)]=new
  log.append((off,old,new,p['label'],p['offset'],p['textbox']))
 out.write_bytes(mod)
 logpath=out.with_suffix(out.suffix+'.log.txt')
 with logpath.open('w') as f:
  f.write(f'HardCut ME7.5 port\nInput: {a.bin}\nOutput: {out}\nECU: {ECU_NAME}\nRPM: {rpm}\nVariant: {variant_raw}\n\n')
  for i,(off,old,new,lab,rel,tb) in enumerate(log,1):f.write(f'{i:03d} 0x{off:06X} {lab}{rel:+d} {tb}  ORI: {old.hex(" ").upper()}  MOD: {new.hex(" ").upper()}\n')

 print('\n' + '-'*60)
 print('MODIFICATION COMPLETE')
 print('-'*60)
 print(f'HardCut RPM      : {rpm} RPM')
 print(f'Modified blocks  : {len(log)}')
 print(f'Output file      : {out}')
 print(f'Modification log : {logpath}')
 print('Checksum status  : Not corrected')
 if skipped:print(f'Skipped rules    : {len(skipped)}')
 print('-'*60)
 print('Run the proper checksum tool before flashing.')

if __name__=='__main__':main()
