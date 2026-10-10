"""Graph builder on top of bp_t3d: declare nodes and pins, link(a, b), emit paste text.

Links are written on both ends, so the pasted graph never depends on one-sided LinkedTo.
"""
from bp_t3d import G, head, comment_box, T, F, TGT


class Pin:
    def __init__(self, node, name, cat, sub="None", subcat="", out=False, hidden=False, adv=False, extra=""):
        self.node, self.name, self.cat, self.sub, self.subcat = node, name, cat, sub, subcat
        self.out, self.hidden, self.adv, self.extra, self.id, self.links = out, hidden, adv, extra, G(), []
        self.member_ref = ""   # e.g. MemberParent=...,MemberName="ReceiveTick" for an event's OutputDelegate
        self.container = "None"  # "Array" for array pins
        self.wrapper = False     # TSubclassOf function parameters
        self.ref = False         # by-reference parameter
        self.const = False

    def text(self):
        l = ("LinkedTo=(" + "".join(f"{p.node.name} {p.id}," for p in self.links) + "),") if self.links else ""
        d = 'Direction="EGPD_Output",' if self.out else ""
        return (f'   CustomProperties Pin (PinId={self.id},PinName="{self.name}",{self.extra}{d}'
                f'PinType.PinCategory="{self.cat}",PinType.PinSubCategory="{self.subcat}",'
                f'PinType.PinSubCategoryObject={self.sub},'
                + T.replace("PinType.PinSubCategoryMemberReference=()",
                            f"PinType.PinSubCategoryMemberReference=({self.member_ref})")
                   .replace("PinType.ContainerType=None", f"PinType.ContainerType={self.container}")
                   .replace("PinType.bIsUObjectWrapper=False", f"PinType.bIsUObjectWrapper={self.wrapper}")
                   .replace("PinType.bIsReference=False", f"PinType.bIsReference={self.ref}")
                   .replace("PinType.bIsConst=False", f"PinType.bIsConst={self.const}") + l
                + F % ("True" if self.hidden else "False", "True" if self.adv else "False"))


class Node:
    def __init__(self, graph, klass, name, x, y, comment="", body=()):
        self.klass, self.name, self.x, self.y, self.comment, self.body = klass, name, x, y, comment, list(body)
        self.pins = {}
        graph.nodes.append(self)

    def pin(self, name, cat, **kw):
        p = Pin(self, name, cat, **kw)
        self.pins[name] = p
        return p

    def __getitem__(self, name):
        return self.pins[name]

    def text(self):
        return head(self.klass, self.name, self.x, self.y, self.comment, self.body) + \
            [p.text() for p in self.pins.values()] + ["End Object"]


class Graph:
    def __init__(self):
        self.nodes, self.extra, self.boxes = [], [], []

    def link(self, a, b):
        a.links.append(b)
        b.links.append(a)

    def box(self, name, x, y, w, h, text):
        self.boxes.append([name, x, y, w, h, text])

    def text(self):
        out = list(self.extra)
        for b in self.boxes:
            out += comment_box(*b)
        for n in self.nodes:
            out += n.text()
        return out

    # ---- readable layout -------------------------------------------------------------------------------------
    @staticmethod
    def _size(n):
        """Conservative on-screen size of a node (the editor does not export it): one ~30 px row per visible pin on the
        longer side (the exec pins share the header row), ~7.5 px per character of the widest input + output label,
        room for default-value boxes, and the comment bubble above the node (as wide as its text)."""
        import re as _re
        vis = [p for p in n.pins.values() if not p.hidden and not (p.adv and not p.links)]
        ins = [p for p in vis if not p.out and p.cat != "exec"]
        outs = [p for p in vis if p.out and p.cat != "exec"]
        execs = any(p.cat == "exec" for p in vis)
        label = lambda p: len(_re.sub(r"(?<!^)([A-Z])", r" \1", p.name))   # CamelCase -> "Camel Case"
        win = max([label(p) + (12 if ("DefaultValue" in p.extra and not p.links) else 0) for p in ins] + [0])
        wout = max([label(p) for p in outs] + [0])
        title = 0
        for b in n.body:
            m = _re.search(r'MemberName="([^"]+)"', b)
            if m:
                title = len(_re.sub(r"(?<!^)([A-Z])", r" \1", m.group(1)))
        w = max(160, int(7.5 * max(title + 6, win + wout + 6)) + 40)
        rows = max(len(ins), len(outs)) + (1 if execs else 0)
        h = 44 + 30 * max(rows, 1)
        if n.comment:
            w = max(w, int(7 * len(n.comment)) + 40)
            h += 40
        return w, h

    def layout(self, col_gap=110, row_gap=46, box_gap=260, pad=80):
        """Re-place every node so nothing overlaps and execution flows left to right.

        Each node belongs to the comment box that contained its original position (the smallest one), or to a
        trailing "rest" group. Inside a group, a node's column is its longest-path depth over the links inside the
        group (data producers to the left of their consumers, exec chains left to right); nodes in a column are
        ordered by the average row of what feeds them. Groups are stacked top to bottom in their original order and
        each box is resized to enclose its nodes."""
        def contains(b, n):
            return b[1] <= n.x <= b[1] + b[3] and b[2] <= n.y <= b[2] + b[4]

        groups = {i: [] for i in range(len(self.boxes))}
        home = {}
        for n in self.nodes:
            inside = [i for i, b in enumerate(self.boxes) if contains(b, n)]
            if inside:
                home[id(n)] = min(inside, key=lambda i: self.boxes[i][3] * self.boxes[i][4])
        for _ in range(8):   # a node outside every box joins the box of a node it is linked to
            for n in self.nodes:
                if id(n) in home:
                    continue
                for p in n.pins.values():
                    hit = [home[id(q.node)] for q in p.links if id(q.node) in home]
                    if hit:
                        home[id(n)] = hit[0]
                        break
        rest = []
        for n in self.nodes:
            (groups[home[id(n)]] if id(n) in home else rest).append(n)
        order = sorted(groups, key=lambda i: (self.boxes[i][2], self.boxes[i][1]))
        y_cursor = min([b[2] for b in self.boxes] + [0])
        x0 = min([b[1] for b in self.boxes] + [0])
        for gi in order + [None]:
            members = groups[gi] if gi is not None else rest
            if not members:
                continue
            ids = set(id(n) for n in members)
            preds = {id(n): [] for n in members}
            for n in members:
                for p in n.pins.values():
                    if p.out:
                        for q in p.links:
                            if id(q.node) in ids and q.node is not n:
                                preds[id(q.node)].append(n)
            depth = {id(n): 0 for n in members}
            for _ in range(len(members)):
                changed = False
                for n in members:
                    for m in preds[id(n)]:
                        if depth[id(m)] + 1 > depth[id(n)] and depth[id(m)] + 1 < len(members):
                            depth[id(n)] = depth[id(m)] + 1
                            changed = True
                if not changed:
                    break
            cols = {}
            for n in members:
                cols.setdefault(depth[id(n)], []).append(n)
            top = y_cursor + pad + 40
            x = x0 + pad
            bottom = top
            row_of = {}
            for c in sorted(cols):
                col = cols[c]
                col.sort(key=lambda n: (sum(row_of.get(id(m), n.y) for m in preds[id(n)]) / len(preds[id(n)])) if preds[id(n)] else n.y)
                width = max(self._size(n)[0] for n in col)
                y = top
                for n in col:
                    w, h = self._size(n)
                    n.x, n.y = int(x), int(y + (40 if n.comment else 0))
                    row_of[id(n)] = y
                    y += h + row_gap
                bottom = max(bottom, y)
                x += width + col_gap
            if gi is not None:
                b = self.boxes[gi]
                b[1], b[2], b[3], b[4] = int(x0), int(y_cursor), int(x - x0 + pad), int(bottom - y_cursor + pad)
            y_cursor = bottom + pad + box_gap
