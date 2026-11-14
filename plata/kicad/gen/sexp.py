"""Минимальный разбор и запись S-выражений KiCad."""


class Q(str):
    """Строка, которую пишем в кавычках."""


def parse(text):
    pos, n = 0, len(text)
    stack, cur = [], []
    while pos < n:
        c = text[pos]
        if c in ' \t\r\n':
            pos += 1
        elif c == '(':
            stack.append(cur)
            cur = []
            pos += 1
        elif c == ')':
            done = cur
            cur = stack.pop()
            cur.append(done)
            pos += 1
        elif c == '"':
            pos += 1
            buf = []
            while text[pos] != '"':
                if text[pos] == '\\':
                    pos += 1
                    buf.append({'n': '\n', 't': '\t'}.get(text[pos], text[pos]))
                else:
                    buf.append(text[pos])
                pos += 1
            pos += 1
            cur.append(Q(''.join(buf)))
        else:
            start = pos
            while pos < n and text[pos] not in ' \t\r\n()"':
                pos += 1
            cur.append(text[start:pos])
    return cur[0] if len(cur) == 1 else cur


def _atom(a):
    if isinstance(a, Q):
        return '"' + a.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'
    if isinstance(a, float):
        s = ('%.4f' % a).rstrip('0').rstrip('.')
        return '0' if s in ('-0', '') else s
    return str(a)


def dump(e, ind=0):
    if not isinstance(e, list):
        return _atom(e)
    simple = all(not isinstance(x, list) for x in e)
    if simple:
        return '(' + ' '.join(_atom(x) for x in e) + ')'
    pad = '\t' * (ind + 1)
    out = '(' + ' '.join(_atom(x) for x in e if not isinstance(x, list))
    for x in e:
        if isinstance(x, list):
            out += '\n' + pad + dump(x, ind + 1)
    return out + '\n' + '\t' * ind + ')'


def find(e, key):
    for x in e:
        if isinstance(x, list) and x and x[0] == key:
            return x
    return None


def findall(e, key):
    return [x for x in e if isinstance(x, list) and x and x[0] == key]
